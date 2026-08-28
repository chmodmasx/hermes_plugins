from __future__ import annotations

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audit_workflow  # noqa: E402


class PackageIntegrityTests(unittest.TestCase):
    def test_skill_local_reference_paths_exist(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        paths = sorted(set(re.findall(r"`((?:references|templates|scripts)/[^` ]+)`", text)))
        missing = [p for p in paths if "<" not in p and not (ROOT / p).exists()]
        self.assertEqual(missing, [])

    def test_no_runtime_dependency_on_old_gitea_actions_skill(self):
        # README/INSTALL may mention the old skill only as migration guidance.
        checked = [ROOT / "SKILL.md"] + list((ROOT / "references").rglob("*.md"))
        offenders = []
        for path in checked:
            if "gitea-actions" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_bundled_templates_have_no_high_or_critical_audit_findings(self):
        bad = {}
        for path in sorted((ROOT / "templates" / "actions").glob("*.yaml")):
            findings = audit_workflow.audit(path.read_text(encoding="utf-8").splitlines())
            serious = [(f.severity, f.code, f.line) for f in findings if f.severity in {"HIGH", "CRITICAL"}]
            if serious:
                bad[path.name] = serious
        self.assertEqual(bad, {})

    def test_manifest_matches_package_files(self):
        manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
        declared = {item["path"]: item for item in manifest["files"]}
        actual = {}
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or path.name == "MANIFEST.json" or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            data = path.read_bytes()
            rel = path.relative_to(ROOT).as_posix()
            actual[rel] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        self.assertEqual(set(declared), set(actual))
        for rel, info in actual.items():
            self.assertEqual(declared[rel]["bytes"], info["bytes"], rel)
            self.assertEqual(declared[rel]["sha256"], info["sha256"], rel)

    def test_manifest_and_skill_versions_match(self):
        manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(r"(?m)^version:\s*([^\s]+)", skill)
        self.assertIsNotNone(match)
        self.assertEqual(manifest["version"], match.group(1))


if __name__ == "__main__":
    unittest.main()
