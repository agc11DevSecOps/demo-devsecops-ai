"""Extract sanitized, self-contained SVG from Archify-delivered local HTML.

Archify styles its inline SVG from a stylesheet in the surrounding HTML (theme
variables plus class rules). A standalone ``.svg`` loses that stylesheet and
renders black, so the extractor copies the stylesheet into the SVG and pins the
dark theme. The output is still checked for scripts, event handlers, foreign
content and external references, and must parse as namespaced SVG.
"""

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
STYLE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
OPEN_TAG = re.compile(r"<svg\b[^>]*>", re.DOTALL)
VIEWBOX = re.compile(r'viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"')


SVG_ELEMENTS = frozenset({"svg", "g", "path", "rect", "line", "polyline", "polygon", "circle", "ellipse", "text", "tspan", "marker", "pattern", "defs", "title", "desc", "use", "lineargradient", "radialgradient", "stop", "clippath", "mask", "symbol"})
CLASS_TOKEN = re.compile(r"\.([A-Za-z_][A-Za-z0-9_-]*)")
ELEMENT_TOKEN = re.compile(r"(?:^|[\s>+~,(])([a-zA-Z][a-zA-Z0-9-]*)")
LOCAL_URL = re.compile(r"url\(\s*['\"]?(?!#)", re.IGNORECASE)


def _blocks(css: str) -> list[tuple[str, str]]:
    """Split CSS into top-level (prelude, body) blocks with brace matching."""
    blocks: list[tuple[str, str]] = []
    position = 0
    while position < len(css):
        brace = css.find("{", position)
        if brace < 0:
            break
        prelude = css[position:brace].strip()
        depth = 1
        cursor = brace + 1
        while cursor < len(css) and depth:
            if css[cursor] == "{":
                depth += 1
            elif css[cursor] == "}":
                depth -= 1
            cursor += 1
        blocks.append((prelude.split(";")[-1].strip(), css[brace + 1:cursor - 1]))
        position = cursor
    return blocks


def _relevant(selector: str, classes: set[str]) -> bool:
    if ":root" in selector or "[data-theme" in selector or "[data-preset" in selector:
        return True
    if any(token in classes for token in CLASS_TOKEN.findall(selector)):
        return True
    without_classes = CLASS_TOKEN.sub(" ", selector)
    elements = {token.lower() for token in ELEMENT_TOKEN.findall(without_classes)}
    return bool(elements) and elements <= SVG_ELEMENTS


def _filter(css: str, classes: set[str]) -> str:
    """Keep only rules that can style this SVG and reference no external URL."""
    kept: list[str] = []
    for prelude, body in _blocks(css):
        lowered = prelude.lower()
        if lowered.startswith(("@media", "@supports", "@layer")):
            inner = _filter(body, classes)
            if inner:
                kept.append(f"{prelude} {{\n{inner}\n}}")
            continue
        if lowered.startswith("@keyframes") or lowered.startswith("@-webkit-keyframes"):
            if not LOCAL_URL.search(body):
                kept.append(f"{prelude} {{{body}}}")
            continue
        if lowered.startswith("@"):
            continue
        if LOCAL_URL.search(body):
            continue
        if _relevant(prelude, classes):
            kept.append(f"{prelude} {{{body}}}")
    # Blank lines in the delivered stylesheet can contain trailing whitespace.
    # Remove it so generated SVGs pass the repository whitespace check.
    return "\n".join(line.rstrip() for line in "\n".join(kept).splitlines())


def extract(name: str) -> tuple[Path, str]:
    source = SOURCE / f"{name}.html"
    if not source.is_file():
        raise SystemExit(f"missing delivered HTML: {source}")
    text = source.read_text(encoding="utf-8")
    match = SVG.search(text)
    if match is None:
        raise SystemExit(f"no inline SVG in {source}")
    svg = match.group(0)
    styles = [COMMENT.sub("", block).strip() for block in STYLE.findall(text[: match.start()])]
    classes = {token for value in re.findall(r'class="([^"]*)"', svg) for token in value.split()}
    stylesheet = _filter("\n".join(block for block in styles if block), classes)
    if not stylesheet:
        raise SystemExit(f"no stylesheet in {source}")
    if "]]>" in stylesheet or "</style" in stylesheet.lower():
        raise SystemExit(f"unsafe stylesheet in {source}")
    for pattern in FORBIDDEN:
        if re.search(pattern, svg, re.IGNORECASE) or re.search(pattern, stylesheet, re.IGNORECASE):
            raise SystemExit(f"forbidden pattern {pattern!r} in {source}")
    if re.search(r"@import|url\(\s*['\"]?(?!#)", stylesheet, re.IGNORECASE):
        raise SystemExit(f"external stylesheet reference in {source}")
    viewbox = VIEWBOX.search(svg)
    if viewbox is None:
        raise SystemExit(f"missing viewBox in {source}")
    width, height = viewbox.group(3), viewbox.group(4)
    attributes = [
        'xmlns="http://www.w3.org/2000/svg"',
        f'width="{width}"',
        f'height="{height}"',
        'preserveAspectRatio="xMidYMid meet"',
    ]
    if "xlink:" in svg:
        attributes.insert(1, 'xmlns:xlink="http://www.w3.org/1999/xlink"')
    if "data-theme=" not in OPEN_TAG.search(svg).group(0):
        attributes.append('data-theme="dark"')
    svg = svg.replace("<svg ", "<svg " + " ".join(attributes) + " ", 1)
    opening = OPEN_TAG.search(svg)
    svg = svg[: opening.end()] + "\n<style><![CDATA[\n" + stylesheet + "\n]]></style>" + svg[opening.end():]
    svg = "\n".join(line.rstrip() for line in svg.splitlines())
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as error:
        raise SystemExit(f"invalid SVG in {source}: {error}") from error
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise SystemExit(f"missing SVG namespace in {source}")
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
