from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from freizeitmanager.database import db
from freizeitmanager.database.models import Group, RelationshipLevel
from freizeitmanager.integration import lifeplanner_bridge as bridge
from freizeitmanager.integration.legacy_import import import_legacy
from freizeitmanager.logic import contact_service as cs
from freizeitmanager.logic import dashboard_service as dash

TODAY = date(2026, 8, 20)


def test_standalone_schreibt_keine_bridge(session, monkeypatch):
    monkeypatch.delenv("LIFEPLANNER_BRIDGE_DIR", raising=False)
    cockpit = dash.build_cockpit(session, today=TODAY)
    assert bridge.publish_focus(cockpit, TODAY) is None


def test_bridge_outbox_haelt_den_modulvertrag_ein(session, tmp_path, monkeypatch):
    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path / "bridge"))
    monkeypatch.setenv("LIFEPLANNER_PROFILE_ID", "default")

    p = cs.create_contact(session, "Patrick", importance=5, target_interval_days=30)
    cs.log_interaction(session, p.id, "meet", occurred_on=TODAY - timedelta(62))
    session.flush()

    cockpit = dash.build_cockpit(session, today=TODAY)
    target = bridge.publish_focus(cockpit, TODAY)
    assert target is not None and target.name == "freizeitmanager_to_lifeplanner.jsonl"

    lines = target.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    manifest = records[0]
    assert manifest["schema"] == bridge.MANIFEST_SCHEMA
    assert manifest["module"] == "freizeitmanager"
    assert manifest["counts"]["due_now"] == 1
    assert all(r["schema"] == "freizeitmanager.focus.v1" for r in records[1:])
    # Der Host darf nie Rohdaten sehen.
    assert not any("note" in r or "notes" in r for r in records)


def test_bridge_schreibt_atomar_ohne_tempdatei(session, tmp_path, monkeypatch):
    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path / "bridge"))
    cockpit = dash.build_cockpit(session, today=TODAY)
    bridge.publish_focus(cockpit, TODAY)
    leftovers = list((tmp_path / "bridge").glob("*.tmp"))
    assert leftovers == []


def test_event_landet_im_profilordner(session, tmp_path, monkeypatch):
    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path / "profile" / "bridge"))
    bridge.emit_event(bridge.EVENT_INTERACTION_LOGGED, {"contact_id": 1})
    lines = (tmp_path / "profile" / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    assert record["schema"] == "lifeplanner.event.v1"
    assert record["event"] == "freizeit.interaction.logged"


def _legacy_db(path):
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        CREATE TABLE kontakte (id INTEGER PRIMARY KEY, name TEXT, gruppe TEXT,
            beziehungsgrad TEXT, letztes_treffen TEXT, naechstes_treffen TEXT,
            geplantes_treffen TEXT, notizen TEXT, ist_gebucht INTEGER);
        CREATE TABLE beziehungsgrade (beziehungsgrad TEXT PRIMARY KEY, exclude_3_day_rule INTEGER);
        CREATE TABLE groups (gruppe TEXT PRIMARY KEY);
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO groups VALUES ('Segelclub');
        INSERT INTO beziehungsgrade VALUES ('Nachbar', 0);
        INSERT INTO settings VALUES ('max_days_per_week','4'),('allowed_weekdays','0,1,2');
        INSERT INTO kontakte VALUES (1,'Alt-Marko','Segelclub','Nachbar','12.07.2026',NULL,NULL,'Notiz',0);
    """)
    conn.commit()
    conn.close()
    return path


def test_legacy_import_uebernimmt_stammdaten_und_historie(session, tmp_path):
    legacy = _legacy_db(tmp_path / "termine.db")
    stats = import_legacy(session, legacy)
    session.flush()

    assert stats["groups"] == 1 and stats["levels"] == 1 and stats["contacts"] == 1
    assert session.query(Group).filter_by(name="Segelclub").one()
    assert session.query(RelationshipLevel).filter_by(name="Nachbar").one()
    assert db.get_int_setting(session, "capacity.max_social_days_per_week") == 4
    # Freitext wurde zu echten Referenzen, letztes_treffen zur Interaktion.
    contact = session.query(cs.Contact).filter_by(name="Alt-Marko").one()
    assert [g.name for g in contact.groups] == ["Segelclub"]
    assert contact.level.name == "Nachbar"
    assert contact.interactions[0].occurred_on == date(2026, 7, 12)


def test_gruppen_und_tags_werden_wirklich_verknuepft(session):
    c = cs.create_contact(session, "Marko", groups=["Freunde"], tags=["Brettspiele", "Essen"])
    session.flush()
    session.expire_all()
    c = session.query(cs.Contact).filter_by(name="Marko").one()
    assert [g.name for g in c.groups] == ["Freunde"]
    assert sorted(t.name for t in c.tags) == ["Brettspiele", "Essen"]


def test_gruppe_umbenennen_bricht_die_referenz_nicht(session):
    """Der Kernfehler des alten Modells: Freitext-Gruppen wurden verwaist."""
    c = cs.create_contact(session, "Marko", groups=["Freunde"])
    session.flush()
    group = session.query(Group).filter_by(name="Freunde").one()
    group.name = "Enge Freunde"
    session.flush()
    session.expire_all()
    c = session.query(cs.Contact).filter_by(name="Marko").one()
    assert [g.name for g in c.groups] == ["Enge Freunde"]
