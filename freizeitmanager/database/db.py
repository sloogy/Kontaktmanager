"""Datenbankzugriff, Schemaversionierung und Standardwerte."""
from __future__ import annotations

import logging
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from freizeitmanager import paths
from freizeitmanager.database.models import AppSetting, Base, Group, RelationshipLevel, SchemaMigration

_log = logging.getLogger(__name__)

SCHEMA_VERSION = 1

_engine = None
_SessionFactory = None

# Standardeinstellungen. Die Kapazitaetsgrenzen sind die sinnvoll
# weiterentwickelten Felder des alten Kontaktmanagers.
DEFAULT_SETTINGS: dict[str, str] = {
    "capacity.max_social_days_per_week": "3",
    "capacity.max_social_days_per_week_active": "1",
    "capacity.max_weekends_per_month": "3",
    "capacity.max_weekends_per_month_active": "1",
    "capacity.allowed_weekdays": "0,1,2,3,4,5,6",
    "capacity.allowed_weekdays_active": "0",
    "capacity.min_days_between_contacts": "2",
    "focus.max_suggestions": "3",
    "focus.energy_state": "normal",
    "focus.energy_state_date": "",
    "ui.mode": "simple",
    "ui.language": "de",
    "bridge.enabled": "1",
}

# Beziehungsgrade und Gruppen sind Nutzerdaten: Sie werden einmalig in der
# aktiven Sprache angelegt und danach nicht mehr angefasst. Sie spaeter
# mitzuuebersetzen waere falsch - der Nutzer darf sie umbenennen.
DEFAULT_LEVELS: list[tuple[str, int, int, int]] = [
    # Uebersetzungsschluessel, sort_order, default_interval_days, default_importance
    ("seed.level_family", 10, 21, 5),
    ("seed.level_close_friend", 20, 21, 5),
    ("seed.level_friend", 30, 45, 4),
    ("seed.level_acquaintance", 40, 120, 2),
]

DEFAULT_GROUPS = ["seed.group_family", "seed.group_friends",
                  "seed.group_work", "seed.group_unknown"]


def get_engine():
    global _engine, _SessionFactory
    if _engine is None:
        target = paths.db_path()
        _engine = create_engine(f"sqlite:///{target}", future=True)

        @event.listens_for(_engine, "connect")
        def _fk_on(dbapi_conn, _rec):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        _SessionFactory = sessionmaker(bind=_engine, future=True, expire_on_commit=False)
        _log.info("Datenbank: %s", target)
    return _engine


def reset_engine() -> None:
    """Verbindung loesen - noetig fuer Tests und Profilwechsel."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None


@contextmanager
def get_session() -> Session:
    get_engine()
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def initialize_database() -> None:
    """Schema anlegen, Migrationen fahren, Standardwerte ergaenzen."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    with get_session() as s:
        applied = {row.version for row in s.scalars(select(SchemaMigration))}
        if SCHEMA_VERSION not in applied:
            s.add(SchemaMigration(version=SCHEMA_VERSION, applied_at=datetime.now()))
        _seed_settings(s)
        _seed_levels(s)
        _seed_groups(s)


def _seed_settings(s: Session) -> None:
    existing = {row.key for row in s.scalars(select(AppSetting))}
    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            s.add(AppSetting(key=key, value=value))


def _seed_levels(s: Session) -> None:
    from freizeitmanager.i18n.translator import t
    if s.scalar(select(RelationshipLevel).limit(1)) is not None:
        return
    for key, order, interval, importance in DEFAULT_LEVELS:
        s.add(RelationshipLevel(name=t(key), sort_order=order,
                                default_interval_days=interval,
                                default_importance=importance))


def _seed_groups(s: Session) -> None:
    from freizeitmanager.i18n.translator import t
    if s.scalar(select(Group).limit(1)) is not None:
        return
    for idx, key in enumerate(DEFAULT_GROUPS):
        s.add(Group(name=t(key), sort_order=idx * 10))


# ── Einstellungen ─────────────────────────────────────────────────────────────

def get_setting(session: Session, key: str, default: str = "") -> str:
    row = session.get(AppSetting, key)
    if row is None or row.value is None:
        return DEFAULT_SETTINGS.get(key, default)
    return row.value


def get_int_setting(session: Session, key: str, default: int = 0) -> int:
    try:
        return int(str(get_setting(session, key, str(default))).strip())
    except (TypeError, ValueError):
        return default


def get_bool_setting(session: Session, key: str, default: bool = False) -> bool:
    raw = str(get_setting(session, key, "1" if default else "0")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def set_setting(session: Session, key: str, value: str) -> None:
    row = session.get(AppSetting, key)
    if row is None:
        session.add(AppSetting(key=key, value=str(value)))
    else:
        row.value = str(value)


# ── Sicherung ─────────────────────────────────────────────────────────────────

def create_backup() -> Path | None:
    src = paths.db_path()
    if not src.is_file():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = paths.backups_dir() / f"freizeitmanager_{stamp}.db"
    shutil.copy2(src, dst)
    return dst
