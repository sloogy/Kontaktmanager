"""Modulweit gemeinsames Theme.

Der Modul-Host-Vertrag verbietet den Zugriff auf fremde Datenbanken. Ein
gemeinsames Erscheinungsbild fuer BudgetManager, FPM, FreizeitManager und den
LifePlanner selbst darf also nicht ueber gegenseitige Settings-Zugriffe
entstehen, sondern nur ueber eine versionierte Datei im Bridge-Ordner des
Profils:

    $LIFEPLANNER_BRIDGE_DIR/shared_theme.json      Schema lifeplanner.theme.v1

Regeln, bewusst so gewaehlt:

* **Lesen ist freiwillig.** Ein Modul uebernimmt das gemeinsame Theme nur,
  wenn der Nutzer das dort eingeschaltet hat. Sonst gilt die lokale Wahl.
* **Schreiben ist eine ausdrueckliche Handlung.** Nur wer "fuer alle Module
  uebernehmen" anhakt, veraendert die Datei. Ein Modul, das beim Start
  ungefragt sein Theme veroeffentlicht, wuerde die Wahl der anderen
  ueberschreiben.
* **Ohne Host passiert nichts.** Im Standalone-Betrieb gibt es keinen
  Bridge-Ordner; alle Funktionen hier sind dann stille No-Ops.

Die Datei enthaelt Namen und Farbwerte, damit ein Modul ein Theme auch dann
darstellen kann, wenn es das Profil selbst gar nicht mitliefert.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from freizeitmanager import paths
from freizeitmanager.app_info import APP_ID, APP_VERSION
from freizeitmanager.ui.theme_manager import REFERENCE_FONT_SIZE

_log = logging.getLogger(__name__)

SHARED_THEME_SCHEMA = "lifeplanner.theme.v1"
SHARED_THEME_FILE = "shared_theme.json"


def shared_theme_path() -> Path | None:
    """Pfad der gemeinsamen Datei. ``None`` bedeutet Standalone-Betrieb."""
    bridge = paths.bridge_dir()
    return None if bridge is None else bridge / SHARED_THEME_FILE


def read_shared_theme() -> dict[str, Any] | None:
    """Liest das gemeinsame Theme. Fehlerhafte Datei = kein Theme."""
    path = shared_theme_path()
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("Gemeinsames Theme nicht lesbar (%s): %s", path, exc)
        return None
    if not isinstance(data, dict) or data.get("schema") != SHARED_THEME_SCHEMA:
        _log.warning("Gemeinsames Theme hat ein unerwartetes Schema: %r",
                     data.get("schema") if isinstance(data, dict) else type(data).__name__)
        return None
    if not str(data.get("name", "")).strip():
        _log.warning("Gemeinsames Theme ohne Namen - wird ignoriert.")
        return None
    return data


def publish_shared_theme(name: str, profile_data: dict[str, Any]) -> Path | None:
    """Veroeffentlicht ein Theme fuer alle Module. Nur auf ausdruecklichen Wunsch."""
    path = shared_theme_path()
    if path is None:
        return None

    record = {
        "schema": SHARED_THEME_SCHEMA,
        "name": str(name).strip(),
        "modus": str(profile_data.get("modus", "hell")).strip().lower(),
        # Der gemeinsame Bezugswert ist 10, nicht die eigene Schriftgroesse 14 -
        # sonst bekaeme ein Schwesterprogramm daraus einen Faktor 1.4.
        "schriftgroesse": int(profile_data.get("schriftgroesse", REFERENCE_FONT_SIZE)
                              or REFERENCE_FONT_SIZE),
        # Farben mitgeben, damit ein Modul das Theme auch darstellen kann,
        # wenn es dieses Profil selbst nicht mitliefert.
        "farben": {key: value for key, value in profile_data.items()
                   if isinstance(value, str) and value.strip().startswith("#")},
        "gesetzt_von": APP_ID,
        "modul_version": APP_VERSION,
        "profil": os.environ.get("LIFEPLANNER_PROFILE_ID", ""),
        "geaendert_am": datetime.now(UTC).isoformat(timespec="seconds"),
    }

    # Atomar schreiben: ein anderes Modul darf nie eine halbe Datei lesen.
    # Seit Loop 29 der gemeinsame Helfer - er traegt fsync auf Datei und
    # Verzeichnis bei und gibt der Zwischendatei die Prozessnummer statt
    # eines festen Namens, den zwei Instanzen sich teilen wuerden.
    from freizeitmanager.atomic_write import atomar_schreiben

    atomar_schreiben(path, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    _log.info("Gemeinsames Theme veroeffentlicht: %s (%s)", record["name"], path)
    return path


def shared_theme_as_profile_data(data: dict[str, Any]) -> dict[str, Any]:
    """Formt einen gemeinsamen Eintrag in ein lokales Profil um."""
    profile: dict[str, Any] = {
        "modus": str(data.get("modus", "hell")).strip().lower(),
        "schriftgroesse": data.get("schriftgroesse", 14),
    }
    farben = data.get("farben")
    if isinstance(farben, dict):
        profile.update({key: value for key, value in farben.items()
                        if isinstance(value, str)})
    return profile


def describe_shared_theme() -> str:
    """Kurze Herkunftsangabe fuer die Einstellungsseite."""
    from freizeitmanager.i18n.translator import t
    data = read_shared_theme()
    if data is None:
        return t("settings.shared_theme_none")
    return t("settings.shared_theme_from",
             name=data.get("name", "?"), module=data.get("gesetzt_von", "?"))
