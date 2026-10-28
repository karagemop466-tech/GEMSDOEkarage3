import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from scripts.check_format import inspect


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.transform = from_origin(100, 400, 100, 100)
        self.sample = self.root / 'sample.tif'
        self.data = np.zeros((4, 4), dtype=np.float32)
        self.data[0, 0] = np.nan  # outside the footprint
        self.write(self.sample, self.data, nodata=np.nan)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, array, *, nodata=None, mask=None, internal=True, transform=None, dtype='float32'):
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=internal):
            with rasterio.open(path, 'w', driver='GTiff', height=4, width=4, count=1, dtype=dtype,
                               crs='EPSG:32611', transform=transform or self.transform, nodata=nodata) as dst:
                dst.write(array.astype(dtype), 1)
                if mask is not None:
                    dst.write_mask(mask)

    def test_raw_finite_with_internal_null_mask_can_pass_local_checks(self):
        candidate = self.root / 'prediction.tif'
        values = np.zeros((4, 4), np.float32)
        values[2, 2] = 0.4
        mask = np.full((4, 4), 255, np.uint8)
        mask[0, 0] = 0
        self.write(candidate, values, mask=mask)
        result = inspect(candidate, self.sample)
        self.assertTrue(result['strict_format_gate_pass'])
        self.assertTrue(result['all_cell_finite_range'])
        self.assertTrue(result['outside_null_or_nan'])
        self.assertFalse(result['slot_approved'])

    def test_zero_outside_is_not_explicitly_null(self):
        p = self.root / 'zero-outside.tif'
        self.write(p, np.zeros((4, 4), np.float32))
        result = inspect(p, self.sample)
        self.assertTrue(result['all_cell_finite_range'])
        self.assertFalse(result['outside_null_or_nan'])
        self.assertFalse(result['strict_format_gate_pass'])

    def test_nan_outside_may_fail_full_array_range_check(self):
        p = self.root / 'nan-outside.tif'
        self.write(p, self.data, nodata=np.nan)
        result = inspect(p, self.sample)
        self.assertTrue(result['outside_null_or_nan'])
        self.assertFalse(result['all_cell_finite_range'])
        self.assertEqual(result['inside_nonfinite'], 0)
        self.assertFalse(result['strict_format_gate_pass'])

    def test_bad_inside_values_are_not_repaired(self):
        for bad in (np.nan, np.inf, -1., 1.1, -3.4e38):
            with self.subTest(bad=bad):
                values = np.zeros((4, 4), np.float32)
                values[1, 1] = bad
                p = self.root / 'bad.tif'
                self.write(p, values)
                result = inspect(p, self.sample)
                self.assertFalse(result['checks']['inside_finite_and_in_range'])
                self.assertFalse(result['strict_format_gate_pass'])
                with rasterio.open(p) as ds:
                    actual = ds.read(1)[1, 1]
                self.assertTrue(np.isnan(actual) if np.isnan(bad) else actual == np.float32(bad))

    def test_grid_mismatch_fails_closed(self):
        p = self.root / 'mismatch.tif'
        self.write(p, np.zeros((4, 4), np.float32), transform=from_origin(200, 400, 100, 100))
        result = inspect(p, self.sample)
        self.assertFalse(result['checks']['crs_shape_transform_match_template'])
        self.assertFalse(result['strict_format_gate_pass'])
        self.assertIsNone(result['inside_nonfinite'])

    def test_external_mask_sidecar_is_not_a_portable_single_tiff(self):
        p = self.root / 'external.tif'
        mask = np.full((4, 4), 255, np.uint8)
        mask[0, 0] = 0
        self.write(p, np.zeros((4, 4), np.float32), mask=mask, internal=False)
        result = inspect(p, self.sample)
        self.assertFalse(result['checks']['self_contained_no_sidecars'])
        self.assertFalse(result['strict_format_gate_pass'])

    def test_masked_inside_cannot_be_hidden_as_valid(self):
        p = self.root / 'masked-inside.tif'
        mask = np.full((4, 4), 255, np.uint8)
        mask[0, 0] = 0
        mask[1, 1] = 0
        self.write(p, np.zeros((4, 4), np.float32), mask=mask)
        result = inspect(p, self.sample)
        self.assertFalse(result['checks']['inside_not_masked'])
        self.assertEqual(result['inside_masked_pixels'], 1)


if __name__ == '__main__':
    unittest.main()
