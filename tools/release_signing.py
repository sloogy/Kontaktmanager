"""Deterministischer Baum-Hash und optionale Ed25519-Signatur.

Der Hash ist bitgenau derselbe wie in ``lifeplanner_core/updater/io.py``.
Weicht er ab, lehnt der Host das Paket mit "payload_sha256 stimmt nicht"
ab - deshalb darf diese Funktion niemals "verbessert" werden.
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path


def tree_sha256(root: Path) -> str:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"Kein Verzeichnis: {root}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(rel).to_bytes(4, "big"))
        digest.update(rel)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _decode_key(value: str, *, label: str) -> bytes:
    try:
        raw = base64.b64decode(str(value).strip(), validate=True)
    except Exception as exc:
        raise ValueError(f"{label} ist kein gueltiges Base64") from exc
    if len(raw) != 32:
        raise ValueError(f"{label} muss genau 32 rohe Ed25519-Bytes enthalten")
    return raw


def private_key_from_b64(value: str):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.from_private_bytes(_decode_key(value, label="Privater Schluessel"))


def public_key_b64_from_private(value: str) -> str:
    from cryptography.hazmat.primitives import serialization
    public = private_key_from_b64(value).public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(public).decode("ascii")


def key_id(public_key_b64: str) -> str:
    raw = _decode_key(public_key_b64, label="Oeffentlicher Schluessel")
    return "ed25519:" + hashlib.sha256(raw).hexdigest()[:16]


def sign_b64(data: bytes, private_key_b64: str) -> bytes:
    return base64.b64encode(private_key_from_b64(private_key_b64).sign(data)) + b"\n"


def verify_b64(data: bytes, signature_b64: bytes | str, public_key_b64: str) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if isinstance(signature_b64, str):
        signature_b64 = signature_b64.encode("ascii")
    try:
        signature = base64.b64decode(signature_b64.strip(), validate=True)
    except Exception as exc:
        raise ValueError("Signatur ist kein gueltiges Base64") from exc
    if len(signature) != 64:
        raise ValueError("Ed25519-Signatur muss 64 Bytes lang sein")
    public = Ed25519PublicKey.from_public_bytes(_decode_key(public_key_b64, label="Oeffentlicher Schluessel"))
    public.verify(signature, data)   # wirft InvalidSignature
