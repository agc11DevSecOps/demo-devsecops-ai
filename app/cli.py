"""Command-line entry point; no network or external process execution."""

from __future__ import annotations

import argparse
import json
import sys

from app.demo import SCENARIOS, reset, run
from app.workload import activate_stop, deactivate_stop, handle_payload, serve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["reset", "run", "workload", "serve-workload", "gateway", "garak", "kill", "unkill", "pipeline"])
    parser.add_argument("--run", choices=["A", "B"])
    parser.add_argument("--scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--stage", type=int, choices=range(1, 12))
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--preserve-evidence", action="store_true")
    parser.add_argument("--request-id")
    parser.add_argument("--requester")
    parser.add_argument("--question")
    args = parser.parse_args()
    if args.command == "reset":
        reset(clear_evidence=not args.preserve_evidence)
        return
    if args.command == "serve-workload":
        serve()
        return
    if args.command == "gateway":
        from app.gateway import serve as serve_gateway

        serve_gateway()
        return
    if args.command == "garak":
        from app.garak_campaign import main as garak_main

        garak_main()
        return
    if args.command == "pipeline":
        from app.pipeline import run_pipeline

        run_pipeline(only=args.stage)
        return
    if args.command == "kill":
        activate_stop()
        return
    if args.command == "unkill":
        deactivate_stop()
        return
    if args.command == "workload":
        if args.request_id is None or args.requester is None or args.question is None:
            parser.error("workload requires --request-id, --requester and --question")
        status, payload = handle_payload({"request_id": args.request_id, "requester": args.requester, "question": args.question})
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        if status != 200:
            sys.exit(2)
        return
    if args.run is None:
        parser.error("--run is required for run")
    if args.fresh:
        reset(clear_evidence=False)
    run(args.run, [args.scenario] if args.scenario else None)


if __name__ == "__main__":
    main()
