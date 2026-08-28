from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audit_workflow  # noqa: E402


class WorkflowAuditTests(unittest.TestCase):
    def test_mutable_action_ref_is_high(self):
        findings = audit_workflow.audit(["      - uses: actions/checkout@v4"])
        self.assertTrue(any(f.code == "MUTABLE_ACTION_REF" and f.severity == "HIGH" for f in findings))

    def test_docker_socket_is_critical(self):
        findings = audit_workflow.audit(["          - /var/run/docker.sock:/var/run/docker.sock"])
        self.assertTrue(any(f.code == "DOCKER_SOCKET" and f.severity == "CRITICAL" for f in findings))

    def test_reviewed_sha_placeholder_is_not_high(self):
        findings = audit_workflow.audit([
            "      - uses: actions/checkout@REPLACE_WITH_REVIEWED_COMMIT_SHA"
        ])
        self.assertTrue(any(f.code == "ACTION_SHA_PLACEHOLDER" and f.severity == "INFO" for f in findings))
        self.assertFalse(any(f.severity in {"HIGH", "CRITICAL"} for f in findings))

    def test_gitea_native_context_is_not_github_alias(self):
        findings = audit_workflow.audit(["          SHA: ${{ gitea.sha }}"])
        self.assertFalse(any(f.code == "GITHUB_CONTEXT_ALIAS" for f in findings))


if __name__ == "__main__":
    unittest.main()
