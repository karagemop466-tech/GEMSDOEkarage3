import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation

from scripts.audit_priority_rasters import PRIORITY, budget_bound, disk, fetch_input

ROOT = Path(__file__).resolve().parents[1]


class PriorityAuditTests(unittest.TestCase):
    def test_disk_includes_euclidean_boundary_only(self):
        seed = np.zeros((9, 9), dtype=bool)
        seed[4, 4] = True
        cover = binary_dilation(seed, structure=disk(3))
        self.assertTrue(cover[4, 7])
        self.assertTrue(cover[6, 6])
        self.assertFalse(cover[7, 7])
        self.assertEqual(int(cover.sum()), 29)

    def test_counting_bound_and_exact_70_percent(self):
        self.assertFalse(budget_bound(3, 10)['necessarily_exceeds_70_percent'])
        self.assertTrue(budget_bound(2, 10)['necessarily_exceeds_70_percent'])
        self.assertEqual(budget_bound(20, 10)['minimum_overlap_count'], 0)
        with self.assertRaises(ValueError):
            budget_bound(0, 0)
        with self.assertRaises(ValueError):
            budget_bound(-1, 10)

    def test_offline_corrupt_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'x.tif'
            path.write_bytes(b'not authentic')
            item = {'id': 'x', 'bytes': path.stat().st_size, 'sha256': '0' * 64}
            with self.assertRaises(ValueError):
                fetch_input(item, Path(tmp), offline=True)

    def test_published_report_is_consistent_and_does_not_claim_full_registry(self):
        manifest = json.loads((ROOT / 'evidence/priority_inputs.json').read_text())
        report = json.loads((ROOT / 'docs/priority-audit.json').read_text())
        inputs = {x['id']: x for x in manifest['files']}
        rows = {x['site'].replace('GEMSDOE', ''): x for x in report['historical_rasters']}
        self.assertEqual(set(rows), set(PRIORITY))
        for key in PRIORITY:
            self.assertEqual(rows[key]['file_sha256'], inputs[key]['sha256'])
            self.assertFalse(rows[key]['unique_vs_other_eight_historical_masks'])
        self.assertEqual(len(report['directional_comparisons']), 72)
        self.assertTrue(all(x['exceeds_70_percent'] for x in report['directional_comparisons']))
        lattice = report['lattice']
        self.assertEqual(lattice['sha256'], inputs['lattice']['sha256'])
        self.assertEqual(lattice['counting_bound'], budget_bound(lattice['uncovered_footprint_pixels'], 37654))
        self.assertTrue(lattice['counting_bound']['necessarily_exceeds_70_percent'])
        self.assertIn('not a full registry', report['scope'])
        self.assertTrue(report['lineage']['25_and_30_in_footprint_masks_identical'])
        self.assertTrue(report['lineage']['32_equals_31_after_2px_catalogue_collar'])


if __name__ == '__main__':
    unittest.main()
