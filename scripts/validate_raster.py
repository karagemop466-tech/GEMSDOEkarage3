#!/usr/bin/env python3
"""Audit exact saved GeoTIFF bytes against a template; never modify or authorize a file.

Two outside-footprint conventions are reported separately. The organizer's
wording and the reported portal range error leave actual acceptance unknown.
A local format result is NOT a scientific or weekly-slot authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(candidate: Path, template: Path) -> dict:
    candidate = Path(candidate)
    template = Path(template)
    with rasterio.open(template) as reference:
        if reference.count != 1 or reference.crs is None:
            raise ValueError("Template must contain one band and a CRS")
        ref_values = reference.read(1)
        footprint = (reference.read_masks(1) != 0) & np.isfinite(ref_values)
        if not footprint.any():
            raise ValueError("Template footprint is empty")
        ref_shape, ref_crs, ref_transform = reference.shape, reference.crs, reference.transform
    with rasterio.open(candidate) as ds:
        basic = {
            "single_band": ds.count == 1,
            "float32": ds.count == 1 and ds.dtypes[0] == "float32",
            "shape_matches": ds.shape == ref_shape,
            "crs_matches": ds.crs == ref_crs,
            "transform_matches": ds.transform == ref_transform,
        }
        # Do not interpret unsupported dtypes, bands or mismatched grids as probabilities.
        if not all(basic.values()):
            return {"candidate": str(candidate), "candidate_sha256": sha256(candidate),
                    "template_sha256": sha256(template), "checks": basic, "core_format_pass": False,
                    "outside_template_null_pass": None, "whole_array_finite_range_pass": None,
                    "organizer_acceptance": "unknown", "authorization": "NOT AUTHORIZED"}
        arr = ds.read(1, masked=False)
        valid_mask = ds.read_masks(1) != 0
        inner = arr[footprint]
        finite = np.isfinite(inner)
        basic["inside_all_finite"] = bool(finite.all())
        basic["inside_range_0_1"] = bool(finite.all() and (inner >= 0).all() and (inner <= 1).all())
        basic["inside_not_nodata_or_masked"] = bool(valid_mask[footprint].all())
        # A NaN or an explicitly masked/nodata pixel outside is considered null.
        outside = arr[~footprint]
        outside_mask = valid_mask[~footprint]
        null_outside = bool((np.isnan(outside) | ~outside_mask).all())
        # Check raw values (not a masked read) so numeric sentinels cannot disappear.
        whole_finite_range = bool(np.isfinite(arr).all() and (arr >= 0).all() and (arr <= 1).all())
        return {
            "candidate": str(candidate), "candidate_sha256": sha256(candidate),
            "template": str(template), "template_sha256": sha256(template),
            "checks": basic, "core_format_pass": all(basic.values()),
            "inside_nonfinite_count": int((~finite).sum()),
            "inside_masked_count": int((~valid_mask[footprint]).sum()),
            "inside_min": float(inner.min()) if finite.all() and inner.size else None,
            "inside_max": float(inner.max()) if finite.all() and inner.size else None,
            "outside_template_null_pass": null_outside,
            "whole_array_finite_range_pass": whole_finite_range,
            "outside_policy_note": "Template-footprint null interpretation and all-finite diagnostic are separate; neither proves portal acceptance.",
            "organizer_acceptance": "unknown", "authorization": "NOT AUTHORIZED",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--template", type=Path, required=True, help="Organizer template or explicitly identified mirror")
    parser.add_argument("--require", choices=("core", "template-null", "whole-array"), default="template-null",
                        help="Local exit-code policy, not authorization (default: conservative template-null)")
    args = parser.parse_args()
    try:
        result = audit(args.candidate, args.template)
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        result = {"candidate": str(args.candidate), "template": str(args.template),
                  "error": str(exc), "core_format_pass": False,
                  "organizer_acceptance": "unknown", "authorization": "NOT AUTHORIZED"}
        print(json.dumps(result, indent=2, allow_nan=False))
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    passed = result["core_format_pass"]
    if args.require == "template-null":
        passed = passed and result["outside_template_null_pass"] is True
    elif args.require == "whole-array":
        passed = passed and result["whole_array_finite_range_pass"] is True
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
