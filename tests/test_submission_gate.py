"""Regression tests for the automated submission gate and its published verdicts."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import validate_submission as vs  # noqa: E402


class PackageRuleTests(unittest.TestCase):
    def test_zip_with_exactly_one_tif_is_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            z = Path(d) / "a.zip"
            with zipfile.ZipFile(z, "w") as zf:
                zf.writestr("only.tif", b"II*\x00")
            out = vs.unzip_single_tif(z, Path(d) / "out" / "only.tif")
            self.assertEqual(out.read_bytes(), b"II*\x00")

    def test_zip_with_extra_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            z = Path(d) / "b.zip"
            with zipfile.ZipFile(z, "w") as zf:
                zf.writestr("one.tif", b"x")
                zf.writestr("readme.txt", b"extra")
            with self.assertRaises(ValueError):
                vs.unzip_single_tif(z, Path(d) / "o.tif")


class PublishedVerdictTests(unittest.TestCase):
    def test_no_published_gate_verdict_is_ok_to_submit(self):
        for p in (ROOT / "docs" / "downloads").glob("*-gate.json"):
            with self.subTest(file=p.name):
                self.assertEqual(json.loads(p.read_text())["verdict"], "DO NOT SUBMIT")

    def test_site_uniqueness_flags_every_measured_candidate(self):
        # Regression guard: no file may be cleared while the literal rule is violated.
        data = json.loads((ROOT / "evidence" / "site-uniqueness-20261029.json").read_text())
        self.assertEqual(len(data["candidates"]), 11)
        for c in data["candidates"]:
            with self.subTest(candidate=c["label"]):
                self.assertGreater(c["registry_rasters_over_0_70_within3"], 0)
                self.assertFalse(c["literal_dot_rule_0_70_passed_vs_all_measured"])

    def test_executive_summary_banner_and_table_are_generated(self):
        page = (ROOT / "executive-summary.html").read_text()
        self.assertIn("NO FILE IS CLEARED TO SUBMIT", page)
        self.assertEqual(page.count("GATE-BANNER:START"), 1)
        self.assertEqual(page.count("NINE-SITE-GATE:START"), 1)
        for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                     "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
            self.assertIn(f"<strong>{site}</strong>", page)

    def test_candidate_note_limit(self):
        gate = json.loads((ROOT / "docs/downloads/gemsdoe32-karage3-consensus-hgrad-k37654-20261029T183206Z-4786d9bd-gate.json").read_text())
        self.assertLessEqual(len(gate["note"]), 140)


if __name__ == "__main__":
    unittest.main()
