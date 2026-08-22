#!/usr/bin/env python3
"""Prueft ein fertiges .lpmodule so, wie der LifePlanner es pruefen wuerde.

Das ist das letzte Tor vor der Veroeffentlichung: Es wird das tatsaechlich
hochzuladende Archiv geprueft, nicht ein Zwischenstand. Faellt die Pruefung
durch, darf kein Release entstehen.
"""
from __future__ import annotations

import argparse
import json
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.release_signing import tree_sha256, verify_b64

# Grenzen fuers Entpacken, gleich wie in den anderen Programmen der Suite.
MAX_ZIP_ENTRIES = 100_000
MAX_MEMBER_BYTES = 512 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 250


def sicher_entpacken(archive: zipfile.ZipFile, ziel: Path) -> None:
    """Entpackt ohne Pfad-Traversal, Symlinks und Zip-Bomben.

    Vorher stand hier ein blankes ``extractall``. Geprueft wird hier ein Paket,
    das gerade erst hereingekommen ist und dessen Signatur noch gar nicht
    kontrolliert wurde - genau der Moment, in dem ein praeparierter Pfad
    Dateien ausserhalb des temporaeren Ordners ueberschreiben koennte.
    """
    wurzel = ziel.resolve()
    eintraege = archive.infolist()
    if len(eintraege) > MAX_ZIP_ENTRIES:
        raise ValueError("Modulpaket enthaelt zu viele Eintraege")
    gesamt = 0
    for eintrag in eintraege:
        roh = eintrag.filename.replace("\\", "/")
        if not roh:
            continue
        teile = Path(roh).parts
        if roh.startswith("/") or ".." in teile or ":" in teile[0]:
            raise ValueError(f"Unsicherer Pfad im Modulpaket: {eintrag.filename}")
        if stat.S_ISLNK(eintrag.external_attr >> 16):
            raise ValueError(f"Symlink im Modulpaket nicht erlaubt: {eintrag.filename}")
        pfad = (ziel / Path(*teile)).resolve()
        if pfad != wurzel and wurzel not in pfad.parents:
            raise ValueError(f"Pfad verlaesst das Zielverzeichnis: {eintrag.filename}")
        if eintrag.file_size > MAX_MEMBER_BYTES:
            raise ValueError(f"Datei im Modulpaket zu gross: {eintrag.filename}")
        gesamt += eintrag.file_size
        if gesamt > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Modulpaket ist entpackt unplausibel gross")
        if (eintrag.compress_size > 0
                and eintrag.file_size / eintrag.compress_size > MAX_COMPRESSION_RATIO):
            raise ValueError(
                f"Auffaellige Kompressionsrate im Modulpaket: {eintrag.filename}")
    archive.extractall(ziel)

COMPONENT_SCHEMA = "lifeplanner.component.v1"
# Beide Modulschemata sind gueltig - wie im Paketbauer und in FPMs
# Referenz-Verifizierer. v2 ist v1 plus requires_host: der Host prueft damit
# vor dem Start, ob er das Modul ueberhaupt bedienen kann.
MODULE_SCHEMAS = ("lifeplanner.module.v1", "lifeplanner.module.v2")


def verify(package: Path, *, expect_version: str = "", expect_platform: str = "",
           public_key_b64: str = "") -> list[str]:
    problems: list[str] = []
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        if "component.json" not in names:
            return ["component.json fehlt"]
        metadata_bytes = archive.read("component.json")
        metadata = json.loads(metadata_bytes)
        signature = archive.read("component.json.sig") if "component.json.sig" in names else None

        if metadata.get("schema") != COMPONENT_SCHEMA:
            problems.append(f"Schema {metadata.get('schema')!r} statt {COMPONENT_SCHEMA}")
        if metadata.get("kind") != "module":
            problems.append(f"kind {metadata.get('kind')!r} statt 'module'")
        if expect_version and metadata.get("version") != expect_version:
            problems.append(f"Version {metadata.get('version')} != {expect_version}")
        if expect_platform and metadata.get("platforms") != [expect_platform]:
            problems.append(f"Plattform {metadata.get('platforms')} != ['{expect_platform}']")
        if not str(metadata.get("requires_host", "")).strip():
            problems.append("requires_host fehlt")

        if "payload/module.json" not in names:
            problems.append("payload/module.json fehlt")
            return problems
        manifest = json.loads(archive.read("payload/module.json"))
        module_schema = manifest.get("schema")
        if module_schema not in MODULE_SCHEMAS:
            problems.append(
                f"Modulschema {module_schema!r} statt {' oder '.join(MODULE_SCHEMAS)}")
        elif module_schema == "lifeplanner.module.v2":
            # Die Hostanforderung darf nicht nur aussen am Paket stehen: der
            # Host liest sie aus dem Manifest, der Installer aus component.json.
            # Weichen sie ab, prueft jeder etwas anderes.
            verlangt = str(manifest.get("requires_host", "")).strip()
            if not verlangt:
                problems.append("module.v2 ohne requires_host")
            elif verlangt != str(metadata.get("requires_host", "")).strip():
                problems.append("requires_host in module.json weicht von component.json ab")
        if manifest.get("version") != metadata.get("version"):
            problems.append("Version in module.json weicht von component.json ab")

        platform = (metadata.get("platforms") or [""])[0]
        key = "windows_executable" if str(platform).startswith("windows") else "linux_executable"
        executable = str(manifest.get(key, "")).strip()
        if not executable:
            problems.append(f"module.json deklariert kein Programm fuer {platform}")
        else:
            arcname = f"payload/{Path(executable).as_posix()}"
            if arcname not in names:
                problems.append(f"Deklariertes Programm fehlt im Paket: {arcname}")
            elif not str(platform).startswith("windows"):
                mode = stat.S_IMODE(archive.getinfo(arcname).external_attr >> 16)
                if not mode & stat.S_IXUSR:
                    problems.append(f"{arcname} ist nicht ausfuehrbar (Modus {mode:o}) - "
                                    "das installierte Modul wuerde mit Errno 13 scheitern")
                if mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
                    problems.append(f"{arcname} traegt setuid/setgid/sticky")

        declared = str(metadata.get("payload_sha256", "")).strip().lower()
        if not declared:
            problems.append("payload_sha256 fehlt - die Signatur wuerde den Inhalt nicht binden")
        else:
            with tempfile.TemporaryDirectory(prefix="verify-lpmodule-") as temp:
                target = Path(temp)
                sicher_entpacken(archive, target)
                actual = tree_sha256(target / "payload")
            if actual != declared:
                problems.append(f"payload_sha256 stimmt nicht: {declared} != {actual}")

    if public_key_b64:
        if signature is None:
            problems.append("Signatur erwartet, aber component.json.sig fehlt")
        else:
            try:
                verify_b64(metadata_bytes, signature, public_key_b64)
            except Exception as exc:
                problems.append(f"Signatur ungueltig: {exc}")
    elif signature is not None:
        problems.append("Paket ist signiert, aber es wurde kein Schluessel zum Pruefen uebergeben")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--expect-version", default="")
    parser.add_argument("--expect-platform", default="")
    parser.add_argument("--public-key-env", default="")
    args = parser.parse_args()

    import os
    public_key = os.environ.get(args.public_key_env, "").strip() if args.public_key_env else ""
    problems = verify(args.package, expect_version=args.expect_version,
                      expect_platform=args.expect_platform, public_key_b64=public_key)
    for problem in problems:
        print(f"FEHLER: {problem}", file=sys.stderr)
    if problems:
        return 1
    size = args.package.stat().st_size / (1024 * 1024)
    print(f"OK: {args.package.name} ({size:.1f} MB) erfuellt den Host-Vertrag.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
