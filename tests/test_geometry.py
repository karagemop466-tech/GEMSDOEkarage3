import unittest
from fractions import Fraction
import numpy as np
from scripts.audit_registry import api_path, binary_spearman, dilate_disk, dot_bound


class GeometryTests(unittest.TestCase):
    def test_disk_has_29_cells_and_includes_distance_exactly_three(self):
        mask = np.zeros((9, 9), bool)
        mask[4, 4] = True
        result = dilate_disk(mask, 3)
        self.assertEqual(result.sum(), 29)
        self.assertTrue(result[4, 7])
        self.assertFalse(result[6, 7])

    def test_disk_does_not_wrap_at_image_edges(self):
        mask = np.zeros((5, 5), bool)
        mask[0, 0] = True
        result = dilate_disk(mask, 3)
        self.assertFalse(result[-1, -1])
        self.assertEqual(result.sum(), 11)
        np.testing.assert_array_equal(dilate_disk(mask, 0), mask)

    def test_disk_larger_than_small_image(self):
        mask = np.zeros((2, 2), bool)
        mask[0, 0] = True
        self.assertEqual(int(dilate_disk(mask, 3).sum()), 4)

    def test_binary_spearman_with_ties_and_constants(self):
        foot = np.ones((2, 3), bool)
        a = np.array([[1, 0, 1], [0, 0, 0]], bool)
        self.assertAlmostEqual(binary_spearman(a, a, foot), 1)
        self.assertAlmostEqual(binary_spearman(a, ~a, foot), -1)
        self.assertIsNone(binary_spearman(a, np.zeros_like(a), foot))
        # Ignored outside-footprint pixels cannot influence ranks.
        foot[0, 0] = False
        b = a.copy()
        b[0, 0] = False
        self.assertAlmostEqual(binary_spearman(a, b, foot), 1)

    def test_bound_70_percent_equal_allowed_more_is_stopped(self):
        self.assertFalse(dot_bound(10, 3)["duplicate_stop_proven"])
        self.assertTrue(dot_bound(11, 3)["duplicate_stop_proven"])
        self.assertEqual(dot_bound(3, 5)["minimum_overlap_fraction"], 0)
        r = dot_bound(37654, 6649)
        self.assertEqual(r["minimum_overlap_dots"], 31005)
        self.assertAlmostEqual(r["minimum_overlap_fraction"], float(Fraction(31005, 37654)))

    def test_bound_rejects_invalid_counts(self):
        for n, u in [(0, 1), (-1, 0), (2, -1), (True, 1), (1.5, 1)]:
            with self.subTest(n=n, u=u), self.assertRaises(ValueError):
                dot_bound(n, u)

    def test_api_path_accepts_only_immutable_github_blob(self):
        sha = 'a' * 40
        url = f'https://github.com/owner/repo/blob/{sha}/sub/file.tif'
        self.assertEqual(api_path(url), f'repos/owner/repo/contents/sub/file.tif?ref={sha}')
        for bad in ['https://example.com/o/r/blob/'+sha+'/f', 'https://github.com/o/r/blob/main/f']:
            with self.assertRaises(ValueError):
                api_path(bad)


if __name__ == '__main__':
    unittest.main()
