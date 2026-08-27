"""Markenbilder als Qt-Objekte - mit Rueckfall, wenn eines fehlt.

Die Regel dieses Moduls: Ein fehlendes oder unlesbares Bild darf nie eine
leere Flaeche, ein Loch im Layout oder einen Absturz erzeugen. Alle
Funktionen geben in diesem Fall ``None`` zurueck, und die Aufrufstellen
lassen die Flaeche dann ganz weg statt ein leeres Label einzuhaengen.

Das Banner gibt es in zwei Fassungen. Der Schriftzug ist zur Haelfte
dunkelblau; auf den dunklen Profilen - die Seitenleisten gehen bis #050505 -
waere genau dieses halbe Wort weg. Welche Fassung genommen wird, entscheidet
dieses Modul anhand der tatsaechlichen Flaechenfarbe aus dem aktiven Profil
und nicht die Aufrufstelle: Sonst muesste jede Stelle dieselbe
Fallunterscheidung noch einmal treffen, und eine wuerde sie vergessen.

Gefragt wird die Farbe der konkreten Flaeche, nicht das Hell/Dunkel-Kennzeichen
des Profils. Die Seitenleiste ist eine eigene Farbe: ``Hell - Gruen`` traegt
dort #c5e1a5, ``Gruvbox - Hell`` #f2e5bc - beides hell, aber ein Profil koennte
hier auch dunkel werden, ohne insgesamt dunkel zu sein.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from freizeitmanager import branding
from freizeitmanager.ui.theme_manager import ThemeManager

_log = logging.getLogger(__name__)

#: Ab welcher Helligkeit der Flaeche die dunkle Schrift noch lesbar ist.
#: ``QColor.lightnessF`` liefert 0.0 bis 1.0; die Mitte trennt die hellen
#: Seitenleisten (ab #c5e1a5) sauber von den dunklen (bis #050505).
HELLIGKEITS_GRENZE = 0.5

#: Flaeche, auf der ein Banner ohne naehere Angabe liegt.
STANDARD_FLAECHE = "hintergrund_app"


def flaeche_ist_dunkel(farbschluessel: str = STANDARD_FLAECHE) -> bool:
    """Ob auf diese Flaeche die helle Bannerfassung gehoert.

    Scheitert die Abfrage des Profils - etwa weil noch keines geladen ist -
    gilt hell: das ist die Fassung, die es immer gibt.
    """
    try:
        farbe = QColor(ThemeManager.instance().current_profile().color(farbschluessel))
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as fehler:
        _log.debug("Flaechenfarbe %r nicht ermittelbar: %s", farbschluessel, fehler)
        return False
    if not farbe.isValid():
        return False
    return farbe.lightnessF() < HELLIGKEITS_GRENZE


def app_icon() -> QIcon:
    """Das Programmsymbol in allen abgelegten Groessen.

    Alle Groessen in einem ``QIcon``, damit Qt fuer Titelleiste, Taskleiste
    und Alt-Tab jeweils die passende nimmt, statt eine einzige zu skalieren.
    """
    symbol = QIcon()
    for pfad in branding.app_icon_pfade().values():
        symbol.addFile(str(pfad))
    return symbol


def _geladen(pfad) -> QPixmap | None:
    if pfad is None:
        return None
    bild = QPixmap(str(pfad))
    if bild.isNull():
        _log.debug("Markenbild nicht lesbar: %s", pfad)
        return None
    return bild


def logo_pixmap(
    breite: int,
    *,
    farbschluessel: str = STANDARD_FLAECHE,
    device_pixel_ratio: float = 1.0,
) -> QPixmap | None:
    """Das Banner auf ``breite`` logische Bildpunkte, Seitenverhaeltnis erhalten.

    ``device_pixel_ratio`` sorgt dafuer, dass auf HiDPI-Anzeigen tatsaechlich
    mehr Bildpunkte entstehen; die logische Breite bleibt ``breite``.
    """
    quelle = _geladen(
        branding.logo_pfad(fuer_dunklen_untergrund=flaeche_ist_dunkel(farbschluessel))
    )
    if quelle is None:
        return None
    verhaeltnis = float(device_pixel_ratio)
    if verhaeltnis <= 0.0:
        verhaeltnis = 1.0
    ziel = max(1, int(round(breite * verhaeltnis)))
    skaliert = quelle.scaledToWidth(ziel, Qt.TransformationMode.SmoothTransformation)
    skaliert.setDevicePixelRatio(verhaeltnis)
    return skaliert


def icon_pixmap(kante: int, *, device_pixel_ratio: float = 1.0) -> QPixmap | None:
    """Das quadratische Programmsymbol mit ``kante`` logischen Bildpunkten."""
    quelle = _geladen(branding.app_icon_pfad())
    if quelle is None:
        return None
    verhaeltnis = float(device_pixel_ratio)
    if verhaeltnis <= 0.0:
        verhaeltnis = 1.0
    ziel = max(1, int(round(kante * verhaeltnis)))
    skaliert = quelle.scaled(
        ziel,
        ziel,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    skaliert.setDevicePixelRatio(verhaeltnis)
    return skaliert


def _bildpunktverhaeltnis(widget: QWidget | None) -> float:
    if widget is None:
        return 1.0
    try:
        return float(widget.devicePixelRatioF())
    except (RuntimeError, TypeError, ValueError):
        return 1.0


def logo_label(
    parent: QWidget | None,
    breite: int,
    *,
    farbschluessel: str = STANDARD_FLAECHE,
    objektname: str = "",
) -> QLabel | None:
    """Fertiges, zentriertes Banner-Label - oder ``None`` ohne Bild.

    Gibt bewusst ``None`` zurueck statt eines leeren Labels: eine
    Marken-Flaeche ohne Bild soll im Layout gar keinen Platz belegen.
    """
    bild = logo_pixmap(
        breite,
        farbschluessel=farbschluessel,
        device_pixel_ratio=_bildpunktverhaeltnis(parent),
    )
    if bild is None:
        return None
    label = QLabel(parent)
    if objektname:
        label.setObjectName(objektname)
    label.setPixmap(bild)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    # Das Banner traegt den Programmnamen bereits als Bild; fuer Screenreader
    # wird er hier noch einmal ausgesprochen.
    label.setAccessibleName("FreizeitManager")
    return label


__all__ = [
    "HELLIGKEITS_GRENZE",
    "STANDARD_FLAECHE",
    "app_icon",
    "flaeche_ist_dunkel",
    "icon_pixmap",
    "logo_label",
    "logo_pixmap",
]
