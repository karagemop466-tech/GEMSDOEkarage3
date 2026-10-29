"""Regression checks for the public no-submit decision and stale candidate links."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_STEM = "karage3-unique-offcat-20261029T180337Z-6a8c2368"


class SubmissionSafetyTests(unittest.TestCase):
    def test_public_pages_do_not_advertise_uncleared_candidate(self):
        for relative in ("index.html", "executive-summary.html"):
            page = (ROOT / relative).read_text(encoding="utf-8").lower()
            self.assertIn("do not submit", page)
            self.assertNotIn(CANDIDATE_STEM, page)
            self.assertNotIn("ready to download", page)
            self.assertNotIn("target &gt; 0.2778", page)

    def test_release_decision_remains_negative(self):
        decision = json.loads((ROOT / "docs/current-gate-decision.json").read_text())
        self.assertEqual(decision["verdict"], "negative")
        self.assertIs(decision["ok_to_submit"], False)
        self.assertIs(decision["selector_approval"], False)

    def test_unapproved_advertised_bundle_is_not_distributed(self):
        downloads = ROOT / "docs/downloads"
        for path in downloads.glob(f"{CANDIDATE_STEM}*"):
            self.fail(f"Unapproved candidate artifact remains publicly downloadable: {path}")


if __name__ == "__main__":
    unittest.main()
