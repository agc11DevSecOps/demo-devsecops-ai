"""Fetch pinned external tool binaries and wheels with hash verification.

Provisioning is a recorded, explicitly approved egress step: this module
requests only the exact URLs pinned below (or in ``vendor/python.lock.json``)
over HTTPS from allowlisted hosts, verifies each download against its pinned
SHA-256 before it is written into ``vendor/`` and never executes anything it
downloads. Large artifacts are fetched rather than committed to git; the pinned
hash is the integrity anchor.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / "vendor"
WHEELS_DIR = VENDOR / "python"
WHEELS_MANIFEST = VENDOR / "python.lock.json"

ALLOWED_HOSTS = {
    "github.com": (
        "/open-policy-agent/opa/releases/download/",
        "/sigstore/cosign/releases/download/",
        "/explosion/spacy-models/releases/download/",
    ),
    "files.pythonhosted.org": ("/packages/",),
    "download.pytorch.org": ("/whl/cpu/",),
}
CHUNK = 1 << 20

TOOLS = {
    "opa": {
        "version": "1.21.2",
        "url": (
            "https://github.com/open-policy-agent/opa/releases/download/"
            "v1.21.2/opa_linux_amd64_static"
        ),
        "sha256": "830ab11f61ffec760b5e19db0d7ad02bf037e13f5ef4d665faeaf17632177527",
    },
    "cosign": {
        "version": "3.1.3",
        "url": (
            "https://github.com/sigstore/cosign/releases/download/"
            "v3.1.3/cosign-linux-amd64"
        ),
        "sha256": "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _check_url(url: str) -> None:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        raise ValueError(f"refusing non-https url: {url}")
    prefixes = ALLOWED_HOSTS.get(parts.hostname)
    if prefixes is None:
        raise ValueError(f"refusing host {parts.hostname!r} outside allowlist")
    if not any(parts.path.startswith(prefix) for prefix in prefixes):
        raise ValueError(f"refusing unexpected release path: {parts.path}")


def _download(url: str, dest: Path, sha256: str, label: str, mode: int) -> bool:
    _check_url(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and _sha256(dest) == sha256:
        print(f"{label}: up to date")
        return False

    digest = hashlib.sha256()
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "prov"}),
            timeout=600,
        ) as response:
            while True:
                block = response.read(CHUNK)
                if not block:
                    break
                digest.update(block)
                out.write(block)
        actual = digest.hexdigest()
        if actual != sha256:
            raise ValueError(f"{label}: sha256 mismatch expected {sha256} got {actual}")
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, dest)
        tmp_name = None
        print(f"{label}: fetched ({actual})")
        return True
    finally:
        if tmp_name is not None and os.path.exists(tmp_name):
            os.unlink(tmp_name)


def fetch_tools() -> None:
    for name, spec in TOOLS.items():
        _download(spec["url"], VENDOR / name, spec["sha256"], name, 0o755)


def fetch_wheels() -> None:
    manifest = json.loads(WHEELS_MANIFEST.read_text())
    for entry in manifest:
        _download(entry["url"], WHEELS_DIR / entry["file"], entry["sha256"], entry["file"], 0o644)


def main() -> int:
    fetch_tools()
    fetch_wheels()
    return 0


if __name__ == "__main__":
    sys.exit(main())
