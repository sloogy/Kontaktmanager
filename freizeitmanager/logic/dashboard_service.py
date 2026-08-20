"""Fokus-Cockpit.

Vorbild BudgetManager: Das Cockpit beantwortet nicht "wie steht alles?",
sondern "was waere jetzt dran?". Vorbild FPM: leere Bereiche verschwinden,
und im ruhigen Zustand erscheint eine kompakte Entwarnung statt einer
leeren Tabelle.

Deshalb liefert dieser Service maximal ``focus.max_suggestions`` Eintraege -
unabhaengig davon, wie viele Kandidaten die Engine intern kennt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from freizeitmanager.database import db
from freizeitmanager.database.models import PlannedActivity
from freizeitmanager.logic import rotation_engine as rot
from freizeitmanager.logic.rule_engine import load_capacity

CALM_MESSAGE = "Alles im gruenen Bereich. Nichts, was jetzt dringend waere."
WELCOME_BACK = "Schoen, dass du wieder da bist. Diese Kontakte waeren jetzt sinnvoll."


@dataclass
class UpcomingPlan:
    activity_id: int
    title: str
    on: date
    names: list[str] = field(default_factory=list)

    def label(self) -> str:
        who = ", ".join(self.names) if self.names else "-"
        return f"{self.on.strftime('%a %d.%m.')} \N{MIDDLE DOT} {self.title} ({who})"


@dataclass
class FocusSummary:
    """Die vier Kacheln oben - mehr Zahlen bekommt der Startbildschirm nicht."""
    due_now: int = 0
    this_week: int = 0
    planned: int = 0
    all_good: int = 0
    resting: int = 0
    energy: str = rot.ENERGY_NORMAL
    capacity_notes: list[str] = field(default_factory=list)

    def tiles(self) -> list[tuple[str, int]]:
        return [("Jetzt passend", self.due_now), ("Diese Woche", self.this_week),
                ("Geplant", self.planned), ("Alles gut", self.all_good)]

    @property
    def is_calm(self) -> bool:
        return self.due_now == 0


@dataclass
class Cockpit:
    summary: FocusSummary
    next_steps: list[rot.Candidate] = field(default_factory=list)
    upcoming: list[UpcomingPlan] = field(default_factory=list)
    message: str = ""


def _upcoming(session: Session, today: date, days: int = 14) -> list[UpcomingPlan]:
    rows = session.scalars(
        select(PlannedActivity)
        .options(selectinload(PlannedActivity.participants))
        .where(PlannedActivity.status == "planned",
               PlannedActivity.planned_date >= today,
               PlannedActivity.planned_date <= today + timedelta(days=days))
        .order_by(PlannedActivity.planned_date)).all()
    return [UpcomingPlan(r.id, r.title, r.planned_date, [c.name for c in r.participants])
            for r in rows]


def build_cockpit(session: Session, *, today: date | None = None,
                  energy: str | None = None,
                  exclude_ids: set[int] | None = None,
                  remember: bool = True) -> Cockpit:
    """Erzeugt den kompletten Startbildschirm-Zustand."""
    today = today or date.today()
    energy = energy or db.get_setting(session, "focus.energy_state", rot.ENERGY_NORMAL)
    limit = db.get_int_setting(session, "focus.max_suggestions", 3)

    candidates = rot.evaluate_all(session, energy, today)
    focus = rot.pick_focus(candidates, limit, exclude_ids)

    summary = FocusSummary(energy=energy)
    for cand in candidates:
        if cand.planned_on is not None:
            summary.planned += 1
        elif cand.blocks:
            summary.resting += 1
        elif cand.urgency in (rot.URGENCY_DUE, rot.URGENCY_LONG):
            summary.due_now += 1
        elif cand.urgency == rot.URGENCY_SOON:
            summary.this_week += 1
        else:
            summary.all_good += 1

    summary.capacity_notes = load_capacity(session, today).reasons()

    if remember and focus:
        rot.remember_suggestions(session, focus, today)

    # Kein Schuldenberg: Auch bei 17 offenen Kandidaten bleibt der Ton ruhig.
    if summary.is_calm:
        message = CALM_MESSAGE
    elif summary.due_now > limit:
        message = WELCOME_BACK
    else:
        message = ""

    return Cockpit(summary=summary, next_steps=focus,
                   upcoming=_upcoming(session, today), message=message)


def reroll(session: Session, current: list[rot.Candidate], *,
           today: date | None = None, energy: str | None = None) -> Cockpit:
    """'Andere Vorschlaege' - dieselben Personen kommen nicht sofort wieder."""
    return build_cockpit(session, today=today, energy=energy,
                         exclude_ids={c.contact_id for c in current})


def set_energy(session: Session, energy: str, today: date | None = None) -> None:
    if energy not in rot.ENERGY_STATES:
        raise ValueError(f"Unbekannter Energiezustand: {energy!r}")
    db.set_setting(session, "focus.energy_state", energy)
    db.set_setting(session, "focus.energy_state_date", (today or date.today()).isoformat())


def current_energy(session: Session, today: date | None = None) -> str:
    """Der Energiezustand gilt nur fuer den Tag - danach wieder 'normal'."""
    today = today or date.today()
    stamp = db.get_setting(session, "focus.energy_state_date", "")
    if stamp != today.isoformat():
        return rot.ENERGY_NORMAL
    return db.get_setting(session, "focus.energy_state", rot.ENERGY_NORMAL)
