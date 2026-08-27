"""Verhaltenstests fuer Markenbilder, Icons und den Startbildschirm.

Geprueft wird das Ergebnis, nicht das Werkzeug: dass die ausgelieferten
Dateien die richtigen Kantenlaengen haben, dass das Banner randlos ist, dass
das Icon mittig sitzt, dass es eine lesbare Fassung fuer dunkle Flaechen gibt
und dass der Startbildschirm sich in jedem Fall wieder schliesst.

Die Kopfdaten der PNG- und ICO-Dateien liest die Standardbibliothek. Pillow
steht nur in requirements-build, nicht in requirements - die Bilder sind
ausgeliefertes Programm und muessen auch dort pruefbar sein, wo das
Erzeugungswerkzeug fehlt.
"""
from __future__ import annotations

import os
import struct
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from freizeitmanager import branding

ICON_DIR = Path(branding.__file__).resolve().parent / "resources" / "icons"
PNG_GROESSEN = branding.APP_ICON_GROESSEN
ERWARTETE_ICO_GROESSEN = {16, 32, 48, 64, 128, 256}

# Dieselbe Schwelle wie in tools/create_icons.py: Die gelieferten Marken-PNGs
# tragen einen unsichtbaren Alphaschleier, der jede Randmessung gegen Null
# wertlos macht.
ALPHA_SCHWELLE = 8


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ── Dateikopf-Leser ──────────────────────────────────────────────


def _png_groesse(pfad: Path) -> tuple[int, int]:
    """Breite und Hoehe aus dem IHDR-Block eines PNG."""
    daten = pfad.read_bytes()
    assert daten[:8] == b"\x89PNG\r\n\x1a\n", f"{pfad.name} ist kein PNG"
    assert daten[12:16] == b"IHDR", f"{pfad.name} hat keinen IHDR-Block"
    breite, hoehe = struct.unpack(">II", daten[16:24])
    return breite, hoehe


def _png_hat_alpha(pfad: Path) -> bool:
    """True, wenn der PNG-Farbtyp einen Alphakanal traegt (4 oder 6)."""
    return pfad.read_bytes()[25] in (4, 6)


def _ico_groessen(pfad: Path) -> set[tuple[int, int]]:
    """Alle im ICONDIR gemeldeten Aufloesungen (0 bedeutet 256)."""
    daten = pfad.read_bytes()
    reserviert, art, anzahl = struct.unpack("<HHH", daten[:6])
    assert reserviert == 0 and art == 1, f"{pfad.name} ist keine .ico"
    groessen: set[tuple[int, int]] = set()
    for nummer in range(anzahl):
        versatz = 6 + nummer * 16
        groessen.add((daten[versatz] or 256, daten[versatz + 1] or 256))
    return groessen


def _motiv_rahmen(pfad: Path) -> tuple[int, int, int, int]:
    """Rahmen um alles Sichtbare: links, oben, rechts, unten (exklusiv)."""
    bild = QImage(str(pfad))
    assert not bild.isNull(), f"{pfad.name} laesst sich nicht laden"
    links, oben = bild.width(), bild.height()
    rechts = unten = 0
    for y in range(bild.height()):
        for x in range(bild.width()):
            if bild.pixelColor(x, y).alpha() > ALPHA_SCHWELLE:
                links = min(links, x)
                oben = min(oben, y)
                rechts = max(rechts, x + 1)
                unten = max(unten, y + 1)
    assert rechts > links and unten > oben, f"{pfad.name} ist vollstaendig unsichtbar"
    return links, oben, rechts, unten


def _mittlere_helligkeit(pfad: Path) -> float:
    """Durchschnittliche Helligkeit aller sichtbaren Bildpunkte, 0.0 bis 1.0."""
    bild = QImage(str(pfad))
    assert not bild.isNull(), f"{pfad.name} laesst sich nicht laden"
    summe = 0.0
    gezaehlt = 0
    for y in range(bild.height()):
        for x in range(bild.width()):
            farbe = bild.pixelColor(x, y)
            if farbe.alpha() > ALPHA_SCHWELLE:
                summe += farbe.lightnessF()
                gezaehlt += 1
    assert gezaehlt, f"{pfad.name} ist vollstaendig unsichtbar"
    return summe / gezaehlt


# ── Quellbilder ──────────────────────────────────────────────────


def test_quellbilder_liegen_im_repo():
    """Ohne Quellbilder waeren die Ausgaben nicht reproduzierbar erzeugbar."""
    motiv = ICON_DIR / "freizeitmanager-source.png"
    banner = ICON_DIR / "freizeitmanager-logo-source.png"

    assert motiv.is_file()
    assert banner.is_file()

    breite, hoehe = _png_groesse(motiv)
    assert breite == hoehe, "Das Icon-Quellbild muss quadratisch sein"
    assert breite >= max(PNG_GROESSEN), "Kleiner als die groesste Ausgabe"
    assert _png_hat_alpha(motiv)

    banner_breite, banner_hoehe = _png_groesse(banner)
    assert banner_breite > banner_hoehe, "Das Banner ist ein breites Bild"
    assert _png_hat_alpha(banner)


# ── Erzeugte Icons ───────────────────────────────────────────────


@pytest.mark.parametrize("groesse", PNG_GROESSEN)
def test_jede_icongroesse_liegt_vor(groesse: int):
    pfad = ICON_DIR / f"freizeitmanager-{groesse}.png"
    assert pfad.is_file()
    assert _png_groesse(pfad) == (groesse, groesse)
    assert _png_hat_alpha(pfad), "Icons muessen transparent bleiben"


def test_alle_groessen_sind_ueber_branding_erreichbar():
    """Die Oberflaeche findet die Bilder ohne Pfadwissen an der Aufrufstelle."""
    gefunden = branding.app_icon_pfade()
    assert set(gefunden) == set(PNG_GROESSEN)
    assert branding.app_icon_pfad() is not None
    assert branding.app_ico_pfad() is not None


def test_ico_traegt_alle_ueblichen_aufloesungen():
    pfad = branding.app_ico_pfad()
    assert pfad is not None
    groessen = _ico_groessen(pfad)
    for kante in ERWARTETE_ICO_GROESSEN:
        assert (kante, kante) in groessen, f"{kante}px fehlt in der .ico"


@pytest.mark.parametrize("groesse", (128, 256, 512))
def test_icon_motiv_sitzt_mittig(qapp, groesse: int):
    """Gleicher Rand links wie rechts und oben wie unten.

    Das Quellbild ist unsymmetrisch beschnitten (links 0, rechts 18, oben 49,
    unten 54 Bildpunkte). Unkorrigiert haengt das Symbol in Taskleiste und
    Titelleiste schief - sichtbar erst neben anderen Symbolen.
    """
    links, oben, rechts, unten = _motiv_rahmen(
        ICON_DIR / f"freizeitmanager-{groesse}.png"
    )
    # Eine ungerade Restbreite laesst sich nicht gleichmaessig verteilen,
    # deshalb ein Bildpunkt Spielraum.
    assert abs(links - (groesse - rechts)) <= 1, f"{groesse}px sitzt waagerecht schief"
    assert abs(oben - (groesse - unten)) <= 1, f"{groesse}px sitzt senkrecht schief"


@pytest.mark.parametrize("groesse", (128, 256, 512))
def test_icon_motiv_fuellt_die_flaeche(qapp, groesse: int):
    """Das Motiv soll die Kachel fuellen, nicht darin schwimmen.

    Ohne diese Schranke faellt es nicht auf, wenn jemand ein Quellbild mit
    breitem Rand einsetzt: Das Icon waere korrekt erzeugt und trotzdem in
    jeder Groesse zu klein.
    """
    links, oben, rechts, unten = _motiv_rahmen(
        ICON_DIR / f"freizeitmanager-{groesse}.png"
    )
    laengste = max(rechts - links, unten - oben)
    assert laengste >= 0.9 * groesse, (
        f"{groesse}px: Motiv belegt nur {laengste} von {groesse} Bildpunkten"
    )


# ── Banner ───────────────────────────────────────────────────────


def test_banner_hat_keinen_unsichtbaren_rand(qapp):
    """Randlos, sonst passt es in keine Flaeche.

    Die Quelldatei traegt links 25 und rechts 88 unsichtbare Bildpunkte. Wer
    ein solches Bild in eine Flaeche fester Breite legt, bekommt ein Logo,
    das zu klein wirkt und sichtbar aus der Mitte rutscht - obwohl das
    Layout korrekt zentriert.
    """
    banner = branding.logo_pfad()
    assert banner is not None
    assert _png_hat_alpha(banner)

    breite, hoehe = _png_groesse(banner)
    assert _motiv_rahmen(banner) == (0, 0, breite, hoehe)


def test_es_gibt_eine_fassung_fuer_dunkle_flaechen(qapp):
    """Auf dunklen Profilen muss das ganze Wort lesbar bleiben.

    Der Schriftzug ist zur Haelfte dunkelblau (#0D1B3A); die Seitenleisten
    der dunklen Profile gehen bis #050505. Der Test vergleicht die mittlere
    Helligkeit beider Fassungen - die helle muss deutlich heller sein, sonst
    ist sie nur eine Kopie.
    """
    hell = branding.logo_pfad(fuer_dunklen_untergrund=True)
    dunkel = branding.logo_pfad(fuer_dunklen_untergrund=False)
    assert hell is not None and dunkel is not None
    assert hell != dunkel, "Ohne eigene Fassung ist das Logo dort halb weg"

    assert _png_groesse(hell) == _png_groesse(dunkel), "Dieselbe Zeichnung"
    assert _mittlere_helligkeit(hell) > _mittlere_helligkeit(dunkel) + 0.15


def test_die_bannerfassung_folgt_der_flaechenfarbe(qapp, session):
    """Nicht die Aufrufstelle waehlt die Fassung, sondern die Flaeche.

    ``session`` legt die Datenbank an: Der ThemeManager liest seine Wahl
    aus den Einstellungen, und ohne Tabelle kaeme er gar nicht bis zur
    Farbe.
    """
    from freizeitmanager.ui.branding import flaeche_ist_dunkel
    from freizeitmanager.ui.theme_manager import ThemeManager

    try:
        ThemeManager.instance().set_current("Standard - Dunkel")
        assert flaeche_ist_dunkel("hintergrund_seitenleiste") is True

        ThemeManager.instance().set_current("Standard - Hell")
        assert flaeche_ist_dunkel("hintergrund_seitenleiste") is False
    finally:
        ThemeManager.reset()


def test_seitenleisten_banner_passt_in_die_schmalste_leiste(qapp, session):
    """Die Bannerbreite muss zur Mindestbreite der Leiste passen.

    Gerechnet wird bewusst mit der Mindestbreite: Die Leiste darf zwischen
    210 und 250 Punkten liegen, und ein Banner, das nur in der breiten
    Fassung passt, waere in der schmalen abgeschnitten.
    """
    from freizeitmanager.ui.styles import (
        SEITENLEISTE_INNENABSTAND,
        SEITENLEISTE_MIN_BREITE,
        sidebar_logo_breite,
    )
    from freizeitmanager.ui.theme_manager import ThemeManager

    try:
        profil = ThemeManager.instance().current_profile()
        mass = profil.point_size / 10.0
        grenze = (SEITENLEISTE_MIN_BREITE - 2 * SEITENLEISTE_INNENABSTAND) * mass
        assert 0 < sidebar_logo_breite() <= grenze + 1
    finally:
        ThemeManager.reset()


def test_seitenleiste_zeigt_das_banner_statt_einer_textzeile(qapp, session):
    from PySide6.QtWidgets import QLabel

    from freizeitmanager.ui.main_window import MainWindow

    fenster = MainWindow()
    try:
        marke = fenster.findChild(QLabel, "sidebarLogo")
        assert marke is not None, "Die Seitenleiste hat keine Marken-Flaeche"
        assert not marke.pixmap().isNull(), "Dort steht immer noch nur Text"
    finally:
        fenster.close()
        fenster.deleteLater()


# ── Startbildschirm ──────────────────────────────────────────────


def test_splash_erscheint_und_verschwindet_mit_dem_hauptfenster(qapp):
    from PySide6.QtWidgets import QWidget

    from freizeitmanager.ui.startup_splash import StartupSplash

    splash = StartupSplash.start(qapp)
    try:
        assert splash.is_visible(), "Der Startbildschirm muss beim Start sichtbar sein"

        fenster = QWidget()
        fenster.show()
        splash.finish(fenster)

        assert not splash.is_visible()
        assert splash.widget() is None
        assert StartupSplash._active is None
        fenster.close()
    finally:
        StartupSplash.close_active()


def test_splash_weicht_einem_modalen_dialog(qapp):
    """Sonst klebt er ueber jedem Hinweis, den der Start zeigen will."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialog

    from freizeitmanager.ui.startup_splash import StartupSplash

    splash = StartupSplash.start(qapp)
    try:
        assert splash.is_visible()

        sichtbar_waehrend_dialog: list[bool] = []
        dialog = QDialog()
        QTimer.singleShot(
            0,
            lambda: (
                sichtbar_waehrend_dialog.append(splash.is_visible()),
                dialog.accept(),
            ),
        )
        dialog.exec()
        qapp.processEvents()

        assert sichtbar_waehrend_dialog == [False]
        assert splash.is_visible(), "Danach soll er das Laden weiter ueberbruecken"
    finally:
        StartupSplash.close_active()


def test_splash_laesst_sich_ohne_referenz_und_mehrfach_schliessen(qapp):
    """Der Notausgang aus main.py haelt keine Referenz auf den Splash."""
    from freizeitmanager.ui.startup_splash import StartupSplash

    splash = StartupSplash.start(qapp)
    StartupSplash.close_active()
    assert not splash.is_visible()

    # Idempotent: ein zweiter Aufruf darf nicht scheitern.
    StartupSplash.close_active()
    splash.close()
    splash.finish(None)
    assert StartupSplash._active is None
