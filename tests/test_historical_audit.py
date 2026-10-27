import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.audit_historical_rasters import ROOT, SNAPSHOT, binary_rank_correlation, canonical_validator, restore


class IntegrityTests(unittest.TestCase):
    def test_upstream_snapshots_unchanged(self):
        for row in json.loads((SNAPSHOT / 'manifest.json').read_text()):
            data = (SNAPSHOT / row['path']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), row['sha256'], row['path'])

    def test_public_json_is_strict_and_source_hashes_match(self):
        def reject_constant(value):
            raise ValueError(f'Non-JSON constant: {value}')
        for path in (ROOT / 'docs').glob('*.json'):
            json.loads(path.read_text(), parse_constant=reject_constant)
        for site in json.loads((ROOT / 'docs/sites.json').read_text())['sites']:
            for source in site.get('sources', []):
                data = (ROOT / source['local']).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), source['sha256'])

    def test_unsafe_fetch_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in ['../escape', '/absolute', 'file?ref=main']:
                with self.subTest(path=path), self.assertRaises(ValueError):
                    restore(dict(repo='org/repo', ref='a' * 40, path=path, dest='x'), Path(directory))

    def test_corrupt_download_not_published(self):
        def fake_run(command, stdout, **kwargs):
            stdout.write(b'bad')
        with tempfile.TemporaryDirectory() as directory, patch('subprocess.run', fake_run):
            row = dict(id='test', repo='org/repo', ref='a' * 40, path='x', dest='x',
                       bytes=3, sha256='a' * 64)
            with self.assertRaises(ValueError):
                restore(row, Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_historical_receipt_is_not_release(self):
        result = json.loads((ROOT / 'docs/historical-audit.json').read_text())
        self.assertFalse(result['ok_to_submit'])
        self.assertFalse(result['complete_registry'])
        self.assertFalse(result['continuous_surfaces_checked'])
        self.assertEqual(result['experiments_run'], 0)
        self.assertTrue(result['champion_autopsy']['exact_base_pruned_within_2px'])
        self.assertEqual(len(result['rasters']), 10)
        for row in result['rasters']:
            self.assertFalse(row['ok_to_submit'])
            self.assertFalse(row['unique'])
            self.assertGreater(row['partial_registry']['max_overlap_3px'], .7)


class NumericalTests(unittest.TestCase):
    def test_binary_spearman_matches_scipy_tied_ranks(self):
        import numpy as np
        from scipy.stats import spearmanr
        rng = np.random.default_rng(17)
        for _ in range(10):
            a, b = rng.random(100) > .7, rng.random(100) > .8
            self.assertAlmostEqual(binary_rank_correlation(a, b), spearmanr(a, b).statistic)
        self.assertIsNone(binary_rank_correlation([0, 0], [1, 0]))
        with self.assertRaises(ValueError):
            binary_rank_correlation([], [])

    def test_canonical_validator_rejects_saved_range_errors(self):
        import numpy as np
        import rasterio
        validator = canonical_validator()
        shape = (3730, 3292)
        foot = np.zeros(shape, dtype=bool)
        foot.flat[:5167373] = True
        labels = np.zeros(shape, dtype=bool)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic-format-fixture.tif'
            with rasterio.open(path, 'w', driver='GTiff', width=shape[1], height=shape[0], count=1,
                               dtype='float32', crs='EPSG:32611', compress='deflate',
                               transform=rasterio.transform.from_origin(243350, 4508550, 100, 100)) as ds:
                ds.write(np.zeros(shape, dtype='float32'), 1)
            self.assertTrue(validator(path, foot, labels)['all_checks_passed'])
            for value in [-3.4028235e38, -0.1, 1.01, float('nan'), float('inf')]:
                with self.subTest(value=value):
                    with rasterio.open(path, 'r+') as ds:
                        ds.write(np.array([[value]], dtype='float32'), 1,
                                 window=rasterio.windows.Window(0, 0, 1, 1))
                    with self.assertRaises(ValueError):
                        validator(path, foot, labels)


if __name__ == '__main__':
    unittest.main()
