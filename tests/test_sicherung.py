"""Die Sicherung ist in sich stimmig, geschuetzt und begrenzt.

Frueher war das ein ``shutil.copy2``. Eine SQLite-Datei laesst sich aber nicht
gefahrlos kopieren, waehrend jemand hineinschreibt: Die Kopie kann mitten in
einer Transaktion entstehen und ist dann unbrauchbar - was erst auffaellt,
wenn man sie zurueckspielen will.
"""

from __future__ import annotations

import os
import sqlite3
import stat

import pytest

from freizeitmanager import paths
from freizeitmanager.database import db


@pytest.fixture()
def datenordner(tmp_path, monkeypatch):
    monkeypatch.setenv("FREIZEITMANAGER_DATA_DIR", str(tmp_path))
    db.reset_engine()
    db.initialize_database()
    yield tmp_path
    db.reset_engine()


def test_die_sicherung_ist_lesbar_und_vollstaendig(datenordner):
    pfad = db.create_backup()
    assert pfad is not None and pfad.is_file()
    with sqlite3.connect(pfad) as verbindung:
        assert verbindung.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # Die Tabellen der Anwendung sind mitgekommen, nicht nur eine leere Datei.
        tabellen = {
            row[0]
            for row in verbindung.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "contacts" in tabellen, tabellen


def test_die_sicherung_haelt_einer_offenen_transaktion_stand(datenordner):
    """Der eigentliche Grund fuer die Umstellung: Wer sichert, waehrend jemand
    schreibt, bekam vorher womoeglich eine Kopie mitten in der Transaktion."""
    from freizeitmanager.database.models import Contact

    with db.get_session() as sitzung:
        sitzung.add(Contact(name="Probe Person"))
        sitzung.flush()  # geschrieben, aber noch nicht bestaetigt
        pfad = db.create_backup()
    with sqlite3.connect(pfad) as verbindung:
        assert verbindung.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


@pytest.mark.skipif(os.name == "nt", reason="Windows kennt keine POSIX-Modi")
def test_die_sicherung_gehoert_nur_dem_eigentuemer(datenordner):
    """Sie traegt dieselben personenbezogenen Daten wie die Datenbank."""
    pfad = db.create_backup()
    assert stat.S_IMODE(pfad.stat().st_mode) == 0o600


def test_alte_sicherungen_werden_aufgeraeumt(datenordner, monkeypatch):
    """Ohne Grenze fuellt sich der Ordner still, bis die Platte voll ist - und
    dann scheitert die Sicherung genau dann, wenn man sie braucht."""
    monkeypatch.setattr(db, "BACKUP_AUFBEWAHREN", 3)
    for nummer in range(6):
        # Die Namen tragen einen Zeitstempel auf Sekunden; hier von Hand
        # gesetzt, damit der Test nicht sechs Sekunden dauert.
        (paths.backups_dir() / f"freizeitmanager_2026010{nummer}_000000.db").touch()
    db.create_backup()
    verblieben = sorted(paths.backups_dir().glob("freizeitmanager_*.db"))
    assert len(verblieben) == 3, [p.name for p in verblieben]
    # Die juengsten bleiben - die neue Sicherung ist darunter.
    assert any("2026010" not in p.name for p in verblieben)


def test_ohne_datenbank_gibt_es_nichts_zu_sichern(tmp_path, monkeypatch):
    monkeypatch.setenv("FREIZEITMANAGER_DATA_DIR", str(tmp_path))
    db.reset_engine()
    try:
        assert db.create_backup() is None
    finally:
        db.reset_engine()
