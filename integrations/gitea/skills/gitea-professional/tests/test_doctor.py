from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import doctor  # noqa: E402


class DoctorTests(unittest.TestCase):
    def test_parse_127_patch(self):
        self.assertEqual(doctor.parse_version({"version": "1.27.2"}), (1, 27, 2))

    def test_parse_v_prefix_and_suffix(self):
        self.assertEqual(doctor.parse_version("v1.27.0+gitea"), (1, 27, 0))

    def test_parse_other_minor(self):
        self.assertEqual(doctor.parse_version("1.28.0"), (1, 28, 0))

    def test_parse_invalid(self):
        self.assertIsNone(doctor.parse_version("development"))


if __name__ == "__main__":
    unittest.main()
