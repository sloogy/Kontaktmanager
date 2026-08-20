from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("FREIZEITMANAGER_DB_PATH", str(tmp_path / "test.db"))
    from freizeitmanager.database import db
    db.reset_engine()
    db.initialize_database()
    with db.get_session() as s:
        yield s
    db.reset_engine()


@pytest.fixture()
def today() -> date:
    return date(2026, 8, 20)  # Donnerstag


@pytest.fixture()
def days():
    return lambda base, n: base - timedelta(days=n)
