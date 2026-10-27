#!/usr/bin/env python3
"""Read-only saved-byte GeoTIFF audit. Never writes, clips, or thresholds predictions.

This is an independent format audit, not a replacement for the shared submission writer or
holdout evaluator. A supplied template is not made authentic merely by passing this audit.
Outside-footprint nullness and whole-grid finiteness are reported separately because the
organizer wording and the reported upload error do not establish which encoding the portal
will accept. This tool does not authorize a weekly submission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from rasterio.crs import CRS


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(raster_path: Path, template_path: Path) -> dict:
    raster_path, template_path = Path(raster_path), Path(template_path)
    candidate_before = digest_file(raster_path)
    reference_before = digest_file(template_path)
    with rasterio.open(template_path) as template, rasterio.open(raster_path) as candidate:
        if template.count != 1 or template.crs is None:
            raise ValueError("reference must have one band and a CRS")
        ref_values = template.read(1)
        foot = np.isfinite(ref_values) & (template.read_masks(1) > 0)
        if not foot.any():
            raise ValueError("reference has an empty finite footprint")
        arr = candidate.read(1)
        same_shape = (candidate.height, candidate.width) == (template.height, template.width)
        same_crs = candidate.crs == template.crs
        same_transform = candidate.transform == template.transform
        # Size mismatch means there is no meaningful shared mask. Do not index with it.
        if not same_shape:
            raise ValueError("candidate shape does not match reference; cannot audit the footprint")
        valid_mask = candidate.read_masks(1) > 0
        finite = np.isfinite(arr)
        inf_count = int(np.count_nonzero(np.isinf(arr)))
        finite_out_of_range = finite & ((arr < 0) | (arr > 1))
        inside_nonfinite = int(np.count_nonzero(foot & ~finite))
        inside_masked = int(np.count_nonzero(foot & ~valid_mask))
        inside_out_of_range = int(np.count_nonzero(foot & finite_out_of_range))
        outside = ~foot
        outside_nonnull = int(np.count_nonzero(outside & valid_mask & ~np.isnan(arr)))
        finite_inside = arr[foot & finite]
        checks = {
            "single_band": candidate.count == 1,
            "float32": candidate.dtypes[0] == "float32",
            "reference_epsg_32611": template.crs == CRS.from_epsg(32611),
            "reference_100m_north_up": (template.transform.a == 100 and template.transform.b == 0
                                        and template.transform.d == 0 and template.transform.e == -100),
            "crs_match": same_crs,
            "shape_match": same_shape,
            "transform_match": same_transform,
            "finite_unmasked_inside": inside_nonfinite == 0 and inside_masked == 0,
            "range_0_1_inside": inside_out_of_range == 0,
            "no_inf_anywhere": inf_count == 0,
            # A finite nodata sentinel can trigger an organizer range error even when masked.
            "all_finite_values_in_0_1": not bool(finite_out_of_range.any()),
        }
        result = {
            "schema_version": 1,
            "kind": "READ-ONLY-FORMAT-AUDIT — not organizer acceptance or a release decision",
            "candidate": str(raster_path), "raster_sha256": candidate_before,
            "template": str(template_path), "template_sha256": reference_before,
            "template_authenticity": "NOT ESTABLISHED BY THIS TOOL",
            "shape": [candidate.height, candidate.width], "crs": str(candidate.crs),
            "transform": list(tuple(candidate.transform)[:6]), "dtype": candidate.dtypes[0],
            "inside_footprint_pixels": int(foot.sum()), "inside_nonfinite": inside_nonfinite,
            "inside_masked": inside_masked, "inside_out_of_range": inside_out_of_range,
            "inside_min": float(finite_inside.min()) if finite_inside.size else None,
            "inside_max": float(finite_inside.max()) if finite_inside.size else None,
            "inside_binary": bool(inside_nonfinite == 0 and np.all((arr[foot] == 0) | (arr[foot] == 1))),
            "nan_anywhere": int(np.count_nonzero(np.isnan(arr))), "inf_anywhere": inf_count,
            "finite_out_of_range_anywhere": int(np.count_nonzero(finite_out_of_range)),
            "outside_footprint_nonnull": outside_nonnull,
            "outside_footprint_all_null_or_nan": outside_nonnull == 0,
            "whole_grid_finite_and_in_range": bool(finite.all() and not finite_out_of_range.any()),
            "checks": checks,
        }
    # Bind findings to stable bytes; a file modified during inspection fails closed.
    checks["candidate_bytes_stable"] = digest_file(raster_path) == candidate_before
    checks["template_bytes_stable"] = digest_file(template_path) == reference_before
    result["core_checks_passed"] = all(checks.values())
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raster", type=Path)
    parser.add_argument("template", type=Path, help="Organizer template when available; mirror authenticity is not proven")
    parser.add_argument("--require-null-outside", action="store_true", help="Require null/NaN outside the reference footprint")
    parser.add_argument("--require-allfinite", action="store_true", help="Additionally require every grid cell finite and in [0,1]")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.raster, args.template)
        passed = report["core_checks_passed"]
        if args.require_null_outside:
            passed &= report["outside_footprint_all_null_or_nan"]
        if args.require_allfinite:
            passed &= report["whole_grid_finite_and_in_range"]
        report["requested_checks_passed"] = bool(passed)
        text = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text)
        print(text, end="")
        return 0 if passed else 2
    except (OSError, ValueError) as exc:
        print(f"Format audit failed closed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
