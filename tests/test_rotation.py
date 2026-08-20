from __future__ import annotations

from datetime import date, timedelta

from freizeitmanager.database import db
from freizeitmanager.database.models import (KIND_CALL, KIND_MEET,
                                             KIND_MESSAGE, STATUS_NO_ROTATION)
from freizeitmanager.logic import contact_service as cs
from freizeitmanager.logic import dashboard_service as dash
from freizeitmanager.logic import rotation_engine as rot
from freizeitmanager.logic.rule_engine import load_capacity

TODAY = date(2026, 8, 20)


def ago(n: int) -> date:
    return TODAY - timedelta(days=n)


def _person(session, name, *, importance=4, interval=21, **kw):
    return cs.create_contact(session, name, importance=importance,
                             target_interval_days=interval, **kw)


def test_ueberfaelliger_wichtiger_kontakt_schlaegt_frischen(session):
    a = _person(session, "Patrick", importance=5, interval=30)
    b = _person(session, "Nadine", importance=5, interval=30)
    cs.log_interaction(session, a.id, KIND_MEET, occurred_on=ago(62))
    cs.log_interaction(session, b.id, KIND_MEET, occurred_on=ago(8))
    session.flush()

    result = rot.evaluate_all(session, rot.ENERGY_NORMAL, TODAY)
    assert result[0].name == "Patrick"
    assert result[0].urgency in (rot.URGENCY_DUE, rot.URGENCY_LONG)
    by_name = {c.name: c for c in result}
    assert by_name["Nadine"].urgency == rot.URGENCY_FRESH


def test_geplanter_termin_nimmt_aus_dem_fokus(session):
    p = _person(session, "Leandro", interval=30)
    cs.log_interaction(session, p.id, KIND_MEET, occurred_on=ago(50))
    cs.plan_activity(session, "Spieleabend", TODAY + timedelta(3), [p.id])
    session.flush()

    cand = {c.name: c for c in rot.evaluate_all(session, today=TODAY)}["Leandro"]
    assert cand.blocks == ["planned"]
    assert cand.score == 0.0
    assert rot.pick_focus([cand]) == []


def test_snooze_blockt_und_interaktion_hebt_ihn_auf(session):
    p = _person(session, "Marko", interval=21)
    cs.log_interaction(session, p.id, KIND_MEET, occurred_on=ago(40))
    session.flush()
    assert rot.pick_focus(rot.evaluate_all(session, today=TODAY))

    rot.snooze_contact(session, p.id, days=10, today=TODAY)
    session.flush()
    assert rot.pick_focus(rot.evaluate_all(session, today=TODAY)) == []

    cs.log_interaction(session, p.id, KIND_CALL, occurred_on=TODAY)
    session.flush()
    cand = {c.name: c for c in rot.evaluate_all(session, today=TODAY)}["Marko"]
    assert "snoozed" not in cand.blocks


def test_status_ohne_rotation_wird_nie_vorgeschlagen(session):
    p = _person(session, "Kollege X", status=STATUS_NO_ROTATION, interval=90)
    session.flush()
    cand = {c.name: c for c in rot.evaluate_all(session, today=TODAY)}["Kollege X"]
    assert "status" in cand.blocks
    assert rot.pick_focus([cand]) == []


def test_wenig_energie_schlaegt_kein_treffen_vor(session):
    p = _person(session, "Marko", interval=21)
    cs.log_interaction(session, p.id, KIND_MEET, occurred_on=ago(45))
    session.flush()

    normal = {c.name: c for c in rot.evaluate_all(session, rot.ENERGY_SOCIAL, TODAY)}["Marko"]
    low = {c.name: c for c in rot.evaluate_all(session, rot.ENERGY_LOW, TODAY)}["Marko"]
    assert normal.suggestion == rot.SUGGESTION_MEET
    assert low.suggestion != rot.SUGGESTION_MEET


def test_wochenbudget_daempft_auf_kleineren_schritt(session):
    p = _person(session, "Marko", interval=21)
    cs.log_interaction(session, p.id, KIND_MEET, occurred_on=ago(45))
    # Drei bereits stattgefundene Treffen in dieser Woche fuellen das Budget.
    for n, other in enumerate(("A", "B", "C")):
        o = _person(session, other)
        cs.log_interaction(session, o.id, KIND_MEET, occurred_on=TODAY - timedelta(days=n))
    session.flush()

    cap = load_capacity(session, TODAY)
    assert cap.week_full and not cap.allows_meetings
    cand = {c.name: c for c in rot.evaluate_all(session, rot.ENERGY_SOCIAL, TODAY)}["Marko"]
    assert cand.suggestion != rot.SUGGESTION_MEET


def test_fokus_ist_gedeckelt_und_erzeugt_keinen_schuldenberg(session):
    for i in range(17):
        p = _person(session, f"Person {i:02d}", interval=21)
        cs.log_interaction(session, p.id, KIND_MEET, occurred_on=ago(60 + i))
    session.flush()

    cockpit = dash.build_cockpit(session, today=TODAY)
    assert len(cockpit.next_steps) == 3
    assert cockpit.summary.due_now == 17
    assert cockpit.message == dash.WELCOME_BACK


def test_reroll_zeigt_andere_personen(session):
    for i in range(8):
        p = _person(session, f"Person {i:02d}", interval=21)
        cs.log_interaction(session, p.id, KIND_MEET, occurred_on=ago(60 + i))
    session.flush()

    first = dash.build_cockpit(session, today=TODAY)
    session.flush()
    second = dash.reroll(session, first.next_steps, today=TODAY)
    assert {c.contact_id for c in first.next_steps} & {c.contact_id for c in second.next_steps} == set()


def test_ruhiger_zustand_meldet_entwarnung(session):
    p = _person(session, "Nadine", interval=30)
    cs.log_interaction(session, p.id, KIND_MEET, occurred_on=ago(3))
    session.flush()

    cockpit = dash.build_cockpit(session, today=TODAY)
    assert cockpit.next_steps == []
    assert cockpit.summary.is_calm
    assert cockpit.message == dash.CALM_MESSAGE


def test_erledigter_termin_wird_zur_interaktion(session):
    p = _person(session, "Marko", interval=21)
    act = cs.plan_activity(session, "Spieleabend", ago(2), [p.id])
    session.flush()
    cs.complete_activity(session, act.id)
    session.flush()

    cand = {c.name: c for c in rot.evaluate_all(session, today=TODAY)}["Marko"]
    assert cand.freshness.real_gap_days == 2
    assert not cand.blocks


def test_begruendung_ist_lesbar_und_ohne_punktzahl(session):
    p = _person(session, "Patrick", importance=5, interval=30)
    cs.log_interaction(session, p.id, KIND_MEET, occurred_on=ago(62))
    session.flush()
    cand = rot.evaluate_all(session, today=TODAY)[0]
    assert cand.why()
    assert all(isinstance(r, str) and r for r in cand.why())
    assert "wichtiger Mensch fuer dich" in cand.why()
    assert str(cand.score) not in cand.headline()
