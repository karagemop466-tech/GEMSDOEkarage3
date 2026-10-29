"""Regression tests for the session-6 receipts and the generated submission summary.

These tests read committed receipts and generated pages only (no competition rasters),
so they run in CI without the restored .cache data.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def _load(name):
    return json.loads((DATA / name).read_text())


class SummaryReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = _load("submission-summary.json")

    def test_decision_blocks_every_file(self):
        self.assertEqual(self.s["decision"], "NO FILE IS CLEARED FOR SUBMISSION")
        for row in self.s["rows"]:
            self.assertEqual(row["submit_status"], "DO NOT SUBMIT", row["site"])

    def test_nine_sites_in_order_with_user_reported_labels(self):
        sites = sorted(r["site"] for r in self.s["rows"])
        self.assertEqual(sites, SITES)
        for row in self.s["rows"]:
            self.assertEqual(row["score_status"], "USER-REPORTED / UNVERIFIED", row["site"])

    def test_no_projection_is_written_as_a_score(self):
        for row in self.s["rows"]:
            self.assertEqual(row["estimated_leaderboard_score"], "NOT ESTIMABLE from local evidence")

    def test_holdout_values_carry_the_required_labels(self):
        for row in self.s["rows"]:
            h = row["sgmc_calibrated_holdout_dti"]
            self.assertEqual(h["label"], "HOLDOUT-DTI")
            self.assertTrue(h["evaluator"].startswith("GEMSDOE32-SGMC-CAL"))
            self.assertLessEqual(h["ci95"][0], h["value"])
            self.assertLessEqual(h["value"], h["ci95"][1])
            self.assertEqual(h["withheld_positives"], 62703)

    def test_no_site_is_unique_under_the_70_percent_rule(self):
        for row in self.s["rows"]:
            self.assertFalse(row["unique_vs_other_eight"], row["site"])
            self.assertGreater(row["max_directional_overlap_vs_other_site"], 0.70, row["site"])
        # Measured floor is 0.9758 (GEMSDOE36); the banner must not understate it.
        floor = min(r["max_directional_overlap_vs_other_site"] for r in self.s["rows"])
        self.assertGreaterEqual(floor, 0.975)

    def test_zero_catalogue_pixel_dots_for_all_nine(self):
        for row in self.s["rows"]:
            self.assertEqual(row["dots_on_catalogue_pixel"], 0, row["site"])

    def test_geometry_bins_add_up_to_total_dots(self):
        for row in self.s["rows"]:
            total = (row["dots_on_catalogue_pixel"] + row["dots_1_to_3px_from_catalogue"]
                     + row["dots_gt_3px_from_catalogue"])
            self.assertEqual(total, row["n_dots"], row["site"])

    def test_best_reported_site_is_gemsdoe32_at_0_2778(self):
        self.assertEqual(self.s["best_reported_site"], "GEMSDOE32")
        self.assertAlmostEqual(self.s["best_reported_score"], 0.2778)

    def test_h1_is_blocked_by_the_literal_rule(self):
        h1 = self.s["h1"]
        self.assertEqual(h1["n_dots"], 14186)
        self.assertTrue(h1["literal_70pct_rule_triggered"])
        self.assertGreater(h1["overlap_vs_13gems_lattice"], 0.70)
        self.assertTrue(str(h1["holdout_evaluated"]).startswith("No"))
        self.assertIn("BLOCKED", h1["status"].upper())

    def test_lattice_gap_numbers_are_consistent(self):
        lg = _load("lattice-gap-analysis.json")
        self.assertEqual(lg["gap_cells_not_within_3px"], 6649)
        self.assertEqual(lg["max_budget_for_literal_70pct_if_all_gap_used"], 22163)
        # Literal 70% rule: at least 30% of dots must sit in gap cells, so budget <= gap / 0.30.
        self.assertEqual(int(lg["gap_cells_not_within_3px"] / 0.30), lg["max_budget_for_literal_70pct_if_all_gap_used"])
        self.assertLess(lg["recall_ceiling_gap_only_share"], 0.01)

    def test_summary_html_says_no_file_is_cleared(self):
        html = (ROOT / "submission-summary.html").read_text()
        self.assertIn("no file is cleared", html.lower())
        self.assertIn("0.4544", html)
        self.assertIn("Rank 47", html)


class SummaryMatchesSources(unittest.TestCase):
    """Every number in the summary must equal its source receipt (no retyped values)."""

    @classmethod
    def setUpClass(cls):
        cls.s = _load("submission-summary.json")
        cls.audit = {r["site"]: r for r in _load("gemsdoe-top9-audit.json")["sites"]}
        cls.analysis = {r["site"]: r for r in _load("gemsdoe-top9-analysis.json")["per_file"]}

    def test_file_identity_matches_audit(self):
        for row in self.s["rows"]:
            src = self.audit[row["site"]]
            self.assertEqual(row["sha256"], src["sha256"], row["site"])
            self.assertEqual(row["file_url"], src["file_url"], row["site"])
            self.assertEqual(row["file_name"], src["file_name"], row["site"])

    def test_dot_counts_match_analysis(self):
        for row in self.s["rows"]:
            src = self.analysis[row["site"]]
            self.assertEqual(row["n_dots"], src["n_dots"], row["site"])
            self.assertEqual(row["dots_1_to_3px_from_catalogue"], src["dots_1_to_3px_from_catalogue"], row["site"])
            self.assertEqual(row["dots_gt_3px_from_catalogue"], src["dots_gt_3px_from_catalogue"], row["site"])
            self.assertAlmostEqual(row["off_catalogue_share"], src["off_catalogue_fraction"], places=4, msg=row["site"])

    def test_holdout_values_match_evaluator_json(self):
        for row in self.s["rows"]:
            ev = _load(f"evaluator/eval_{row['site']}.json")
            sg = ev["sgmc_off_catalogue"]
            self.assertEqual(row["sgmc_calibrated_holdout_dti"]["value"], round(sg["sgmc_prevalence_calibrated_dti"], 6), row["site"])
            self.assertEqual(row["sgmc_calibrated_holdout_dti"]["withheld_positives"], sg["n_withheld_positives"], row["site"])
            hr = ev["hide_and_recover"]
            self.assertEqual(row["hide_recover_holdout_dti"]["value"], round(hr["pooled_dti"], 6), row["site"])
            self.assertEqual(row["hide_recover_holdout_dti"]["withheld_positives"], hr["n_withheld_positives"], row["site"])


class SavedByteAndFootprintReceipts(unittest.TestCase):
    def test_saved_byte_receipt_covers_every_docs_tif(self):
        rec = json.loads((ROOT / "evidence" / "saved-tiffs-literal-20261028.json").read_text())
        on_disk = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs").rglob("*.tif"))
        self.assertEqual(sorted(r["file"] for r in rec["rasters"]), on_disk)
        self.assertTrue(all(r["duplicate_stop"] for r in rec["rasters"]))
        self.assertTrue(all(r["ok_to_submit"] is False for r in rec["rasters"]))

    def test_unique_offcat_main_file_is_not_cleared_by_footprint_check(self):
        rec = _load("unique-offcat-inside-footprint-check.json")
        self.assertEqual(rec["total_dots"], 12000)
        self.assertEqual(rec["dots_inside_template_footprint"] + rec["dots_outside_template_footprint"], rec["total_dots"])
        self.assertEqual(rec["dots_outside_template_footprint"], 7483)
        self.assertTrue(rec["literal_70pct_rule_on_inside_dots_triggered"])
        self.assertGreater(rec["inside_within3px_of_lattice_share"], 0.70)
        self.assertFalse(rec["ok_to_submit"])


class GeoconduitClaimIsNotCleared(unittest.TestCase):
    def test_lattice_overlap_fails_literal_rule(self):
        rec = _load("geoconduit-uniqueness.json")
        self.assertEqual(rec["candidate_dots"], 35615)
        self.assertTrue(rec["literal_70pct_rule_triggered"])
        self.assertGreater(rec["worst_directional_overlap"]["candidate_within3px_of_registry"], 0.70)

    def test_shared_evaluator_off_catalogue_value_is_recorded(self):
        ev = _load("evaluator/eval_geoconduit.json")["sgmc_off_catalogue"]
        self.assertEqual(ev["evaluator_version"], "GEMSDOE32-SGMC-CAL-v3.0")
        self.assertLess(ev["sgmc_prevalence_calibrated_dti"], 0.058)  # below the lowest nine-site value

    def test_inside_footprint_receipt_has_no_outside_dots(self):
        rec = _load("geoconduit-inside-footprint-check.json")
        self.assertEqual(rec["dots_outside_template_footprint"], 0)
        self.assertFalse(rec["ok_to_submit"])


class LeaderboardSnapshot(unittest.TestCase):
    def test_top_50_monotone_with_expected_anchors(self):
        snap = _load("leaderboard-snapshot-20261029.json")
        rows = snap["rows"]
        self.assertEqual(len(rows), 50)
        scores = [r["best_public_dw_tversky"] for r in rows]
        self.assertTrue(all(a >= b for a, b in zip(scores, scores[1:])))
        self.assertEqual(scores[0], 0.4544)
        self.assertEqual(scores[46], 0.3195)  # rank 47
        self.assertEqual(scores[-1], 0.3167)  # rank 50
        self.assertFalse(snap["gems_values_visible_on_top50"])
        self.assertTrue(all(r["rank"] == i + 1 for i, r in enumerate(rows)))


class BlockedArtefactsStayOutOfDocs(unittest.TestCase):
    def test_no_h1_tif_is_published_under_docs(self):
        hits = [p for p in (ROOT / "docs").rglob("*") if "h1-ridge" in p.name.lower()]
        self.assertEqual(hits, [])

    def test_h1_tif_is_only_in_gitignored_cache(self):
        receipt = _load("h1-candidate-receipt.json")
        path = receipt["blocked_tif"]["path"]
        self.assertTrue(path.startswith(".cache/"), path)
        self.assertEqual(receipt["blocked_tif"]["status"], "BLOCKED - DO NOT SUBMIT")


class FrontPageBanner(unittest.TestCase):
    def test_index_has_no_clearance_banner(self):
        html = (ROOT / "index.html").read_text()
        self.assertIn("No file is cleared", html)
        self.assertIn('href="submission-summary.html"', html)


class IrregularityRegister(unittest.TestCase):
    def test_session6_entries_present(self):
        text = (ROOT / "knowledge" / "irregularities.md").read_text()
        for i in range(1, 14):
            self.assertIn(f"IR-S6-{i:02d}", text)


if __name__ == "__main__":
    unittest.main()
