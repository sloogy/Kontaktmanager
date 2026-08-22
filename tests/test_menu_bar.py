"""Die Menueleiste des Hauptfensters (Loop 33).

Der FreizeitManager hatte bis dahin keine - wie FPM bis Loop 32. Der
BudgetManager ist die Design-Vorlage der Suite; diese Tests halten fest, was
daran verbindlich ist: nicht die Beschriftungen, sondern der Aufbau und die
Richtlinien, nach denen er entsteht.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from freizeitmanager.i18n.translator import t


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def fenster(qapp, session):
    from freizeitmanager.ui.main_window import MainWindow

    w = MainWindow()
    yield w
    w.close()


def _menues(fenster) -> dict:
    """Die Menues, wie das Fenster sie haelt.

    Nicht ueber ``menuBar().actions()[i].menu()``: ``QAction.menu`` liefert in
    PySide6 eine Huelle, die Python gehoert - als verworfener Zwischenwert
    nimmt sie das Menue mit. Genau deshalb haelt das Fenster sie selbst fest.
    """
    return {menu.title(): menu for menu in fenster._menus}


def test_die_vier_menues_der_vorlage_sind_da(fenster):
    """Datei, Ansicht, Extras, Hilfe - in dieser Reihenfolge, wie im
    BudgetManager."""
    assert list(_menues(fenster)) == [
        t("menu.file"), t("menu.view"), t("menu.extras"), t("menu.help")
    ]


def test_jedes_menue_hat_eindeutige_zugriffstasten(fenster):
    """Zwei Eintraege mit demselben ``&``-Buchstaben machen die Zugriffstaste
    wertlos - sie springt dann nur noch hin und her."""
    for titel, menu in _menues(fenster).items():
        tasten = [a.text().split("&", 1)[1][:1].lower()
                  for a in menu.actions() if "&" in a.text()]
        assert len(tasten) == len(set(tasten)), f"{titel}: {tasten}"


def test_auslassungspunkte_nur_wo_ein_dialog_folgt(fenster):
    """``…`` steht nur vor Befehlen mit Rueckfrage, und nie als drei Punkte."""
    mit_dialog = {t("menu.add_contact")}
    for menu in _menues(fenster).values():
        for aktion in menu.actions():
            text = aktion.text()
            if not text:
                continue
            assert "..." not in text, text
            if text.endswith("…"):
                assert text in mit_dialog, text


def test_ueber_steht_zuletzt(fenster):
    hilfe = _menues(fenster)[t("menu.help")]
    assert [a.text() for a in hilfe.actions() if a.text()][-1] == t("menu.about")


def test_das_ansichtsmenue_kennt_jede_seite(fenster):
    """Das Menue ist eine zweite Tuer zum selben Raum: Was die Seitenleiste
    anbietet, muss auch hier stehen."""
    from freizeitmanager.ui.main_window import PAGES

    assert len(fenster._menu_page_actions) == len(PAGES)
    assert set(fenster._menu_page_actions) == {k for k, _, _ in PAGES}


def test_expertenseiten_bleiben_im_einfachmodus_auch_im_menue_verborgen(fenster):
    """Sonst fuehrt das Menue auf eine Seite, die die Seitenleiste
    ausdruecklich versteckt - und der Modus waere nur noch halb echt."""
    rotation = fenster._menu_page_actions["rotation"]
    if fenster._expert:
        fenster._toggle_mode()
    assert not rotation.isVisible()
    fenster._toggle_mode()
    assert rotation.isVisible()


def test_der_modus_im_menue_folgt_dem_fenster(fenster):
    """Der Umschalter sitzt an drei Stellen - Seitenleiste, Kuerzel, Menue.
    Zeigen sie Verschiedenes, ist einer davon falsch."""
    for _ in range(2):
        fenster._toggle_mode()
        assert fenster._menu_mode_actions[fenster._expert].isChecked()
        assert not fenster._menu_mode_actions[not fenster._expert].isChecked()


def test_die_menueleiste_ersetzt_die_seitenleiste_nicht(fenster):
    """Wer den FreizeitManager kennt, soll nach dem Update nicht umlernen."""
    assert fenster._nav_buttons
    assert fenster._help_button is not None


def test_zugriffstasten_sind_in_jeder_sprache_eindeutig():
    """Uebersetzt wird Wort fuer Wort, das ``&`` wandert mit - und landet
    leicht auf einem Buchstaben, den im selben Menue schon jemand hat. Der
    Konflikt faellt sonst erst dem Nutzer auf, der die Sprache benutzt."""
    gruppen = {
        "leiste": ["file", "view", "extras", "help"],
        "file": ["settings", "open_data_folder", "exit"],
        "view": ["pages", "mode", "fullscreen"],
        "extras": ["add_contact", "toggle_mode"],
        "help": ["manual", "about"],
    }
    wurzel = Path(__file__).resolve().parents[1] / "freizeitmanager" / "i18n"
    for sprache in ("de", "en", "fr"):
        menu = json.loads((wurzel / f"{sprache}.json").read_text(encoding="utf-8"))["menu"]
        for name, schluessel in gruppen.items():
            fehlend = [k for k in schluessel if "&" not in menu[k]]
            assert not fehlend, f"{sprache}/{name} ohne Zugriffstaste: {fehlend}"
            tasten = [menu[k].split("&", 1)[1][:1].lower() for k in schluessel]
            assert len(tasten) == len(set(tasten)), f"{sprache}/{name}: {tasten}"


def test_das_menue_waechst_mit_der_profilschrift(session):
    """Loop 8 hat das durchgesetzt, Loop 9 die abgestuften Radien. Eine
    Menueleiste mit festen Pixelwerten waere in beidem ein Rueckschritt."""
    from freizeitmanager.ui.styles import get_stylesheet

    def polster(css: str) -> str:
        i = css.index("QMenuBar::item {")
        return css[i:css.index("}", i)]

    klein = polster(get_stylesheet(1.0))
    gross = polster(get_stylesheet(1.6))
    assert klein != gross
    assert "border-radius" in klein
