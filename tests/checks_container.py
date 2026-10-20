from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContainerIntegrationTests(unittest.TestCase):
    def test_runner_profile_is_restricted(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        for option in ("--network none", "--read-only", "--cap-drop ALL", "--security-opt no-new-privileges", "--memory 128m", "--cpus 0.5", "--pids-limit 32"):
            self.assertIn(option, makefile)
        self.assertNotIn("--privileged", makefile)
        self.assertNotIn("docker.sock", makefile)

    def test_demo_artifacts_confirm_container_boundary(self) -> None:
        marker = ROOT / "sandbox" / "PWNED_BY_MODEL"
        self.assertFalse(marker.exists(), "Run B must reset the Run A marker")
        for run in ("A", "B"):
            records = [json.loads(line) for line in (ROOT / "evidence" / run / "s1.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(records)
            self.assertTrue(all(record["run"] == run for record in records))
        a_records = (ROOT / "evidence" / "A" / "s1.jsonl").read_text(encoding="utf-8")
        b_records = (ROOT / "evidence" / "B" / "s1.jsonl").read_text(encoding="utf-8")
        self.assertIn('"decision":"EXECUTED"', a_records)
        self.assertIn('"decision":"BLOCKED"', b_records)

    def test_demo_records_each_scenario_pair_and_honest_s6(self) -> None:
        for scenario in ("s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"):
            for run in ("A", "B"):
                records = [json.loads(line) for line in (ROOT / "evidence" / run / f"{scenario}.jsonl").read_text(encoding="utf-8").splitlines()]
                self.assertTrue(records, f"missing {run}/{scenario} evidence")
                self.assertTrue(all(record["scenario"] == scenario.upper() for record in records))
        for run in ("A", "B"):
            s6 = json.loads((ROOT / "evidence" / run / "s6.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(s6["decision"], "NOT TESTED")
            self.assertEqual(s6["label"], "NOT TESTED")
            self.assertEqual(s6["aisvs_ids"], [])


if __name__ == "__main__":
    unittest.main()
