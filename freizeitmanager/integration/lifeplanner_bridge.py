"""LifePlanner-Anbindung nach ``docs/MODUL_HOST_VERTRAG.md``.

Der Host importiert keine Fachlogik des Moduls und das Modul öffnet keine
fremde Datenbank. Der Austausch läuft ausschließlich über versionierte Dateien
im Bridge-/Event-Bereich des Profils.

Der FreizeitManager veröffentlicht dabei nur Ergebnisse - nie Notizen oder
sonstige Rohdaten. Der Host soll eine kleine Fokus-Zusammenfassung zeichnen
können, mehr nicht.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

from freizeitmanager import paths
from freizeitmanager.app_info import APP_ID, APP_VERSION, BRIDGE_SCHEMA
from freizeitmanager.integration.lifeplanner_events import publish_event

_log = logging.getLogger(__name__)

OUTBOX_NAME = "freizeitmanager_to_lifeplanner.jsonl"
MANIFEST_SCHEMA = "freizeitmanager.focus.manifest.v1"


def outbox_path() -> Path | None:
    bridge = paths.bridge_dir()
    return None if bridge is None else bridge / OUTBOX_NAME


def publish_focus(cockpit, today: date | None = None) -> Path | None:
    """Schreibt den aktuellen Fokus als Outbox. Standalone: No-Op."""
    target = outbox_path()
    if target is None:
        return None
    today = today or date.today()

    lines = [
        json.dumps(
            {
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
            },
            ensure_ascii=False,
        )
    ]

    for cand in cockpit.next_steps:
        lines.append(
            json.dumps(
                {
                    "schema": BRIDGE_SCHEMA,
                    "kind": "next_step",
                    "contact_id": cand.contact_id,
                    "name": cand.name,
                    "urgency": cand.urgency,
                    "suggestion": cand.suggestion,
                    "headline": cand.headline(),
                    "detail": f"{cand.suggestion_text} \N{MIDDLE DOT} {cand.suggestion_effort}",
                    "date": today.isoformat(),
                },
                ensure_ascii=False,
            )
        )

    for plan in cockpit.upcoming:
        lines.append(
            json.dumps(
                {
                    "schema": BRIDGE_SCHEMA,
                    "kind": "planned",
                    "activity_id": plan.activity_id,
                    "title": plan.title,
                    "names": plan.names,
                    "date": plan.on.isoformat(),
                },
                ensure_ascii=False,
            )
        )

    from freizeitmanager.atomic_write import atomar_schreiben

    atomar_schreiben(target, "\n".join(lines) + "\n")
    _log.info("Fokus veröffentlicht: %s (%d Zeilen)", target, len(lines))
    return target


def emit_event(name: str, payload: dict | None = None) -> None:
    """Schreibt ein Fachevent exakt im ``lifeplanner.event.v1``-Schema."""
    publish_event(name, payload)


# Fachevents, auf die andere Module später reagieren dürfen.
EVENT_INTERACTION_LOGGED = "freizeit.interaction.logged"
EVENT_FOCUS_CHANGED = "freizeit.focus.changed"
EVENT_PLAN_CREATED = "freizeit.plan.created"
EVENT_PLAN_COMPLETED = "freizeit.plan.completed"
