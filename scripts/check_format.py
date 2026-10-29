#!/usr/bin/env python3
"""Inspect exact saved bytes for grid/range/footprint problems. Never repairs data.

This is an independent diagnostic, NOT the shared submission writer, not a
holdout/novelty evaluator, and not authorization to spend a weekly slot.

Gate = the organizer's published submission-format rules (DrivenData GEMS problem
page, https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format):
single-layer float32 GeoTIFF, EPSG:32611, 100 m, same bounds as the training data,
values in [0,1] inside the bounds, and "data outside the bounds is null or nan".

Diagnostic only (NOT a gate): all_cell_finite_range. A previously reported portal
error "Predicted values must be in range [0, 1]" is UNEXPLAINED; no organizer
receipt links it to any file. Its cause is recorded as unverified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect(candidate: Path, template: Path) -> dict:
    """Return component-level tests, even on normal validation failures."""
    with rasterio.open(template) as ref:
        if ref.count != 1 or ref.dtypes[0] != "float32" or ref.crs is None:
            raise ValueError("Template must be a single-band float32 raster with a CRS")
        if len(ref.files) != 1:
            raise ValueError("Template depends on sidecar files; a single-file footprint cannot be verified")
        base = ref.read(1)
        foot = np.isfinite(base) & (ref.read_masks(1) > 0)
        if not foot.any():
            raise ValueError("Template footprint is empty")
        expected = (ref.shape, ref.crs, ref.transform)
        template_ok = (ref.crs == CRS.from_epsg(32611) and ref.transform.a == 100
                       and ref.transform.e == -100 and ref.transform.b == 0
                       and ref.transform.d == 0)
    with rasterio.open(candidate) as ds:
        grid_ok = (ds.shape, ds.crs, ds.transform) == expected
        checks = {
            "template_epsg32611_and_100m_unrotated": bool(template_ok),
            "geotiff": ds.driver == "GTiff",
            "self_contained_no_sidecars": len(ds.files) == 1,
            "single_band": ds.count == 1,
            "float32": ds.count == 1 and ds.dtypes[0] == "float32",
            "crs_shape_transform_match_template": grid_ok,
        }
        report = {"file": candidate.name, "sha256": digest(candidate),
                  "template_sha256": digest(template), "checks": checks,
                  "all_cell_finite_range_diagnostic": None, "outside_null_or_nan": None,
                  "inside_nonfinite": None, "inside_out_of_range": None,
                  "min_all_finite": None, "max_all_finite": None,
                  "format_gate_pass": False, "strict_format_gate_pass": False, "slot_approved": False,
                  "note": "Local format checks only; not an organizer receipt, novelty check, holdout, or slot approval."}
        if not grid_ok or ds.count != 1:
            return report
        values = ds.read(1, masked=False)
        valid_mask = ds.read_masks(1) > 0
        inside = values[foot]
        out = values[~foot]
        inside_finite = np.isfinite(inside)
        finite = np.isfinite(values)
        report["inside_nonfinite"] = int((~inside_finite).sum())
        report["inside_out_of_range"] = int((inside_finite & ((inside < 0) | (inside > 1))).sum())
        report["inside_masked_pixels"] = int((~valid_mask[foot]).sum())
        report["footprint_pixels"] = int(foot.sum())
        report["whole_array_pixels"] = int(values.size)
        report["whole_array_nonfinite"] = int((~finite).sum())
        report["whole_array_out_of_range_finite"] = int((finite & ((values < 0) | (values > 1))).sum())
        if finite.any():
            report["min_all_finite"] = float(values[finite].min())
            report["max_all_finite"] = float(values[finite].max())
        checks["inside_finite_and_in_range"] = bool(
            inside_finite.all() and np.all((inside >= 0) & (inside <= 1)))
        checks["inside_not_masked"] = bool(valid_mask[foot].all())
        checks["no_positive_outside_footprint"] = bool(np.all(~(np.isfinite(out) & (out > 0))))
        # Diagnostic only: not an official requirement (official rule allows null/NaN outside bounds).
        report["all_cell_finite_range_diagnostic"] = bool(finite.all() and np.all((values >= 0) & (values <= 1)))
        # Official rule: outside the bounds the value must be null or NaN. A dataset-mask null still has raw bytes.
        report["outside_null_or_nan"] = bool(np.all((~valid_mask[~foot]) | np.isnan(out)))
        checks["outside_null_or_nan"] = report["outside_null_or_nan"]
        report["format_gate_pass"] = all(checks.values())
        report["strict_format_gate_pass"] = report["format_gate_pass"]  # kept for back-compat with old receipts
        return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("candidate", type=Path)
    p.add_argument("--template", type=Path, required=True)
    p.add_argument("--out", type=Path, help="Write JSON report in addition to stdout")
    a = p.parse_args()
    try:
        report = inspect(a.candidate, a.template)
        text = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(text)
        print(text, end="")
        return 0 if report["format_gate_pass"] else 1
    except (OSError, ValueError, rasterio.errors.RasterioError) as e:
        print(f"FORMAT CHECK FAILED CLOSED: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
