"""LifePlanner-Anbindung nach ``docs/MODUL_HOST_VERTRAG.md`` (v1).

Wichtig: Der Host importiert keine Fachlogik des Moduls und das Modul oeffnet
keine fremde Datenbank. Der Austausch laeuft ausschliesslich ueber eine
versionierte JSONL-Datei im Bridge-Ordner des Profils.

Der FreizeitManager veroeffentlicht dabei nur das Ergebnis - nie Rohdaten,
nie Notizen. Der Host soll eine kleine Kachel zeichnen koennen, mehr nicht.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

from freizeitmanager import paths
from freizeitmanager.app_info import APP_ID, APP_VERSION, BRIDGE_SCHEMA

_log = logging.getLogger(__name__)

OUTBOX_NAME = "freizeitmanager_to_lifeplanner.jsonl"
MANIFEST_SCHEMA = "freizeitmanager.focus.manifest.v1"
EVENTS_NAME = "events.jsonl"


def outbox_path() -> Path | None:
    bridge = paths.bridge_dir()
    return None if bridge is None else bridge / OUTBOX_NAME


def publish_focus(cockpit, today: date | None = None) -> Path | None:
    """Schreibt den aktuellen Fokus als Outbox. Standalone: No-Op."""
    target = outbox_path()
    if target is None:
        return None
    today = today or date.today()

    lines = [json.dumps({
        "schema": MANIFEST_SCHEMA,
        "module": APP_ID,
        "module_version": APP_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "profile": os.environ.get("LIFEPLANNER_PROFILE_ID", ""),
        "host_version": os.environ.get("LIFEPLANNER_HOST_VERSION", ""),
        "counts": {
            "due_now": cockpit.summary.due_now,
            "this_week": cockpit.summary.this_week,
            "planned": cockpit.summary.planned,
            "all_good": cockpit.summary.all_good,
        },
    }, ensure_ascii=False)]

    for cand in cockpit.next_steps:
        lines.append(json.dumps({
            "schema": BRIDGE_SCHEMA,
            "kind": "next_step",
            "contact_id": cand.contact_id,
            "name": cand.name,
            "urgency": cand.urgency,
            "suggestion": cand.suggestion,
            "headline": cand.headline(),
            "detail": f"{cand.suggestion_text} \N{MIDDLE DOT} {cand.suggestion_effort}",
            "date": today.isoformat(),
        }, ensure_ascii=False))

    for plan in cockpit.upcoming:
        lines.append(json.dumps({
            "schema": BRIDGE_SCHEMA,
            "kind": "planned",
            "activity_id": plan.activity_id,
            "title": plan.title,
            "names": plan.names,
            "date": plan.on.isoformat(),
        }, ensure_ascii=False))

    tmp = target.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(target)  # atomar: der Host liest nie eine halbe Datei
    _log.info("Fokus veroeffentlicht: %s (%d Zeilen)", target, len(lines))
    return target


def emit_event(name: str, payload: dict | None = None) -> None:
    """Lokales Lebenszyklus-/Fachevent im Schema ``lifeplanner.event.v1``."""
    bridge = paths.bridge_dir()
    if bridge is None:
        return
    events_dir = bridge.parent / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "lifeplanner.event.v1",
        "event": name,
        "module": APP_ID,
        "at": datetime.now().isoformat(timespec="seconds"),
        "payload": payload or {},
    }
    with (events_dir / EVENTS_NAME).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# Fachevents, auf die andere Module spaeter reagieren duerfen.
EVENT_INTERACTION_LOGGED = "freizeit.interaction.logged"
EVENT_FOCUS_CHANGED = "freizeit.focus.changed"
EVENT_PLAN_CREATED = "freizeit.plan.created"
EVENT_PLAN_COMPLETED = "freizeit.plan.completed"
