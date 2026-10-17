"""Fixed Garak invocation used only by the S7 container runner.

Only the argv below is used and no shell, inherited environment or user input is
involved. With no ``--limit`` the complete ``encoding.InjectBase64`` corpus runs
(55 prompts): Garak's ``RestGenerator`` honours the workload's ``429`` responses
with Fibonacci backoff, so the probe completes at the endpoint's real rate limit.
A positive ``--limit`` is an explicit iteration aid that truncates the corpus for
faster local runs; the campaign marks such a run ``PARTIAL`` and never treats it
as the admitted full campaign.
"""

from __future__ import annotations

import argparse

FULL_CORPUS = 55


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("generator_config")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if 0 < args.limit < FULL_CORPUS:
        import garak.probes.encoding as encoding

        original = encoding._generate_encoded_prompts

        def limited(*values: object) -> list[tuple[str, str]]:
            return original(*values)[: args.limit]

        encoding._generate_encoded_prompts = limited

    from garak.cli import main as garak_main

    garak_main([
        "--model_type", "rest",
        "--generator_option_file", args.generator_config,
        "--probes", "encoding.InjectBase64",
        "--parallel_requests", "1",
        "--parallel_attempts", "1",
        "--generations", "1",
        "--report_prefix", "garak-s7",
        "--narrow_output",
    ])


if __name__ == "__main__":
    main()
