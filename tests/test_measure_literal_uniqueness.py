"""Regression checks for the literal uniqueness measurement (no raster data needed)."""
import unittest

import numpy as np
from scipy.spatial import cKDTree

from scripts.audit_registry import binary_spearman
from scripts.measure_literal_uniqueness import RADIUS, phi


class MeasureLiteralUniquenessTests(unittest.TestCase):
    def test_phi_matches_shared_binary_spearman(self):
        rng = np.random.default_rng(7)
        foot = np.ones((50, 60), bool)
        a = rng.random(foot.shape) < 0.05
        b = rng.random(foot.shape) < 0.07
        n, x, y = int(foot.sum()), int(a.sum()), int(b.sum())
        both = int((a & b).sum())
        self.assertAlmostEqual(phi(n, x, y, both), binary_spearman(a, b, foot), places=12)

    def test_three_px_rule_is_inclusive_euclidean(self):
        self.assertEqual(RADIUS, 3.0)
        reg = np.array([[10.0, 10.0]])
        cand = np.array([[10.0, 13.0],   # exactly 3 px away: counts (inclusive)
                         [10.0, 13.5],   # 3.5 px: does not count
                         [13.0, 13.0]])  # diagonal, 4.24 px: does not count
        dist, _ = cKDTree(reg).query(cand, k=1, distance_upper_bound=RADIUS + 1e-9)
        self.assertEqual(int(np.sum(dist <= RADIUS)), 1)


if __name__ == "__main__":
    unittest.main()
