#!/usr/bin/env python3
"""FreizeitManager - Einstiegspunkt.

Laeuft eigenstaendig und als LifePlanner-Modul. Im Modulbetrieb gibt der Host
den Datenordner ueber Umgebungsvariablen vor (siehe freizeitmanager/paths.py).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from freizeitmanager import paths                                # noqa: E402
from freizeitmanager.app_info import APP_NAME, APP_VERSION       # noqa: E402
from freizeitmanager.database import db                          # noqa: E402
from freizeitmanager.database.models import Contact              # noqa: E402
from freizeitmanager.integration import lifeplanner_bridge as bridge  # noqa: E402
from freizeitmanager.integration.legacy_import import import_legacy   # noqa: E402

_log = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr),
                  logging.FileHandler(paths.logs_dir() / "freizeitmanager.log", encoding="utf-8")],
    )


def _import_legacy_once() -> None:
    """Uebernimmt den alten Kontaktmanager-Bestand beim allerersten Start."""
    root = Path(__file__).resolve().parent
    legacy = next((p for p in (root / "legacy" / "termine.db", root / "termine.db")
                   if p.is_file()), None)
    if legacy is None:
        return
    with db.get_session() as session:
        if session.query(Contact).first() is not None:
            return
        if db.get_setting(session, "legacy.imported", "0") == "1":
            return
        stats = import_legacy(session, legacy)
        db.set_setting(session, "legacy.imported", "1")
    _log.info("Alter Bestand uebernommen: %s", stats)


def main() -> int:
    _setup_logging()
    _log.info("%s %s startet (%s)", APP_NAME, APP_VERSION,
              "LifePlanner-Modul" if paths.is_hosted() else "eigenstaendig")
    db.initialize_database()
    _import_legacy_once()
    bridge.emit_event("module.started", {"version": APP_VERSION})

    from PySide6.QtWidgets import QApplication
    from freizeitmanager.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    window = MainWindow()
    window.show()
    try:
        return app.exec()
    finally:
        bridge.emit_event("module.stopped", {"version": APP_VERSION})


if __name__ == "__main__":
    raise SystemExit(main())
