#!/usr/bin/env python3
"""FreizeitManager - Einstiegspunkt.

Laeuft eigenstaendig und als LifePlanner-Modul. Im Modulbetrieb gibt der Host
den Datenordner ueber Umgebungsvariablen vor (siehe freizeitmanager/paths.py).
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from freizeitmanager import paths
from freizeitmanager.app_info import APP_NAME, APP_VERSION
from freizeitmanager.database import db
from freizeitmanager.database.models import Contact
from freizeitmanager.integration import lifeplanner_bridge as bridge
from freizeitmanager.integration.legacy_import import import_legacy

_log = logging.getLogger(__name__)


def _say(message: str) -> None:
    """Ausgabe, die auch im Fenstermodus ueberlebt.

    PyInstaller baut mit ``console=False`` ein Programm ohne Konsole; dort ist
    ``sys.stdout`` None und ein einfaches ``print`` bricht ab. Der Selbsttest
    darf daran nicht scheitern - sein Ergebnis ist der Exitcode.
    """
    stream = sys.stdout or sys.stderr
    if stream is None:
        return
    try:
        stream.write(message + "\n")
        stream.flush()
    except (OSError, ValueError):
        pass


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


def _smoke() -> int:
    """Selbsttest des gebauten Programms.

    Baut Datenbank und Fenster auf und beendet sich sofort. Genau das faengt
    fehlende PyInstaller-Importe ab - der haeufigste Grund, warum ein Paket
    zwar entsteht, aber beim Doppelklick nichts passiert.
    """
    import tempfile
    with tempfile.TemporaryDirectory(prefix="fzm_smoke_") as temp:
        os.environ["FREIZEITMANAGER_DATA_DIR"] = temp
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        db.reset_engine()
        db.initialize_database()
        from PySide6.QtWidgets import QApplication

        from freizeitmanager.ui.main_window import MainWindow
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        window.show()
        app.processEvents()
        for page in ("contacts", "settings", "cockpit"):
            window.show_page(page)
            app.processEvents()
        window.close()
        db.reset_engine()
    _say(f"{APP_NAME} {APP_VERSION}: Selbsttest bestanden.")
    return 0


def main() -> int:
    if "--version" in sys.argv:
        _say(f"{APP_NAME} {APP_VERSION}")
        return 0
    if "--smoke" in sys.argv:
        return _smoke()

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
