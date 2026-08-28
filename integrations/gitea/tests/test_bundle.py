from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BundleTests(unittest.TestCase):
    def test_required_layout(self):
        required = [
            "integration.json",
            "plugin/gitea-hermes/plugin.yaml",
            "plugin/gitea-hermes/__init__.py",
            "skills/gitea-professional/SKILL.md",
            "install.sh", "uninstall.sh", "verify.sh",
            "docs/COMPATIBILITY.md", "docs/SOURCES.md", "docs/WEBHOOKS.md",
        ]
        self.assertEqual([], [p for p in required if not (ROOT / p).exists()])

    def test_integration_metadata(self):
        meta = json.loads((ROOT / "integration.json").read_text())
        self.assertEqual("gitea", meta["id"])
        self.assertIn("gitea-hermes", meta["components"]["plugins"])
        self.assertIn("gitea-professional", meta["components"]["skills"])
        self.assertEqual("Gitea 1.27.2", meta["baseline"])

    def test_no_symlinks_in_distributed_tree(self):
        bad = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_symlink()]
        self.assertEqual([], bad)

    def test_no_manifest_v2_dependency(self):
        text = (ROOT / "plugin/gitea-hermes/plugin.yaml").read_text()
        self.assertNotIn("manifest_version:", text)
        self.assertNotIn("api_version:", text)
        self.assertNotIn("python_dependencies:", text)

    def test_installer_copies_plugin_and_skill_without_credentials(self):
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ)
            env["HERMES_HOME"] = td
            env.pop("GITEA_BASE_URL", None); env.pop("GITEA_TOKEN", None)
            result = subprocess.run([str(ROOT / "install.sh"), "--no-config", "--no-enable"], cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((Path(td) / "plugins/gitea-hermes/plugin.yaml").exists())
            self.assertTrue((Path(td) / "skills/gitea-professional/SKILL.md").exists())
            self.assertFalse((Path(td) / ".env").exists())

    def test_installer_configures_secret_env_without_leaking_token(self):
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ)
            env["HERMES_HOME"] = td
            env["GITEA_BASE_URL"] = "https://git.example.com"
            token = "test-secret-token-never-print"
            env["GITEA_TOKEN"] = token
            result = subprocess.run([str(ROOT / "install.sh"), "--no-enable"], cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(0, result.returncode, result.stderr)
            combined = result.stdout + result.stderr
            self.assertNotIn(token, combined)
            env_file = Path(td) / ".env"
            self.assertTrue(env_file.exists())
            self.assertEqual(0o600, env_file.stat().st_mode & 0o777)
            text = env_file.read_text()
            self.assertIn("GITEA_BASE_URL=https://git.example.com", text)
            self.assertIn("GITEA_TOKEN=" + token, text)


if __name__ == "__main__":
    unittest.main()
