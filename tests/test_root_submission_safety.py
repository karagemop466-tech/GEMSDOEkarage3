from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicRootSubmissionSafety(unittest.TestCase):
    def test_public_entry_pages_agree_with_negative_gate(self):
        gate = json.loads((ROOT / "docs/current-gate-decision.json").read_text())
        self.assertFalse(gate["ok_to_submit"])
        for name in ("index.html", "executive-summary.html"):
            page = (ROOT / name).read_text()
            with self.subTest(page=name):
                self.assertIn("DO NOT SUBMIT", page)
                self.assertIn("No score estimate", page) if name == "index.html" else self.assertIn("No defensible score estimate", page)
                self.assertNotIn("READY TO DOWNLOAD", page)
                self.assertNotIn("submission-ready", page.lower())
                self.assertNotIn("Target &gt; 0.2778", page)
        home = (ROOT / "index.html").read_text()
        summary = (ROOT / "executive-summary.html").read_text()
        self.assertIn("Archived TIFF for research only — do not submit", home)
        self.assertIn("Archived TIFF (do not submit)", summary)
        self.assertIn("NOT ESTABLISHED", summary)
        self.assertIn("no protocol-conforming holdout win", home)
        self.assertIn("complete literal registry uniqueness audit", home)


if __name__ == "__main__":
    unittest.main()
