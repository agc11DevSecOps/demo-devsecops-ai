"""Tests for the pinned model fetcher argument handling.

The fetcher must behave identically on every supported interpreter. Python
3.10 and 3.11 validate an empty ``nargs="*"`` list against argparse's
``choices=``, which made ``fetch_models`` without arguments fail on those
interpreters. The validation is therefore done in code and tested here.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from tools import fetch_models

ROOT = Path(__file__).resolve().parents[1]


class ParseModelsTests(unittest.TestCase):
    def test_no_arguments_selects_every_known_model(self) -> None:
        self.assertEqual(fetch_models.parse_models([]), sorted(fetch_models.MODELS))

    def test_an_explicit_model_is_selected_on_its_own(self) -> None:
        self.assertEqual(fetch_models.parse_models(["flan-t5-small"]), ["flan-t5-small"])

    def test_several_models_are_kept_in_the_requested_order(self) -> None:
        selected = fetch_models.parse_models(["prompt-guard-2-22m", "flan-t5-small"])
        self.assertEqual(selected, ["prompt-guard-2-22m", "flan-t5-small"])

    def test_an_unknown_model_is_refused_with_the_valid_choices(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            fetch_models.parse_models(["not-a-model"])
        self.assertEqual(raised.exception.code, 2)

    def test_the_error_message_names_the_valid_models(self) -> None:
        stderr = _capture_stderr(lambda: fetch_models.parse_models(["not-a-model"]))
        self.assertIn("not-a-model", stderr)
        for name in sorted(fetch_models.MODELS):
            self.assertIn(name, stderr)

    def test_the_known_models_are_the_admitted_pair(self) -> None:
        self.assertEqual(sorted(fetch_models.MODELS), ["flan-t5-small", "prompt-guard-2-22m"])

    def test_the_gated_model_is_the_only_one_that_needs_a_token(self) -> None:
        gated = [name for name, spec in fetch_models.MODELS.items() if spec["requires_token"]]
        self.assertEqual(gated, ["prompt-guard-2-22m"])


class MakefileWiringTests(unittest.TestCase):
    def test_the_makefile_exposes_the_fetch_targets(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertRegex(makefile, r"(?m)^fetch-models:")
        self.assertRegex(makefile, r"(?m)^fetch-workload-model:")
        self.assertIn("flan-t5-small", makefile)


def _capture_stderr(action) -> str:
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer):
        try:
            action()
        except SystemExit:
            pass
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
