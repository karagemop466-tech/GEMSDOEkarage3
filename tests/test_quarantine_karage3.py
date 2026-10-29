"""Regression guard: the quarantined karage3 file must never again be offered as ready."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
QUAR = ROOT / 'docs/quarantine/karage3-unique-offcat'
STALE_PHRASES = ('READY TO DOWNLOAD', 'UNIQUE · DOWNLOADABLE', 'NEW UNIQUE SUBMISSION AVAILABLE FOR DOWNLOAD',
                 'LOCALLY VALIDATED · NOT YET SUBMITTED')


def public_html():
    for path in sorted(ROOT.rglob('*.html')):
        if '.venv' in path.parts or 'vendor' in path.parts or '.git' in path.parts:
            continue
        yield path


class QuarantineTests(unittest.TestCase):
    def test_quarantined_files_exist_and_are_not_in_downloads(self):
        self.assertTrue((QUAR / 'NOT-CLEARED.md').is_file())
        self.assertEqual(sorted(p.name for p in (ROOT / 'docs/downloads').glob('karage3-unique-offcat*')), [])
        self.assertGreaterEqual(len(list(QUAR.glob('*.tif'))), 2)

    def test_no_page_links_to_quarantined_file_as_download(self):
        for path in public_html():
            text = path.read_text(encoding='utf-8', errors='replace')
            self.assertNotIn('docs/downloads/karage3-unique-offcat', text, str(path))

    def test_no_page_claims_the_karage3_file_is_ready(self):
        for path in public_html():
            text = path.read_text(encoding='utf-8', errors='replace')
            for phrase in STALE_PHRASES:
                self.assertNotIn(phrase, text, f'{path}: {phrase}')

    def test_notice_states_measured_overlap(self):
        notice = (QUAR / 'NOT-CLEARED.md').read_text()
        self.assertIn('99.89%', notice)
        self.assertIn('4,517', notice)
        self.assertIn('Verdict: **negative**', notice)
        self.assertIsNotNone(re.search(r'b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2', notice))


if __name__ == '__main__':
    unittest.main()
