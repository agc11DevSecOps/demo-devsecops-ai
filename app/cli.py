"""Command-line entry point; no network or external process execution."""

from __future__ import annotations

import argparse

from app.demo import SCENARIOS, reset, run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["reset", "run"])
    parser.add_argument("--run", choices=["A", "B"])
    parser.add_argument("--scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--preserve-evidence", action="store_true")
    args = parser.parse_args()
    if args.command == "reset":
        reset(clear_evidence=not args.preserve_evidence)
        return
    if args.run is None:
        parser.error("--run is required for run")
    if args.fresh:
        reset(clear_evidence=False)
    run(args.run, [args.scenario] if args.scenario else None)


if __name__ == "__main__":
    main()
