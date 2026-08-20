"""Pfadaufloesung fuer Standalone- und LifePlanner-Modulbetrieb.

Regel aus dem Modul-Host-Vertrag: Der Host gibt den Datenordner ueber
Umgebungsvariablen vor. Fehlt der Host, faellt das Modul auf einen eigenen,
plattformueblichen Ordner zurueck - niemals auf das Arbeitsverzeichnis.
Genau das war der Fehler des alten Kontaktmanagers (``termine.db`` landete
dort, wo das Programm zufaellig gestartet wurde).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from freizeitmanager.app_info import APP_ID, DB_FILENAME

_TRUE = {"1", "true", "yes", "on"}


def _env_path(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    return Path(raw).expanduser() if raw else None


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def is_portable() -> bool:
    raw = os.environ.get("FREIZEITMANAGER_PORTABLE", "").strip().lower()
    return raw in _TRUE or (app_dir() / "portable.flag").is_file()


def data_dir() -> Path:
    """Datenordner des Moduls. Host-Vorgabe hat immer Vorrang."""
    base = _env_path("FREIZEITMANAGER_DATA_DIR") or _env_path("LIFEPLANNER_MODULE_DATA_DIR")
    if base is None:
        if is_portable() or not getattr(sys, "frozen", False):
            base = app_dir() / "data"
        elif sys.platform.startswith("win"):
            local = os.environ.get("LOCALAPPDATA", "").strip()
            base = Path(local) / "FreizeitManager" if local else Path.home() / "AppData/Local/FreizeitManager"
        else:
            xdg = os.environ.get("XDG_DATA_HOME", "").strip()
            base = Path(xdg) / APP_ID if xdg else Path.home() / ".local/share" / APP_ID
    base.mkdir(parents=True, exist_ok=True)
    return base.resolve()


def db_path() -> Path:
    override = _env_path("FREIZEITMANAGER_DB_PATH")
    if override is not None:
        override.parent.mkdir(parents=True, exist_ok=True)
        return override.resolve()
    return data_dir() / DB_FILENAME


def backups_dir() -> Path:
    path = data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bridge_dir() -> Path | None:
    """Austauschordner des Hosts. ``None`` bedeutet Standalone-Betrieb."""
    path = _env_path("LIFEPLANNER_BRIDGE_DIR")
    if path is None:
        return None
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def is_hosted() -> bool:
    return bridge_dir() is not None
