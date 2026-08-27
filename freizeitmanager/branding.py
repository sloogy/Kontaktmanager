"""Wo die Markenbilder liegen - im Quellbaum wie im gebauten Paket.

Der FreizeitManager trat bis hierhin ohne Bild auf: Das Fenster trug das
graue Ersatzsymbol des Fenstermanagers, die Seitenleiste den Programmnamen
als fette Textzeile, und zwischen Programmstart und Hauptfenster stand
nichts. Vier Programme, die eine Suite sein sollen, sahen an genau der
Stelle zusammenhanglos aus, an der man sie zuerst sieht.

Dieses Modul kennt nur Pfade, kein Qt. Das ist Absicht - dieselbe Trennung
wie im LifePlanner: Wer wissen will, ob ein Bild vorhanden ist (der
Paketbau, ein Test, ein Pruefwerkzeug), soll dafuer keine Oberflaeche
starten muessen. Das Laden uebernimmt ``freizeitmanager.ui.branding``.
"""
from __future__ import annotations

import sys
from pathlib import Path

#: Die erzeugten Kantenlaengen des Programmsymbols, aufsteigend.
#: ``tools/create_icons.py`` schreibt genau diese.
APP_ICON_GROESSEN: tuple[int, ...] = (16, 32, 48, 64, 128, 256, 512)

#: Banner fuer helle Flaechen. Der Schriftzug ist dort dunkelblau.
LOGO_DATEI = "freizeitmanager-logo.png"

#: Dieselbe Zeichnung fuer dunkle Flaechen: Dunkelblau wird weiss.
LOGO_HELL_DATEI = "freizeitmanager-logo-hell.png"

#: Quadratisches Programmsymbol in voller Groesse.
ICON_DATEI = "freizeitmanager.png"

#: Symboldatei mit mehreren Aufloesungen, fuer Windows und den Installer.
ICO_DATEI = "freizeitmanager.ico"


def icons_dir() -> Path:
    """Ordner der mitgelieferten Bilder - im Quellbaum wie im Build.

    Dieselbe Reihenfolge wie ``ThemeManager.bundled_dir``: erst das
    Entpackverzeichnis von PyInstaller, dann der Ordner neben der
    ausfuehrbaren Datei, zuletzt der Quellbaum. Gibt es keinen davon, kommt
    der letzte Kandidat zurueck - die Funktionen unten melden dann schlicht
    "kein Bild", statt hier eine Ausnahme zu werfen. Ein fehlendes Bild darf
    den Start nicht kosten.
    """
    kandidaten: list[Path] = []
    bundle = getattr(sys, "_MEIPASS", "")
    if bundle:
        kandidaten.append(Path(bundle) / "freizeitmanager" / "resources" / "icons")
    if getattr(sys, "frozen", False):
        neben_exe = Path(sys.executable).resolve().parent
        kandidaten.append(neben_exe / "freizeitmanager" / "resources" / "icons")
        kandidaten.append(
            neben_exe / "_internal" / "freizeitmanager" / "resources" / "icons"
        )
    kandidaten.append(Path(__file__).resolve().parent / "resources" / "icons")
    for kandidat in kandidaten:
        if kandidat.is_dir():
            return kandidat
    return kandidaten[-1]


def _vorhanden(dateiname: str) -> Path | None:
    pfad = icons_dir() / dateiname
    return pfad if pfad.is_file() else None


def app_icon_pfade() -> dict[int, Path]:
    """Alle vorhandenen Groessen des Programmsymbols, Kantenlaenge zu Datei."""
    ordner = icons_dir()
    gefunden: dict[int, Path] = {}
    for groesse in APP_ICON_GROESSEN:
        pfad = ordner / f"freizeitmanager-{groesse}.png"
        if pfad.is_file():
            gefunden[groesse] = pfad
    return gefunden


def app_icon_pfad() -> Path | None:
    """Das quadratische Programmsymbol in voller Groesse."""
    return _vorhanden(ICON_DATEI)


def app_ico_pfad() -> Path | None:
    """Die ``.ico`` mit mehreren Aufloesungen."""
    return _vorhanden(ICO_DATEI)


def logo_pfad(*, fuer_dunklen_untergrund: bool = False) -> Path | None:
    """Das breite Banner in der Fassung fuer diesen Untergrund.

    Fehlt die helle Fassung, kommt die dunkle zurueck: ein schwer lesbares
    Logo ist immer noch besser als eine leere Flaeche.
    """
    if fuer_dunklen_untergrund:
        hell = _vorhanden(LOGO_HELL_DATEI)
        if hell is not None:
            return hell
    return _vorhanden(LOGO_DATEI)


__all__ = [
    "APP_ICON_GROESSEN",
    "ICO_DATEI",
    "ICON_DATEI",
    "LOGO_DATEI",
    "LOGO_HELL_DATEI",
    "app_ico_pfad",
    "app_icon_pfad",
    "app_icon_pfade",
    "icons_dir",
    "logo_pfad",
]
