"""Meldungen des FreizeitManagers an das LifePlanner-Dashboard.

Der Host zeigt seit LifePlanner 0.5.16 auf seiner Übersichtsseite, was die
Module melden. Das Schema ``lifeplanner.notice.v1`` stammt aus genau diesem
Modul: ``publish_focus`` schrieb solche Meldungen (kind, urgency, headline,
detail) als einziges — nur eben in einem eigenen Format, das nur der Host
kannte, und nur an einer Stelle gelesen wurde.

Beides bleibt bestehen. ``freizeitmanager.focus.v1`` trägt die
Fokus-Zusammenfassung mit ihren Zählwerten; diese Datei trägt die Meldungen,
die im Dashboard neben denen der anderen Module stehen.

Zwei Punkte aus dem Modul-Host-Vertrag:

* **Der Text ist hier schon fertig.** Der Host übersetzt nichts.
* **Nur Ergebnisse.** Eine Meldung trägt eine Zeile Text und eine
  Dringlichkeit — keine Notizen, keine Geburtstage, keine Interaktions-
  historie. Ein Name darf darin vorkommen: Ohne ihn wäre „jemand wäre mal
  wieder dran" keine brauchbare Meldung. Alles andere bleibt in der
  Datenbank.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from freizeitmanager import paths
from freizeitmanager.app_info import APP_ID, APP_VERSION
from freizeitmanager.logic.rotation_engine import (
    URGENCY_DUE,
    URGENCY_LONG,
    URGENCY_SOON,
)

_log = logging.getLogger(__name__)

NOTICES_FILE = "freizeitmanager_notices.jsonl"
MANIFEST_SCHEMA = "lifeplanner.notice.manifest.v1"
NOTICE_SCHEMA = "lifeplanner.notice.v1"

# Aufsteigend nach Dringlichkeit - der Host sortiert danach.
DRINGLICHKEITEN = ("info", "warnung", "kritisch")

# Die vier Stufen der Rotation auf die drei des Hosts.
#
# ``fresh`` fehlt bewusst: Wer gerade erst Kontakt hatte, ist keine Meldung.
# ``long`` wird "warnung" und nicht "kritisch" - eine Freundschaft, die
# still geworden ist, ist kein Alarm. Das Programm ist ausdrücklich so
# gebaut, dass es keinen Schuldenberg aufbaut (siehe README); eine rote
# Meldung im Host würde genau das wieder einführen.
STUFEN = {
    URGENCY_LONG: "warnung",
    URGENCY_DUE: "info",
    URGENCY_SOON: "info",
}

# Das Cockpit zeigt selbst höchstens drei Vorschläge. Mehr im Dashboard
# wäre mehr Druck, als das Programm machen will.
HOECHSTZAHL = 3


@dataclass(frozen=True)
class Meldung:
    """Eine Zeile fürs Host-Dashboard."""

    kennung: str
    dringlichkeit: str
    ueberschrift: str
    zusatz: str = ""
    bereich: str = ""

    def __post_init__(self) -> None:
        if self.dringlichkeit not in DRINGLICHKEITEN:
            raise ValueError(
                f"unbekannte Dringlichkeit {self.dringlichkeit!r}; "
                f"erlaubt sind {DRINGLICHKEITEN}"
            )
        if not self.ueberschrift.strip():
            raise ValueError("eine Meldung ohne Überschrift sagt nichts")

    def als_zeile(self) -> dict:
        return {
            "schema": NOTICE_SCHEMA,
            "id": self.kennung,
            "urgency": self.dringlichkeit,
            "headline": self.ueberschrift,
            "detail": self.zusatz,
            "area": self.bereich,
        }


def kennung(*teile: object) -> str:
    """Stabile Kennung aus den Bestandteilen einer Meldung.

    Gekürzter Hash statt Klartext: Die Kennung steht auch dann in der Datei,
    wenn die Überschrift später anders formuliert wird.
    """
    roh = "\x1f".join(str(teil) for teil in teile)
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()[:16]


def notices_path() -> Path | None:
    bridge = paths.bridge_dir()
    return None if bridge is None else bridge / NOTICES_FILE


def aus_cockpit(cockpit) -> list[Meldung]:
    """Bildet die Meldungen aus den Vorschlägen des Fokus-Cockpits.

    Genommen wird, was ohnehin auf dem Schirm steht - nicht der volle
    Kandidatenkreis. Was das Cockpit bewusst nicht zeigt, gehört auch nicht
    ins Dashboard des Hosts.
    """
    meldungen: list[Meldung] = []
    for kandidat in cockpit.next_steps:
        stufe = STUFEN.get(kandidat.urgency)
        if stufe is None:
            continue  # fresh: kein Anlass
        meldungen.append(
            Meldung(
                kennung=kennung("next_step", kandidat.contact_id),
                dringlichkeit=stufe,
                ueberschrift=kandidat.headline(),
                zusatz=kandidat.suggestion_text,
                bereich="rotation",
            )
        )
    return meldungen


def publish_notices(cockpit) -> Path | None:
    """Schreibt den Meldungsstand. Ohne Host ein No-Op.

    Kein Anhängen: Die Datei ist eine Momentaufnahme. Wer heute angerufen
    hat, verschwindet damit von selbst aus dem Dashboard.
    """
    ziel = notices_path()
    if ziel is None:
        return None

    geordnet = sorted(
        aus_cockpit(cockpit),
        key=lambda m: (-DRINGLICHKEITEN.index(m.dringlichkeit), m.ueberschrift),
    )[:HOECHSTZAHL]

    zeilen = [
        json.dumps(
            {
                "schema": MANIFEST_SCHEMA,
                "module": APP_ID,
                "module_version": APP_VERSION,
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "profile": os.environ.get("LIFEPLANNER_PROFILE_ID", ""),
                "count": len(geordnet),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    ]
    zeilen.extend(
        json.dumps(m.als_zeile(), ensure_ascii=False, sort_keys=True) for m in geordnet
    )

    from freizeitmanager.atomic_write import atomar_schreiben

    atomar_schreiben(ziel, "\n".join(zeilen) + "\n")
    _log.info("Meldungen veröffentlicht: %s (%d)", ziel, len(geordnet))
    return ziel
