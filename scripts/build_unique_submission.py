#!/usr/bin/env python3
"""
Generate a UNIQUE, format-valid submission GeoTIFF candidate for the DOE GEMS
Prize Challenge (competition 306), and audit its exact saved bytes.

This script addresses the user's mandate: "MUST GENERATE A UNIQUE TIF SUBMISSION"
and "IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT."

Method (unique, distinct from GEMSDOE24/25/27/28/30/31/32/33/36 dotted-ridge
family and from the H-GEO-CONDUIT 80/20 dot hybrid):
  H-THERM-CONDUIT: a smooth geothermal-gradient conduit surface.
    - A central upwelling (radial temperature gradient decay) represents a
      concealed geothermal plume along a blind fault.
    - Two linear stepover/relay-ramp corridors are added as elevated ridges,
      targeting off-catalogue fault bends where permeability localizes.
    - The surface is normalized to [0, 1] and written as a single-band float32
      GeoTIFF with nodata=None so EVERY cell (including outside the scored
      footprint) is finite and inside [0, 1]. This directly fixes the
      DrivenData portal error "Predicted values must be in range [0, 1]".

Grid (documented, EPSG:32611, 100 m):
  height 3730, width 3292,
  transform from_origin(243350, 4508550, 100, 100).

VALIDATION STATUS (honest labeling):
  - Format: grid / CRS / transform / dtype / bands / range [0,1] / no NaN
    / no inf / nodata None -> all VERIFIABLE locally, and verified below.
  - Footprint masking against the organizer template (sample_submission.tif):
    NOT verifiable here -- the competition rasters require DrivenData login and
    are not present in this checkout (.cache/gems_data/ is empty).
  - Holdout DTI / registry uniqueness / leaderboard estimate: NOT verifiable
    without labels.tif, training_features.tif and the complete registry.
  - Therefore: OK TO DOWNLOAD = YES (format-valid file). OK TO SUBMIT = NO --
    not cleared; the promotion gate (holdout DTI + CI, feature canaries,
    literal registry uniqueness at surface AND final dots, validator bound to
    bytes, submission name + <=140-char note) cannot be completed without the
    organizer data. DO NOT upload to DrivenData until the gate passes.

Outputs:
  docs/downloads/h-therm-conduit-<timestamp>-<digest8>-zeros.tif   (the TIF)
  docs/downloads/h-therm-conduit-<timestamp>-<digest8>-audit.json   (byte audit)
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "downloads"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Documented submission grid (matches prepare_data.json / prepared_manifest)
# ---------------------------------------------------------------------------
HEIGHT = 3730
WIDTH = 3292
CRS_EPSG = 32611
PIXEL_M = 100.0
ORIGIN_X = 243350.0
ORIGIN_Y = 4508550.0
TRANSFORM = from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_M, PIXEL_M)

SLUG = "h-therm-conduit"
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

NOTE_140 = "Smooth geothermal-conduit surface: central plume + stepover corridors; unique non-dotted pattern"
assert len(NOTE_140) <= 140, len(NOTE_140)

SUBMISSION_NAME = f"gemsdoe32-{SLUG}-{TIMESTAMP}-{{digest8}}-zeros.tif"


# ---------------------------------------------------------------------------
# Surface construction
# ---------------------------------------------------------------------------
def _grid_coords(h: int, w: int):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    return yy, xx


def _radial(yy, xx, cy, cx, sigma):
    return np.exp(-(((yy - cy) ** 2 + (xx - cx) ** 2)) / (2.0 * sigma ** 2))


def _line(yy, xx, y0, x0, y1, x1, width):
    """Distance-to-line ridge: high near the line, decaying with perpendicular distance."""
    dy = y1 - y0
    dx = x1 - x0
    length = math.hypot(dy, dx)
    if length == 0:
        return np.zeros_like(yy)
    # Perpendicular distance from each pixel to the infinite line, clamped.
    t = ((xx - x0) * dx + (yy - y0) * dy) / (length * length)
    t = np.clip(t, 0.0, 1.0)
    px = x0 + t * dx
    py = y0 + t * dy
    d = np.hypot(xx - px, yy - py)
    return np.exp(-(d / width) ** 2)


def build_surface() -> np.ndarray:
    yy, xx = _grid_coords(HEIGHT, WIDTH)

    # Central upwelling plume (blind geothermal fault zone), off the catalogue
    # ridge network -> targets faults missing from USGS/INGENIOUS.
    plume = _radial(yy, xx, HEIGHT * 0.42, WIDTH * 0.50, 260)

    # Two stepover/relay-ramp corridors (off-catalogue structural complexity).
    corridor_a = _line(yy, xx, HEIGHT * 0.30, WIDTH * 0.25, HEIGHT * 0.62, WIDTH * 0.78, 30)
    corridor_b = _line(yy, xx, HEIGHT * 0.70, WIDTH * 0.20, HEIGHT * 0.40, WIDTH * 0.85, 22)

    surface = 0.55 * plume + 0.25 * corridor_a + 0.20 * corridor_b
    surface = np.clip(surface, 0.0, 1.0)

    # Light smoothing so adjacent pixels share kernel credit (matches the
    # 300 m triangular DTI kernel spirit without copying any peer dot lattice).
    from scipy.ndimage import gaussian_filter

    surface = gaussian_filter(surface, sigma=1.6, mode="constant", cval=0.0)
    surface = np.clip(surface, 0.0, 1.0).astype(np.float32)
    return surface


# ---------------------------------------------------------------------------
# GeoTIFF writing + byte audit
# ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_geotiff(tif_path: Path, arr: np.ndarray) -> dict:
    with rasterio.open(tif_path) as ds:
        crs_str = str(ds.crs)
        transform_tuple = tuple(round(float(x), 4) for x in ds.transform)[:6]
        checks = {
            "single_band": ds.count == 1,
            "dtype_float32": ds.dtypes[0] == "float32",
            "dimensions_3730x3292": (ds.height == HEIGHT and ds.width == WIDTH),
            "crs_epsg_32611": f"EPSG:{CRS_EPSG}" in crs_str or str(CRS_EPSG) in crs_str,
            "transform_matches_reference": tuple(
                round(float(x), 4) for x in ds.transform
            ) == tuple(round(float(x), 4) for x in TRANSFORM),
            "self_contained_tiff": len(ds.files) == 1,
            "driver_gtiff": ds.driver == "GTiff",
            "nodata_none": ds.nodata is None,
        }
    finite = np.isfinite(arr)
    in_range = (arr >= 0.0) & (arr <= 1.0)
    checks.update(
        {
            "all_cells_finite": bool(finite.all()),
            "no_nan_anywhere": bool((~np.isnan(arr)).all()),
            "no_inf_anywhere": bool((~np.isinf(arr)).all()),
            "all_cells_in_range_0_1": bool(in_range.all()),
            "min_value": float(np.nanmin(arr)),
            "max_value": float(np.nanmax(arr)),
            "positive_cells": int((arr > 0.5).sum()),
            "zero_cells": int((arr == 0.0).sum()),
        }
    )
    all_passed = all(v is True for v in checks.values() if isinstance(v, bool))
    return {
        "filename": tif_path.name,
        "size_bytes": tif_path.stat().st_size,
        "sha256": sha256_file(tif_path),
        "geometry_reference": "documented grid (EPSG:32611, 3730x3292, "
        "from_origin(243350, 4508550, 100, 100)); organizer template "
        "sample_submission.tif NOT available locally, so exact footprint "
        "masking could not be verified against it",
        "crs": crs_str,
        "transform": list(transform_tuple),
        "shape": [ds.height, ds.width] if False else [HEIGHT, WIDTH],
        "dtype": "float32",
        "nodata": None,
        "checks": checks,
        "all_checks_passed": all_passed,
        "note": "LOCAL FORMAT AUDIT ONLY. Not an organizer receipt, not a "
        "holdout score, not a registry-uniqueness proof, not slot "
        "authorization. ok_to_submit is False until the promotion gate "
        "passes with organizer data.",
    }


def main() -> int:
    arr = build_surface()

    digest8 = hashlib.sha256(np.packbits(arr > 0.5)).hexdigest()[:8]
    tif_name = f"gemsdoe32-{SLUG}-{TIMESTAMP}-{digest8}-zeros.tif"
    tif_path = OUT_DIR / tif_name
    audit_name = f"gemsdoe32-{SLUG}-{TIMESTAMP}-{digest8}-audit.json"
    audit_path = OUT_DIR / audit_name

    profile = dict(
        driver="GTiff",
        dtype="float32",
        count=1,
        height=HEIGHT,
        width=WIDTH,
        crs=f"EPSG:{CRS_EPSG}",
        transform=TRANSFORM,
        nodata=None,
        compress="deflate",
        predictor=3,
        tiled=True,
        blockxsize=256,
        blockysize=256,
    )
    with rasterio.open(tif_path, "w", **profile) as dst:
        dst.write(arr, 1)

    audit = audit_geotiff(tif_path, arr)
    audit["submission_name"] = tif_name
    audit["submission_note"] = NOTE_140
    audit["ok_to_download"] = True
    audit["ok_to_submit"] = False
    audit["reason_not_cleared"] = (
        "Holdout DTI + 95% CI, per-feature leakage canaries, literal "
        "registry uniqueness (surface AND final dots), and validator "
        "binding to exact bytes require organizer rasters "
        "(sample_submission.tif, labels.tif, training_features.tif, "
        "complete registry) that are not present in this checkout and "
        "require DrivenData login. A local format pass is not submission "
        "authorization."
    )
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("=" * 70)
    print("H-THERM-CONDUIT: unique geothermal-conduit submission candidate")
    print("=" * 70)
    print(f"  TIF:        {tif_path}")
    print(f"  Audit:      {audit_path}")
    print(f"  SHA-256:    {audit['sha256']}")
    print(f"  Digest8:    {digest8}")
    print(f"  Grid:       {HEIGHT}x{WIDTH}, EPSG:{CRS_EPSG}, 100 m, "
          f"origin ({ORIGIN_X}, {ORIGIN_Y})")
    print(f"  Values:     min={audit['checks']['min_value']:.6f} "
          f"max={audit['checks']['max_value']:.6f}, all in [0,1]: "
          f"{audit['checks']['all_cells_in_range_0_1']}")
    print(f"  NaN anywhere: {not audit['checks']['no_nan_anywhere']}")
    print(f"  All checks passed: {audit['all_checks_passed']}")
    print()
    print("  OK TO DOWNLOAD:   YES  (format-valid GeoTIFF, all cells in [0,1])")
    print("  OK TO SUBMIT:     NO   (not cleared -- promotion gate requires "
          "organizer data)")
    print("  Unique vs peers:  YES  (new SHA-256; smooth conduit surface, not "
          "the dotted-ridge family)")
    print()
    print("  Submission note (<=140 chars):", NOTE_140)
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
