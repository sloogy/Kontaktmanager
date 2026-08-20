"""Harte Regeln und Kapazitaet.

Trennung mit Absicht: Die RuleEngine entscheidet, ob eine Person ueberhaupt
vorgeschlagen werden DARF und wie viel soziale Kapazitaet gerade uebrig ist.
Die Gewichtung, WER zuerst kommt, macht ausschliesslich die RotationEngine.

Die Kapazitaetsgrenzen sind die weiterentwickelten Einstellungen des alten
Kontaktmanagers (max. Tage pro Woche, max. Wochenenden pro Monat, erlaubte
Wochentage). Neu ist, dass sie nicht mehr nur gespeichert, sondern wirksam
werden - und dass sie Vorschlaege abschwaechen statt sie zu verbieten.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from freizeitmanager.database import db
from freizeitmanager.database.models import (KIND_MEET, KIND_MEET_LONG,
                                             ROTATING_STATUSES, Contact,
                                             Interaction, PlannedActivity,
                                             INTERACTION_KINDS, RotationSnooze,
                                             STATUS_PAUSED)
from freizeitmanager.logic.freshness import is_substantial

MEETING_KINDS = {KIND_MEET, KIND_MEET_LONG}
SUBSTANTIAL_KINDS = {k for k in INTERACTION_KINDS if is_substantial(k)}

# Ausschlussgruende - werden fuer die "Warum?"-Erklaerung mitgefuehrt.
BLOCK_STATUS = "status"
BLOCK_PAUSED = "paused"
BLOCK_SNOOZED = "snoozed"
BLOCK_PLANNED = "planned"
BLOCK_COOLDOWN = "cooldown"

BLOCK_LABELS = {
    BLOCK_STATUS: "nicht in der Rotation",
    BLOCK_PAUSED: "pausiert",
    BLOCK_SNOOZED: "zurueckgestellt",
    BLOCK_PLANNED: "Termin ist bereits geplant",
    BLOCK_COOLDOWN: "gerade erst Kontakt gehabt",
}


@dataclass
class CapacityState:
    """Wie viel soziale Kapazitaet ist in diesem Zeitraum noch offen?"""
    social_days_used: int = 0
    social_days_limit: int | None = None
    weekends_used: int = 0
    weekends_limit: int | None = None
    allowed_weekdays: set[int] = field(default_factory=lambda: set(range(7)))
    min_days_between: int = 0

    @property
    def week_full(self) -> bool:
        return self.social_days_limit is not None and self.social_days_used >= self.social_days_limit

    @property
    def weekends_full(self) -> bool:
        return self.weekends_limit is not None and self.weekends_used >= self.weekends_limit

    @property
    def allows_meetings(self) -> bool:
        return not self.week_full

    def reasons(self) -> list[str]:
        out: list[str] = []
        if self.week_full:
            out.append(f"diese Woche schon {self.social_days_used} soziale Tage")
        if self.weekends_full:
            out.append(f"Wochenendbudget ausgeschoepft ({self.weekends_used})")
        return out


@dataclass
class RuleVerdict:
    allowed: bool
    blocks: list[str] = field(default_factory=list)
    planned_activity: PlannedActivity | None = None
    snoozed_until: date | None = None

    def labels(self) -> list[str]:
        return [BLOCK_LABELS.get(b, b) for b in self.blocks]


def _week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def _month_bounds(day: date) -> tuple[date, date]:
    start = day.replace(day=1)
    nxt = (start + timedelta(days=32)).replace(day=1)
    return start, nxt - timedelta(days=1)


def load_capacity(session: Session, today: date | None = None) -> CapacityState:
    """Zaehlt bereits verbrauchte soziale Tage aus Historie UND Planung."""
    today = today or date.today()
    state = CapacityState()

    if db.get_bool_setting(session, "capacity.max_social_days_per_week_active", True):
        state.social_days_limit = db.get_int_setting(session, "capacity.max_social_days_per_week", 3)
    if db.get_bool_setting(session, "capacity.max_weekends_per_month_active", True):
        state.weekends_limit = db.get_int_setting(session, "capacity.max_weekends_per_month", 3)
    if db.get_bool_setting(session, "capacity.allowed_weekdays_active", False):
        raw = db.get_setting(session, "capacity.allowed_weekdays", "0,1,2,3,4,5,6")
        parsed = {int(p) for p in str(raw).split(",") if p.strip().isdigit()}
        state.allowed_weekdays = parsed or set(range(7))
    state.min_days_between = db.get_int_setting(session, "capacity.min_days_between_contacts", 2)

    week_start, week_end = _week_bounds(today)
    month_start, month_end = _month_bounds(today)

    social_days: set[date] = set()
    for row in session.scalars(
        select(Interaction).where(Interaction.kind.in_(MEETING_KINDS),
                                  Interaction.occurred_on >= week_start,
                                  Interaction.occurred_on <= week_end)):
        social_days.add(row.occurred_on)
    for row in session.scalars(
        select(PlannedActivity).where(PlannedActivity.status == "planned",
                                      PlannedActivity.planned_date >= week_start,
                                      PlannedActivity.planned_date <= week_end)):
        social_days.add(row.planned_date)
    state.social_days_used = len(social_days)

    weekend_days: set[date] = set()
    for row in session.scalars(
        select(Interaction).where(Interaction.kind.in_(MEETING_KINDS),
                                  Interaction.occurred_on >= month_start,
                                  Interaction.occurred_on <= month_end)):
        if row.occurred_on.weekday() >= 5:
            weekend_days.add(row.occurred_on)
    for row in session.scalars(
        select(PlannedActivity).where(PlannedActivity.status == "planned",
                                      PlannedActivity.planned_date >= month_start,
                                      PlannedActivity.planned_date <= month_end)):
        if row.planned_date.weekday() >= 5:
            weekend_days.add(row.planned_date)
    # Ein Wochenende zaehlt einmal, nicht zweimal (Sa + So).
    state.weekends_used = len({d.isocalendar()[:2] for d in weekend_days})
    return state


def check_contact(session: Session, contact: Contact, capacity: CapacityState,
                  today: date | None = None, planned_horizon_days: int = 21) -> RuleVerdict:
    """Harte Pruefung fuer eine einzelne Person."""
    today = today or date.today()
    verdict = RuleVerdict(allowed=True)

    if contact.status not in ROTATING_STATUSES:
        if contact.status == STATUS_PAUSED:
            verdict.blocks.append(BLOCK_PAUSED)
        else:
            verdict.blocks.append(BLOCK_STATUS)

    if contact.paused_until and contact.paused_until >= today:
        if BLOCK_PAUSED not in verdict.blocks:
            verdict.blocks.append(BLOCK_PAUSED)

    snooze = session.scalar(
        select(RotationSnooze)
        .where(RotationSnooze.contact_id == contact.id,
               RotationSnooze.snoozed_until >= today)
        .order_by(RotationSnooze.snoozed_until.desc()).limit(1))
    if snooze is not None:
        verdict.blocks.append(BLOCK_SNOOZED)
        verdict.snoozed_until = snooze.snoozed_until

    horizon = today + timedelta(days=planned_horizon_days)
    activity = session.scalar(
        select(PlannedActivity)
        .join(PlannedActivity.participants)
        .where(Contact.id == contact.id,
               PlannedActivity.status == "planned",
               PlannedActivity.planned_date >= today,
               PlannedActivity.planned_date <= horizon)
        .order_by(PlannedActivity.planned_date).limit(1))
    if activity is not None:
        verdict.blocks.append(BLOCK_PLANNED)
        verdict.planned_activity = activity

    if capacity.min_days_between > 0:
        # Nur echte Kontakte loesen eine Sperrfrist aus. Ein Daumen-hoch von
        # gestern darf einen ueberfaelligen Freund nicht aus dem Fokus nehmen.
        recent = session.scalar(
            select(Interaction)
            .where(Interaction.contact_id == contact.id,
                   Interaction.kind.in_(SUBSTANTIAL_KINDS),
                   Interaction.occurred_on > today - timedelta(days=capacity.min_days_between))
            .limit(1))
        if recent is not None:
            verdict.blocks.append(BLOCK_COOLDOWN)

    verdict.allowed = not verdict.blocks
    return verdict
