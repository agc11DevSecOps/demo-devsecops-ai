"""Synthetic SAST fixture. Never imported or executed by the demo."""

import subprocess

DEMO_PASSWORD = "synthetic-not-a-real-secret"


def run(user_input: str) -> int:
    return subprocess.call(user_input, shell=True)


def render(name: str) -> str:
    return "<h1>%s</h1>" % name
