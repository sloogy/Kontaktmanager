#!/usr/bin/env python3
"""Startet die Oberflaeche headless und klickt die Kernwege durch.

Faengt die haeufigsten Release-Blocker ab: fehlendes Qt, kaputte Importe,
Fenster laesst sich nicht bauen, Seitenwechsel stuerzt ab, Schnellaktion
schreibt nicht. Ersetzt keine manuelle Pruefung, aber verhindert, dass ein
offensichtlich totes Paket veroeffentlicht wird.
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    temp = tempfile.TemporaryDirectory(prefix="fzm_smoke_")
    os.environ.setdefault("FREIZEITMANAGER_DATA_DIR", temp.name)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError as exc:
        print(f"UEBERSPRUNGEN: PySide6 fehlt ({exc.name})")
        return 77

    try:
        from freizeitmanager.database import db
        from freizeitmanager.database.models import Interaction
        from freizeitmanager.logic import contact_service as cs
        from freizeitmanager.ui.main_window import MainWindow
    except Exception as exc:
        print(f"FEHLER: Import/Start fehlgeschlagen: {exc}")
        return 1

    app = QApplication.instance() or QApplication([])
    db.initialize_database()

    today = date.today()
    with db.get_session() as session:
        person = cs.create_contact(session, "Rauchtest", importance=5,
                                   target_interval_days=21, groups=["Freunde"])
        session.flush()
        cs.log_interaction(session, person.id, "meet", occurred_on=today - timedelta(60))
        contact_id = person.id

    window = MainWindow()
    window.resize(1180, 800)
    window.show()
    app.processEvents()

    checks: list[str] = []

    if not window._dashboard._cards:
        checks.append("Cockpit zeigt keinen Vorschlag, obwohl ein Kontakt ueberfaellig ist")

    for page in ("contacts", "settings"):
        window.show_page(page)
        app.processEvents()
    window._toggle_mode()
    window.show_page("rotation")
    app.processEvents()
    window._toggle_mode()
    window.show_page("cockpit")
    app.processEvents()

    if window._dashboard._cards:
        window._dashboard._log_done(contact_id, "call")
        app.processEvents()
        with db.get_session() as session:
            rows = session.query(Interaction).filter_by(contact_id=contact_id).all()
        if len(rows) != 2 or rows[-1].kind != "call":
            checks.append("Schnellaktion hat keine Interaktion geschrieben")

    if checks:
        for problem in checks:
            print(f"FEHLER: {problem}")
        return 1
    print("Rauchtest bestanden: Fenster, Seitenwechsel, Modus, Schnellaktion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
