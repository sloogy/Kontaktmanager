#!/usr/bin/env python3
"""Haelt die Version an genau einer Stelle.

Quelle ist ``version.json``. Daraus werden ``app_info.APP_VERSION`` und
``module.json`` abgeleitet. ``--check`` schreibt nichts und faellt mit
Exitcode 1 aus, wenn etwas auseinanderlaeuft - so bricht die Pipeline ab,
bevor ein Paket mit falscher Version veroeffentlicht wird.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_version() -> str:
    data = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
    version = str(data.get("version", "")).strip()
    if not VERSION_RE.fullmatch(version):
        raise SystemExit(f"version.json enthaelt keine gueltige SemVer-Version: {version!r}")
    return version


def _app_info_version() -> str:
    text = (ROOT / "freizeitmanager" / "app_info.py").read_text(encoding="utf-8")
    match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        raise SystemExit("APP_VERSION nicht in app_info.py gefunden")
    return match.group(1)


def _write_app_info(version: str) -> bool:
    path = ROOT / "freizeitmanager" / "app_info.py"
    text = path.read_text(encoding="utf-8")
    new = re.sub(r'^APP_VERSION\s*=\s*"[^"]+"',
                 f'APP_VERSION = "{version}"', text, count=1, flags=re.MULTILINE)
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def _write_module_json(version: str) -> bool:
    path = ROOT / "module.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") == version:
        return False
    data["version"] = version
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="nur pruefen, nichts schreiben")
    parser.add_argument("--expect-tag", default="",
                        help="Git-Tag, der zur Version passen muss (z.B. v0.1.0)")
    args = parser.parse_args()

    version = read_version()
    module_version = json.loads((ROOT / "module.json").read_text(encoding="utf-8")).get("version")
    problems: list[str] = []

    if args.expect_tag:
        expected = args.expect_tag.lstrip("v")
        if expected != version:
            problems.append(f"Tag {args.expect_tag} passt nicht zu version.json {version}")

    if args.check:
        if _app_info_version() != version:
            problems.append(f"app_info.APP_VERSION {_app_info_version()} != {version}")
        if module_version != version:
            problems.append(f"module.json {module_version} != {version}")
        for problem in problems:
            print(f"FEHLER: {problem}", file=sys.stderr)
        if problems:
            print("Abhilfe: python3 tools/sync_version.py", file=sys.stderr)
            return 1
        print(f"Version einheitlich: {version}")
        return 0

    for problem in problems:
        print(f"FEHLER: {problem}", file=sys.stderr)
    if problems:
        return 1
    changed = [name for name, did in (("app_info.py", _write_app_info(version)),
                                      ("module.json", _write_module_json(version))) if did]
    print(f"Version {version}" + (f" -> {', '.join(changed)}" if changed else " (bereits einheitlich)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
