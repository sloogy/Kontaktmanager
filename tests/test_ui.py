"""UI-Rauchtest: Die Schnellaktionen muessen wirklich in der Datenbank landen.

Lehre aus FPM 0.2.77: Eine zentrale Aktion, die still fehlschlaegt, ist
schlimmer als eine fehlende Aktion.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from freizeitmanager.database.models import (Contact, Interaction,   # noqa: E402
                                             RotationSnooze)
from freizeitmanager.logic import contact_service as cs             # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def seeded(session):
    today = date.today()
    for name, interval, gap in (("Marko", 21, 45), ("Patrick", 30, 70), ("Nadine", 30, 4)):
        person = cs.create_contact(session, name, importance=5, target_interval_days=interval)
        cs.log_interaction(session, person.id, "meet", occurred_on=today - timedelta(gap))
    session.commit()
    return session


def test_cockpit_zeigt_hoechstens_drei_karten(qapp, seeded):
    from freizeitmanager.ui.dashboard_widget import DashboardWidget
    widget = DashboardWidget()
    assert len(widget._cards) <= 3
    assert widget._cards, "ueberfaellige Kontakte muessen im Fokus erscheinen"
    names = [c.candidate.name for c in widget._cards]
    assert "Nadine" not in names   # frisch, gehoert nicht in den Fokus


def test_erledigt_taste_schreibt_wirklich_eine_interaktion(qapp, seeded, session):
    from freizeitmanager.ui.dashboard_widget import DashboardWidget
    widget = DashboardWidget()
    card = widget._cards[0]
    contact_id = card.candidate.contact_id
    before = session.query(Interaction).filter_by(contact_id=contact_id).count()

    widget._log_done(contact_id, "call")

    session.expire_all()
    rows = session.query(Interaction).filter_by(contact_id=contact_id).all()
    assert len(rows) == before + 1
    assert rows[-1].kind == "call"
    assert rows[-1].occurred_on == date.today()


def test_spaeter_legt_snooze_an_und_entfernt_aus_dem_fokus(qapp, seeded, session):
    from freizeitmanager.ui.dashboard_widget import DashboardWidget
    widget = DashboardWidget()
    contact_id = widget._cards[0].candidate.contact_id

    widget._snooze(contact_id, 7)

    session.expire_all()
    snooze = session.query(RotationSnooze).filter_by(contact_id=contact_id).one()
    assert snooze.snoozed_until == date.today() + timedelta(7)
    assert contact_id not in [c.candidate.contact_id for c in widget._cards]


def test_reroll_zeigt_andere_personen(qapp, session):
    from freizeitmanager.ui.dashboard_widget import DashboardWidget
    today = date.today()
    for i in range(8):
        person = cs.create_contact(session, f"Person {i:02d}", importance=4, target_interval_days=21)
        cs.log_interaction(session, person.id, "meet", occurred_on=today - timedelta(60 + i))
    session.commit()

    widget = DashboardWidget()
    first = {c.candidate.contact_id for c in widget._cards}
    widget._reroll()
    second = {c.candidate.contact_id for c in widget._cards}
    assert first and second and not (first & second)


def test_energiewahl_aendert_den_vorschlag(qapp, seeded):
    from freizeitmanager.ui.dashboard_widget import DashboardWidget
    from freizeitmanager.logic import rotation_engine as rot
    widget = DashboardWidget()

    social = next(b for b in widget._energy_group.buttons() if b.property("energy") == rot.ENERGY_SOCIAL)
    widget._energy_chosen(social)
    assert any(c.candidate.suggestion == rot.SUGGESTION_MEET for c in widget._cards)

    low = next(b for b in widget._energy_group.buttons() if b.property("energy") == rot.ENERGY_LOW)
    widget._energy_chosen(low)
    assert all(c.candidate.suggestion != rot.SUGGESTION_MEET for c in widget._cards)


def test_ruhiger_zustand_zeigt_keine_leere_tabelle(qapp, session):
    from freizeitmanager.ui.common import CalmCard
    from freizeitmanager.ui.dashboard_widget import DashboardWidget
    person = cs.create_contact(session, "Nadine", target_interval_days=30)
    cs.log_interaction(session, person.id, "meet", occurred_on=date.today() - timedelta(2))
    session.commit()

    widget = DashboardWidget()
    assert widget._cards == []
    assert widget._steps_box.count() == 1
    assert isinstance(widget._steps_box.itemAt(0).widget(), CalmCard)
    assert widget._planned_group.isHidden()           # leere Bereiche verschwinden
    assert widget._reroll_button.isHidden()


def test_kontaktliste_zeigt_ampel_und_klartext(qapp, seeded):
    from freizeitmanager.ui.contacts_widget import ContactsWidget
    widget = ContactsWidget()
    assert widget._table.rowCount() == 3
    stati = [widget._table.item(r, 6).text() for r in range(3)]
    assert any("guter Zeitpunkt" in s or "lange still" in s for s in stati)
    assert all(not s.replace(".", "").isdigit() for s in stati)   # nie eine Punktzahl


def test_expertenmodus_blendet_rotation_ein(qapp, session):
    from freizeitmanager.ui.main_window import MainWindow
    window = MainWindow()
    assert window._nav_buttons["rotation"].isHidden()
    window._toggle_mode()
    assert not window._nav_buttons["rotation"].isHidden()
    window._toggle_mode()
