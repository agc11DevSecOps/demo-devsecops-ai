"""Build the AISVS v1.01 catalog from a reviewed local source snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


COMMIT = "55dc2203d861af14482b529c564f5b312134b165"
TREE = "9287f3198e1ee7832fc2490e0afbc7b114490e9a"
SOURCE_SHA256 = "c23aa4d6ac5313787ee82a31528df71b378521f6c59e61456d6d8f135ace74c5"
EXPECTED_REQUIREMENTS = 213
CHAPTER = re.compile(r"^# C([1-9]|1[0-2])\s+", re.MULTILINE)
ROW = re.compile(r"^\|\s*\*\*(\d+\.\d+\.\d+)\*\*\s*\|\s*(.*?)\s*\|\s*([123])\s*\|\s*$", re.MULTILINE)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_digest(paths: list[Path]) -> str:
    """Hash file names and content digests in stable source-file order."""
    records = []
    for path in paths:
        records.append(f"{_sha256(path.read_bytes())}  {path.name}\n".encode("ascii"))
    return _sha256(b"".join(records))


def build_catalog(source_dir: Path, *, expected_digest: str, expected_count: int) -> dict[str, Any]:
    source = source_dir.resolve()
    paths = sorted(source.glob("0x10-C*.md"))
    if len(paths) != 12 or any(not path.is_file() or path.is_symlink() for path in paths):
        raise ValueError("invalid_aisvs_source_layout")
    digest = source_digest(paths)
    if digest != expected_digest:
        raise ValueError("aisvs_source_digest_mismatch")

    requirements = []
    for path in paths:
        content = path.read_text(encoding="utf-8")
        chapter_match = CHAPTER.search(content)
        if chapter_match is None:
            raise ValueError(f"missing_chapter_header:{path.name}")
        chapter = chapter_match.group(1)
        for requirement, text, level in ROW.findall(content):
            if requirement.split(".", 1)[0] != chapter:
                raise ValueError(f"chapter_mismatch:{path.name}:{requirement}")
            requirements.append({
                "id": f"v1.01-C{requirement}",
                "chapter": f"C{chapter}",
                "level": int(level),
                # Preserve the source Markdown table cell verbatim, excluding padding.
                "text": text,
            })
    requirements.sort(key=lambda item: tuple(int(part) for part in item["id"].removeprefix("v1.01-C").split(".")))
    ids = [item["id"] for item in requirements]
    if len(requirements) != expected_count or len(set(ids)) != len(ids):
        raise ValueError("unexpected_aisvs_requirement_count")
    return {
        "format_version": 2,
        "source_status": "PINNED: OWASP AISVS v1.01 local snapshot verified",
        "source": {
            "publisher": "OWASP",
            "repository": "https://github.com/OWASP/AISVS",
            "version": "1.01",
            "commit": COMMIT,
            "tree": TREE,
            "source_sha256": digest,
            "license": "CC-BY-SA-4.0",
        },
        "requirements": requirements,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="reviewed 1.01/en snapshot directory")
    parser.add_argument("--output", type=Path, default=Path("scorecard/requirements_v1.01.json"))
    args = parser.parse_args()
    catalog = build_catalog(args.source_dir, expected_digest=SOURCE_SHA256, expected_count=EXPECTED_REQUIREMENTS)
    args.output.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({len(catalog['requirements'])} requirements)")


if __name__ == "__main__":
    main()
