"""Prueft das .lpmodule gegen den Host-Vertrag.

Die Erwartungen stammen aus ``lifeplanner_core/module_installer.py``:
component.json mit Schema lifeplanner.component.v1, ein payload/-Verzeichnis,
ein payload_sha256 ueber genau diesen Baum und ein ausfuehrbares Programm.
Faellt einer dieser Punkte weg, installiert der Host das Modul nicht oder
es startet mit "[Errno 13] Keine Berechtigung".
"""
from __future__ import annotations

import json
import stat
import zipfile
from pathlib import Path

import pytest

from tools.build_lifeplanner_module import COMPONENT_SCHEMA, build_module, load_manifest, module_asset_name
from tools.release_signing import tree_sha256


@pytest.fixture()
def runtime(tmp_path) -> Path:
    """Minimale Attrappe einer PyInstaller-Ausgabe."""
    root = tmp_path / "dist" / "FreizeitManager"
    (root / "_internal").mkdir(parents=True)
    (root / "FreizeitManager").write_bytes(b"#!/bin/sh\necho fake\n")
    (root / "FreizeitManager.exe").write_bytes(b"MZfake")
    (root / "_internal" / "libQt6Core.so.6").write_bytes(b"\0" * 2048)
    (root / "version.json").write_text('{"app": "FreizeitManager"}', encoding="utf-8")
    return root


def _pack(runtime: Path, tmp_path: Path, platform: str = "linux-x86_64", **kw) -> Path:
    manifest = load_manifest()
    output = tmp_path / module_asset_name(manifest["id"], manifest["version"], platform)
    return build_module(runtime_dir=runtime, runtime_name="FreizeitManager",
                        platform=platform, output=output, **kw)


def test_paket_hat_die_vom_host_erwartete_struktur(runtime, tmp_path):
    package = _pack(runtime, tmp_path)
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        metadata = json.loads(archive.read("component.json"))

    assert "component.json" in names
    assert "payload/module.json" in names
    assert "payload/FreizeitManager/FreizeitManager" in names
    assert metadata["schema"] == COMPONENT_SCHEMA
    assert metadata["kind"] == "module"
    assert metadata["id"] == "freizeitmanager"
    assert metadata["platforms"] == ["linux-x86_64"]
    assert metadata["requires_host"] == ">=0.5.15,<0.6"


def test_payload_hash_passt_zum_tatsaechlichen_inhalt(runtime, tmp_path):
    """Der Host rechnet den Hash selbst nach und lehnt bei Abweichung ab."""
    package = _pack(runtime, tmp_path)
    extracted = tmp_path / "auspacken"
    with zipfile.ZipFile(package) as archive:
        archive.extractall(extracted)
        declared = json.loads(archive.read("component.json"))["payload_sha256"]
    assert declared == tree_sha256(extracted / "payload")
    assert len(declared) == 64


def test_linux_programm_traegt_das_ausfuehrbit(runtime, tmp_path):
    """Ohne das startet das installierte Modul mit "Errno 13"."""
    package = _pack(runtime, tmp_path)
    with zipfile.ZipFile(package) as archive:
        info = archive.getinfo("payload/FreizeitManager/FreizeitManager")
        mode = stat.S_IMODE(info.external_attr >> 16)
        other = archive.getinfo("payload/FreizeitManager/_internal/libQt6Core.so.6")
        other_mode = stat.S_IMODE(other.external_attr >> 16)

    assert mode & stat.S_IXUSR, "Eigentuemer darf ausfuehren"
    assert not mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX), "nie setuid/setgid/sticky"
    assert not other_mode & stat.S_IXUSR, "nur das deklarierte Programm wird ausfuehrbar"


def test_windows_paket_nutzt_die_exe(runtime, tmp_path):
    package = _pack(runtime, tmp_path, platform="windows-x86_64")
    with zipfile.ZipFile(package) as archive:
        metadata = json.loads(archive.read("component.json"))
        assert "payload/FreizeitManager/FreizeitManager.exe" in archive.namelist()
    assert metadata["platforms"] == ["windows-x86_64"]
    assert package.name.endswith("_Windows_x86_64.lpmodule")


def test_fehlendes_programm_bricht_den_build_ab(tmp_path):
    """Lieber kein Release als ein unstartbares Paket."""
    leer = tmp_path / "dist" / "FreizeitManager"
    (leer / "_internal").mkdir(parents=True)
    (leer / "_internal" / "irgendwas.so").write_bytes(b"\0")
    with pytest.raises(ValueError, match="Deklariertes Programm fehlt"):
        _pack(leer, tmp_path)


def test_version_von_modul_und_anwendung_muss_uebereinstimmen(runtime, tmp_path, monkeypatch):
    import tools.build_lifeplanner_module as builder
    from freizeitmanager import app_info
    monkeypatch.setattr(app_info, "APP_VERSION", "9.9.9")
    with pytest.raises(ValueError, match="sync_version"):
        builder.load_manifest()


def test_unsigniertes_paket_traegt_keine_signaturspuren(runtime, tmp_path):
    package = _pack(runtime, tmp_path)
    with zipfile.ZipFile(package) as archive:
        assert "component.json.sig" not in archive.namelist()
        assert "signing_key_id" not in json.loads(archive.read("component.json"))


def test_signiertes_paket_ist_pruefbar(runtime, tmp_path):
    pytest.importorskip("cryptography")
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from tools.release_signing import public_key_b64_from_private, verify_b64

    private = Ed25519PrivateKey.generate()
    raw = private.private_bytes(encoding=serialization.Encoding.Raw,
                                format=serialization.PrivateFormat.Raw,
                                encryption_algorithm=serialization.NoEncryption())
    key_b64 = base64.b64encode(raw).decode("ascii")

    package = _pack(runtime, tmp_path, private_key_b64=key_b64, release_tag="v0.1.0")
    with zipfile.ZipFile(package) as archive:
        metadata_bytes = archive.read("component.json")
        signature = archive.read("component.json.sig")

    verify_b64(metadata_bytes, signature, public_key_b64_from_private(key_b64))
    metadata = json.loads(metadata_bytes)
    assert metadata["signing_key_id"].startswith("ed25519:")
    assert metadata["release_tag"] == "v0.1.0"


def test_app_info_kennt_dasselbe_modulschema_wie_das_manifest():
    """Die Version im Programm und die im Manifest muessen dieselbe sein.

    ``app_info.MODULE_SCHEMA`` stand auf v1, waehrend module.json laengst v2
    deklarierte - und weil die Konstante gerade niemand las, fiel es nicht auf.
    Wer sie das naechste Mal liest, bekaeme die falsche Antwort.
    """
    from freizeitmanager.app_info import APP_VERSION, MODULE_SCHEMA

    manifest = load_manifest()
    assert manifest["schema"] == MODULE_SCHEMA
    assert manifest["version"] == APP_VERSION


def test_verifizierer_akzeptiert_beide_modulschemata():
    """v1-Pakete bleiben installierbar; nur v2 verlangt zusaetzlich requires_host."""
    from tools.verify_lpmodule import MODULE_SCHEMAS

    assert set(MODULE_SCHEMAS) == {"lifeplanner.module.v1", "lifeplanner.module.v2"}


def test_verifizierer_erkennt_abweichende_hostanforderung(runtime, tmp_path):
    """requires_host steht in component.json und module.json - beide muessen gleich sein.

    Der Host liest die Anforderung aus dem Manifest, der Installer aus den
    Paketdaten. Weichen sie ab, prueft jeder etwas anderes, und ein Modul kann
    an der Installation vorbei in einen Host geraten, den es nicht bedient.
    """
    from tools.verify_lpmodule import verify

    package = _pack(runtime, tmp_path)
    manipuliert = tmp_path / "fremde_hostanforderung.lpmodule"
    with zipfile.ZipFile(package) as src, \
            zipfile.ZipFile(manipuliert, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "component.json":
                metadata = json.loads(data)
                metadata["requires_host"] = ">=99.0.0"
                data = json.dumps(metadata).encode("utf-8")
            dst.writestr(info, data)

    assert any("requires_host" in p for p in verify(manipuliert))


def test_modulmanifest_erfuellt_den_host_vertrag():
    manifest = load_manifest()
    assert manifest["schema"] == "lifeplanner.module.v2"
    assert manifest["requires_host"] == ">=0.5.15,<0.6"
    assert manifest["source_entry"] == "main.py"
    assert manifest["environment"]["LIFEPLANNER_MODULE_DATA_DIR"] == "{module_data_dir}"
    assert manifest["environment"]["FREIZEITMANAGER_DATA_DIR"] == "{module_data_dir}"
    assert manifest["environment"]["LIFEPLANNER_BRIDGE_DIR"] == "{bridge_dir}"
    assert manifest["bridge"]["publishes"][0]["file"] == "freizeitmanager_to_lifeplanner.jsonl"
    assert set(manifest["permissions"]) <= {"own_data_read", "own_data_write",
                                            "bridge_read", "bridge_write",
                                            "network_optional"}


# ── Verifizierer: das letzte Tor vor der Veroeffentlichung ───────────────────

def _repack(source: Path, target: Path, *, replace: bytes | None = None,
            mode: int | None = None) -> Path:
    """Baut das Archiv neu und veraendert dabei nur die Programmdatei."""
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.endswith("/FreizeitManager"):
                if replace is not None:
                    data = replace
                if mode is not None:
                    info.external_attr = mode << 16
            dst.writestr(info, data)
    return target


def test_verifizierer_akzeptiert_ein_sauberes_paket(runtime, tmp_path):
    from tools.verify_lpmodule import verify
    package = _pack(runtime, tmp_path)
    assert verify(package, expect_version=load_manifest()["version"],
                  expect_platform="linux-x86_64") == []


def test_verifizierer_erkennt_ausgetauschtes_programm(runtime, tmp_path):
    """component.json bleibt unveraendert, der Inhalt nicht - der Hash muss anschlagen."""
    from tools.verify_lpmodule import verify
    package = _pack(runtime, tmp_path)
    tampered = _repack(package, tmp_path / "manipuliert.lpmodule", replace=b"#!/bin/sh\nboese\n")
    problems = verify(tampered)
    assert any("payload_sha256 stimmt nicht" in p for p in problems)


def test_verifizierer_erkennt_fehlendes_ausfuehrbit(runtime, tmp_path):
    from tools.verify_lpmodule import verify
    package = _pack(runtime, tmp_path)
    broken = _repack(package, tmp_path / "ohne_exec.lpmodule", mode=0o644)
    problems = verify(broken)
    assert any("nicht ausfuehrbar" in p for p in problems)


def test_verifizierer_erkennt_falsche_version_und_plattform(runtime, tmp_path):
    from tools.verify_lpmodule import verify
    package = _pack(runtime, tmp_path)
    problems = verify(package, expect_version="9.9.9", expect_platform="windows-x86_64")
    assert len(problems) == 2


def test_verifizierer_verlangt_schluessel_fuer_signierte_pakete(runtime, tmp_path):
    """Ein signiertes Paket ungeprueft durchzuwinken waere schlimmer als keine Signatur."""
    pytest.importorskip("cryptography")
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from tools.verify_lpmodule import verify

    private = Ed25519PrivateKey.generate()
    key_b64 = base64.b64encode(private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption())).decode("ascii")

    package = _pack(runtime, tmp_path, private_key_b64=key_b64)
    problems = verify(package)
    assert any("kein Schluessel" in p for p in problems)


def test_baumelnder_symlink_bricht_den_build_ab(runtime, tmp_path):
    """Eine defekte Runtime darf nicht in ein Paket wandern.

    PyInstaller legt fuer verschobene Bibliotheken Symlinks an. Zeigt einer ins
    Leere, startet die Anwendung oft trotzdem - sie laedt die Bibliothek nur
    nie. Der Defekt faellt dann erst beim Benutzer auf.
    """
    (runtime / "_internal" / "libQt6Kaputt.so.6").symlink_to("gibtesnicht.so.6")
    with pytest.raises(ValueError, match="Symlinks ins Leere"):
        _pack(runtime, tmp_path)
