"""Durabler Writer für ``lifeplanner.event.v1``-Fachevents.

Der LifePlanner-Core liest Events als ``LifePlannerEvent`` mit exakt den Feldern
``event_id``, ``schema``, ``event_type``, ``source``, ``occurred_at``,
``profile_id`` und ``payload``. Der alte FreizeitManager-Writer verwendete
andere Feldnamen und die Events wurden deshalb vom Host verworfen.
"""
from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from freizeitmanager import paths

EVENTS_NAME = "events.jsonl"
LOCK_NAME = ".events.lock"


def _events_dir() -> Path | None:
    bridge = paths.bridge_dir()
    return None if bridge is None else bridge.parent / "events"


def _acquire_lock(lock_dir: Path, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            lock_dir.mkdir()
            (lock_dir / "owner").write_text(str(os.getpid()), encoding="ascii")
            return
        except FileExistsError:
            try:
                age = time.time() - lock_dir.stat().st_mtime
                if age > 30:
                    shutil.rmtree(lock_dir, ignore_errors=True)
                    continue
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError("LifePlanner-Eventbus ist vorübergehend gesperrt")
            time.sleep(0.05)


def publish_event(event_type: str, payload: dict | None = None) -> Path | None:
    """Hängt ein Host-kompatibles Fachevent dauerhaft an den Eventbus an."""
    event_type = str(event_type or "").strip()
    if not event_type:
        raise ValueError("event_type darf nicht leer sein")
    if payload is not None and not isinstance(payload, dict):
        raise TypeError("payload muss ein dict sein")

    events_dir = _events_dir()
    if events_dir is None:
        return None
    events_dir.mkdir(parents=True, exist_ok=True)
    target = events_dir / EVENTS_NAME
    lock_dir = events_dir / LOCK_NAME
    record = {
        "event_id": str(uuid.uuid4()),
        "schema": "lifeplanner.event.v1",
        "event_type": event_type,
        "source": "freizeitmanager",
        "occurred_at": datetime.now(UTC).isoformat(),
        "profile_id": os.environ.get("LIFEPLANNER_PROFILE_ID", ""),
        "payload": payload or {},
    }

    _acquire_lock(lock_dir)
    try:
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        with target.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        shutil.rmtree(lock_dir, ignore_errors=True)
    return target
