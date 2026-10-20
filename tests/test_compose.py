"""Static checks for the local gateway composition's security contract."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ComposeContractTests(unittest.TestCase):
    def test_gateway_uses_the_real_local_profile(self) -> None:
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        for required in (
            "OPS_DEMO_GATEWAY_TOKEN: ${OPS_DEMO_GATEWAY_TOKEN:?",
            "user: \"${OPS_DEMO_UID:?Use make compose-up}:${OPS_DEMO_GID:?Use make compose-up}\"",
            "OPS_DEMO_WORKLOAD_MODE: local",
            "OPS_DEMO_PROMPT_GUARD: \"1\"",
            "OPS_DEMO_PRESIDIO: \"1\"",
            "OPS_DEMO_VECTOR: \"1\"",
            "./vendor/models:/models:ro",
            "127.0.0.1:${OPS_DEMO_GATEWAY_PORT:-8080}:8080",
        ):
            self.assertIn(required, compose)


if __name__ == "__main__":
    unittest.main()
