"""Regression tests for the 2026-10-31 executive summary, run cards and quarantine.

These guard claims made on the executive summary. They do not establish that any file
is good: they check that nothing is cleared, that the receipts exist, and that the
generated pages say what the receipts say.
"""
import glob
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_KEYS = ('H1', 'H2', 'H1X')
CANDIDATE_DIRS = ('colocation-h1', 'strain-signchange-h2', 'colocation-h1-expanded')
NINE = ('24', '25', '27', '28', '30', '31', '32', '33', '36')


class ExecutiveSummaryTests(unittest.TestCase):
    def test_summary_banner_says_no_and_names_all_nine_sites(self):
        page = (ROOT / 'docs/executive-summary-20261031.html').read_text()
        self.assertIn('Download and submit? <b>NO. No file in this session is cleared.</b>', page)
        for n in NINE:
            self.assertIn(f'GEMSDOE{n}', page, n)
        self.assertIn('0.4544', page)
        self.assertIn('0.3195', page)

    def test_summary_labels_every_number_source(self):
        page = (ROOT / 'docs/executive-summary-20261031.html').read_text()
        for label in ('USER-REPORTED', 'HOLDOUT-DTI', 'PROJECTION'):
            self.assertIn(label, page)

    def test_landing_page_links_summary_prominently(self):
        index = (ROOT / 'index.html').read_text()
        self.assertIn('docs/executive-summary-20261031.html', index)
        self.assertLess(index.index('docs/executive-summary-20261031.html'), index.index('<aside'))
        self.assertIn('DO NOT SUBMIT', index)

    def test_submission_guide_is_blocked(self):
        guide = (ROOT / 'docs/submission-20261031.html').read_text()
        self.assertIn('Status: BLOCKED', guide)
        self.assertIn('promotion_gate.py', guide)


class RunCardTests(unittest.TestCase):
    def test_session_card_is_negative_with_no_slot(self):
        card = json.loads((ROOT / 'evidence/run-card-20261031.json').read_text())
        self.assertEqual(card['verdict'], 'negative')
        self.assertIs(card['ok_to_submit_any_file'], False)
        self.assertEqual(card['weekly_slots_used'], 0)
        self.assertIs(card['slot_selected'], False)
        self.assertLessEqual(card['experiments_run'], card['experiments_limit'])

    def test_each_candidate_card_is_negative_and_gate_agrees(self):
        for key in CANDIDATE_KEYS:
            card = json.loads((ROOT / f'evidence/run-cards-20261031/{key}.json').read_text())
            gate = json.loads((ROOT / f'evidence/run-cards-20261031/{key}.gate.json').read_text())
            self.assertEqual(card['verdict'], 'negative', key)
            self.assertIs(card['ok_to_submit'], False, key)
            self.assertEqual(gate['verdict'], 'negative', key)
            self.assertIs(gate['ok_to_submit'], False, key)
            self.assertTrue(gate['reasons'], key)
            self.assertLessEqual(len(card['note']), 140, key)
            self.assertTrue(card['submission_name'].endswith('.tif'), key)
            self.assertRegex(card['raster_sha256'], r'^[0-9a-f]{64}$', key)

    def test_candidate_cards_report_lattice_duplicate_not_pass(self):
        for key in CANDIDATE_KEYS:
            gate = json.loads((ROOT / f'evidence/run-cards-20261031/{key}.gate.json').read_text())
            self.assertTrue(any('above 0.70' in r for r in gate['reasons']), key)


class QuarantineTests(unittest.TestCase):
    def test_candidates_are_quarantined_not_downloads(self):
        for d in CANDIDATE_DIRS:
            folder = ROOT / 'docs/quarantine' / d
            self.assertTrue((folder / 'NOT-CLEARED.md').is_file(), d)
            self.assertTrue(list(folder.glob('*-nan.tif')), d)
        downloads = {p.name for p in (ROOT / 'docs/downloads').glob('*.tif')}
        for d in CANDIDATE_DIRS:
            for p in (ROOT / 'docs/quarantine' / d).glob('*.tif'):
                self.assertNotIn(p.name, downloads)

    def test_prior_zeros_quarantine_files_still_present(self):
        # Regression guard: a bad cleanup once deleted these tracked files. Restored from git.
        expected = [
            'docs/quarantine/blind-conduit-stepper-zeros/gemsdoe32-karage3-blind-conduit-stepper-v1-20261031T000000Z-e71280c6-zeros.tif',
            'docs/quarantine/geoconduit-hybrid/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif',
            'docs/quarantine/h1-seismic-gravity-basin/gemsdoe32-karage3-h1-seismic-gravity-basin-20261029T182309Z-91540319-zeros.tif',
            'docs/quarantine/k8d-scarponly/gemsdoe32-karage3-k8d-scarponly-n44k-20261031T010414Z-857c3fc6-zeros.tif',
            'docs/quarantine/karage3-unique-offcat/karage3-unique-offcat-20261029T180337Z-6a8c2368-zeros.tif',
        ]
        for rel in expected:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_saved_byte_receipts_cover_every_docs_tiff(self):
        disk = {str(Path(p).relative_to(ROOT)) for p in glob.glob(str(ROOT / 'docs/**/*.tif'), recursive=True)}
        for rel in ('evidence/saved-tiffs-literal-20261028.json', 'evidence/saved-tiffs-literal-20261030.json'):
            rows = {r['file'] for r in json.loads((ROOT / rel).read_text())['rasters']}
            self.assertEqual(rows, disk, rel)


if __name__ == '__main__':
    unittest.main()
