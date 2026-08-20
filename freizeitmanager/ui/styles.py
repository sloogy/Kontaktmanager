"""Stylesheet des FreizeitManagers.

Bewusst nah an FPM/BudgetManager, damit die LifePlanner-Module wie eine
Familie wirken. Skalierbar, weil Laptop- und HiDPI-Displays sonst
abgeschnittene Eingabefelder zeigen.
"""
from __future__ import annotations


def _px(value: float, scale: float) -> int:
    return max(1, int(round(float(value) * float(scale))))


def get_stylesheet(scale: float = 1.0) -> str:
    scale = max(0.85, min(1.50, float(scale or 1.0)))
    base = _px(14, scale)
    small = _px(13, scale)
    tiny = _px(12, scale)
    nav = _px(15, scale)
    title = _px(21, scale)
    radius = _px(6, scale)

    return f"""
QMainWindow, QDialog, QWidget {{
    background-color: #f1f5f9;
    color: #1e293b;
    font-family: "Segoe UI", "Helvetica Neue", Cantarell, Arial, sans-serif, "Noto Color Emoji", "Segoe UI Emoji";
    font-size: {base}px;
}}

/* QLabel erbt sonst die Seitenfarbe und zeichnet graue Baender in die Karten. */
QLabel {{ background: transparent; }}
QCheckBox {{ background: transparent; }}

/* ── Sidebar ─────────────────────────────────────────────── */
QWidget#sidebar {{
    background-color: #0b1220;
    border-right: 3px solid #2563eb;
    min-width: {_px(210, scale)}px;
    max-width: {_px(250, scale)}px;
}}
QWidget#sidebar QWidget {{ background-color: #0b1220; }}
QLabel#sidebarLogo {{
    color: #f8fafc; font-size: {_px(17, scale)}px; font-weight: 800;
    padding: {_px(20, scale)}px {_px(16, scale)}px {_px(14, scale)}px {_px(16, scale)}px;
    background-color: #020617;
}}
QPushButton#navButton {{
    background-color: #0f172a; color: #e2e8f0; border: none;
    text-align: left; padding: {_px(12, scale)}px {_px(16, scale)}px;
    font-size: {nav}px; border-radius: 0; min-height: {_px(40, scale)}px;
}}
QPushButton#navButton:hover {{ background-color: #1e293b; color: #ffffff; }}
QPushButton#navButton:checked {{ background-color: #1d4ed8; color: #ffffff; font-weight: 800; }}
QPushButton#modeToggle {{
    background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155;
    border-radius: {radius}px; padding: {_px(8, scale)}px;
    margin: {_px(8, scale)}px {_px(12, scale)}px; font-size: {tiny}px; font-weight: 700;
}}
QPushButton#modeToggle:hover {{ background-color: #334155; }}
QLabel#sidebarVersion {{ color: #64748b; font-size: {tiny}px; padding: {_px(10, scale)}px {_px(16, scale)}px; }}

/* ── Seitenkopf ──────────────────────────────────────────── */
QLabel#pageTitle {{ font-size: {title}px; font-weight: 800; color: #0f172a; }}
QLabel#pageHint {{ font-size: {small}px; color: #64748b; }}

/* ── Kacheln ─────────────────────────────────────────────── */
QFrame#focusTile {{ background: #ffffff; border: 2px solid #dbe3ec; border-radius: {_px(9, scale)}px; }}
QFrame#focusTile:hover {{ background: #f8fbff; }}
QLabel#tileTitle {{ border: none; font-size: {tiny}px; font-weight: 800; }}
QLabel#tileValue {{ border: none; font-size: {_px(26, scale)}px; font-weight: 800; color: #0f172a; }}
QLabel#tileDetail {{ border: none; font-size: {tiny}px; color: #64748b; }}

/* ── Vorschlagskarten ────────────────────────────────────── */
QFrame#stepCard {{ background: #ffffff; border: 1px solid #dbe3ec;
    border-left: {_px(5, scale)}px solid #94a3b8; border-radius: {_px(9, scale)}px; }}
QLabel#stepDot {{ border: none; font-size: {_px(15, scale)}px; }}
QLabel#stepName {{ border: none; font-size: {_px(17, scale)}px; font-weight: 800; color: #0f172a; }}
QLabel#stepUrgency {{ border: none; font-size: {tiny}px; font-weight: 700; }}
QLabel#stepSuggestion {{ border: none; font-size: {base}px; color: #334155; }}
QLabel#stepGap {{ border: none; font-size: {tiny}px; color: #64748b; }}
QLabel#stepWhy {{ border: none; font-size: {tiny}px; color: #475569; }}
QPushButton#whyToggle {{ background: transparent; border: none; color: #2563eb;
    font-size: {tiny}px; text-align: left; padding: 0; }}
QPushButton#whyToggle:hover {{ text-decoration: underline; }}

/* ── Ruhezustand ─────────────────────────────────────────── */
QFrame#calmCard {{ background: #f0fdf4; border: 1px solid #86efac; border-radius: {_px(9, scale)}px; }}
QLabel#calmText {{ border: none; color: #15803d; font-size: {_px(15, scale)}px; font-weight: 700; }}

/* ── Energiewahl ─────────────────────────────────────────── */
QPushButton#energyButton {{
    background: #ffffff; color: #475569; border: 1px solid #cbd5e1;
    border-radius: {_px(16, scale)}px; padding: {_px(6, scale)}px {_px(14, scale)}px;
    font-size: {small}px;
}}
QPushButton#energyButton:checked {{ background: #1d4ed8; color: #ffffff; border-color: #1d4ed8; font-weight: 700; }}

/* ── Bereiche ────────────────────────────────────────────── */
QGroupBox {{
    background: #ffffff; border: 1px solid #dbe3ec; border-radius: {_px(9, scale)}px;
    margin-top: {_px(16, scale)}px; padding-top: {_px(14, scale)}px; font-weight: 700;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: {_px(12, scale)}px;
    padding: 0 {_px(6, scale)}px; color: #334155; }}

/* ── Tabellen ────────────────────────────────────────────── */
QTableWidget {{ background: #ffffff; border: 1px solid #dbe3ec; border-radius: {radius}px;
    gridline-color: #eef2f7; selection-background-color: #dbeafe; selection-color: #0f172a; }}
QHeaderView::section {{ background: #f8fafc; color: #475569; border: none;
    border-bottom: 1px solid #dbe3ec; padding: {_px(7, scale)}px; font-weight: 700; font-size: {tiny}px; }}
QTableWidget::item {{ padding: {_px(5, scale)}px; }}

/* ── Eingaben ────────────────────────────────────────────── */
QLineEdit, QSpinBox, QComboBox, QDateEdit, QTextEdit {{
    background: #ffffff; border: 1px solid #cbd5e1; border-radius: {radius}px;
    padding: {_px(5, scale)}px {_px(8, scale)}px; min-height: {_px(26, scale)}px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {{ border-color: #2563eb; }}
QPushButton {{ min-height: {_px(28, scale)}px; }}
QScrollArea {{ border: none; background: #f1f5f9; }}
QScrollArea > QWidget > QWidget {{ background: #f1f5f9; }}
"""


def install_emoji_fallback() -> None:
    """Sorgt dafuer, dass die Ampel- und Vorschlagssymbole wirklich erscheinen.

    Qt waehlt aus einer Stylesheet-Familienkette die erste vorhandene Schrift
    und faellt fuer Emoji nicht zuverlaessig weiter. Ohne diesen Eingriff
    bleiben die Symbole je nach System einfach leer.
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
    base = QFont().family()
    QFont.insertSubstitutions(base, [emoji])
    for name in ("Segoe UI", "Helvetica Neue", "Cantarell", "Arial"):
        if name in families:
            QFont.insertSubstitutions(name, [emoji])
