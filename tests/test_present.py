from __future__ import annotations

import io
import unittest
from unittest import mock

from app.present import colorize, stream


class PresentTests(unittest.TestCase):
    def test_colorize_wraps_a_known_label(self) -> None:
        out = colorize("[B] [S5] [MEASURED] tool quota -> BLOCKED :: contained")
        self.assertIn("\033[1;32m[MEASURED]\033[0m", out)
        self.assertTrue(out.endswith(":: contained"))

    def test_colorize_leaves_unlabelled_lines_untouched(self) -> None:
        line = "make[1]: Entering directory"
        self.assertEqual(colorize(line), line)

    def test_stream_writes_ansi_only_when_colour_is_on(self) -> None:
        source = io.StringIO("[B] [S7] [NOT TESTED] Garak campaign -> NOT TESTED\nplain\n")
        colored = io.StringIO()
        plain = io.StringIO()
        stream(source, colored, color=True, pause=0)
        source.seek(0)
        stream(source, plain, color=False, pause=0)
        self.assertIn("\033[1;31m", colored.getvalue())
        self.assertNotIn("\033[", plain.getvalue())
        self.assertEqual(plain.getvalue(), "[B] [S7] [NOT TESTED] Garak campaign -> NOT TESTED\nplain\n")

    def test_stream_paces_one_sleep_per_line(self) -> None:
        source = io.StringIO("a\nb\nc\n")
        sleep = mock.Mock()
        stream(source, io.StringIO(), color=False, pause=0.5, sleep=sleep)
        self.assertEqual(sleep.call_count, 3)
        sleep.assert_called_with(0.5)


if __name__ == "__main__":
    unittest.main()
