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


def test_der_wrapper_gibt_es() -> None:
    """Die Pinnung allein reicht nicht - sie muss sich auch fahren lassen.

    Der Test oben verlangt, dass die *lokal installierte* Version zur Pinnung
    passt. Das ist eine Zusage an den Entwicklerrechner, keine Eigenschaft des
    Projekts: Wer eine andere Version hat, bekommt ein anderes Urteil als die
    CI - und sieht am eigenen gruenen Lauf nicht, was der CI-Lauf sehen wird.

    ``tools/gepinnte_werkzeuge.py`` faehrt die gepinnte Version in einer
    eigenen Umgebung. Die anderen drei Programme der Suite haben ihn seit
    Loop 37 beziehungsweise 57; hier fehlte er als einzigem.
    """
    from pathlib import Path

    wurzel = Path(__file__).resolve().parents[1]
    wrapper = wurzel / "tools" / "gepinnte_werkzeuge.py"
    assert wrapper.is_file(), "tools/gepinnte_werkzeuge.py fehlt"

    text = wrapper.read_text(encoding="utf-8")
    # Er muss die Version aus den requirements lesen, nicht selbst eine nennen.
    assert "requirements" in text
    assert "gepinnte_version" in text


def test_der_wrapper_nennt_keine_eigene_version() -> None:
    """Sonst gaebe es zwei Wahrheiten - die requirements und ihn."""
    import re
    from pathlib import Path

    wurzel = Path(__file__).resolve().parents[1]
    text = (wurzel / "tools" / "gepinnte_werkzeuge.py").read_text(encoding="utf-8")
    # Erlaubt ist die Musterzeile im Docstring; verboten eine echte Pinnung.
    treffer = re.findall(r"(?m)^\s*[A-Z_]+\s*=\s*[\"']\d+\.\d+\.\d+[\"']", text)
    assert not treffer, f"Der Wrapper nennt eigene Versionen: {treffer}"
