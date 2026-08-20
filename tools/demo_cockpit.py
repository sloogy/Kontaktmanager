"""Zeigt das Fokus-Cockpit mit Beispieldaten - ohne Qt, rein zur Kontrolle."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FREIZEITMANAGER_DB_PATH", os.path.join(tempfile.mkdtemp(), "demo.db"))

from freizeitmanager.database import db                     # noqa: E402
from freizeitmanager.database.models import (KIND_CALL_LONG, KIND_MEET,       # noqa: E402
                                             KIND_MESSAGE, KIND_REACTION)
from freizeitmanager.logic import contact_service as cs     # noqa: E402
from freizeitmanager.logic import dashboard_service as dash  # noqa: E402
from freizeitmanager.logic import rotation_engine as rot    # noqa: E402

TODAY = date(2026, 8, 20)


def ago(n: int) -> date:
    return TODAY - timedelta(days=n)


def seed(s):
    marko = cs.create_contact(s, "Marko", level="Enger Freund", target_interval_days=21,
                              tags=["Brettspiele", "Essen"], groups=["Freunde"])
    nadine = cs.create_contact(s, "Nadine", level="Enger Freund", target_interval_days=30,
                               groups=["Freunde"])
    patrick = cs.create_contact(s, "Patrick", level="Enger Freund", target_interval_days=30,
                                tags=["Wandern"], groups=["Freunde"])
    leandro = cs.create_contact(s, "Leandro", level="Freund", target_interval_days=30,
                                groups=["Freunde"])
    kollege = cs.create_contact(s, "Kollege X", level="Bekannter", target_interval_days=90,
                                groups=["Arbeit"])
    s.flush()

    cs.log_interaction(s, marko.id, KIND_MEET, occurred_on=ago(32))
    cs.log_interaction(s, marko.id, KIND_REACTION, occurred_on=ago(1))
    cs.log_interaction(s, nadine.id, KIND_MEET, occurred_on=ago(8))
    cs.log_interaction(s, patrick.id, KIND_MEET, occurred_on=ago(62))
    cs.log_interaction(s, patrick.id, KIND_MESSAGE, occurred_on=ago(20))
    cs.log_interaction(s, leandro.id, KIND_CALL_LONG, occurred_on=ago(18))
    cs.plan_activity(s, "Spieleabend", TODAY + timedelta(2), [leandro.id])
    cs.log_interaction(s, kollege.id, KIND_MEET, occurred_on=ago(200))
    s.flush()


def render(cockpit, title):
    print("\n" + "=" * 74)
    print(f"  {title}   (Energie: {cockpit.summary.energy})")
    print("=" * 74)
    tiles = cockpit.summary.tiles()
    print("  " + " | ".join(f"{n:<14}" for n, _ in tiles))
    print("  " + " | ".join(f"{v:<14}" for _, v in tiles))
    for note in cockpit.summary.capacity_notes:
        print(f"  ! {note}")
    if cockpit.message:
        print(f"\n  {cockpit.message}")
    if cockpit.next_steps:
        print("\n  Meine naechsten Schritte")
        print("  " + "-" * 70)
        for c in cockpit.next_steps:
            print(f"  {c.headline()}")
            print(f"     {c.suggestion_icon} {c.suggestion_text} · {c.suggestion_effort}"
                  f"   (zuletzt {c.gap_text})")
            for reason in c.why():
                print(f"       - {reason}")
            print(f"     [Erledigt] [Planen] [Spaeter]    intern: {c.score} {c.breakdown}")
    if cockpit.upcoming:
        print("\n  Geplant")
        for p in cockpit.upcoming:
            print(f"     {p.label()}")


def main():
    db.initialize_database()
    with db.get_session() as s:
        seed(s)
    with db.get_session() as s:
        render(dash.build_cockpit(s, today=TODAY, energy=rot.ENERGY_NORMAL), "Cockpit - normaler Tag")
    with db.get_session() as s:
        render(dash.build_cockpit(s, today=TODAY, energy=rot.ENERGY_LOW, remember=False),
               "Cockpit - wenig Energie")
    with db.get_session() as s:
        render(dash.build_cockpit(s, today=TODAY, energy=rot.ENERGY_SOCIAL, remember=False),
               "Cockpit - Lust auf Leute")


if __name__ == "__main__":
    main()
