"""Alle angebotenen Sprachen muessen den deutschen Schluesselsatz abdecken."""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from freizeitmanager.i18n.translator import FALLBACK_LANGUAGE, LANGUAGES

LOCALE_DIR = Path(__file__).resolve().parents[1] / "freizeitmanager" / "i18n"


def _flatten(data: dict, prefix: str = "") -> dict:
    out: dict = {}
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(_flatten(value, full))
        else:
            out[full] = value
    return out


def _load(lang: str) -> dict:
    return _flatten(json.loads((LOCALE_DIR / f"{lang}.json").read_text(encoding="utf-8")))


@pytest.mark.parametrize("lang", sorted(set(LANGUAGES) - {FALLBACK_LANGUAGE}))
def test_language_covers_fallback_keys(lang: str) -> None:
    base = _load(FALLBACK_LANGUAGE)
    other = _load(lang)
    assert not set(base) - set(other), f"{lang}: fehlende Schluessel"
    assert not set(other) - set(base), f"{lang}: unbekannte Schluessel"


@pytest.mark.parametrize("lang", sorted(set(LANGUAGES) - {FALLBACK_LANGUAGE}))
def test_placeholders_and_lists_match_fallback(lang: str) -> None:
    """Ein fehlender Platzhalter wuerde erst zur Laufzeit als KeyError auffallen."""
    base = _load(FALLBACK_LANGUAGE)
    other = _load(lang)
    for key, expected in base.items():
        actual = other[key]
        if isinstance(expected, str):
            assert isinstance(actual, str), f"{lang}/{key}: kein Text"
            assert set(re.findall(r"\{(\w+)\}", expected)) == set(
                re.findall(r"\{(\w+)\}", actual)
            ), f"{lang}/{key}: Platzhalter weichen ab"
        elif isinstance(expected, list):
            assert isinstance(actual, list) and len(actual) == len(expected), f"{lang}/{key}: Laenge"


def test_every_offered_language_has_a_file() -> None:
    for lang in LANGUAGES:
        assert (LOCALE_DIR / f"{lang}.json").is_file(), f"{lang}.json fehlt"


# ── Laufzeitpruefung: keine Schluessel in der Oberflaeche ────────────────────

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def _visible_texts(widget) -> list[str]:
    """Sammelt jeden sichtbaren Text aus einem Widgetbaum."""
    from PySide6.QtWidgets import QAbstractButton, QComboBox, QGroupBox, QLabel, QTableWidget
    texts: list[str] = []
    for child in widget.findChildren(object):
        if isinstance(child, QLabel | QAbstractButton | QGroupBox):
            texts.append(child.text() if hasattr(child, "text") else child.title())
        if isinstance(child, QComboBox):
            texts.extend(child.itemText(i) for i in range(child.count()))
        if isinstance(child, QTableWidget):
            header = child.horizontalHeader()
            texts.extend(child.horizontalHeaderItem(i).text()
                         for i in range(child.columnCount())
                         if child.horizontalHeaderItem(i) is not None)
            texts.extend(child.item(r, c).text()
                         for r in range(child.rowCount())
                         for c in range(child.columnCount())
                         if child.item(r, c) is not None)
            del header
    return [text for text in texts if text]


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_keine_unaufgeloesten_schluessel_in_der_oberflaeche(session, lang):
    """Ein vergessenes t() faellt sonst erst dem Benutzer auf.

    ``t()`` gibt bei einem unbekannten Schluessel den Schluessel selbst
    zurueck. Genau danach wird hier gesucht - in jeder Sprache und auf
    jeder Seite.
    """
    pytest.importorskip("PySide6")
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from freizeitmanager.i18n.translator import set_language
    from freizeitmanager.logic import contact_service as cs

    app = QApplication.instance() or QApplication([])
    person = cs.create_contact(session, "Marko", importance=5, target_interval_days=21)
    cs.log_interaction(session, person.id, "meet",
                       occurred_on=date.today() - timedelta(days=60))
    session.commit()

    set_language(lang)
    from freizeitmanager.ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    app.processEvents()

    leaks: list[str] = []
    for page in ("cockpit", "contacts", "settings", "rotation"):
        window.show_page(page)
        app.processEvents()
        leaks += [text for text in _visible_texts(window) if KEY_PATTERN.match(text)]

    set_language("de")
    assert not leaks, f"{lang}: unaufgeloeste Schluessel {sorted(set(leaks))}"
