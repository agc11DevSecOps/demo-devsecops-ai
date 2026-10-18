"""Presentation filter for the one-line demo verdicts.

Reads verdict lines on stdin and writes them to stdout, optionally colourising
the honest label and pacing the stream for a live audience. It never changes a
verdict or a label; it only wraps the fixed ``[LABEL]`` token in ANSI colour.
Colour is on only for a TTY (or ``DEMO_COLOR=1``) and is disabled by
``NO_COLOR``; pacing is off unless ``DEMO_PAUSE`` is a positive number.
"""

from __future__ import annotations

import os
import re
import sys
import time

LABEL_COLORS = {
    "MEASURED": "32",
    "RECORDED": "36",
    "SCRIPTED": "33",
    "PARTIAL": "33",
    "DESIGNED": "35",
    "NOT TESTED": "31",
}
_LABEL = re.compile(r"\[(MEASURED|RECORDED|SCRIPTED|PARTIAL|DESIGNED|NOT TESTED)\]")
_RESET = "\033[0m"


def colorize(line: str) -> str:
    """Wrap the first honest-label token in bold colour; leave the rest intact."""
    match = _LABEL.search(line)
    if match is None:
        return line
    code = LABEL_COLORS[match.group(1)]
    return f"{line[: match.start()]}\033[1;{code}m{match.group(0)}{_RESET}{line[match.end() :]}"


def enabled(stream: object) -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    return os.environ.get("DEMO_COLOR") == "1" or bool(getattr(stream, "isatty", lambda: False)())


def stream(input_stream: object = sys.stdin, output_stream: object = sys.stdout, *, color: bool | None = None, pause: float | None = None, sleep: object = time.sleep) -> None:
    color = enabled(output_stream) if color is None else color
    pause = float(os.environ.get("DEMO_PAUSE", "0") or 0) if pause is None else pause
    for raw in input_stream:
        line = raw.rstrip("\n")
        output_stream.write((colorize(line) if color else line) + "\n")
        output_stream.flush()
        if pause > 0:
            sleep(pause)


def main() -> int:
    stream()
    return 0


if __name__ == "__main__":
    sys.exit(main())
