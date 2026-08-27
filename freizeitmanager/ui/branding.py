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


class BannerLabel(QLabel):
    """Ein Banner, das sich seiner Flaeche anpasst, statt beschnitten zu werden.

    Ein gewoehnliches ``QLabel`` mit Bild zeichnet das Bild in voller Groesse
    und schneidet ab, was nicht hineinpasst. Genau das passiert in einer
    vollen Seitenleiste: Reicht die Hoehe des Fensters nicht fuer alle
    Eintraege, verteilt das Layout den Mangel auf alle Kinder, und vom Banner
    bleibt ein Streifen. Eine feste Groessenrichtlinie hilft dabei nicht -
    wenn die Summe der Mindestgroessen die Flaeche uebersteigt, geht das
    Layout auch unter jede Mindestgroesse.

    Deshalb behaelt dieses Label das unskalierte Bild und rechnet es bei
    jeder Groessenaenderung neu in die tatsaechlich verfuegbare Flaeche.
    Kleiner ist es dann - aber ganz.

    ``minimumSizeHint`` meldet dieselbe Hoehe wie ``sizeHint``. Ein kleinerer
    Mindestwert klaenge nachgiebiger, waere hier aber falsch: Der Innenabstand
    aus dem Stylesheet ist fest, und sobald die zugeteilte Hoehe darunter
    faellt, bleibt fuer das Bild rechnerisch nichts uebrig. Lieber nimmt das
    Layout den Platz woanders weg.
    """

    def __init__(
        self,
        quelle: QPixmap,
        breite: int,
        *,
        parent: QWidget | None = None,
        device_pixel_ratio: float = 1.0,
    ) -> None:
        super().__init__(parent)
        self._quelle = quelle
        self._breite = max(1, int(breite))
        self._verhaeltnis = float(device_pixel_ratio) or 1.0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._neu_zeichnen(self._breite, self._hoehe_zu(self._breite))

    def _hoehe_zu(self, breite: int) -> int:
        if self._quelle.width() <= 0:
            return 1
        return max(1, round(breite * self._quelle.height() / self._quelle.width()))

    def _rahmen(self) -> tuple[int, int]:
        """Innenmasse: Groesse abzueglich der Raender aus dem Stylesheet."""
        rand = self.contentsMargins()
        return (
            self.width() - rand.left() - rand.right(),
            self.height() - rand.top() - rand.bottom(),
        )

    def _neu_zeichnen(self, breite: int, hoehe: int) -> None:
        breite = max(1, min(breite, self._breite))
        hoehe = max(1, hoehe)
        # In die Flaeche einpassen: Die knappere der beiden Kanten entscheidet.
        if breite * self._quelle.height() > hoehe * self._quelle.width():
            breite = max(1, round(hoehe * self._quelle.width() / self._quelle.height()))
        ziel = max(1, round(breite * self._verhaeltnis))
        bild = self._quelle.scaledToWidth(
            ziel, Qt.TransformationMode.SmoothTransformation
        )
        bild.setDevicePixelRatio(self._verhaeltnis)
        self.setPixmap(bild)

    def sizeHint(self):
        rand = self.contentsMargins()
        masse = super().sizeHint()
        masse.setWidth(self._breite + rand.left() + rand.right())
        masse.setHeight(self._hoehe_zu(self._breite) + rand.top() + rand.bottom())
        return masse

    def minimumSizeHint(self):
        return self.sizeHint()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        breite, hoehe = self._rahmen()
        # Beide Masse werden in _neu_zeichnen auf mindestens 1 gehoben. Hier
        # nicht abzubrechen ist Absicht: Bleibt nach dem Innenabstand nichts
        # uebrig, soll ein winziges Banner erscheinen und kein angeschnittenes.
        self._neu_zeichnen(breite, hoehe)


def logo_label(
    parent: QWidget | None,
    breite: int,
    *,
    farbschluessel: str = STANDARD_FLAECHE,
    objektname: str = "",
) -> BannerLabel | None:
    """Fertiges, zentriertes Banner-Label - oder ``None`` ohne Bild.

    Gibt bewusst ``None`` zurueck statt eines leeren Labels: eine
    Marken-Flaeche ohne Bild soll im Layout gar keinen Platz belegen.
    """
    quelle = _geladen(
        branding.logo_pfad(fuer_dunklen_untergrund=flaeche_ist_dunkel(farbschluessel))
    )
    if quelle is None:
        return None
    label = BannerLabel(
        quelle,
        breite,
        parent=parent,
        device_pixel_ratio=_bildpunktverhaeltnis(parent),
    )
    if objektname:
        label.setObjectName(objektname)
    # Das Banner traegt den Programmnamen bereits als Bild; fuer Screenreader
    # wird er hier noch einmal ausgesprochen.
    label.setAccessibleName("FreizeitManager")
    return label


__all__ = [
    "HELLIGKEITS_GRENZE",
    "STANDARD_FLAECHE",
    "BannerLabel",
    "app_icon",
    "flaeche_ist_dunkel",
    "icon_pixmap",
    "logo_label",
    "logo_pixmap",
]
