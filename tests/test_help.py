"""Hilfe und Handbuch.

Die Hilfe ist der einzige Ort, an dem die Anwendung sich selbst erklaert.
Ein fehlender Text faellt hier auf und nicht erst dem Benutzer.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from freizeitmanager.i18n.translator import LANGUAGES, set_language, t
from freizeitmanager.ui.help_dialog import HELP_TOPICS, HelpDialog, matches

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _german_again():
    yield
    set_language("de")


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_jedes_thema_hat_titel_und_text(lang):
    """Ein fehlender Schluessel wuerde als roher Schluessel im Text landen."""
    set_language(lang)
    for key in HELP_TOPICS:
        title = t(f"help.topics.{key}.title")
        body = t(f"help.topics.{key}.body")
        assert title and not title.startswith("help."), f"{lang}/{key}: Titel fehlt"
        assert len(body) > 120 and not body.startswith("help."), f"{lang}/{key}: Text fehlt"


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_dialog_baut_in_jeder_sprache_auf(qapp, session, lang):
    set_language(lang)
    dialog = HelpDialog()
    assert dialog._topics.count() == len(HELP_TOPICS)
    assert dialog.current_topic() == HELP_TOPICS[0]
    assert "help." not in dialog._text.toPlainText()
    assert dialog.windowTitle() and "help." not in dialog.windowTitle()


def test_suche_findet_auch_im_text(qapp, session):
    """Eine Suche nur ueber Titel fände zu wenig - der Import steht im Text."""
    set_language("de")
    assert matches("import", "Excel")
    assert matches("birthdays", "29. Februar")
    assert not matches("birthdays", "Quartalsabschluss")


def test_suche_filtert_die_themenliste(qapp, session):
    dialog = HelpDialog()
    dialog._search.setText("Geburtstag")
    assert dialog._topics.count() < len(HELP_TOPICS)
    assert dialog._topics.count() >= 1
    dialog._search.setText("Quartalsabschluss")
    assert dialog._topics.count() == 0
    assert dialog._empty.isVisible() or not dialog._topics.isVisible()
    dialog._search.setText("")
    assert dialog._topics.count() == len(HELP_TOPICS)


def test_dialog_springt_auf_ein_thema(qapp, session):
    dialog = HelpDialog("birthdays")
    assert dialog.current_topic() == "birthdays"
    assert not dialog.show_topic("gibt_es_nicht")


def test_hilfeknopf_und_f1_hängen_am_hauptfenster(qapp, session):
    from freizeitmanager.ui.main_window import MainWindow
    window = MainWindow()
    assert window._help_button.text() == t("help.button")
    assert hasattr(window, "open_help")


def test_handbuch_ist_aktuell():
    """Sonst weicht das Handbuch nach zwei Releases von der Hilfe ab."""
    result = subprocess.run([sys.executable, "tools/build_handbook.py", "--check"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_handbuch_enthaelt_jedes_thema():
    guide = (ROOT / "docs" / "USER_GUIDE.de.md").read_text(encoding="utf-8")
    page = (ROOT / "docs" / "help" / "index.html").read_text(encoding="utf-8")
    topics = json.loads((ROOT / "freizeitmanager" / "i18n" / "de.json")
                        .read_text(encoding="utf-8"))["help"]["topics"]
    for key in HELP_TOPICS:
        title = topics[key]["title"]
        assert title in guide, f"{key} fehlt im Handbuch"
        assert title in page, f"{key} fehlt auf der Hilfeseite"


def test_handbuch_liegt_im_paket():
    """Ohne diesen Eintrag fuehrt der Knopf 'Handbuch oeffnen' ins Leere."""
    spec = (ROOT / "FreizeitManager.spec").read_text(encoding="utf-8")
    assert 'docs" / "help" / "index.html"' in spec or "docs/help" in spec
