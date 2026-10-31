from __future__ import annotations

import unittest

from tools.present_check import PresentationCheckError, _assert_dom, _safe_name


class PresentationCheckTests(unittest.TestCase):
    def test_safe_capture_name_uses_only_fixed_route_parts(self) -> None:
        self.assertEqual(_safe_name("S4", "payload"), "s4-payload")

    def test_dom_rejects_node_stringification(self) -> None:
        with self.assertRaisesRegex(PresentationCheckError, "presentation_dom_failure"):
            _assert_dom("<dd>[object HTMLSpanElement]</dd>")

    def test_dom_rejects_a_missing_expected_payload(self) -> None:
        with self.assertRaisesRegex(PresentationCheckError, "presentation_expected_text_missing"):
            _assert_dom("<main>safe page</main>", "SYSTEM NOTE")

    def test_dom_accepts_expected_synthetic_payload(self) -> None:
        _assert_dom("<main>SYSTEM NOTE</main>", "SYSTEM NOTE")

    def test_dom_requires_the_recorded_inspect_flow(self) -> None:
        with self.assertRaisesRegex(PresentationCheckError, "presentation_expected_text_missing"):
            _assert_dom("<main>Sample s0-benign</main>", "opsassist_flow")


if __name__ == "__main__":
    unittest.main()
