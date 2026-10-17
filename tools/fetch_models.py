"""Fetch pinned Hugging Face model files with hash verification.

Gated models require an accepted licence and an operator-provided ``HF_TOKEN``.
The token is read from the environment only, never logged and never written to
disk. Files are placed under ``vendor/models/<name>/`` (git-ignored) and
verified against pinned SHA-256 values; the immutable revision commit is the
primary anchor.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import argparse
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
        "requires_token": True,
        "files": {
            "config.json": "1dc4742d04507072cafffb7235dc5dba5af9ba126f7a9830b95ed7ec00fd9104",
            "model.safetensors": "5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1",
            "special_tokens_map.json": "9463f61e1b109a8eb4688b829260d7c6b1e6dff04c98ff7269bb89e2b92369b9",
            "tokenizer.json": "6eb983352e73f1697b883a8c3f6b66bdfa336ab3d29dd3687f8316d0ff2789c1",
            "tokenizer_config.json": "557b3d33d3f41b81ad769244e506549e98a1857d41dd58160aacd4d98d710b5a",
        },
    },
    "flan-t5-small": {
        "repo": "google/flan-t5-small",
        "revision": "0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab",
        "requires_token": False,
        "files": {
            "config.json": "439aa0fecf5a5546a1def68b1fc45e538e2c94528ce805378daf091e2bf6e4de",
            "generation_config.json": "f5a1c7e2be8092018d8835128987edf0111637dd98e90599cc80310fef75d95a",
            "model.safetensors": "495fa51e204676f1a857a9fc13c4c89f3f5ba9f480b898cebca02add25e6d749",
            "special_tokens_map.json": "5c87151ef0f72a99d1f766a4c418bd2a1f90aaa30a8e22fe5eca9641daebb64f",
            "spiece.model": "d60acb128cf7b7f2536e8f38a5b18a05535c9e14c7a355904270e15b0945ea86",
            "tokenizer.json": "fe2ebbbbde2985be723e0ce18217853e4020c5e9d35bd07be2c27ab9d3ead57a",
            "tokenizer_config.json": "fcde0f79bffda3688119c94330866a8fbf8de20ae65a8c492c9bd47c704655a0",
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
    headers = {"User-Agent": "prov"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
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
    parser = argparse.ArgumentParser()
    parser.add_argument("models", nargs="*", choices=sorted(MODELS))
    selected = parser.parse_args().models or sorted(MODELS)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    report: dict[str, dict[str, str]] = {}
    for name in selected:
        spec = MODELS[name]
        directory = VENDOR / name
        directory.mkdir(parents=True, exist_ok=True)
        checks: dict[str, str] = {}
        missing_gated_file = spec["requires_token"] and not token and any(
            not (directory / filename).is_file() or (expected is not None and _sha256(directory / filename) != expected)
            for filename, expected in spec["files"].items()
        )
        if missing_gated_file:
            print(f"Set HF_TOKEN to download gated model {name} after accepting its licence.", file=sys.stderr)
            return 2
        for filename, expected in spec["files"].items():
            dest = directory / filename
            if dest.is_file() and (expected is None or _sha256(dest) == expected):
                checks[filename] = _sha256(dest)
                continue
            try:
                checks[filename] = fetch_file(spec["repo"], spec["revision"], filename, dest, expected, token or "")
            except urllib.error.HTTPError as error:
                print(f"{name}/{filename}: HTTP {error.code} (licence accepted and token valid?)", file=sys.stderr)
                return 1
            print(f"{name}/{filename}: {checks[filename]}")
        report[name] = checks
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
