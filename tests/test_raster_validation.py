from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.validate_raster import audit, sha256


def write(path: Path, array, *, nodata=None, transform=None, dtype="float32", crs="EPSG:32611"):
    array = np.asarray(array, dtype=dtype)
    if array.ndim == 2:
        array = array[None, ...]
    with rasterio.open(path, "w", driver="GTiff", width=array.shape[2], height=array.shape[1],
                       count=array.shape[0], dtype=dtype, nodata=nodata, crs=crs,
                       transform=transform or from_origin(243350, 4508550, 100, 100)) as ds:
        ds.write(array)
    return path


@pytest.fixture
def template(tmp_path):
    return write(tmp_path / "template.tif", [[0, 0, np.nan], [0, 0, np.nan]], nodata=np.nan)


def test_probs_preserved_and_no_mutation(tmp_path, template):
    path = write(tmp_path / "out.tif", [[0.2, 0.8, np.nan], [0, 1, np.nan]], nodata=np.nan)
    before = sha256(path)
    result = audit(path, template)
    assert result["core_format_pass"] and result["outside_template_null_pass"]
    assert not result["whole_array_finite_range_pass"]
    assert result["inside_min"] == 0 and result["inside_max"] == 1
    assert result["authorization"] == "NOT AUTHORIZED"
    assert before == sha256(path)
    with rasterio.open(path) as ds:
        assert ds.read(1)[0, :2] == pytest.approx([0.2, 0.8])


@pytest.mark.parametrize("bad", [-0.001, 1.001, np.nan, np.inf, -3.402823466e38])
def test_bad_values_inside_cannot_pass(tmp_path, template, bad):
    path = write(tmp_path / "bad.tif", [[bad, 0, np.nan], [0, 1, np.nan]], nodata=np.nan)
    result = audit(path, template)
    assert result["core_format_pass"] is False
    assert result["checks"]["inside_range_0_1"] is False


def test_nodata_metadata_cannot_hide_inside_pixels(tmp_path, template):
    path = write(tmp_path / "badnodata.tif", [[0, 0.3, 0], [0, 1, 0]], nodata=0)
    result = audit(path, template)
    assert result["checks"]["inside_all_finite"] is True
    assert result["checks"]["inside_not_nodata_or_masked"] is False
    assert result["core_format_pass"] is False


def test_zero_outside_is_a_separate_whole_array_diagnostic(tmp_path, template):
    path = write(tmp_path / "zeros.tif", [[0.2, 0.8, 0], [0, 1, 0]])
    result = audit(path, template)
    assert result["core_format_pass"] is True
    assert result["whole_array_finite_range_pass"] is True
    assert result["outside_template_null_pass"] is False
    assert result["organizer_acceptance"] == "unknown"


def test_reject_transform_dtype_and_multiband(tmp_path, template):
    bad_transform = write(tmp_path / "transform.tif", [[0, 0, 0], [0, 0, 0]],
                          transform=from_origin(243351, 4508550, 100, 100))
    assert not audit(bad_transform, template)["checks"]["transform_matches"]
    bad_dtype = write(tmp_path / "dtype.tif", [[0, 0, 0], [0, 0, 0]], dtype="float64")
    assert not audit(bad_dtype, template)["checks"]["float32"]
    bad_bands = write(tmp_path / "bands.tif", np.zeros((2, 2, 3)))
    assert not audit(bad_bands, template)["checks"]["single_band"]


def test_reject_shape_and_crs(tmp_path, template):
    shape = write(tmp_path / "shape.tif", np.zeros((3, 3)))
    assert not audit(shape, template)["core_format_pass"]
    crs = write(tmp_path / "crs.tif", np.zeros((2, 3)), crs="EPSG:4326")
    assert not audit(crs, template)["checks"]["crs_matches"]


def test_unsupported_complex_values_fail_closed(tmp_path, template):
    candidate = write(tmp_path / "complex.tif", [[0, 0, 0], [0, 0, 0]], dtype="complex64")
    result = audit(candidate, template)
    assert result["checks"]["float32"] is False
    assert result["core_format_pass"] is False
    assert result["outside_template_null_pass"] is None


def test_cli_reports_missing_inputs_as_json(tmp_path, template):
    import json
    import subprocess
    import sys

    command = [sys.executable, "scripts/validate_raster.py", str(tmp_path / "missing.tif"),
               "--template", str(template)]
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    result = json.loads(proc.stdout)
    assert result["core_format_pass"] is False
    assert result["authorization"] == "NOT AUTHORIZED"
    assert result["error"]
