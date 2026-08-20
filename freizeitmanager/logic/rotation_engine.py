"""Rotation Engine - entscheidet, wer wann sinnvoll dran waere.

Leitgedanke: Die Engine darf innen komplex sein, die Oberflaeche nicht.
Nach aussen gibt sie deshalb nie eine nackte Punktzahl aus, sondern eine
Empfehlung, eine Dringlichkeitsstufe und eine Liste lesbarer Gruende.

Bewusste Nicht-Ziele:
* Kein Schuldenberg. Wer die App drei Wochen nicht oeffnet, sieht danach
  keine 17 roten Versaeumnisse, sondern drei sinnvolle naechste Schritte.
* Keine Zwangsrotation. Kapazitaet und Energie duerfen Vorschlaege
  abschwaechen (Telefonat statt Treffen), statt sie zu erzwingen.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from freizeitmanager.database import db
from freizeitmanager.database.models import (KIND_CALL, KIND_CALL_LONG,
                                             KIND_MEET, KIND_MESSAGE, Contact,
                                             RotationState)
from freizeitmanager.logic import rule_engine
from freizeitmanager.logic.freshness import (FreshnessResult, InteractionFact,
                                             compute_freshness, describe_gap)

_log = logging.getLogger(__name__)

ENERGY_LOW = "low"
ENERGY_NORMAL = "normal"
ENERGY_SOCIAL = "social"
ENERGY_STATES = (ENERGY_LOW, ENERGY_NORMAL, ENERGY_SOCIAL)

# Dringlichkeitsstufen - das ist alles, was die UI an "Score" zeigen darf.
URGENCY_FRESH = "fresh"        # alles gut
URGENCY_SOON = "soon"          # diese Woche waere schoen
URGENCY_DUE = "due"            # jetzt ein guter Zeitpunkt
URGENCY_LONG = "long"          # schon lange still

URGENCY_LABELS = {
    URGENCY_FRESH: "alles gut",
    URGENCY_SOON: "bald wieder",
    URGENCY_DUE: "jetzt ein guter Zeitpunkt",
    URGENCY_LONG: "schon lange still",
}
# Bewusst ein einfacher Punkt statt farbiger Emoji-Kreise: U+1F7E0 und
# Verwandte fehlen in vielen Systemschriften und erscheinen dann als Luecke.
# Der Punkt uebernimmt stattdessen die Akzentfarbe der Karte.
URGENCY_ICONS = {
    URGENCY_FRESH: "\N{BLACK CIRCLE}",
    URGENCY_SOON: "\N{BLACK CIRCLE}",
    URGENCY_DUE: "\N{BLACK CIRCLE}",
    URGENCY_LONG: "\N{BLACK CIRCLE}",
}

# Vorschlagsarten mit realistischer Aufwandsangabe.
SUGGESTION_MEET = "meet"
SUGGESTION_CALL = "call"
SUGGESTION_MESSAGE = "message"

SUGGESTION_LABELS = {
    SUGGESTION_MEET: ("\N{HOT BEVERAGE}", "Treffen vorschlagen", "ein paar Stunden"),
    SUGGESTION_CALL: ("\N{BLACK TELEPHONE}", "Anrufen", "10-20 Minuten"),
    SUGGESTION_MESSAGE: ("\N{ENVELOPE}", "Nachricht schreiben", "2 Minuten"),
}

SUGGESTION_TO_KIND = {
    SUGGESTION_MEET: KIND_MEET,
    SUGGESTION_CALL: KIND_CALL,
    SUGGESTION_MESSAGE: KIND_MESSAGE,
}

# Score-Obergrenzen der einzelnen Anteile.
W_DUE = 45.0
W_IMPORTANCE = 20.0
W_NEGLECT = 15.0
W_CONTEXT = 15.0
W_FAIRNESS = 10.0
W_WISH = 20.0
P_RECENTLY_SHOWN = 15.0

# Ab dieser Ueberfaelligkeit ist jemand ueberhaupt ein Kandidat.
CANDIDATE_RATIO = 0.75


@dataclass
class Candidate:
    contact_id: int
    name: str
    score: float
    urgency: str
    suggestion: str
    freshness: FreshnessResult
    reasons: list[str] = field(default_factory=list)
    breakdown: dict[str, float] = field(default_factory=dict)
    blocks: list[str] = field(default_factory=list)
    planned_on: date | None = None

    @property
    def icon(self) -> str:
        return URGENCY_ICONS.get(self.urgency, "")

    @property
    def gap_text(self) -> str:
        return describe_gap(self.freshness)

    @property
    def suggestion_icon(self) -> str:
        return SUGGESTION_LABELS[self.suggestion][0]

    @property
    def suggestion_text(self) -> str:
        return SUGGESTION_LABELS[self.suggestion][1]

    @property
    def suggestion_effort(self) -> str:
        return SUGGESTION_LABELS[self.suggestion][2]

    def headline(self) -> str:
        return f"{self.icon} {self.name} \N{MIDDLE DOT} {URGENCY_LABELS[self.urgency]}"

    def why(self) -> list[str]:
        """Lesbare Begruendung fuer den Aufklapp-Bereich."""
        return list(self.reasons)


def _facts(contact: Contact) -> list[InteractionFact]:
    return [InteractionFact(i.occurred_on, i.kind, i.quality, i.duration_min)
            for i in contact.interactions]


def _urgency(ratio: float, flex_ratio: float) -> str:
    if ratio >= 2.0:
        return URGENCY_LONG
    if ratio >= 1.0:
        return URGENCY_DUE
    if ratio >= flex_ratio:
        return URGENCY_SOON
    return URGENCY_FRESH


def _due_points(ratio: float, flex_ratio: float, importance: int) -> float:
    """Faelligkeit, moduliert durch Wichtigkeit.

    Wichtigkeit wirkt bewusst nicht nur additiv: Sonst verdraengt eine lose
    Bekanntschaft, die seit einem halben Jahr still ist, einen engen Freund,
    der seit einem Monat still ist. Der Faktor bleibt aber mild (0.7-1.1),
    damit lange vernachlaessigte Bekannte nicht voellig unsichtbar werden.
    """
    if ratio <= flex_ratio:
        return 0.0
    if ratio < 1.0:
        span = max(0.01, 1.0 - flex_ratio)
        raw = 25.0 * (ratio - flex_ratio) / span
    else:
        raw = 25.0 + 20.0 * min(1.0, ratio - 1.0)
    factor = 0.6 + 0.1 * max(1, min(5, importance))
    return min(W_DUE, raw * factor)


def _neglect_points(freshness: FreshnessResult, target: int) -> float:
    """Zusatzgewicht fuer echte lange Funkstille - unabhaengig vom Rhythmus."""
    real = freshness.real_gap_days
    if real is None:
        return W_NEGLECT * 0.8   # noch nie erfasst: auffaellig, aber nicht dramatisch
    over = real - 2 * max(1, target)
    if over <= 0:
        return 0.0
    return min(W_NEGLECT, W_NEGLECT * over / (2.0 * max(1, target)))


def _context_points(contact: Contact, suggestion: str, energy: str,
                    capacity: rule_engine.CapacityState, today: date) -> tuple[float, list[str]]:
    """Passt der Vorschlag zur aktuellen Lage?"""
    points = 0.0
    notes: list[str] = []

    if energy == ENERGY_LOW and suggestion in (SUGGESTION_CALL, SUGGESTION_MESSAGE):
        points += 6.0
        notes.append("passt zu wenig Energie")
    elif energy == ENERGY_SOCIAL and suggestion == SUGGESTION_MEET:
        points += 6.0
        notes.append("du hast Lust auf Leute")
    elif energy == ENERGY_NORMAL:
        points += 3.0

    if energy != ENERGY_LOW and contact.energy_cost <= 1:
        points += 2.0

    is_weekend = today.weekday() >= 5
    if is_weekend and contact.prefers_weekend:
        points += 4.0
        notes.append("Wochenende passt")
    elif not is_weekend and contact.prefers_weekday:
        points += 4.0

    if today.weekday() in capacity.allowed_weekdays:
        points += 3.0

    return min(W_CONTEXT, points), notes


def _fairness_points(state: RotationState | None, today: date) -> tuple[float, float]:
    """Rueckgabe: (Bonus, Abzug). Verhindert immer dieselben Gewinner."""
    if state is None or state.last_suggested_on is None:
        return W_FAIRNESS, 0.0
    days = (today - state.last_suggested_on).days
    if days <= 2:
        return 0.0, P_RECENTLY_SHOWN
    if days <= 6:
        return 2.0, 0.0
    return min(W_FAIRNESS, 2.0 + 0.4 * (days - 6)), 0.0


def _wish_points(contact: Contact, today: date) -> float:
    if not contact.wish_boost:
        return 0.0
    if contact.wish_until and contact.wish_until < today:
        return 0.0
    return min(W_WISH, float(contact.wish_boost))


def _pick_suggestion(contact: Contact, freshness: FreshnessResult, energy: str,
                     capacity: rule_engine.CapacityState) -> tuple[str, list[str]]:
    """Waehlt den kleinsten Schritt, der der Lage angemessen ist."""
    notes: list[str] = []
    meeting_possible = contact.wants_meeting and capacity.allows_meetings and energy != ENERGY_LOW
    if not capacity.allows_meetings and contact.wants_meeting:
        notes.append("Wochenbudget voll - kleinerer Schritt")
    if energy == ENERGY_LOW:
        notes.append("heute wenig Energie")

    if meeting_possible and (freshness.overdue_ratio >= 1.3 or energy == ENERGY_SOCIAL):
        return SUGGESTION_MEET, notes
    if contact.wants_call and energy != ENERGY_LOW:
        return SUGGESTION_CALL, notes
    if contact.wants_call and freshness.overdue_ratio >= 2.0:
        return SUGGESTION_CALL, notes
    if contact.wants_message:
        return SUGGESTION_MESSAGE, notes
    if contact.wants_call:
        return SUGGESTION_CALL, notes
    return SUGGESTION_MEET, notes


def evaluate_contact(session: Session, contact: Contact,
                     capacity: rule_engine.CapacityState,
                     energy: str = ENERGY_NORMAL,
                     today: date | None = None) -> Candidate:
    """Vollstaendige Bewertung einer Person inklusive Begruendung."""
    today = today or date.today()
    target = max(1, int(contact.target_interval_days or 30))
    flex = max(0, int(contact.interval_flex_days or 0))
    flex_ratio = min(0.95, max(0.3, 1.0 - flex / float(target)))

    fresh = compute_freshness(_facts(contact), target, today)
    verdict = rule_engine.check_contact(session, contact, capacity, today)
    suggestion, ctx_notes = _pick_suggestion(contact, fresh, energy, capacity)

    reasons: list[str] = []
    breakdown: dict[str, float] = {}

    due = _due_points(fresh.overdue_ratio, flex_ratio, contact.importance)
    breakdown["Faelligkeit"] = round(due, 1)
    if due > 0:
        reasons.append(f"gewuenschter Rhythmus alle {target} Tage, letzter Kontakt {describe_gap(fresh)}")

    importance = W_IMPORTANCE * (max(1, min(5, contact.importance)) - 1) / 4.0
    breakdown["Wichtigkeit"] = round(importance, 1)
    if contact.importance >= 4:
        reasons.append("wichtiger Mensch fuer dich")

    neglect = _neglect_points(fresh, target)
    breakdown["Funkstille"] = round(neglect, 1)
    if neglect >= 5:
        reasons.append("deutlich laenger still als sonst")

    context, ctx_reasons = _context_points(contact, suggestion, energy, capacity, today)
    breakdown["Kontext"] = round(context, 1)
    reasons.extend(ctx_reasons)
    reasons.extend(ctx_notes)

    state = session.get(RotationState, contact.id)
    fair_bonus, fair_penalty = _fairness_points(state, today)
    breakdown["Rotation"] = round(fair_bonus - fair_penalty, 1)
    if state is None or state.last_suggested_on is None:
        reasons.append("war noch nie im Fokus")

    wish = _wish_points(contact, today)
    breakdown["Wunsch"] = round(wish, 1)
    if wish > 0:
        reasons.append("von dir als 'bald wieder' markiert")

    score = due + importance + neglect + context + fair_bonus + wish - fair_penalty

    if verdict.blocks:
        score = 0.0
        reasons = verdict.labels()
        if verdict.planned_activity is not None:
            reasons = [f"Termin am {verdict.planned_activity.planned_date.strftime('%d.%m.')}"] + reasons[1:]

    return Candidate(
        contact_id=contact.id,
        name=contact.name,
        score=round(max(0.0, score), 1),
        urgency=_urgency(fresh.overdue_ratio, flex_ratio),
        suggestion=suggestion,
        freshness=fresh,
        reasons=reasons,
        breakdown=breakdown,
        blocks=verdict.blocks,
        planned_on=verdict.planned_activity.planned_date if verdict.planned_activity else None,
    )


def evaluate_all(session: Session, energy: str | None = None,
                 today: date | None = None) -> list[Candidate]:
    """Bewertet jeden Kontakt. Reihenfolge: bester Kandidat zuerst."""
    today = today or date.today()
    energy = energy or db.get_setting(session, "focus.energy_state", ENERGY_NORMAL)
    if energy not in ENERGY_STATES:
        energy = ENERGY_NORMAL
    capacity = rule_engine.load_capacity(session, today)

    contacts = session.scalars(
        select(Contact).options(selectinload(Contact.interactions))
    ).all()

    results = [evaluate_contact(session, c, capacity, energy, today) for c in contacts]
    results.sort(key=lambda c: (-c.score, c.name.lower()))
    return results


def pick_focus(candidates: list[Candidate], limit: int = 3,
               exclude_ids: set[int] | None = None) -> list[Candidate]:
    """Waehlt die wenigen Vorschlaege aus, die sichtbar werden duerfen."""
    exclude_ids = exclude_ids or set()
    pool = [c for c in candidates
            if not c.blocks
            and c.freshness.overdue_ratio >= CANDIDATE_RATIO
            and c.contact_id not in exclude_ids]
    return pool[:max(1, int(limit))]


def remember_suggestions(session: Session, candidates: list[Candidate],
                         today: date | None = None) -> None:
    """Rotationsgedaechtnis fortschreiben - Basis fuer Fairness und Reroll."""
    today = today or date.today()
    for cand in candidates:
        state = session.get(RotationState, cand.contact_id)
        if state is None:
            state = RotationState(contact_id=cand.contact_id, suggest_count=0)
            session.add(state)
        state.last_suggested_on = today
        state.suggest_count = int(state.suggest_count or 0) + 1
        state.last_score = int(cand.score)


def snooze_contact(session: Session, contact_id: int, days: int = 7,
                   reason: str = "later", today: date | None = None) -> None:
    """Bewusst zurueckstellen - ohne Schuldgefuehl und ohne Datenverlust."""
    from freizeitmanager.database.models import RotationSnooze
    today = today or date.today()
    session.add(RotationSnooze(contact_id=contact_id,
                               snoozed_until=today + timedelta(days=max(1, days)),
                               reason=reason))
