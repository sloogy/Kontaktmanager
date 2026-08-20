"""Farben und Knopfstile aus dem aktiven Theme.

Bewusst Funktionen statt Konstanten: Ein Modul-Dict wird beim Import
ausgewertet und wuerde das Theme einfrieren, das beim Programmstart aktiv
war. Ein Wechsel zur Laufzeit haette dann keine Wirkung - derselbe Grund,
aus dem auch die Uebersetzungen lazy aufgeloest werden.
"""
from __future__ import annotations

from freizeitmanager.ui.theme_manager import ThemeManager

# Dringlichkeitsstufe -> Farbschluessel im Profil
URGENCY_KEYS = {
    "fresh": "dringlichkeit_frisch",
    "soon": "dringlichkeit_bald",
    "due": "dringlichkeit_faellig",
    "long": "dringlichkeit_lange",
}


def color(key: str) -> str:
    return ThemeManager.instance().current_profile().color(key)


def urgency_accent(urgency: str) -> str:
    """Akzentfarbe einer Dringlichkeitsstufe; unbekannt -> gedaempft."""
    key = URGENCY_KEYS.get(urgency)
    return color(key) if key else color("text_gedimmt")


def planned_accent() -> str:
    return color("dringlichkeit_geplant")


def neutral_accent() -> str:
    return color("text_gedimmt")


def _button(background: str, text: str, *, border: str = "none",
            weight: int = 700) -> str:
    return (f"background:{background};color:{text};border:{border};"
            f"padding:8px 18px;border-radius:6px;font-weight:{weight};")


def btn_primary() -> str:
    return _button(color("akzent"), color("akzent_text"))


def btn_success() -> str:
    return _button(color("erfolg"), color("erfolg_text"))


def btn_secondary() -> str:
    return _button(color("hover_hintergrund"), color("text"),
                   border=f"1px solid {color('rand')}", weight=600)


def btn_quiet() -> str:
    return (f"background:transparent;color:{color('text_gedimmt')};"
            f"border:1px solid {color('rand')};padding:8px 14px;border-radius:6px;")


def btn_danger() -> str:
    return _button(color("gefahr"), color("text_invers"))
