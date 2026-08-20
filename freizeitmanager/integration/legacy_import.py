"""Einmalige Uebernahme aus dem alten Kontaktmanager (``termine.db``).

Der alte Bestand enthaelt keine Kontakte, aber gepflegte Gruppen,
Beziehungsgrade und Kapazitaetseinstellungen. Die werden uebernommen,
Freitextreferenzen dabei in echte Datensaetze aufgeloest.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from freizeitmanager.database import db
from freizeitmanager.database.models import Group, RelationshipLevel
from freizeitmanager.logic.contact_service import create_contact

_log = logging.getLogger(__name__)

# Alte Schluessel -> neue Schluessel. Nicht gelistete werden ignoriert.
SETTING_MAP = {
    "max_days_per_week": "capacity.max_social_days_per_week",
    "max_days_per_week_active": "capacity.max_social_days_per_week_active",
    "max_weekends_per_month": "capacity.max_weekends_per_month",
    "max_weekends_per_month_active": "capacity.max_weekends_per_month_active",
    "allowed_weekdays": "capacity.allowed_weekdays",
    "allowed_weekdays_active": "capacity.allowed_weekdays_active",
}


def _parse_date(raw) -> date | None:
    text = str(raw or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def import_legacy(session: Session, legacy_db: Path) -> dict[str, int]:
    """Uebernimmt Stammdaten und - falls vorhanden - Kontakte."""
    stats = {"groups": 0, "levels": 0, "settings": 0, "contacts": 0, "interactions": 0}
    if not Path(legacy_db).is_file():
        return stats

    conn = sqlite3.connect(str(legacy_db))
    conn.row_factory = sqlite3.Row
    tables = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}

    existing_groups = {g.name for g in session.query(Group)}
    if "groups" in tables:
        for row in conn.execute("select gruppe from groups"):
            name = (row["gruppe"] or "").strip()
            if name and name not in existing_groups:
                session.add(Group(name=name))
                existing_groups.add(name)
                stats["groups"] += 1

    existing_levels = {l.name for l in session.query(RelationshipLevel)}
    if "beziehungsgrade" in tables:
        for row in conn.execute("select beziehungsgrad from beziehungsgrade"):
            name = (row["beziehungsgrad"] or "").strip()
            if name and name not in existing_levels:
                session.add(RelationshipLevel(name=name, sort_order=99))
                existing_levels.add(name)
                stats["levels"] += 1

    if "settings" in tables:
        for row in conn.execute("select key, value from settings"):
            new_key = SETTING_MAP.get(row["key"])
            if new_key:
                db.set_setting(session, new_key, str(row["value"]))
                stats["settings"] += 1

    session.flush()

    if "kontakte" in tables:
        from freizeitmanager.database.models import KIND_MEET
        from freizeitmanager.logic.contact_service import log_interaction
        for row in conn.execute("select * from kontakte"):
            name = (row["name"] or "").strip()
            if not name:
                continue
            contact = create_contact(session, name,
                                     level=(row["beziehungsgrad"] or "").strip() or None,
                                     groups=[g for g in [(row["gruppe"] or "").strip()] if g],
                                     notes=row["notizen"])
            stats["contacts"] += 1
            # "letztes_treffen" wird zur ersten Interaktion der Historie.
            last = _parse_date(row["letztes_treffen"])
            if last is not None:
                log_interaction(session, contact.id, KIND_MEET, occurred_on=last,
                                note="uebernommen aus Kontaktmanager")
                stats["interactions"] += 1

    conn.close()
    _log.info("Legacy-Import: %s", stats)
    return stats
