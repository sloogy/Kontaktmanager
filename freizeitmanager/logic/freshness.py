"""Beziehungsfrische.

Das alte Modell kannte nur ``letztes_treffen``. Damit setzt ein
"Happy Birthday" per WhatsApp einen engen Freund fuer 30 Tage zurueck.

Stattdessen bekommt jede Interaktion eine Wirkung zwischen 0 und 1, die mit
der Zeit exponentiell abklingt. Die Halbwertszeit ist der gewuenschte
Kontaktrhythmus der Person: Ein vollwertiges Treffen ist nach genau einem
Intervall auf 0.5 abgesunken - das ist per Definition der Punkt "faellig".

Aus der Frische wird ein "effektiver Abstand" in Tagen zurueckgerechnet.
Der ist fuer Menschen lesbar ("wie vor 5 Wochen") und fuer die Engine
robuster als ein einzelnes Datum.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

from freizeitmanager.database.models import (KIND_CALL, KIND_CALL_LONG,
                                             KIND_CHAT, KIND_MEET,
                                             KIND_MEET_LONG, KIND_MESSAGE,
                                             KIND_REACTION, QUALITY_INTENSE,
                                             QUALITY_NORMAL, QUALITY_SHORT)

# Grundwirkung je Kontaktart. Konfigurierbar, absichtlich nicht im Schema.
# Bezugspunkt: Ein normales Treffen erfuellt den gewuenschten Rhythmus
# vollstaendig (1.00). Genau das bedeutet "ich moechte uns alle 21 Tage sehen".
# Ein langer gemeinsamer Tag darf darueber hinaus Zeit gutschreiben.
BASE_WEIGHTS: dict[str, float] = {
    KIND_MEET_LONG: 1.15,   # gemeinsamer Tag, Ausflug, Uebernachtung
    KIND_MEET: 1.00,        # normales Treffen
    KIND_CALL_LONG: 0.75,   # laengeres Telefon-/Videogespraech
    KIND_CALL: 0.50,        # kurzes Telefonat
    KIND_CHAT: 0.35,        # echtes laengeres Chatgespraech
    KIND_MESSAGE: 0.15,     # einzelne Nachricht
    KIND_REACTION: 0.05,    # Emoji, Like, Story-Reaktion
}

# Obergrenze der Frische. Werte ueber 1.0 bedeuten Guthaben: Nach einem
# intensiven gemeinsamen Wochenende ist der naechste Kontakt spaeter faellig.
MAX_FRESHNESS = 1.30

QUALITY_FACTORS: dict[str, float] = {
    QUALITY_SHORT: 0.70,
    QUALITY_NORMAL: 1.00,
    QUALITY_INTENSE: 1.25,
}

# Dauer wirkt bewusst schwach und gedeckelt: Ein Treffen ist ein Treffen,
# auch wenn niemand die Minuten mitschreibt.
DURATION_REFERENCE_MIN = 120
DURATION_MIN_FACTOR = 0.75
DURATION_MAX_FACTOR = 1.20

# Obergrenze fuer den zurueckgerechneten Abstand, damit "nie kontaktiert"
# nicht zu unendlich grossen Zahlen fuehrt.
MAX_GAP_INTERVALS = 4.0

# Ab dieser Frische gilt eine Beziehung als faellig (= ein volles Intervall).
DUE_FRESHNESS = 0.5

# Ab dieser Grundwirkung zaehlt etwas als "richtiger Kontakt". Nachrichten und
# Reaktionen liegen bewusst darunter: Sie wirken auf die Frische, loesen aber
# weder eine Sperrfrist aus noch duerfen sie in der UI als letzter Kontakt
# ausgewiesen werden ("zuletzt vor 2 Wochen", obwohl das eine Nachricht war).
SUBSTANTIAL_IMPACT = 0.30


def is_substantial(kind: str) -> bool:
    return BASE_WEIGHTS.get(kind, 0.0) >= SUBSTANTIAL_IMPACT


@dataclass(frozen=True)
class InteractionFact:
    """Entkoppelt die Berechnung vom ORM - macht sie einzeln testbar."""
    occurred_on: date
    kind: str
    quality: str = QUALITY_NORMAL
    duration_min: int | None = None


@dataclass
class FreshnessResult:
    freshness: float             # 0..1.3, >1 = Guthaben nach intensivem Kontakt
    effective_gap_days: float    # zurueckgerechneter Abstand in Tagen
    overdue_ratio: float         # 1.0 = genau faellig, 2.0 = doppelt ueberfaellig
    last_interaction_on: date | None = None
    last_interaction_kind: str | None = None
    real_gap_days: int | None = None   # echte Tage seit irgendeinem Kontakt
    last_substantial_on: date | None = None
    substantial_gap_days: int | None = None
    contributions: list[tuple[date, str, float]] = field(default_factory=list)

    @property
    def is_due(self) -> bool:
        return self.overdue_ratio >= 1.0


def interaction_impact(fact: InteractionFact) -> float:
    """Wirkung einer einzelnen Interaktion am Tag ihres Stattfindens."""
    base = BASE_WEIGHTS.get(fact.kind, BASE_WEIGHTS[KIND_MESSAGE])
    factor = QUALITY_FACTORS.get(fact.quality, 1.0)
    if fact.duration_min:
        ratio = float(fact.duration_min) / DURATION_REFERENCE_MIN
        scaled = 0.85 + 0.35 * min(1.0, ratio)
        factor *= max(DURATION_MIN_FACTOR, min(DURATION_MAX_FACTOR, scaled))
    return max(0.0, min(MAX_FRESHNESS, base * factor))


def _decay(age_days: float, halflife_days: float) -> float:
    if age_days <= 0:
        return 1.0
    return 0.5 ** (age_days / max(1.0, halflife_days))


def compute_freshness(facts: list[InteractionFact],
                      target_interval_days: int,
                      today: date | None = None) -> FreshnessResult:
    """Aggregiert alle Interaktionen zu einer abklingenden Frische."""
    today = today or date.today()
    halflife = max(1, int(target_interval_days or 30))

    total = 0.0
    contributions: list[tuple[date, str, float]] = []
    last_on: date | None = None
    last_kind: str | None = None
    last_real_on: date | None = None

    for fact in facts:
        if fact.occurred_on > today:
            continue  # zukuenftige Eintraege sind Planung, kein Kontakt
        age = (today - fact.occurred_on).days
        value = interaction_impact(fact) * _decay(age, halflife)
        if value <= 0.0005:
            continue
        total += value
        contributions.append((fact.occurred_on, fact.kind, round(value, 4)))
        if last_on is None or fact.occurred_on > last_on:
            last_on, last_kind = fact.occurred_on, fact.kind
        if is_substantial(fact.kind) and (last_real_on is None or fact.occurred_on > last_real_on):
            last_real_on = fact.occurred_on

    freshness = min(MAX_FRESHNESS, total)
    max_gap = MAX_GAP_INTERVALS * halflife

    if freshness <= 0.0:
        gap = max_gap
    else:
        # Negative Werte sind gewollt: sie stehen fuer "Guthaben".
        gap = max(-float(halflife), min(max_gap, -halflife * math.log2(freshness)))

    return FreshnessResult(
        freshness=round(freshness, 4),
        effective_gap_days=round(gap, 1),
        overdue_ratio=round(gap / halflife, 3),
        last_interaction_on=last_on,
        last_interaction_kind=last_kind,
        real_gap_days=(today - last_on).days if last_on else None,
        last_substantial_on=last_real_on,
        substantial_gap_days=(today - last_real_on).days if last_real_on else None,
        contributions=sorted(contributions, key=lambda c: c[0], reverse=True),
    )


def describe_gap(result: FreshnessResult) -> str:
    """Menschliche Formulierung des letzten richtigen Kontakts."""
    if result.last_substantial_on is None:
        if result.last_interaction_on is None:
            return "noch kein Kontakt erfasst"
        return "bisher nur kurze Nachrichten"
    days = result.substantial_gap_days or 0
    if days <= 0:
        return "heute"
    if days == 1:
        return "gestern"
    if days < 14:
        return f"vor {days} Tagen"
    if days < 60:
        return f"vor {days // 7} Wochen"
    return f"vor {days // 30} Monaten"
