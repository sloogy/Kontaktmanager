"""Werkzeuge, die ueber Gates entscheiden, muessen exakt gepinnt sein.

Warum das ein eigener Test ist: Am 22. August 2026 war jeder CI-Lauf dieses
Projekts rot, ohne dass jemand eine Zeile Code geaendert hatte. ``ruff`` stand
als Bereich in den Abhaengigkeiten, eine neue Nebenversion brachte neue Regeln
mit, und weil der Lint-Lauf ueber das Release entscheidet, fiel mit dem Gate
auch die Veroeffentlichung aus.

Ein Gate, das sich ohne Codeaenderung selbst rot machen kann, ist kein Gate.
Ein Versionssprung soll ein Commit sein, den jemand bewusst macht - und der
lokal reproduzierbar ist, weil dieselbe Version auch hier laeuft.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Werkzeuge, deren Urteil einen Lauf rot macht. Laufzeit-Abhaengigkeiten stehen
# bewusst nicht hier: dort ist ein Bereich richtig.
GEPINNTE_WERKZEUGE = ("ruff",)

_ZEILE = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)\s*(?P<rest>.*)$")


def _anforderungen(datei: Path) -> dict[str, str]:
    gefunden: dict[str, str] = {}
    for rohzeile in datei.read_text(encoding="utf-8").splitlines():
        zeile = rohzeile.split("#", 1)[0].strip()
        if not zeile or zeile.startswith("-"):
            continue
        treffer = _ZEILE.match(zeile)
        if treffer:
            gefunden[treffer.group("name").lower()] = treffer.group("rest").strip()
    return gefunden


@pytest.mark.parametrize("werkzeug", GEPINNTE_WERKZEUGE)
def test_gate_werkzeuge_sind_exakt_gepinnt(werkzeug: str) -> None:
    gesehen = False
    for datei in sorted(ROOT.glob("requirements*.txt")):
        rest = _anforderungen(datei).get(werkzeug)
        if rest is None:
            continue
        gesehen = True
        assert rest.startswith("=="), (
            f"{datei.name}: {werkzeug}{rest} ist ein Bereich. "
            "Ein Gate-Werkzeug ohne feste Version macht Laeufe ohne "
            "Codeaenderung rot - bitte exakt pinnen."
        )
        assert "," not in rest, f"{datei.name}: {werkzeug}{rest} ist nicht eindeutig"
    assert gesehen, f"{werkzeug} steht in keiner requirements-Datei"


def test_installierte_version_passt_zur_pinnung() -> None:
    """Sonst prueft die CI etwas anderes als der Entwickler vor dem Push."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        installiert = version("ruff")
    except PackageNotFoundError:  # ruff ist optional fuer den reinen Betrieb
        pytest.skip("ruff ist hier nicht installiert")

    erwartet = ""
    for datei in sorted(ROOT.glob("requirements*.txt")):
        rest = _anforderungen(datei).get("ruff", "")
        if rest.startswith("=="):
            erwartet = rest[2:].strip()
            break
    assert erwartet, "keine ruff-Pinnung gefunden"
    assert installiert == erwartet, (
        f"lokal laeuft ruff {installiert}, die CI nimmt {erwartet} - "
        "die Gates urteilen dann verschieden"
    )
