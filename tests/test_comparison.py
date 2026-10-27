import hashlib
import json
from pathlib import Path
import unittest

from scripts.build_comparison import enrich

ROOT = Path(__file__).resolve().parents[1]

class EvidenceTests(unittest.TestCase):
    def test_recovered_source_hashes(self):
        for entry in json.loads((ROOT/'evidence/upstream/recovered-manifest.json').read_text()):
            self.assertEqual(hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest(), entry['sha256'])

    def test_comparison_rebuild_is_stable(self):
        stored=json.loads((ROOT/'docs/sites.json').read_text())['sites']
        upstream=json.loads((ROOT/'evidence/upstream/GEMSDOE32/evidence/arena48_focus9_overlap.json').read_text())
        self.assertEqual(enrich(json.loads(json.dumps(stored)),upstream),stored)
        self.assertEqual(len(stored),9)
        for row in stored:
            self.assertFalse(row['ok_to_submit'])
            self.assertIsNone(row['estimated_score'])
            self.assertFalse(row['historical_artifact']['locally_validated'])

    def test_local_report_scope_and_pairs(self):
        report=json.loads((ROOT/'docs/historical-raster-audit.json').read_text())
        self.assertEqual(len(report['rasters']),9)
        self.assertEqual(len(report['pairwise']),72)
        self.assertFalse(report['official_template_available'])
        self.assertFalse(report['complete_registry_checked'])
        self.assertFalse(report['new_submission_generated'])
        for pair in report['pairwise']:
            self.assertGreater(pair['candidate_fraction_within_3px'],.7)
