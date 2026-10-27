import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts.validate_geotiff import validate


class GeoTiffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.template = self.root / 'template.tif'
        self.candidate = self.root / 'candidate.tif'
        self.ref = np.zeros((4, 5), dtype='float32')
        self.ref[0, 0] = np.nan
        self.write(self.template, self.ref, nodata=np.nan)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, array, *, nodata=None, transform=None, crs='EPSG:32611', dtype='float32', count=1):
        profile = dict(driver='GTiff', height=array.shape[0], width=array.shape[1], count=count,
                       dtype=dtype, crs=crs, transform=transform or from_origin(1000, 2000, 100, 100),
                       nodata=nodata)
        with rasterio.open(path, 'w', **profile) as dst:
            for n in range(1, count + 1):
                dst.write(array.astype(dtype), n)

    def test_probabilities_not_binarized_and_allfinite_diagnostic(self):
        arr = np.zeros((4, 5), dtype='float32')
        arr[2, 2] = .375
        self.write(self.candidate, arr)
        r = validate(self.candidate, self.template)
        self.assertTrue(r['core_checks_passed'])
        self.assertFalse(r['inside_binary'])
        self.assertTrue(r['whole_grid_finite_and_in_range'])
        self.assertFalse(r['outside_footprint_all_null_or_nan'])
        self.assertAlmostEqual(r['inside_max'], .375)
        self.assertEqual(r['template_authenticity'], 'NOT ESTABLISHED BY THIS TOOL')

    def test_nan_outside_not_confused_with_nan_inside(self):
        arr = self.ref.copy()
        arr[2, 2] = 1
        self.write(self.candidate, arr, nodata=np.nan)
        r = validate(self.candidate, self.template)
        self.assertTrue(r['core_checks_passed'])
        self.assertTrue(r['inside_binary'])
        self.assertTrue(r['outside_footprint_all_null_or_nan'])
        self.assertFalse(r['whole_grid_finite_and_in_range'])
        arr[1, 1] = np.nan
        self.write(self.candidate, arr, nodata=np.nan)
        self.assertFalse(validate(self.candidate, self.template)['core_checks_passed'])

    def test_allfinite_policy_detects_an_outside_mask(self):
        arr = np.zeros((4, 5), dtype='float32')
        self.write(self.candidate, arr)
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
            with rasterio.open(self.candidate, 'r+') as dst:
                mask = np.full((4, 5), 255, dtype='uint8')
                mask[0, 0] = 0
                dst.write_mask(mask)
        r = validate(self.candidate, self.template)
        self.assertTrue(r['core_checks_passed'])
        self.assertTrue(r['whole_grid_finite_and_in_range'])
        self.assertFalse(r['whole_grid_unmasked'])
        self.assertTrue(r['outside_footprint_all_null_or_nan'])

    def test_external_mask_sidecar_is_rejected(self):
        arr = np.zeros((4, 5), dtype='float32')
        self.write(self.candidate, arr)
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
            with rasterio.open(self.candidate, 'r+') as dst:
                mask = np.full((4, 5), 255, dtype='uint8')
                mask[0, 0] = 0
                dst.write_mask(mask)
        self.assertTrue(Path(str(self.candidate) + '.msk').exists())
        result = validate(self.candidate, self.template)
        self.assertFalse(result['checks']['candidate_single_file'])
        self.assertFalse(result['core_checks_passed'])

    def test_external_template_mask_sidecar_is_rejected(self):
        self.write(self.candidate, np.zeros((4, 5), dtype='float32'))
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
            with rasterio.open(self.template, 'r+') as dst:
                mask = np.full((4, 5), 255, dtype='uint8')
                mask[0, 0] = 0
                dst.write_mask(mask)
        result = validate(self.candidate, self.template)
        self.assertFalse(result['checks']['template_single_file'])
        self.assertFalse(result['core_checks_passed'])

    def test_numeric_sentinel_outside_is_detected_even_when_masked(self):
        arr = np.zeros((4, 5), dtype='float32')
        arr[0, 0] = -9999
        self.write(self.candidate, arr, nodata=-9999)
        r = validate(self.candidate, self.template)
        self.assertTrue(r['outside_footprint_all_null_or_nan'])
        self.assertEqual(r['finite_out_of_range_anywhere'], 1)
        self.assertFalse(r['core_checks_passed'])

    def test_out_of_range_infinity_dtype_band_count_transform_and_crs(self):
        for kind in ('negative', 'overone', 'inf', 'dtype', 'bands', 'transform', 'crs'):
            with self.subTest(kind=kind):
                arr = np.zeros((4, 5), dtype='float32')
                kwargs = {}
                if kind == 'negative': arr[2, 1] = -.01
                if kind == 'overone': arr[2, 1] = 1.01
                if kind == 'inf': arr[2, 1] = np.inf
                if kind == 'dtype': kwargs['dtype'] = 'float64'
                if kind == 'bands': kwargs['count'] = 2
                if kind == 'transform': kwargs['transform'] = from_origin(1001, 2000, 100, 100)
                if kind == 'crs': kwargs['crs'] = 'EPSG:4326'
                self.write(self.candidate, arr, **kwargs)
                self.assertFalse(validate(self.candidate, self.template)['core_checks_passed'])

    def test_shape_mismatch_fails_closed(self):
        self.write(self.candidate, np.zeros((2, 3), dtype='float32'))
        with self.assertRaises(ValueError):
            validate(self.candidate, self.template)


if __name__ == '__main__':
    unittest.main()
