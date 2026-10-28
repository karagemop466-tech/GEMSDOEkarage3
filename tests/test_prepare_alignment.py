"""Guard against silently combining geospatially misaligned labels and features."""
import unittest
from types import SimpleNamespace
from rasterio.crs import CRS
from rasterio.transform import from_origin
from scripts.prepare_data import require_aligned_grid


class PrepareAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.crs = CRS.from_epsg(32611)
        self.transform = from_origin(100, 400, 100, 100)
        self.dataset = SimpleNamespace(crs=self.crs, height=4, width=5,
                                       transform=self.transform)

    def check(self):
        require_aligned_grid(self.dataset, self.crs, (4, 5), self.transform, 'input')

    def test_aligned(self):
        self.check()

    def test_same_shape_different_crs_fails(self):
        self.dataset.crs = CRS.from_epsg(32612)
        with self.assertRaisesRegex(ValueError, 'CRS mismatch'):
            self.check()

    def test_same_shape_shifted_transform_fails(self):
        self.dataset.transform = from_origin(200, 400, 100, 100)
        with self.assertRaisesRegex(ValueError, 'transform mismatch'):
            self.check()

    def test_different_shape_fails(self):
        self.dataset.width = 4
        with self.assertRaisesRegex(ValueError, 'shape mismatch'):
            self.check()
