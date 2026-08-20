"""Anstehende Geburtstage im Cockpit.

Die Raender sind hier die eigentliche Arbeit: der Jahreswechsel, der
29. Februar und der Fall ohne Jahrgang, in dem es kein Alter zu nennen gibt.
"""
from __future__ import annotations

from datetime import date

from freizeitmanager.database.models import STATUS_ARCHIVED
from freizeitmanager.logic import contact_service as cs
from freizeitmanager.logic import dashboard_service as dash
from freizeitmanager.logic.contact_import import YEAR_UNKNOWN


def test_naechstes_vorkommen_zaehlt_heute_mit():
    assert dash._next_occurrence(date(1984, 3, 17), date(2026, 3, 17)) == date(2026, 3, 17)


def test_naechstes_vorkommen_springt_ins_neue_jahr():
    """Am 20. Dezember ist ein Geburtstag am 5. Januar der naechste."""
    assert dash._next_occurrence(date(1984, 1, 5), date(2026, 12, 20)) == date(2027, 1, 5)


def test_schalttag_bleibt_im_februar():
    assert dash._next_occurrence(date(1984, 2, 29), date(2026, 1, 1)) == date(2026, 2, 28)
    # Im Schaltjahr steht der echte Tag wieder zur Verfuegung.
    assert dash._next_occurrence(date(1984, 2, 29), date(2028, 1, 1)) == date(2028, 2, 29)


def test_nur_geburtstage_im_zeitfenster(session):
    cs.create_contact(session, "Bald", birthday=date(1990, 8, 25))
    cs.create_contact(session, "Spaeter", birthday=date(1990, 11, 2))
    cs.create_contact(session, "Ohne", birthday=None)
    session.flush()

    found = dash._birthdays(session, date(2026, 8, 20), days=30)
    assert [b.name for b in found] == ["Bald"]


def test_archivierte_kontakte_tauchen_nicht_auf(session):
    person = cs.create_contact(session, "Alt", birthday=date(1990, 8, 25))
    person.status = STATUS_ARCHIVED
    session.flush()
    assert dash._birthdays(session, date(2026, 8, 20)) == []


def test_alter_nur_bei_echtem_jahrgang(session):
    cs.create_contact(session, "Mit Jahrgang", birthday=date(1984, 8, 25))
    cs.create_contact(session, "Ohne Jahrgang", birthday=date(YEAR_UNKNOWN, 8, 26),
                      birthday_has_year=False)
    session.flush()

    found = {b.name: b for b in dash._birthdays(session, date(2026, 8, 20))}
    assert found["Mit Jahrgang"].turns == 42
    # Kein erfundenes Alter aus dem Platzhalterjahr.
    assert found["Ohne Jahrgang"].turns is None
    assert "126" not in found["Ohne Jahrgang"].label()


def test_geburtstag_heute_ist_als_heute_markiert(session):
    cs.create_contact(session, "Heute", birthday=date(1990, 8, 20))
    session.flush()
    found = dash._birthdays(session, date(2026, 8, 20))
    assert found[0].is_today is True
    assert found[0].on == date(2026, 8, 20)


def test_cockpit_liefert_die_geburtstage_mit(session):
    cs.create_contact(session, "Marko", birthday=date(1984, 8, 25))
    session.flush()
    cockpit = dash.build_cockpit(session, today=date(2026, 8, 20), remember=False)
    assert [b.name for b in cockpit.birthdays] == ["Marko"]
    assert "Marko" in cockpit.birthdays[0].label()
