"""Export the fixed lab cases as the Inspect dataset (no runtime import)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.flow import lab_cases  # noqa: E402

TARGET = ROOT / "evals" / "dataset.json"


def export() -> Path:
    cases = lab_cases()
    samples = []
    for case_id in sorted(cases):
        case = cases[case_id]
        sample = {
            "id": case["id"],
            "scenario": case["scenario"],
            "check": case["check"],
            "corpus": case["corpus"],
            "agent": case["agent"],
            "question": case["question"],
        }
        if case.get("expected_source"):
            sample["expected_source"] = case["expected_source"]
        samples.append(sample)
    payload = {"format_version": 1, "scope": "live local evaluation; synthetic fixtures", "samples": samples}
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return TARGET


if __name__ == "__main__":
    print(export())
