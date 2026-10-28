"""Regression checks for the current nine-site comparison, not stale lane dashboards."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOCUS = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}


class EvidenceTests(unittest.TestCase):
    def test_historical_audit_is_complete_for_focus_sites_only(self):
        report = json.loads((ROOT / "docs/historical-raster-audit.json").read_text())
        self.assertEqual({row["site"] for row in report["rasters"]}, FOCUS)
        self.assertEqual(len(report["pairwise"]), 72)
        self.assertFalse(report["official_template_available"])
        self.assertFalse(report["complete_registry_checked"])
        self.assertFalse(report["new_submission_generated"])
        self.assertTrue(all(pair["candidate_fraction_within_3px"] > 0.70 for pair in report["pairwise"]))

    def test_current_summary_does_not_present_score_forecasts_as_results(self):
        page = (ROOT / "docs/preflight-executive.html").read_text()
        self.assertIn("USER-REPORTED / unverified", page)
        self.assertIn("Estimated score", page)
        self.assertIn("Unavailable", page)
        self.assertIn("NO FILE IS APPROVED FOR SUBMISSION", page)
        self.assertIn("not ORGANIZER-CONFIRMED receipts", page)


if __name__ == "__main__":
    unittest.main()
