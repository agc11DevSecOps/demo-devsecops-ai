"""Guard rails that keep local credentials out of the repository.

The demo keeps its secrets in the git-ignored root ``.env`` file. These tests
fail the build if that file is ever staged, if the committed template ever
carries a real value, or if a credential shape appears in any tracked file.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
ENV_TEMPLATE = ROOT / ".env.example"
PROVISION = ROOT / "scripts" / "provision.sh"

# Credential shapes that must never appear in a tracked file.
TOKEN_PATTERNS = (
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)
GATEWAY_ASSIGNMENT = re.compile(r"OPS_DEMO_GATEWAY_TOKEN\s*=\s*[\"']?([^\s\"'#]+)")
APPROVAL_ASSIGNMENT = re.compile(r"OPS_DEMO_APPROVAL_KEY\s*=\s*[\"']?([^\s\"'#]+)")
# Documented demo values are not credentials.
ALLOWED_GATEWAY_VALUES = {"", "local-demo-token", "gateway-smoke-token", "demo-token", "test-token"}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise unittest.SkipTest("git is not available in this environment")
    return [item for item in result.stdout.split("\0") if item]


class EnvFileTests(unittest.TestCase):
    def test_the_env_file_is_git_ignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env", ignore.splitlines())

    def test_the_env_file_is_never_tracked(self) -> None:
        self.assertNotIn(".env", tracked_files())

    def test_the_template_is_tracked(self) -> None:
        self.assertIn(".env.example", tracked_files())

    def test_the_template_carries_no_secret_values(self) -> None:
        secret_keys = {
            "HF_TOKEN",
            "HUGGING_FACE_HUB_TOKEN",
            "OPS_DEMO_GATEWAY_TOKEN",
            "OPS_DEMO_APPROVAL_KEY",
        }
        text = ENV_TEMPLATE.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            if key in secret_keys:
                self.assertEqual(value.strip(), "", f"{key} must be empty in .env.example")

    def test_the_template_documents_every_secret_key(self) -> None:
        text = ENV_TEMPLATE.read_text(encoding="utf-8")
        for key in ("HF_TOKEN", "OPS_DEMO_GATEWAY_TOKEN", "OPS_DEMO_APPROVAL_KEY"):
            self.assertIn(f"# {key}=", text, f"{key} must be documented in the template")

    def test_an_empty_secret_line_is_never_committed(self) -> None:
        """An active empty assignment would clear a value already in the environment."""
        text = ENV_TEMPLATE.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            if key in {"HF_TOKEN", "OPS_DEMO_GATEWAY_TOKEN", "OPS_DEMO_APPROVAL_KEY"}:
                self.assertNotEqual(value.strip(), "", f"{key} must stay commented out")

    def test_the_template_documents_the_format_rules(self) -> None:
        text = ENV_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("KEY=value", text)
        self.assertIn(".env", text)

    def test_the_local_env_file_is_owner_only(self) -> None:
        if not ENV_FILE.is_file():
            self.skipTest("no local .env file in this environment")
        self.assertEqual(ENV_FILE.stat().st_mode & 0o077, 0, ".env must not be readable by group or others")


class TrackedFileTests(unittest.TestCase):
    def test_no_tracked_file_contains_a_credential(self) -> None:
        for name in tracked_files():
            path = ROOT / name
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for pattern in TOKEN_PATTERNS:
                self.assertIsNone(pattern.search(text), f"{name} looks like it contains a credential")

    def test_no_tracked_file_assigns_a_real_gateway_token(self) -> None:
        for name in tracked_files():
            path = ROOT / name
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for value in GATEWAY_ASSIGNMENT.findall(text):
                self.assertIn(value, ALLOWED_GATEWAY_VALUES, f"{name} assigns a real gateway token")

    def test_no_tracked_file_assigns_a_real_approval_key(self) -> None:
        for name in tracked_files():
            path = ROOT / name
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for value in APPROVAL_ASSIGNMENT.findall(text):
                self.assertIn(value, {"", "demo-only"}, f"{name} assigns a real approval key")


class ProvisionScriptTests(unittest.TestCase):
    def test_the_script_never_enables_shell_tracing(self) -> None:
        script = PROVISION.read_text(encoding="utf-8")
        self.assertNotIn("set -x", script)

    def test_the_script_never_prints_a_secret(self) -> None:
        script = PROVISION.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r'(?:echo|printf)[^\n]*"\$\{?HF_TOKEN\}?"', script))
        self.assertIsNone(re.search(r'(?:echo|printf)[^\n]*"\$\{?OPS_DEMO_GATEWAY_TOKEN\}?"', script))

    def test_the_script_reads_the_token_without_echoing_it(self) -> None:
        script = PROVISION.read_text(encoding="utf-8")
        self.assertIn("read -r -s", script)

    def test_the_script_stores_the_token_with_owner_only_permissions(self) -> None:
        script = PROVISION.read_text(encoding="utf-8")
        self.assertIn("chmod 0600", script)

    def test_the_script_only_reads_known_keys(self) -> None:
        script = PROVISION.read_text(encoding="utf-8")
        self.assertIn("KNOWN_KEYS", script)


if __name__ == "__main__":
    unittest.main()
