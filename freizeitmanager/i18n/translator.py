"""Uebersetzungen: laedt die Sprach-JSONs und stellt ``t()`` bereit.

Aufbau bewusst wie in FPM, damit die LifePlanner-Module gleich funktionieren:
Schluessel in Punktschreibweise, Deutsch als Rueckfallebene, fehlende
Schluessel liefern den Schluessel selbst zurueck statt zu scheitern.

Datumsformate gehoeren mit zur Sprache: ein englischsprachiger Nutzer erwartet
"20/08/2026", kein "20.08.2026".
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from freizeitmanager.defensive_log import uebersprungen

FALLBACK_LANGUAGE = "de"

LANGUAGES: dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
    "fr": "Fran\N{LATIN SMALL LETTER C WITH CEDILLA}ais",
}

# Anzeigeformat je Sprache. %-Codes bewusst nicht verwendet: strftime gibt
# Monats- und Tagesnamen in der Systemsprache aus, nicht in der gewaehlten.
DATE_FORMATS: dict[str, str] = {
    "de": "DD.MM.YYYY",
    "en": "DD/MM/YYYY",
    "fr": "DD/MM/YYYY",
}

def locale_dir() -> Path:
    """Ordner der Sprachdateien - im Quellbaum wie im gebauten Paket.

    PyInstaller entpackt mitgelieferte Daten nach ``sys._MEIPASS``. Dort liegt
    ``freizeitmanager/i18n`` neben dem Code, nicht darin.
    """
    bundle = getattr(sys, "_MEIPASS", "")
    if bundle:
        packed = Path(bundle) / "freizeitmanager" / "i18n"
        if packed.is_dir():
            return packed
    return Path(__file__).resolve().parent


_LOCALE_DIR = locale_dir()


class Translator:
    """Singleton. Immer ueber ``instance()`` ansprechen."""

    _instance: Translator | None = None

    def __init__(self) -> None:
        self._lang = FALLBACK_LANGUAGE
        self._data: dict = {}
        self._fallback: dict = self._read(FALLBACK_LANGUAGE)
        self._data = dict(self._fallback)

    @classmethod
    def instance(cls) -> Translator:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def language(self) -> str:
        return self._lang

    @staticmethod
    def _read(lang: str) -> dict:
        path = _LOCALE_DIR / f"{lang}.json"
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def set_language(self, lang: str) -> str:
        lang = str(lang or "").strip().lower()
        if lang not in LANGUAGES:
            lang = FALLBACK_LANGUAGE
        self._data = self._read(lang) or dict(self._fallback)
        self._lang = lang
        return lang

    def load_from_settings(self) -> str:
        """Sprache aus der Datenbank aktivieren. Sicher vor der Initialisierung."""
        try:
            from freizeitmanager.database import db
            with db.get_session() as session:
                return self.set_language(db.get_setting(session, "ui.language", FALLBACK_LANGUAGE))
        except Exception:
            return self.set_language(FALLBACK_LANGUAGE)

    @staticmethod
    def _resolve(data: dict, key: str) -> Any:
        node: Any = data
        for part in key.split("."):
            if not isinstance(node, dict):
                return None
            node = node.get(part)
            if node is None:
                return None
        return node

    def t(self, key: str, **kwargs) -> str:
        node = self._resolve(self._data, key)
        if not isinstance(node, str):
            node = self._resolve(self._fallback, key)
        text = node if isinstance(node, str) else key
        if kwargs:
            # Ein fehlender Platzhalter darf die Oberflaeche nicht zerreissen:
            # lieber der unformatierte Text als eine Ausnahme im Aufbau.
            # Stumm bleiben darf er trotzdem nicht - sonst steht "{name}" im
            # Text und niemand erfaehrt, in welchem Schluessel es klemmt.
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError, ValueError) as fehler:
                uebersprungen(f"t({key!r})", fehler)
        return text

    def format_date(self, value: date | datetime | None) -> str:
        if value is None:
            return "\N{EM DASH}"
        if isinstance(value, datetime):
            value = value.date()
        pattern = DATE_FORMATS.get(self._lang, DATE_FORMATS[FALLBACK_LANGUAGE])
        return (pattern.replace("YYYY", f"{value.year:04d}")
                       .replace("MM", f"{value.month:02d}")
                       .replace("DD", f"{value.day:02d}"))

    def format_short_date(self, value: date | datetime | None) -> str:
        """Tag und Monat ohne Jahr - fuer Termine in naher Zukunft."""
        if value is None:
            return "\N{EM DASH}"
        if isinstance(value, datetime):
            value = value.date()
        if self._lang == "de":
            return f"{value.day:02d}.{value.month:02d}."
        return f"{value.day:02d}/{value.month:02d}"

    def weekday_name(self, value: date, short: bool = True) -> str:
        """Wochentag in der gewaehlten Sprache, nicht in der Systemsprache."""
        keys = "i18n.weekdays_short" if short else "i18n.weekdays"
        names = self._resolve(self._data, keys) or self._resolve(self._fallback, keys)
        if isinstance(names, list) and len(names) == 7:
            return names[value.weekday()]
        return value.strftime("%a" if short else "%A")


def t(key: str, **kwargs) -> str:
    return Translator.instance().t(key, **kwargs)


def set_language(lang: str) -> str:
    return Translator.instance().set_language(lang)


def current_language() -> str:
    return Translator.instance().language


def load_language_from_settings() -> str:
    return Translator.instance().load_from_settings()


def format_date(value) -> str:
    return Translator.instance().format_date(value)


def format_short_date(value) -> str:
    return Translator.instance().format_short_date(value)


def weekday_name(value: date, short: bool = True) -> str:
    return Translator.instance().weekday_name(value, short)
