"""Guards for the nine-site focus summaries. These must never authorize a submission."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_focus9 as b  # noqa: E402

EXPECTED = set(b.EXPECTED)


class Focus9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg, cls.aud, cls.base = b.load_sources()

    def test_exactly_nine_sites_and_matching_hashes(self):
        self.assertEqual(set(self.reg), EXPECTED)
        for site in EXPECTED:
            self.assertEqual(self.reg[site]["sha256"], self.base[site]["sha256"])
            self.assertEqual(self.reg[site]["sha256"], self.aud[site]["format"]["sha256"])

    def test_every_holdout_value_is_labelled_and_not_promotable(self):
        for site in EXPECTED:
            hr = self.base[site]["holdout_dti_hide_and_recover"]
            self.assertEqual(hr["score_label"], "HOLDOUT-DTI")
            self.assertGreater(hr["n_withheld_positives"], 0)
            lo, hi = hr["ci95_cluster_bootstrap"]
            self.assertLessEqual(lo, hr["pooled_dti"] + 1e-12)
            self.assertLessEqual(hr["pooled_dti"], hi + 1e-12)
            self.assertIs(self.base[site]["evaluator_flags"]["promotion_eligible"], False)

    def test_pages_render_negative_and_never_say_yes(self):
        card = b.run_card(self.reg, self.base)
        self.assertEqual(card["verdict"], "negative")
        self.assertIs(card["ok_to_submit"], False)
        self.assertEqual(card["weekly_slots_used"], 0)
        pages = [b.home(self.reg, self.aud, self.base, card)]
        pages += [b.site_page(s, self.reg, self.aud, self.base) for s in sorted(EXPECTED)]
        for html in pages:
            self.assertIn("DO NOT SUBMIT", html)
            self.assertNotIn("OK TO DOWNLOAD AND SUBMIT? YES", html)

    def test_no_site_authorized_and_no_estimate_written_as_score(self):
        for site in EXPECTED:
            self.assertIs(self.aud[site]["new_submission_authorized"], False)
        html = b.site_page("GEMSDOE32", self.reg, self.aud, self.base)
        self.assertIn("Not estimable", html)

    def test_committed_pages_match_builder(self):
        card = b.run_card(self.reg, self.base)
        expected = b.home(self.reg, self.aud, self.base, card)
        self.assertEqual((ROOT / "docs/focus9/index.html").read_text(), expected)
        self.assertEqual(json.loads((ROOT / "docs/focus9/run-card.json").read_text()), card)

    def test_nine_site_summary_never_links_unapproved_candidate_downloads(self):
        page = (ROOT / "docs/nine-site-summary.html").read_text()
        candidate = "gemsdoe32-karage3-k4-offcat-ridge-20k-20261029T183711Z-2a6558a3"
        self.assertIn("Download status: disabled — DO NOT SUBMIT", page)
        self.assertIn("no TIF or ZIP download link", page)
        self.assertNotIn(f'href="docs/downloads/{candidate}-zeros.tif"', page)
        self.assertNotIn(f'href="docs/downloads/{candidate}-zeros.zip"', page)


if __name__ == "__main__":
    unittest.main()
