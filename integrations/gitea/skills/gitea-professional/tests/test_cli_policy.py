from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gitea  # noqa: E402
from gitea_client import GiteaError, Response  # noqa: E402


class FakePRClient:
    def __init__(self):
        self.token = "secret"
        self.merge_body = None

    def get(self, path, query=None):
        if path.endswith("/status"):
            return {"state": "success"}
        if "/pulls/7" in path:
            if self.merge_body:
                return {"state": "closed", "merged": True, "head": {"sha": "abc123"}, "merge_commit_sha": "def456"}
            return {"state": "open", "merged": False, "head": {"sha": "abc123"}}
        raise AssertionError(path)

    def request(self, method, path, query=None, body=None, **kwargs):
        if path.endswith("/merge"):
            self.merge_body = body
            return Response(200, {}, {"merged": True}, "")
        raise AssertionError((method, path))


class FakeSecretClient:
    def __init__(self):
        self.token = "api-token"
        self.body = None

    def request(self, method, path, query=None, body=None, **kwargs):
        if method == "PUT" and "/actions/secrets/" in path:
            self.body = body
            return Response(204, {}, None, "")
        raise AssertionError((method, path))

    def get(self, path, query=None):
        if path.endswith("/actions/secrets"):
            return [{"name": "DEPLOY_TOKEN", "created_at": "now"}]
        raise AssertionError(path)


class PolicyTests(unittest.TestCase):
    def test_confirmation_guard(self):
        with self.assertRaises(GiteaError) as ctx:
            gitea.require_confirm(None, "DELETE_REPO:a/b")
        self.assertEqual(ctx.exception.code, "E_CONFIRMATION_REQUIRED")

    def test_merge_pins_sha_and_never_force_merges(self):
        client = FakePRClient()
        args = SimpleNamespace(
            owner="o",
            repo="r",
            index=7,
            head_sha="abc123",
            strategy="merge",
            delete_branch=True,
            allow_non_green=False,
            confirm="MERGE:o/r#7@abc123",
        )
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            rc = gitea.cmd_pr_merge(client, args)
        self.assertEqual(rc, 0)
        self.assertEqual(client.merge_body["head_commit_id"], "abc123")
        self.assertFalse(client.merge_body["force_merge"])

    def test_merge_rejects_stale_head(self):
        client = FakePRClient()
        args = SimpleNamespace(
            owner="o",
            repo="r",
            index=7,
            head_sha="old",
            strategy="merge",
            delete_branch=True,
            allow_non_green=False,
            confirm="MERGE:o/r#7@old",
        )
        with self.assertRaises(GiteaError) as ctx:
            gitea.cmd_pr_merge(client, args)
        self.assertEqual(ctx.exception.code, "E_STALE_HEAD")

    def test_pr_review_parser_matches_gitea_127_review_state(self):
        args = gitea.parser().parse_args([
            "--base-url", "https://git.example",
            "pr", "review", "o", "r", "7", "--event", "APPROVED",
        ])
        self.assertEqual("APPROVED", args.event)
        with self.assertRaises(SystemExit):
            gitea.parser().parse_args([
                "--base-url", "https://git.example",
                "pr", "review", "o", "r", "7", "--event", "APPROVE",
            ])

    def test_generic_delete_needs_write_guard(self):
        args = gitea.parser().parse_args([
            "--base-url", "https://git.example",
            "request", "DELETE", "/repos/o/r",
        ])
        self.assertFalse(args.write_ok)

    def test_actions_secret_set_uses_environment_and_never_returns_value(self):
        import contextlib
        import io
        import os

        client = FakeSecretClient()
        args = SimpleNamespace(
            owner="o", repo="r", name="DEPLOY_TOKEN",
            value_env="TEST_DEPLOY_SECRET", description="deployment",
            confirm="SET_SECRET:o/r:DEPLOY_TOKEN",
        )
        os.environ["TEST_DEPLOY_SECRET"] = "super-sensitive-value"
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = gitea.cmd_actions_secret_set(client, args)
            self.assertEqual(rc, 0)
            self.assertEqual(client.body["data"], "super-sensitive-value")
            self.assertNotIn("super-sensitive-value", buf.getvalue())
            self.assertIn('"value_exposed": false', buf.getvalue())
        finally:
            os.environ.pop("TEST_DEPLOY_SECRET", None)

    def test_actions_secret_set_requires_exact_confirmation(self):
        import os

        client = FakeSecretClient()
        args = SimpleNamespace(
            owner="o", repo="r", name="DEPLOY_TOKEN",
            value_env="TEST_DEPLOY_SECRET", description=None,
            confirm=None,
        )
        os.environ["TEST_DEPLOY_SECRET"] = "secret"
        try:
            with self.assertRaises(GiteaError) as ctx:
                gitea.cmd_actions_secret_set(client, args)
            self.assertEqual(ctx.exception.code, "E_CONFIRMATION_REQUIRED")
        finally:
            os.environ.pop("TEST_DEPLOY_SECRET", None)


if __name__ == "__main__":
    unittest.main()
