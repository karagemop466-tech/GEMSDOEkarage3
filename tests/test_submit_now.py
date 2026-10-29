"""Consistency checks for the newest candidate and its status pages (no rasters needed; runs in CI)."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "karage3-lgap-scarpstep-19k-20261029-4fc40bd1"
CARD = ROOT / "docs" / "downloads" / f"{NAME}-card.json"


class SubmitNowTests(unittest.TestCase):
    def setUp(self):
        self.card = json.loads(CARD.read_text())

    def test_unpublished_while_gates_fail(self):
        # A file may be published only when every gate passes. Otherwise it must not sit in docs/downloads.
        if self.card["gates"]["download_ok"]:
            self.assertEqual(self.card["file_to_download"], f"docs/downloads/{NAME}.tif")
            self.assertTrue((ROOT / self.card["file_to_download"]).exists())
        else:
            self.assertIsNone(self.card["file_to_download"])
            self.assertFalse(self.card["file_published"])
            self.assertFalse((ROOT / "docs" / "downloads" / f"{NAME}.tif").exists())
            self.assertTrue(self.card["blocking_reasons"])

    def test_note_is_within_limit_and_matches_card(self):
        note = self.card["submission_note"]
        self.assertLessEqual(len(note), 140)
        self.assertEqual(len(note), self.card["submission_note_chars"])

    def test_no_organizer_score_or_estimate_is_written(self):
        self.assertIsNone(self.card["estimated_leaderboard_score"])
        self.assertIsNone(self.card["organizer_confirmed_score"])
        self.assertEqual(self.card["weekly_slots_used"], 0)

    def test_download_gate_is_the_conjunction_of_its_parts(self):
        g = self.card["gates"]
        self.assertEqual(g["download_ok"], bool(g["format_pass"] and g["literal_uniqueness_measured_pass"]
                                                and g["full_inventory_pass"]))

    def test_full_inventory_failure_is_recorded_with_counts(self):
        full = self.card["uniqueness"]["full_inventory"]
        self.assertEqual(full["count_literal_fails"] > 0, not self.card["gates"]["full_inventory_pass"])
        self.assertGreater(full["rasters_compared"], 1900)

    def test_promotion_is_negative_unless_it_beats_best_focus9(self):
        best = self.card["holdout"]["best_focus9_same_evaluator"]["prevalence_calibrated_dti"]
        cand = self.card["holdout"]["sgmc_off_catalogue"]["prevalence_calibrated_dti"]
        if self.card["verdict"] == "promote":
            self.assertTrue(self.card["gates"]["download_ok"] and cand > best)
        else:
            self.assertEqual(self.card["verdict"], "negative")

    def test_labels_present_on_every_holdout_number(self):
        h = self.card["holdout"]
        self.assertEqual(h["hide_and_recover"]["label"], "HOLDOUT-DTI")
        self.assertEqual(h["sgmc_off_catalogue"]["label"], "HOLDOUT-DTI")
        self.assertIn("evaluator_version", h["hide_and_recover"])
        self.assertIn("n_withheld_positives", h["sgmc_off_catalogue"])

    def test_canary_below_threshold(self):
        self.assertLessEqual(self.card["holdout"]["leakage_canary"]["auc_vs_sgmc_offcatalogue"], 0.90)

    def test_submit_now_page_is_current(self):
        r = subprocess.run([sys.executable, "scripts/build_submit_now.py", "--check"],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, msg=r.stderr)

    def test_status_pages_agree_with_card(self):
        expect = "OK TO DOWNLOAD: YES" if self.card["gates"]["download_ok"] else "OK TO DOWNLOAD: NO"
        self.assertIn(expect, (ROOT / "docs" / "submit-now" / "index.html").read_text())

    def test_root_page_still_refuses_submission(self):
        root = (ROOT / "index.html").read_text()
        self.assertIn("OK TO SUBMIT? NO", root)
        self.assertNotIn("READY TO DOWNLOAD", root)
        self.assertNotIn('href="docs/downloads/karage3', root)
        self.assertIn("disabled", root)

    def test_readme_does_not_offer_an_unpublished_download(self):
        text = (ROOT / "README.md").read_text()
        if not self.card["gates"]["download_ok"]:
            self.assertNotIn(f"docs/downloads/{NAME}.tif", text)
            self.assertIn("No file is cleared", text)


if __name__ == "__main__":
    unittest.main()
