from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MonorepoTests(unittest.TestCase):
    def test_every_integration_has_common_contract(self):
        integrations = [p for p in (ROOT / "integrations").iterdir() if p.is_dir()]
        self.assertTrue(integrations)
        for path in integrations:
            meta = json.loads((path / "integration.json").read_text())
            self.assertEqual(path.name, meta["id"])
            for script in ("install.sh", "verify.sh", "uninstall.sh"):
                target = path / script
                self.assertTrue(target.exists(), f"{path.name}/{script}")
                self.assertTrue(os.access(target, os.X_OK), f"{path.name}/{script} not executable")

    def test_root_list_discovers_gitea(self):
        result = subprocess.run([str(ROOT / "install.sh"), "--list"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("gitea", result.stdout.split())

    def test_root_install_all_dispatches_gitea(self):
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ)
            env["HERMES_HOME"] = td
            env.pop("GITEA_BASE_URL", None); env.pop("GITEA_TOKEN", None)
            result = subprocess.run(
                [str(ROOT / "install.sh"), "--no-config", "--no-enable"],
                cwd=ROOT, env=env, text=True, capture_output=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((Path(td) / "plugins/gitea-hermes/plugin.yaml").exists())
            self.assertTrue((Path(td) / "skills/gitea-professional/SKILL.md").exists())

    def test_uninstall_requires_explicit_target(self):
        result = subprocess.run([str(ROOT / "uninstall.sh")], cwd=ROOT, text=True, capture_output=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Refusing", result.stderr)


if __name__ == "__main__":
    unittest.main()
