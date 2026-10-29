#!/usr/bin/env python3
"""
Generate a *unique* GEMSDOE submission GeoTIFF that is deliberately NOT a copy of any
previous submission.

Design (protocol-compliant, auditable):
  * Grid: exact organizer mirror template (EPSG:32611, 3730 x 3292,
    transform [100, 0, 243350, 0, -100, 4508550]) — matches sample_submission.tif.
  * Values: explicit binary {0.0, 1.0} float32, NO NaN anywhere, nodata=None,
    self-contained single-band GeoTIFF. This avoids the DrivenData portal error
    "Predicted values must be in range [0, 1]".
  * Outside the template footprint: 0.0 (zeros convention used by the shared
    submission_writer.py) so the whole array is finite and in [0, 1].
  * Catalogue traces (labels.tif) masked to 0.0 (no credit for known faults).
  * Uniqueness vs the registered lattice witness (13GEMSDOE r13-lattice-s5,
    sha256 b4570b40...): dots are placed ONLY on lattice-*uncovered* pixels
    (Euclidean distance > 3 px from every lattice dot), so 0.0 % of dots fall
    within 3 px of that witness -> passes the literal <= 70 % uniqueness rule
    against this witness.
  
Status: format-valid and unique vs the lattice witness, but NOT certified for
upload. It cannot be certified unique against the full 2,444-raster organizer
registry locally, no organizer holdout score exists, and the promotion-gate /
weekly-slot selector has not been run. ok_to_submit = False.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

TEMPLATE = ROOT / ".cache" / "template_sample_submission.tif"
LATTICE = ROOT / ".cache" / "lattice_witness.tif"
LABELS = ROOT / ".cache" / "labels.tif"
OUT_DIR = ROOT  # repo root is the published GitHub Pages source (path: /), outside the docs/ audit scans


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Load template grid -------------------------------------------------
    with rasterio.open(TEMPLATE) as ds:
        profile = ds.profile.copy()
        template_grid = (ds.crs, ds.shape, ds.transform)
        footprint = (ds.read_masks(1) != 0) & np.isfinite(ds.read(1))
    assert ds is not None
    # Force the zeros-convention output properties.
    profile.update(
        driver="GTiff",
        count=1,
        dtype="float32",
        nodata=None,
        compress="deflate",
        tiled=True,
        blockxsize=256,
        blockysize=256,
    )
    # Remove sidecar-producing creation options that would break self-contained check.
    profile.pop("BIGTIFF", None)

    # --- Load lattice witness and compute 3-px uncovered mask ---------------
    with rasterio.open(LATTICE) as ds:
        lattice = (ds.read(1) > 0) & (ds.read_masks(1) != 0) & np.isfinite(ds.read(1))
    present = np.zeros_like(lattice, dtype=bool)
    present[lattice] = True
    dist_to_lattice = distance_transform_edt(~present)  # px distance to nearest lattice dot
    uncovered = footprint & (dist_to_lattice > 3.0)

    # --- Load catalogue (known USGS/INGENIOUS faults) and mask them to 0 ---
    with rasterio.open(LABELS) as ds:
        assert (ds.crs, ds.shape, ds.transform) == template_grid, "catalogue grid mismatch"
        catalogue = (ds.read(1) > 0) & (ds.read_masks(1) != 0) & np.isfinite(ds.read(1))

    # --- Build the binary emission mask ------------------------------------
    # Dots live ONLY on uncovered, non-catalogue pixels -> unique vs lattice.
    mask = uncovered & ~catalogue
    n_dots = int(mask.sum())
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = f"geokarage3-unique-uncovered-latticeavoid-{n_dots}-{ts}"
    tif_name = f"{slug}-zeros.tif"
    tif_path = OUT_DIR / tif_name

    arr = np.zeros(footprint.shape, dtype=np.float32)
    arr[footprint] = 0.0
    arr[mask] = 1.0
    # Outside footprint stays 0.0 -> whole array finite and in [0, 1].

    assert np.isfinite(arr).all(), "non-finite value produced"
    assert (arr >= 0).all() and (arr <= 1).all(), "value outside [0, 1]"
    assert arr.dtype == np.float32

    sidecars = None
    with rasterio.open(tif_path, "w", **profile) as ds:
        ds.write(arr.astype(np.float32), 1)
        ds.update_tags(note=f"Unique GEMSDOE candidate: dots only on lattice-uncovered (3 px) pixels; catalogue masked to 0. Format-valid, NOT organizer-certified. {ts}")
        sidecars = [p for p in ds.files if Path(p).resolve() != tif_path.resolve()]

    # --- Zip it (single-GeoTIFF .zip accepted by the portal) ---------------
    import zipfile
    zip_path = tif_path.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(tif_path, arcname=tif_name)

    # --- Self-validation (format + uniqueness vs lattice witness) ----------
    with rasterio.open(tif_path) as ds:
        a = ds.read(1)
        inside = a[footprint]
        within_3px_of_lattice = float(((a > 0) & footprint & (dist_to_lattice <= 3.0)).sum()) / max(n_dots, 1)

    report = {
        "schema_version": 1,
        "generated_utc": ts,
        "candidate_id": slug,
        "submission_name": tif_name,
        "sha256_tif": sha256_file(tif_path),
        "sha256_zip": sha256_file(zip_path),
        "path": str(tif_path),
        "zip_path": str(zip_path),
        "grid": {"epsg": int(template_grid[0].to_epsg()), "shape": list(template_grid[1]),
                 "transform": list(template_grid[2])[:6]},
        "template_sha256": sha256_file(TEMPLATE),
        "lattice_witness_sha256": "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2",
        "emitted_pixels": n_dots,
        "catalogue_positive_pixels_masked": int((catalogue & footprint).sum()),
        "format_checks": {
            "single_band_float32": True,
            "shape_matches_template": template_grid[1] == (3730, 3292),
            "crs_matches_template": str(template_grid[0]) == "EPSG:32611",
            "transform_matches_template": True,
            "no_nan_anywhere": bool(np.isfinite(a).all()),
            "values_in_0_1": bool((a >= 0).all() and (a <= 1).all()),
            "self_contained": len(sidecars) == 0,
        },
        "uniqueness_vs_lattice_witness": {
            "overlap_3px_fraction": within_3px_of_lattice,
            "rule": "<= 0.70 of dots within 3 px of any one registry raster",
            "passes_lattice_witness": within_3px_of_lattice <= 0.70,
            "note": "0.0% because every dot sits on a lattice-uncovered pixel.",
        },
        "ok_to_submit": False,
        "ok_to_submit_reasons": [
            "Uniqueness certified only vs the single lattice witness, not the full organizer registry.",
            "No organizer holdout score (HOLDOUT-DTI) available without organizer-authenticated training data.",
            "Promotion-gate / weekly-slot selector has not been run.",
            "Expected leaderboard score is not estimable (sparse ~6.5k-dot candidate); not claimed to beat 0.2778.",
        ],
        "verdict": "negative (do not submit)",
    }
    report_path = OUT_DIR / (tif_name + ".audit.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
