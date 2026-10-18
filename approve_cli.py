#!/usr/bin/env python3
"""Issue or verify a human approval token bound to one exact tool call.

Usage:
    python approve_cli.py issue --tool delete_branch \
        --parameters '{"repo": "demo-app", "branch": "release/2.4"}' \
        --requester presenter
    python approve_cli.py verify --token <token> --tool delete_branch \
        --parameters '{"repo": "demo-app", "branch": "release/2.4"}' \
        --requester presenter

The descriptor digest is recomputed from the pinned tool descriptor, so an
approval cannot be replayed against a changed tool definition.
"""

from __future__ import annotations

import argparse
import json
import sys

from app.approvals import issue, verify
from app.demo import ToolBoundary, descriptor_digest


def _descriptor(tool: str) -> str:
    boundary = ToolBoundary()
    return boundary.pins[tool]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("issue", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--tool", required=True, choices=sorted(ToolBoundary().pins))
        command.add_argument("--parameters", required=True)
        command.add_argument("--requester", required=True)
        command.add_argument("--token")
        command.add_argument("--ttl-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        parameters = json.loads(args.parameters)
        if type(parameters) is not dict:
            raise ValueError
        descriptor = _descriptor(args.tool)
    except (json.JSONDecodeError, KeyError, ValueError):
        parser.error("invalid --parameters or --tool")
    if args.command == "issue":
        print(issue(args.tool, parameters, args.requester, descriptor, ttl_seconds=args.ttl_seconds))
        return 0
    if not args.token:
        parser.error("verify requires --token")
    ok = verify(args.token, tool=args.tool, parameters=parameters, requester=args.requester, descriptor_sha256=descriptor)
    print(json.dumps({"approved": ok}, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
