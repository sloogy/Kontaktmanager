"""Die Oberflaeche waechst mit der eingestellten Schriftgroesse.

Alle vier Programme der Suite fuehren diesen Test unter demselben Namen. Feste
Pixelwerte im Stylesheet setzen sich sonst ueber die Profilschrift hinweg: Wer
die Schrift zur besseren Lesbarkeit hochstellt, bekaeme groesseren Text in
unveraendert engen Feldern.
"""

from __future__ import annotations

import re

import pytest

from freizeitmanager.ui.styles import get_stylesheet
from freizeitmanager.ui.theme_manager import BUILTIN_PROFILES, ThemeProfile


def _stylesheet(schriftgroesse: int) -> str:
    """Das Stylesheet zu einer Schriftgroesse.

    Das Profil wird hier von Hand gebaut statt ueber den ThemeManager geholt:
    der braucht eine offene Datenbank, und um die Groessenrechnung zu pruefen
    ist keine noetig.
    """
    daten = dict(BUILTIN_PROFILES["Standard - Hell"])
    daten["schriftgroesse"] = schriftgroesse
    return get_stylesheet(profile=ThemeProfile("Standard - Hell", daten))


def _groessen(css: str, eigenschaft: str) -> list[int]:
    return [int(x) for x in re.findall(rf"{eigenschaft}:\s*(\d+)px", css)]


@pytest.mark.parametrize("eigenschaft", ["font-size", "border-radius"])
def test_die_masse_wachsen_mit_der_schrift(eigenschaft):
    klein = _groessen(_stylesheet(8), eigenschaft)
    gross = _groessen(_stylesheet(16), eigenschaft)
    assert klein and len(klein) == len(gross), f"{eigenschaft} nicht vergleichbar"
    assert sum(gross) > sum(klein) * 1.3, (
        f"{eigenschaft} waechst kaum mit: {sum(klein)} -> {sum(gross)}"
    )


def test_die_radien_folgen_der_vorlage():
    """Abgestuft wie im BudgetManager, der Design-Vorlage der Suite: je
    groesser die Flaeche, desto runder die Ecke."""
    radien = set(_groessen(_stylesheet(10), "border-radius"))
    assert {4, 6, 8}.issubset(radien), sorted(radien)
