from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicRootSubmissionSafety(unittest.TestCase):
    def test_entry_pages_never_promote_pending_candidate(self):
        for name in ("index.html", "executive-summary.html"):
            page = (ROOT / name).read_text()
            with self.subTest(page=name):
                self.assertIn("DO NOT SUBMIT", page)
                self.assertNotIn("OK TO DOWNLOAD AND SUBMIT: YES", page)
                self.assertNotIn("OK TO SUBMIT: YES", page)
                self.assertNotIn("ready to submit", page.lower())
                self.assertIn("NOT ESTABLISHED", page)
                self.assertIn("0.3047", page)
                self.assertIn("0.4239", page)  # card value must be shown as NOT reproduced
                self.assertIn("did not reproduce", page)
                self.assertIn("HOLDOUT-DTI", page)
                self.assertIn("not an organizer", page.lower())
        card = json.loads((ROOT / "docs/data/candidate-review-20261029.json").read_text())
        self.assertEqual(card["verdict"], "negative")
        self.assertIsNone(card["registry_checks"]["final_dots_overlap_max_3px"])
        self.assertEqual(card["holdout_dti"]["evidence_class"], "HOLDOUT-DTI")
        self.assertIn("not independently reproduced", card["holdout_dti"]["provenance"])
        self.assertLessEqual(len(card["note"]), 140)
        readme = (ROOT / "README.md").read_text()
        self.assertIn("PENDING-REVIEW", readme)
        self.assertIn("No submission note is authorized", readme)
        self.assertIn("literal registry", readme.lower())
        self.assertIn("NO FILE IS CLEARED TO SUBMIT", readme)


if __name__ == "__main__":
    unittest.main()
