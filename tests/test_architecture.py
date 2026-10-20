"""Import-boundary checks for the phase-4 module split."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def python_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*.py") if "__pycache__" not in path.parts)


class ImportBoundaryTests(unittest.TestCase):
    def test_security_modules_do_not_depend_on_runtime_or_scenarios(self) -> None:
        forbidden = {"app.demo", "app.scenarios", "app.workload", "app.cli", "app.pipeline", "app.showcase"}
        for path in python_files(APP / "security"):
            self.assertFalse(imports(path) & forbidden, f"{path} imports a forbidden layer")

    def test_llm_modules_do_not_depend_on_workload_or_scenarios(self) -> None:
        forbidden = {"app.demo", "app.scenarios", "app.workload", "app.cli", "app.pipeline", "app.showcase"}
        for path in python_files(APP / "llm"):
            self.assertFalse(imports(path) & forbidden, f"{path} imports a forbidden layer")

    def test_only_demo_and_cli_wire_scenarios(self) -> None:
        allowed = {APP / "demo.py", APP / "cli.py"}
        for path in python_files(APP):
            if path in allowed or (APP / "scenarios" in path.parents):
                continue
            referenced = {module for module in imports(path) if module.startswith("app.scenarios")}
            self.assertFalse(referenced, f"{path} imports scenarios directly")

    def test_only_cli_imports_demo(self) -> None:
        for path in python_files(APP):
            if path == APP / "cli.py" or path == APP / "demo.py":
                continue
            self.assertNotIn("app.demo", imports(path), f"{path} imports app.demo")

    def test_demo_is_only_a_scenario_dispatcher(self) -> None:
        """Controls remain in app.security rather than growing back into demo.py."""
        allowed = {"__future__", "typing", "app.evidence", "app.scenarios"}
        self.assertEqual(imports(APP / "demo.py"), allowed)

    def test_scenarios_have_one_handler_per_scenario(self) -> None:
        for number in range(9):
            module = APP / "scenarios" / f"s{number}.py"
            self.assertTrue(module.is_file(), f"missing {module}")
            self.assertIn(f"scenario_s{number}", module.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
