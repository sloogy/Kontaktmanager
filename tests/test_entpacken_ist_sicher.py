"""Ein Modulpaket darf beim Entpacken nichts anrichten.

Geprueft wird hier ein Paket, das gerade erst hereingekommen ist und dessen
Signatur noch nicht kontrolliert wurde - genau der Moment, in dem ein
praeparierter Pfad Dateien ausserhalb des Zielordners ueberschreiben koennte.
Vorher stand an dieser Stelle ein blankes ``extractall``.

Alle vier Programme der Suite fuehren diesen Test unter demselben Namen.
"""

from __future__ import annotations

import zipfile

import pytest

from tools.verify_lpmodule import (
    MAX_COMPRESSION_RATIO,
    MAX_MEMBER_BYTES,
    MAX_ZIP_ENTRIES,
    sicher_entpacken,
)


def _entpacke(pfad, ziel):
    with zipfile.ZipFile(pfad, "r") as archiv:
        sicher_entpacken(archiv, ziel)


def _archiv(pfad, eintraege: dict[str, bytes]):
    with zipfile.ZipFile(pfad, "w", zipfile.ZIP_DEFLATED) as z:
        for name, inhalt in eintraege.items():
            z.writestr(name, inhalt)
    return pfad


def test_ein_harmloses_paket_wird_entpackt(tmp_path):
    quelle = _archiv(tmp_path / "gut.zip", {"a.txt": b"x", "payload/b.txt": b"y"})
    ziel = tmp_path / "ziel"
    ziel.mkdir()
    _entpacke(quelle, ziel)
    assert (ziel / "payload" / "b.txt").read_bytes() == b"y"


@pytest.mark.parametrize("name", ["../ausbruch.txt", "unter/../../ausbruch.txt", "/absolut.txt"])
def test_pfad_traversal_wird_abgewiesen(tmp_path, name):
    quelle = _archiv(tmp_path / "boese.zip", {name: b"x"})
    ziel = tmp_path / "ziel"
    ziel.mkdir()
    with pytest.raises(ValueError):
        _entpacke(quelle, ziel)
    assert not (tmp_path / "ausbruch.txt").exists()


def test_ein_symlink_wird_abgewiesen(tmp_path):
    quelle = tmp_path / "link.zip"
    with zipfile.ZipFile(quelle, "w") as z:
        eintrag = zipfile.ZipInfo("link")
        eintrag.external_attr = (0o120777 << 16)
        z.writestr(eintrag, "/etc/passwd")
    ziel = tmp_path / "ziel"
    ziel.mkdir()
    with pytest.raises(ValueError, match="Symlink"):
        _entpacke(quelle, ziel)


def test_eine_zip_bombe_wird_abgewiesen(tmp_path):
    quelle = tmp_path / "bombe.zip"
    with zipfile.ZipFile(quelle, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("gross.bin", b"\0" * (MAX_COMPRESSION_RATIO * 4096))
    ziel = tmp_path / "ziel"
    ziel.mkdir()
    with pytest.raises(ValueError, match="Kompressionsrate"):
        _entpacke(quelle, ziel)


def test_die_grenzen_sind_gesetzt():
    assert MAX_ZIP_ENTRIES > 0
    assert MAX_MEMBER_BYTES > 0
    assert MAX_COMPRESSION_RATIO > 1
