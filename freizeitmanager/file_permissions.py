"""Restriktive Dateirechte für sensible Dateien.

Die Datenbank enthält Namen, Geburtstage, Telefonnummern und private Notizen
zu anderen Menschen - personenbezogene Daten Dritter, die diese dem Programm
nie selbst anvertraut haben. Erzeugt wurde sie bisher mit dem Standard-umask,
auf typischen Linux-Systemen also **0644 (world-readable)**: Auf einem
Mehrbenutzer-System konnte jedes lokale Konto mitlesen.

Dieses Modul setzt die Rechte auf **0600** (nur Eigentümer). Unter Windows
gibt es keine POSIX-Modi; dort ist ``os.chmod`` weitgehend wirkungslos, was
korrekt und unschädlich ist (der Zugriffsschutz läuft dort über ACLs des
Benutzerprofils). Fehler werden bewusst geschluckt: Ein Backup auf einem
FAT/exFAT-Stick darf nicht am ``chmod`` scheitern.

Wortgleich mit BudgetManager/model/file_permissions.py.
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

# rw------- : nur der Eigentümer darf lesen/schreiben
OWNER_ONLY_FILE = 0o600
# rwx------ : nur der Eigentümer darf betreten/auflisten
OWNER_ONLY_DIR = 0o700


def secure_file(path: str | os.PathLike) -> bool:
    """Setzt 0600 auf eine Datei. True bei Erfolg."""
    return _chmod(path, OWNER_ONLY_FILE)


def secure_dir(path: str | os.PathLike) -> bool:
    """Setzt 0700 auf ein Verzeichnis. True bei Erfolg."""
    return _chmod(path, OWNER_ONLY_DIR)


def _chmod(path: str | os.PathLike, mode: int) -> bool:
    p = Path(path)
    try:
        if not p.exists():
            return False
        os.chmod(p, mode)
        return True
    except (OSError, NotImplementedError) as e:
        # Windows / FAT / Netzlaufwerke: nicht fatal.
        logger.debug("chmod %s auf %s nicht möglich: %s", oct(mode), p, e)
        return False


def is_world_accessible(path: str | os.PathLike) -> bool:
    """True, wenn Gruppe oder Andere Rechte auf der Datei haben (POSIX).

    Unter Windows liefert ``st_mode`` keine sinnvollen Gruppen-/Andere-Bits;
    dort gibt die Funktion immer ``False`` zurück.
    """
    if os.name == "nt":
        return False
    p = Path(path)
    try:
        mode = stat.S_IMODE(p.stat().st_mode)
    except OSError:
        return False
    return bool(mode & (stat.S_IRWXG | stat.S_IRWXO))
