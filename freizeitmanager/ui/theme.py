"""Zentrale Stilkonstanten. Einzige Quelle fuer spaetere Theme-Anpassungen."""
from __future__ import annotations

# Ampelfarben der Dringlichkeit - bewusst freundlich, kein Alarmrot.
ACCENT_FRESH = "#16a34a"
ACCENT_SOON = "#ca8a04"
ACCENT_DUE = "#ea580c"
ACCENT_LONG = "#2563eb"
ACCENT_PLANNED = "#0891b2"
ACCENT_NEUTRAL = "#64748b"

URGENCY_ACCENTS = {
    "fresh": ACCENT_FRESH,
    "soon": ACCENT_SOON,
    "due": ACCENT_DUE,
    "long": ACCENT_LONG,
}

BTN_PRIMARY = ("background:#2563eb;color:white;border:none;padding:8px 18px;"
               "border-radius:6px;font-weight:700;")
BTN_SUCCESS = ("background:#16a34a;color:white;border:none;padding:8px 18px;"
               "border-radius:6px;font-weight:700;")
BTN_SECONDARY = ("background:#e2e8f0;color:#1e293b;border:1px solid #cbd5e1;"
                 "padding:8px 16px;border-radius:6px;font-weight:600;")
BTN_QUIET = ("background:transparent;color:#64748b;border:1px solid #cbd5e1;"
             "padding:8px 14px;border-radius:6px;")
