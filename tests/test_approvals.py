from __future__ import annotations

import unittest

from app.approvals import issue, verify
from app.sandbox import reset
from app.security.tool_boundary import ToolBoundary


class ApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        reset()
        self.boundary = ToolBoundary()
        self.parameters = {"repo": "demo-app", "branch": "release/2.4"}
        self.descriptor = self.boundary.pins["delete_branch"]

    def _issue(self, **overrides: object) -> str:
        arguments = {"tool": "delete_branch", "parameters": self.parameters, "requester": "presenter", "descriptor_sha256": self.descriptor}
        arguments.update(overrides)
        return issue(**arguments)  # type: ignore[arg-type]

    def test_approval_verifies_only_for_the_exact_call(self) -> None:
        token = self._issue()
        self.assertTrue(verify(token, tool="delete_branch", parameters=self.parameters, requester="presenter", descriptor_sha256=self.descriptor))
        self.assertFalse(verify(token, tool="delete_branch", parameters={"repo": "demo-app", "branch": "main"}, requester="presenter", descriptor_sha256=self.descriptor))
        self.assertFalse(verify(token, tool="delete_branch", parameters=self.parameters, requester="someone-else", descriptor_sha256=self.descriptor))
        self.assertFalse(verify(token, tool="delete_branch", parameters=self.parameters, requester="presenter", descriptor_sha256="0" * 64))

    def test_tampered_token_is_rejected(self) -> None:
        body, signature = self._issue().split(".")
        self.assertFalse(verify(f"{body}.{'0' * 64}", tool="delete_branch", parameters=self.parameters, requester="presenter", descriptor_sha256=self.descriptor))
        self.assertFalse(verify("not-a-token", tool="delete_branch", parameters=self.parameters, requester="presenter", descriptor_sha256=self.descriptor))
        self.assertFalse(verify(signature, tool="delete_branch", parameters=self.parameters, requester="presenter", descriptor_sha256=self.descriptor))

    def test_expired_token_is_rejected(self) -> None:
        token = self._issue(ttl_seconds=-1)
        self.assertFalse(verify(token, tool="delete_branch", parameters=self.parameters, requester="presenter", descriptor_sha256=self.descriptor))


if __name__ == "__main__":
    unittest.main()
