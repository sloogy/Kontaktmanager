#!/usr/bin/env python3
"""Packt eine gebaute Runtime als LifePlanner-``.lpmodule``.

Das Paketformat ist durch ``lifeplanner_core/module_installer.py`` vorgegeben:

    component.json          Schema lifeplanner.component.v1
    component.json.sig      optional, Ed25519 ueber component.json
    payload/module.json
    payload/<Runtime>/...

Das Werkzeug baut die Anwendung bewusst NICHT selbst. Es verpackt nur eine
bereits erzeugte und geprueft Runtime - so kann die Pipeline zwischen Bauen,
Pruefen und Veroeffentlichen sauber trennen.
"""
from __future__ import annotations

import argparse
import json
import shutil
import stat
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.release_signing import key_id, public_key_b64_from_private, sign_b64, tree_sha256

PLATFORM_SUFFIX = {
    "linux-x86_64": "Linux_x86_64",
    "windows-x86_64": "Windows_x86_64",
}

COMPONENT_SCHEMA = "lifeplanner.component.v1"
DEFAULT_REQUIRES_HOST = ">=0.5.0"


def canonical_json(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def module_asset_name(module_id: str, version: str, platform: str) -> str:
    return f"{module_id}_{version}_{PLATFORM_SUFFIX[platform]}.lpmodule"


def load_manifest() -> dict:
    manifest = json.loads((ROOT / "module.json").read_text(encoding="utf-8"))
    from freizeitmanager.app_info import APP_VERSION
    if manifest.get("version") != APP_VERSION:
        raise ValueError(f"module.json {manifest.get('version')} != app_info {APP_VERSION}; "
                         "python3 tools/sync_version.py ausfuehren")
    if manifest.get("schema") != "lifeplanner.module.v1":
        raise ValueError(f"Unerwartetes Modulschema: {manifest.get('schema')!r}")
    return manifest


def _declared_executable(manifest: dict, platform: str) -> str:
    key = "windows_executable" if platform.startswith("windows") else "linux_executable"
    return str(manifest.get(key, "")).strip()


def _validate_runtime(runtime_dir: Path, runtime_name: str) -> Path:
    if not runtime_name or Path(runtime_name).name != runtime_name or {"\\", ":"} & set(runtime_name):
        raise ValueError("Runtime-Name muss ein einfacher Verzeichnisname sein")
    runtime = Path(runtime_dir).resolve()
    if not runtime.is_dir():
        raise ValueError(f"Runtime-Verzeichnis fehlt: {runtime}")

    # PyInstaller legt fuer verschobene Bibliotheken Symlinks an. Zeigt einer
    # ins Leere, ist die Runtime defekt - und zwar oft, ohne dass die
    # Anwendung es beim Start merkt. Lieber hier abbrechen als ein Paket
    # ausliefern, das erst bei einer selten genutzten Funktion zerbricht.
    dangling = sorted(str(path.relative_to(runtime))
                      for path in runtime.rglob("*")
                      if path.is_symlink() and not path.exists())
    if dangling:
        raise ValueError("Runtime enthaelt Symlinks ins Leere: "
                         + ", ".join(dangling[:5])
                         + (f" (und {len(dangling) - 5} weitere)" if len(dangling) > 5 else ""))
    return runtime


def build_module(*, runtime_dir: Path, runtime_name: str, platform: str,
                 output: Path, requires_host: str = DEFAULT_REQUIRES_HOST,
                 private_key_b64: str | None = None,
                 release_tag: str | None = None) -> Path:
    if platform not in PLATFORM_SUFFIX:
        raise ValueError(f"Nicht unterstuetzte Plattform: {platform}")
    runtime = _validate_runtime(runtime_dir, runtime_name)
    manifest = load_manifest()

    executable = _declared_executable(manifest, platform)
    if not executable:
        raise ValueError(f"module.json deklariert kein Programm fuer {platform}")
    exe_arcname = (Path("payload") / Path(executable)).as_posix()

    with tempfile.TemporaryDirectory(prefix="lpmodule-") as temp_name:
        payload = Path(temp_name) / "payload"
        payload.mkdir()
        shutil.copy2(ROOT / "module.json", payload / "module.json")
        shutil.copytree(runtime, payload / runtime_name)

        if not (payload.parent / exe_arcname).is_file():
            raise ValueError(f"Deklariertes Programm fehlt im Paket: {exe_arcname}. "
                             "Ein unstartbares Modul wird nicht veroeffentlicht.")

        metadata = {
            "schema": COMPONENT_SCHEMA,
            "id": manifest["id"],
            "name": manifest.get("name", manifest["id"]),
            "version": manifest["version"],
            "kind": "module",
            "requires_host": requires_host,
            "description": manifest.get("description", ""),
            "platforms": [platform],
            "payload_sha256": tree_sha256(payload),
            "created_at": datetime.now(UTC).isoformat(),
        }
        if private_key_b64:
            metadata["signing_key_id"] = key_id(public_key_b64_from_private(private_key_b64))
        if release_tag:
            metadata["release_tag"] = release_tag
        metadata_bytes = canonical_json(metadata)

        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.unlink(missing_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr("component.json", metadata_bytes)
            if private_key_b64:
                archive.writestr("component.json.sig", sign_b64(metadata_bytes, private_key_b64))
            for path in sorted(payload.rglob("*"), key=lambda p: p.relative_to(payload).as_posix()):
                if not path.is_file():
                    continue
                arcname = (Path("payload") / path.relative_to(payload)).as_posix()
                info = zipfile.ZipInfo.from_file(path, arcname)
                info.compress_type = zipfile.ZIP_DEFLATED
                mode = stat.S_IMODE(info.external_attr >> 16) or 0o644
                if arcname == exe_arcname:
                    # Das Ausfuehrbit wird direkt ins Archiv geschrieben, nicht
                    # vom Dateisystem uebernommen: CI-Artefakte verlieren Unix-
                    # Rechte, und ein Linux-Paket kann auf einem Windows-Runner
                    # entstehen. Ohne das startet das Modul mit "Errno 13".
                    # Leserechte werden gespiegelt; nie setuid/setgid/sticky.
                    mode |= (mode & 0o444) >> 2
                info.external_attr = (mode & 0o7777) << 16
                with path.open("rb") as source, archive.open(info, "w") as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", required=True, type=Path,
                        help="Verzeichnis der gebauten Runtime (dist/FreizeitManager)")
    parser.add_argument("--runtime-name", default="FreizeitManager",
                        help="Verzeichnisname im Paket, muss zu module.json passen")
    parser.add_argument("--platform", required=True, choices=sorted(PLATFORM_SUFFIX))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--requires-host", default=DEFAULT_REQUIRES_HOST)
    parser.add_argument("--release-tag", default="")
    parser.add_argument("--signing-key-env", default="",
                        help="Name der Umgebungsvariable mit dem privaten Ed25519-Schluessel")
    parser.add_argument("--allow-unsigned", action="store_true",
                        help="ohne Schluessel bauen; das Paket bleibt sichtbar unsigniert")
    args = parser.parse_args()

    import os
    private_key = os.environ.get(args.signing_key_env, "").strip() if args.signing_key_env else ""
    if not private_key and not args.allow_unsigned:
        print("FEHLER: kein Signaturschluessel. Entweder --signing-key-env setzen "
              "oder --allow-unsigned angeben.", file=sys.stderr)
        return 1

    manifest = load_manifest()
    output = args.output_dir / module_asset_name(manifest["id"], manifest["version"], args.platform)
    target = build_module(runtime_dir=args.runtime_dir, runtime_name=args.runtime_name,
                          platform=args.platform, output=output,
                          requires_host=args.requires_host,
                          private_key_b64=private_key or None,
                          release_tag=args.release_tag or None)
    size = target.stat().st_size / (1024 * 1024)
    print(f"{target.name}  ({size:.1f} MB, {'signiert' if private_key else 'unsigniert'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
