from __future__ import annotations

from datetime import date, timedelta

from freizeitmanager.database.models import (
    KIND_CALL_LONG,
    KIND_MEET,
    KIND_MEET_LONG,
    KIND_REACTION,
    QUALITY_INTENSE,
    QUALITY_SHORT,
)
from freizeitmanager.logic.freshness import (
    MAX_FRESHNESS,
    InteractionFact,
    compute_freshness,
    describe_gap,
    interaction_impact,
)

TODAY = date(2026, 8, 20)


def ago(n: int) -> date:
    return TODAY - timedelta(days=n)


def test_frischer_kontakt_ist_nicht_faellig():
    r = compute_freshness([InteractionFact(ago(2), KIND_MEET)], 30, TODAY)
    assert r.overdue_ratio < 0.2
    assert not r.is_due


def test_ein_intervall_ohne_kontakt_ist_faellig():
    r = compute_freshness([InteractionFact(ago(30), KIND_MEET)], 30, TODAY)
    assert r.is_due


def test_emoji_setzt_engen_freund_nicht_zurueck():
    """Kernanforderung: ein Daumen-hoch darf keine 30 Tage Ruhe erzeugen."""
    ohne = compute_freshness([InteractionFact(ago(42), KIND_MEET)], 21, TODAY)
    mit = compute_freshness([InteractionFact(ago(42), KIND_MEET),
                             InteractionFact(ago(1), KIND_REACTION)], 21, TODAY)
    assert mit.overdue_ratio > 1.5
    assert ohne.overdue_ratio - mit.overdue_ratio < 0.5


def test_langes_telefonat_wirkt_deutlich():
    r = compute_freshness([InteractionFact(ago(42), KIND_MEET),
                           InteractionFact(ago(3), KIND_CALL_LONG)], 21, TODAY)
    assert not r.is_due


def test_ohne_historie_maximaler_abstand():
    r = compute_freshness([], 30, TODAY)
    assert r.freshness == 0.0
    assert r.overdue_ratio == 4.0
    assert describe_gap(r) == "noch kein Kontakt erfasst"


def test_zukunftstermine_zaehlen_nicht_als_kontakt():
    r = compute_freshness([InteractionFact(TODAY + timedelta(5), KIND_MEET)], 30, TODAY)
    assert r.freshness == 0.0


def test_qualitaet_und_dauer_wirken_in_der_erwarteten_richtung():
    kurz = interaction_impact(InteractionFact(TODAY, KIND_MEET, QUALITY_SHORT))
    lang = interaction_impact(InteractionFact(TODAY, KIND_MEET_LONG, QUALITY_INTENSE))
    assert kurz < lang <= MAX_FRESHNESS


def test_freshness_ist_gedeckelt():
    facts = [InteractionFact(ago(i), KIND_MEET_LONG) for i in range(6)]
    assert compute_freshness(facts, 30, TODAY).freshness == MAX_FRESHNESS
