"""Stylesheet des FreizeitManagers - vollstaendig aus dem aktiven Theme.

Frueher standen hier rund fuenfzig feste Farbwerte. Jede einzelne kam aus
dem Profil zu ersetzen war der eigentliche Sinn dieser Umstellung: Ein
dunkles Theme, das an drei Stellen noch weisse Flaechen zeigt, ist
schlimmer als gar keines.

Die Schriftgroesse kommt ebenfalls aus dem Profil; ``scale`` bleibt als
zusaetzlicher Faktor fuer HiDPI-Anzeigen erhalten.
"""
from __future__ import annotations

from freizeitmanager.ui.theme_manager import ThemeManager, ThemeProfile


def _px(value: float, scale: float) -> int:
    return max(1, int(round(float(value) * float(scale))))


def get_stylesheet(scale: float = 1.0, profile: ThemeProfile | None = None) -> str:
    profile = profile or ThemeManager.instance().current_profile()
    scale = max(0.85, min(1.50, float(scale or 1.0)))

    c = profile.color
    base = _px(profile.point_size, scale)
    # Zwei Faktoren, bewusst getrennt: ``scale`` ist die Bedienskalierung der
    # Oberflaeche, ``mass`` bezieht zusaetzlich die Profilschrift ein. Raender
    # und Abstaende folgen ``mass``, damit sie bei grosser Schrift mitwachsen -
    # die Schriftgroesse selbst darf das nicht, sonst zaehlte die Einstellung
    # doppelt.
    mass = max(0.85, min(1.50, scale * profile.point_size / 10.0))
    small = max(1, base - 1)
    tiny = max(1, base - 2)
    nav = base + 1
    title = base + 7
    # Abgestufte Radien nach dem Vorbild des BudgetManagers: je groesser die
    # Flaeche, desto runder die Ecke. Karten standen vorher bei 9, Gruppen
    # ebenfalls - eine eigene Stufe, die sich mit keinem der anderen
    # Programme deckte.
    radius_feld = _px(4, mass)     # Eingaben
    radius = _px(6, mass)          # Schaltflaechen, allgemeine Flaechen
    radius_karte = _px(8, mass)    # Gruppen und Karten

    return f"""
QMainWindow, QDialog, QWidget {{
    background-color: {c('hintergrund_app')};
    color: {c('text')};
    font-family: "Segoe UI", "Helvetica Neue", Cantarell, Arial, sans-serif;
    font-size: {base}px;
}}

/* QLabel erbt sonst die Seitenfarbe und zeichnet graue Baender in die Karten. */
QLabel {{ background: transparent; color: {c('text')}; }}
QCheckBox {{ background: transparent; color: {c('text')}; spacing: {_px(7, mass)}px; }}
QCheckBox::indicator {{
    width: {_px(16, mass)}px;
    height: {_px(16, mass)}px;
    border: 1px solid {c('rand')};
    border-radius: {_px(3, mass)}px;
    background: {c('eingabe_hintergrund')};
}}
QCheckBox::indicator:hover {{ border-color: {c('akzent')}; }}
QCheckBox::indicator:checked {{
    background: {c('akzent')};
    border-color: {c('akzent')};
    image: none;
}}
QCheckBox::indicator:disabled {{ border-color: {c('text_gedimmt')}; background: transparent; }}
QCheckBox:disabled {{ color: {c('text_gedimmt')}; }}
QToolTip {{
    background-color: {c('hintergrund_panel')};
    color: {c('text')};
    border: 1px solid {c('rand')};
    padding: {_px(4, mass)}px;
}}

/* ── Sidebar ─────────────────────────────────────────────── */
QWidget#sidebar {{
    background-color: {c('hintergrund_seitenleiste')};
    border-right: 3px solid {c('akzent')};
    min-width: {_px(210, mass)}px;
    max-width: {_px(250, mass)}px;
}}
QWidget#sidebar QWidget {{ background-color: {c('hintergrund_seitenleiste')}; }}
QLabel#sidebarLogo {{
    color: {c('seitenleiste_text')};
    font-size: {base + 3}px;
    font-weight: 800;
    padding: {_px(20, mass)}px {_px(16, mass)}px {_px(14, mass)}px {_px(16, mass)}px;
}}
QPushButton#navButton {{
    background-color: transparent;
    color: {c('seitenleiste_text')};
    border: none;
    text-align: left;
    padding: {_px(12, mass)}px {_px(16, mass)}px;
    font-size: {nav}px;
    border-radius: 0;
    min-height: {_px(40, mass)}px;
}}
QPushButton#navButton:hover {{ background-color: {c('hover_hintergrund')}; color: {c('hover_text')}; }}
QPushButton#navButton:checked {{
    background-color: {c('akzent')};
    color: {c('akzent_text')};
    font-weight: 800;
}}
/* Der Knopf sitzt in der Seitenleiste und muss deren Farben tragen.
   Mit den Panel-Farben war er in dunklen Themes dunkel auf dunkel - also
   ein leeres Rechteck. */
QPushButton#modeToggle {{
    background-color: transparent;
    color: {c('seitenleiste_text')};
    border: 1px solid {c('seitenleiste_text_gedimmt')};
    border-radius: {radius}px;
    padding: {_px(8, mass)}px;
    margin: {_px(8, mass)}px {_px(12, mass)}px;
    font-size: {tiny}px;
    font-weight: 700;
}}
QPushButton#modeToggle:hover {{ background-color: {c('akzent')}; color: {c('akzent_text')}; border-color: {c('akzent')}; }}
QLabel#sidebarVersion {{
    color: {c('seitenleiste_text_gedimmt')};
    font-size: {tiny}px;
    padding: {_px(10, mass)}px {_px(16, mass)}px;
}}

/* ── Seitenkopf ──────────────────────────────────────────── */
QLabel#pageTitle {{ font-size: {title}px; font-weight: 800; color: {c('text')}; }}
QLabel#pageHint {{ font-size: {small}px; color: {c('text_gedimmt')}; }}

/* ── Kacheln ─────────────────────────────────────────────── */
QFrame#focusTile {{
    background: {c('karte_hintergrund')};
    border: 2px solid {c('karte_rand')};
    border-radius: {radius_karte}px;
}}
QLabel#tileTitle {{ border: none; font-size: {tiny}px; font-weight: 800; }}
QLabel#tileValue {{ border: none; font-size: {base + 12}px; font-weight: 800; color: {c('text')}; }}
QLabel#tileDetail {{ border: none; font-size: {tiny}px; color: {c('text_gedimmt')}; }}

/* ── Vorschlagskarten ────────────────────────────────────── */
QFrame#stepCard {{
    background: {c('karte_hintergrund')};
    border: 1px solid {c('karte_rand')};
    border-left: {_px(5, mass)}px solid {c('text_gedimmt')};
    border-radius: {radius_karte}px;
}}
QLabel#stepDot {{ border: none; font-size: {base + 1}px; }}
QLabel#stepName {{ border: none; font-size: {base + 3}px; font-weight: 800; color: {c('text')}; }}
QLabel#stepUrgency {{ border: none; font-size: {tiny}px; font-weight: 700; }}
QLabel#stepSuggestion {{ border: none; font-size: {base}px; color: {c('text')}; }}
QLabel#stepGap {{ border: none; font-size: {tiny}px; color: {c('text_gedimmt')}; }}
QLabel#stepWhy {{ border: none; font-size: {tiny}px; color: {c('text_gedimmt')}; }}
QPushButton#whyToggle {{
    background: transparent; border: none; color: {c('akzent')};
    font-size: {tiny}px; text-align: left; padding: 0;
}}
QPushButton#whyToggle:hover {{ text-decoration: underline; }}

/* ── Ruhezustand ─────────────────────────────────────────── */
QFrame#calmCard {{
    background: {c('ruhe_hintergrund')};
    border: 1px solid {c('ruhe_rand')};
    border-radius: {radius_karte}px;
}}
QLabel#calmText {{ border: none; color: {c('ruhe_text')}; font-size: {base + 1}px; font-weight: 700; }}

/* ── Energiewahl ─────────────────────────────────────────── */
QPushButton#energyButton {{
    background: {c('hintergrund_panel')};
    color: {c('text_gedimmt')};
    border: 1px solid {c('rand')};
    border-radius: {_px(16, mass)}px;
    padding: {_px(6, mass)}px {_px(14, mass)}px;
    font-size: {small}px;
}}
QPushButton#energyButton:hover {{ background: {c('hover_hintergrund')}; color: {c('hover_text')}; }}
QPushButton#energyButton:checked {{
    background: {c('akzent')};
    color: {c('akzent_text')};
    border-color: {c('akzent')};
    font-weight: 700;
}}

/* ── Bereiche ────────────────────────────────────────────── */
QGroupBox {{
    background: {c('hintergrund_panel')};
    border: 1px solid {c('rand')};
    border-radius: {radius_karte}px;
    margin-top: {_px(16, mass)}px;
    padding-top: {_px(14, mass)}px;
    font-weight: 700;
    color: {c('text')};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: {_px(12, mass)}px;
    padding: 0 {_px(6, mass)}px;
    color: {c('text')};
}}

/* ── Tabellen ────────────────────────────────────────────── */
QTableWidget {{
    background: {c('tabelle_hintergrund')};
    alternate-background-color: {c('tabelle_alt')};
    color: {c('text')};
    border: 1px solid {c('rand')};
    border-radius: {radius}px;
    gridline-color: {c('tabelle_gitter')};
    selection-background-color: {c('auswahl_hintergrund')};
    selection-color: {c('auswahl_text')};
}}
QHeaderView::section {{
    background: {c('tabelle_header')};
    color: {c('tabelle_header_text')};
    border: none;
    border-bottom: 1px solid {c('rand')};
    padding: {_px(7, mass)}px;
    font-weight: 700;
    font-size: {tiny}px;
}}
QTableWidget::item {{ padding: {_px(5, mass)}px; }}
QTableWidget::item:hover {{ background: {c('hover_hintergrund')}; color: {c('hover_text')}; }}

/* ── Eingaben ────────────────────────────────────────────── */
QLineEdit, QSpinBox, QComboBox, QDateEdit, QTextEdit, QListWidget {{
    background: {c('eingabe_hintergrund')};
    color: {c('text')};
    border: 1px solid {c('rand')};
    border-radius: {radius_feld}px;
    padding: {_px(5, mass)}px {_px(8, mass)}px;
    min-height: {_px(26, mass)}px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {{
    border-color: {c('akzent')};
}}
QComboBox QAbstractItemView {{
    background: {c('eingabe_hintergrund')};
    color: {c('text')};
    border: 1px solid {c('rand')};
    selection-background-color: {c('auswahl_hintergrund')};
    selection-color: {c('auswahl_text')};
}}
QListWidget::item:selected {{
    background: {c('auswahl_hintergrund')};
    color: {c('auswahl_text')};
}}
/* Loop 33: Menue und Menueleiste nach der BudgetManager-Vorlage. Die Leiste
   ist neu, das Kontextmenue gab es schon - beide tragen jetzt die abgestuften
   Radien (Loop 9) und wachsen mit der Profilschrift (Loop 8). */
QMenu {{
    background: {c('hintergrund_panel')};
    color: {c('text')};
    border: 1px solid {c('rand')};
    border-radius: {radius}px;
    padding: {_px(4, mass)}px;
    font-size: {base}px;
}}
QMenu::item {{ padding: {_px(6, mass)}px {_px(18, mass)}px; border-radius: {radius_feld}px; }}
QMenu::item:selected {{ background: {c('auswahl_hintergrund')}; color: {c('auswahl_text')}; }}
QMenu::item:disabled {{ color: {c('text_gedimmt')}; }}
QMenu::separator {{ height: 1px; background: {c('rand')}; margin: {_px(4, mass)}px {_px(8, mass)}px; }}
QMenuBar {{ background: {c('hintergrund_panel')}; color: {c('text')}; font-size: {base}px; padding: {_px(2, mass)}px; }}
QMenuBar::item {{ padding: {_px(4, mass)}px {_px(10, mass)}px; border-radius: {radius}px; }}
QMenuBar::item:selected {{ background: {c('auswahl_hintergrund')}; color: {c('auswahl_text')}; }}
QPushButton {{ min-height: {_px(28, mass)}px; }}

QScrollArea {{ border: none; background: {c('hintergrund_app')}; }}
QScrollArea > QWidget > QWidget {{ background: {c('hintergrund_app')}; }}
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {c('hintergrund_app')};
    border: none;
    width: {_px(11, mass)}px;
    height: {_px(11, mass)}px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {c('rand')};
    border-radius: {_px(5, mass)}px;
    min-height: {_px(28, mass)}px;
}}
QScrollBar::handle:hover {{ background: {c('text_gedimmt')}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


def install_emoji_fallback() -> None:
    """Sorgt dafuer, dass Symbole ausserhalb der Basisebene erscheinen koennen.

    Qt waehlt aus einer Stylesheet-Familienkette die erste vorhandene Schrift
    und faellt fuer Symbole nicht zuverlaessig weiter.
    """
    try:
        from PySide6.QtGui import QFont, QFontDatabase
    except ModuleNotFoundError:  # pragma: no cover - headless
        return
    families = set(QFontDatabase.families())
    emoji = next((name for name in ("Noto Color Emoji", "Noto Emoji",
                                    "Segoe UI Emoji", "Apple Color Emoji")
                  if name in families), None)
    if emoji is None:
        return
    for name in (QFont().family(), "Segoe UI", "Helvetica Neue", "Cantarell", "Arial"):
        if name:
            QFont.insertSubstitutions(name, [emoji])
