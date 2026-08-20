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

COMPONENT_SCHEMA = "lifeplanner.component.v1"
MODULE_SCHEMA = "lifeplanner.module.v1"


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
        if manifest.get("schema") != MODULE_SCHEMA:
            problems.append(f"Modulschema {manifest.get('schema')!r} statt {MODULE_SCHEMA}")
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
                archive.extractall(target)
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
