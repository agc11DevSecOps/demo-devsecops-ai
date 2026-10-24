"""Extract sanitized inline SVG from Archify-delivered local HTML."""

from __future__ import annotations

import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "presentation" / "archify" / "out"
TARGET = ROOT / "showcase" / "diagrams"
NAMES = frozenset({
    "model-admission", "request-guardrails", "rag-provenance", "tool-boundary", "evidence-provenance",
    "model-admission-before", "ai-flow-unguarded", "ai-flow-guarded",
    "control-integration-map", "inspect-eval-topology",
})
FORBIDDEN = (
    r"<script\b",
    r"<foreignObject\b",
    r"<iframe\b",
    r"<object\b",
    r"<embed\b",
    r"\son[a-z]+\s*=",
    r"javascript\s*:",
    r"data\s*:\s*text/html",
    r"href\s*=\s*[\"']https?:",
    r"src\s*=\s*[\"']https?:",
    r"url\(\s*[\"']?https?:",
)
SVG = re.compile(r"<svg\b.*?</svg>", re.DOTALL)
VIEWBOX = re.compile(r'viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"')


def extract(name: str) -> tuple[Path, str]:
    source = SOURCE / f"{name}.html"
    if not source.is_file():
        raise SystemExit(f"missing delivered HTML: {source}")
    text = source.read_text(encoding="utf-8")
    match = SVG.search(text)
    if match is None:
        raise SystemExit(f"no inline SVG in {source}")
    svg = match.group(0)
    for pattern in FORBIDDEN:
        if re.search(pattern, svg, re.IGNORECASE):
            raise SystemExit(f"forbidden pattern {pattern!r} in {source}")
    viewbox = VIEWBOX.search(svg)
    if viewbox is None:
        raise SystemExit(f"missing viewBox in {source}")
    width, height = viewbox.group(3), viewbox.group(4)
    svg = svg.replace("<svg ", f'<svg width="{width}" height="{height}" preserveAspectRatio="xMidYMid meet" ', 1)
    try:
        ET.fromstring(svg)
    except ET.ParseError as error:
        raise SystemExit(f"invalid SVG in {source}: {error}") from error
    target = TARGET / f"{name}.svg"
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    target.write_text(svg + "\n", encoding="utf-8")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return target, digest


def main() -> None:
    names = sorted(NAMES)
    if len(sys.argv) > 1:
        names = sys.argv[1:]
        unknown = set(names) - NAMES
        if unknown:
            raise SystemExit(f"unknown diagram(s): {', '.join(sorted(unknown))}")
    for name in names:
        target, digest = extract(name)
        print(f"{target.relative_to(ROOT)} {digest}")


if __name__ == "__main__":
    main()
