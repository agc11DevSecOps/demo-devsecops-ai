"""Fetch the isolated Inspect AI wheel set with pinned SHA-256 checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCK = ROOT / "evals" / "wheels.lock.json"
DEFAULT_DEST = ROOT / "vendor" / "inspect"
ALLOWED_HOSTS = frozenset({"files.pythonhosted.org"})
MAX_WHEEL = 128 * 1024 * 1024


class FetchError(RuntimeError):
    """A bounded fetch failure with no sensitive detail."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_lock(path: Path) -> list[dict[str, str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FetchError("invalid_inspect_lock") from error
    if type(payload) is not dict or payload.get("format_version") != 1 or payload.get("python") != "3.12" or type(payload.get("wheels")) is not list:
        raise FetchError("invalid_inspect_lock")
    wheels: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in payload["wheels"]:
        if type(item) is not dict or set(item) != {"name", "version", "filename", "url", "sha256"}:
            raise FetchError("invalid_inspect_lock")
        filename = item["filename"]
        url = item["url"]
        digest = item["sha256"]
        if not isinstance(filename, str) or "/" in filename or "\\" in filename or not filename.endswith(".whl"):
            raise FetchError("invalid_inspect_lock")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise FetchError("invalid_inspect_lock")
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise FetchError("invalid_inspect_lock")
        if filename in seen:
            raise FetchError("invalid_inspect_lock")
        seen.add(filename)
        wheels.append({"filename": filename, "url": url, "sha256": digest})
    if not wheels:
        raise FetchError("invalid_inspect_lock")
    return wheels


def fetch(lock: Path, dest: Path, *, verify_only: bool = False) -> tuple[int, int]:
    wheels = load_lock(lock)
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    fetched = 0
    verified = 0
    for item in wheels:
        target = dest / item["filename"]
        if target.is_file():
            if _sha256(target) != item["sha256"]:
                raise FetchError(f"hash mismatch: {item['filename']}")
            verified += 1
            continue
        if verify_only:
            raise FetchError(f"missing wheel: {item['filename']}")
        request = urllib.request.Request(item["url"], headers={"User-Agent": "demo-devsecops-ai-inspect-fetch/1"})
        descriptor, temporary = tempfile.mkstemp(prefix=".fetch-", suffix=".part", dir=dest)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if urlparse(response.geturl()).hostname not in ALLOWED_HOSTS:
                    raise FetchError("unexpected_download_host")
                with os.fdopen(descriptor, "wb") as handle:
                    total = 0
                    for block in iter(lambda: response.read(1 << 20), b""):
                        total += len(block)
                        if total > MAX_WHEEL:
                            raise FetchError(f"oversized wheel: {item['filename']}")
                        handle.write(block)
            if _sha256(Path(temporary)) != item["sha256"]:
                raise FetchError(f"hash mismatch: {item['filename']}")
            os.replace(temporary, target)
            fetched += 1
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return fetched, verified


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        fetched, verified = fetch(args.lock, args.dest, verify_only=args.verify_only)
    except FetchError as error:
        print(f"inspect fetch failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(f"inspect wheels: fetched={fetched} verified={verified} dest={args.dest}")


if __name__ == "__main__":
    main()
