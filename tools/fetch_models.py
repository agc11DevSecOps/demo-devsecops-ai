"""Fetch pinned, gated Hugging Face model files with hash verification.

Prompt Guard 2 is a gated model: the download requires an accepted licence and
an operator-provided ``HF_TOKEN`` in the environment. The token is read from the
environment only, never logged and never written to disk. Files are placed under
``vendor/models/<name>/`` (git-ignored) and verified against a pinned SHA-256
once recorded; the immutable revision commit is the primary anchor.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / "vendor" / "models"
HOST = "huggingface.co"
CHUNK = 1 << 20

MODELS = {
    "prompt-guard-2-22m": {
        "repo": "meta-llama/Llama-Prompt-Guard-2-22M",
        "revision": "11614a155199674a0a95e6602d6ab0417b790ed0",
        "files": {
            "config.json": "1dc4742d04507072cafffb7235dc5dba5af9ba126f7a9830b95ed7ec00fd9104",
            "model.safetensors": "5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1",
            "special_tokens_map.json": "9463f61e1b109a8eb4688b829260d7c6b1e6dff04c98ff7269bb89e2b92369b9",
            "tokenizer.json": "6eb983352e73f1697b883a8c3f6b66bdfa336ab3d29dd3687f8316d0ff2789c1",
            "tokenizer_config.json": "557b3d33d3f41b81ad769244e506549e98a1857d41dd58160aacd4d98d710b5a",
        },
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_url(repo: str, revision: str, name: str) -> str:
    url = f"https://{HOST}/{repo}/resolve/{revision}/{urllib.parse.quote(name)}"
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname != HOST:
        raise ValueError(f"refusing unexpected url: {url}")
    return url


def fetch_file(repo: str, revision: str, name: str, dest: Path, expected: str | None, token: str) -> str:
    url = _resolve_url(repo, revision, name)
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": "prov"})
    digest = hashlib.sha256()
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f".{name}.", suffix=".part")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(request, timeout=600) as response:
            while True:
                block = response.read(CHUNK)
                if not block:
                    break
                digest.update(block)
                out.write(block)
            out.flush()
            os.fsync(out.fileno())
        actual = digest.hexdigest()
        if expected is not None and actual != expected:
            raise ValueError(f"{name}: sha256 mismatch expected {expected} got {actual}")
        os.replace(tmp_path, dest)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return actual


def main() -> int:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("Set HF_TOKEN to download the gated model after accepting its licence.", file=sys.stderr)
        return 2
    report: dict[str, dict[str, str]] = {}
    for name, spec in MODELS.items():
        directory = VENDOR / name
        directory.mkdir(parents=True, exist_ok=True)
        checks: dict[str, str] = {}
        for filename, expected in spec["files"].items():
            dest = directory / filename
            if dest.is_file() and (expected is None or _sha256(dest) == expected):
                checks[filename] = _sha256(dest)
                continue
            try:
                checks[filename] = fetch_file(spec["repo"], spec["revision"], filename, dest, expected, token)
            except urllib.error.HTTPError as error:
                print(f"{name}/{filename}: HTTP {error.code} (licence accepted and token valid?)", file=sys.stderr)
                return 1
            print(f"{name}/{filename}: {checks[filename]}")
        report[name] = checks
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
