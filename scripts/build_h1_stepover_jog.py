#!/usr/bin/env python3
"""H1 experiment: Stepover-jog damage-zone annulus blind-fault detector (GEMSDOEkarage3 lane).

Generates a UNIQUE binary submission GeoTIFF targeting blind geothermal-conduit
faults missing from the USGS/INGENIOUS catalogue.

Mechanism (H1, ranked #1 in research/2026-10-29-hypotheses.md):
  1. Compute the Euclidean distance transform from catalogue fault traces
     (labels / existing_faults).
  2. Compute a local fault-density proxy: number of catalogue pixels inside a
     7 px window around each pixel (high density approximates stepovers/jogs
     and fault intersections without explicit skeletonisation).
  3. Emit dots at footprint pixels that are:
       - in the 5..15 px annulus (500 m..1.5 km) from the nearest catalogue trace
         (deliberately beyond the 0..4 px near-collar used by GEMSDOE24-36 and by
         the current karage3 H-GEO-CONDUIT artifact), AND
       - in the top quartile of local fault density (damage-zone / stepover
         targeting), AND
       - NOT on any catalogue pixel (zero leakage by construction).
  4. Cap the dot budget deterministically (farthest-from-trace priority, then
     row/column tie-break).

Geological rationale: GEMSDOE24-36 and H-GEO-CONDUIT cluster dots 0-2 px from
catalogue traces (recovering withheld catalogue segments). H1 deliberately
occupies the 5-15 px damage-zone annulus around complex fault zones - blind
geothermal upflow beside, not on, mapped traces. Zero dots on catalogue pixels.

Output: -zeros.tif (nodata=None, 0 outside footprint) and -nan.tif (NaN outside),
        both single-band float32, EPSG:32611, 3730x3292, values in [0,1], matching
        the sample_submission.tif template grid. Plus an audit sidecar and .zip.
No organizer-confirmed score is claimed; holdout DTI is NOT computed here
(requires external/derived_sgmc_faults_100m_u8.tif and organizer-authenticated inputs).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32.paths import data_dir, downloads_dir  # noqa: E402

ANNULUS_IN_PX = 5.0       # 500 m
ANNULUS_OUT_PX = 15.0     # 1.5 km
DENSITY_WINDOW_PX = 7     # fault-density window (stepover/jog proxy)
MAX_DOTS = 32000          # deterministic cap, below the 37 654 / 44 090 dot budgets
SLUG = "h1-stepper-jog-annulus-blind"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ddir = data_dir()
    sample_tif = ddir / "sample_submission.tif"
    labels_tif = ddir / "labels.tif"
    assert sample_tif.exists(), f"missing template {sample_tif}"
    assert labels_tif.exists(), f"missing labels {labels_tif}"

    with rasterio.open(sample_tif) as tpl:
        template_grid = (tpl.crs, tpl.shape, tpl.transform, tpl.profile)
        tarr = tpl.read(1)
        foot = np.isfinite(tarr) & (tpl.read_masks(1) > 0)
    H, W = tpl.shape

    with rasterio.open(labels_tif) as ds:
        if (ds.crs, ds.shape, ds.transform) != template_grid[:3]:
            raise ValueError("Catalogue grid does not match template")
        labels = (ds.read(1) > 0) & foot

    # --- Distance to nearest catalogue trace ------------------------------
    dist_to_trace = ndimage.distance_transform_edt(~labels)

    # --- Local fault-density proxy (stepover/jog / damage-zone targeting) --
    footprint_f32 = foot.astype(np.float32)
    labels_f32 = labels.astype(np.float32)
    # count of catalogue pixels in a (2w+1)x(2w+1) window, normalised by area
    w = DENSITY_WINDOW_PX
    density = ndimage.convolve(labels_f32, np.ones((2 * w + 1, 2 * w + 1), np.float32),
                               mode="constant", cval=0.0)
    density = density / float((2 * w + 1) ** 2)

    # --- Selection: annulus AND top-quartile local density AND off-catalogue ---
    annulus = (dist_to_trace >= ANNULUS_IN_PX) & (dist_to_trace <= ANNULUS_OUT_PX) & foot
    density_threshold = float(np.percentile(density[foot & (density > 0)], 75))
    pick = annulus & (density >= density_threshold) & ~labels  # ~labels: zero leakage

    ys, xs = np.nonzero(pick)
    n = ys.size
    print(f"candidate pixels before cap: {n}  (density>= {density_threshold:.6f})")

    if n > MAX_DOTS:
        # Deterministic priority: farthest from trace first (deep damage zone),
        # tie-broken by row then column.
        order = np.lexsort((xs, ys, -dist_to_trace[ys, xs]))
        sel = order[:MAX_DOTS]
        ys, xs = ys[sel], xs[sel]

    mask = np.zeros((H, W), dtype=bool)
    mask[ys, xs] = True
    n_emitted = int(mask.sum())
    print(f"emitted dots: {n_emitted}")

    # --- Sanity: zero leakage, range --------------------------------------
    on_cat = int((mask & labels).sum())
    print(f"dots on catalogue pixels: {on_cat}")
    assert on_cat == 0
    assert n_emitted <= MAX_DOTS

    arr = mask.astype(np.float32)
    arr_zeros = np.where(foot, np.clip(arr, 0.0, 1.0), 0.0).astype(np.float32)
    arr_nan = np.where(foot, np.clip(arr, 0.0, 1.0), np.nan).astype(np.float32)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest8 = hashlib.sha256(np.packbits(arr > 0.5)).hexdigest()[:8]
    out_dir = downloads_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    zeros_name = f"gemsdoe32-{SLUG}-{ts}-{digest8}-zeros.tif"
    nan_name = f"gemsdoe32-{SLUG}-{ts}-{digest8}-nan.tif"
    zeros_path = out_dir / zeros_name
    nan_path = out_dir / nan_name

    note = "H1 stepover-jog damage-zone annulus dots 5-15px off catalogue traces; unique non-lattice"
    assert len(note) <= 140, len(note)

    profile = template_grid[3].copy()
    profile.update(driver="GTiff", dtype="float32", count=1, compress="deflate",
                   predictor=3, zlevel=9, tiled=True, blockxsize=256, blockysize=256, nodata=None)
    with rasterio.open(zeros_path, "w", **profile) as dst:
        dst.write(arr_zeros, 1)

    profile_nan = profile.copy(); profile_nan.update(nodata=np.nan)
    with rasterio.open(nan_path, "w", **profile_nan) as dst:
        dst.write(arr_nan, 1)

    # --- Uniqueness vs existing local registrations -----------------------
    uniqueness = {}
    for ref in [
        out_dir / "gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif",
    ]:
        if ref.exists():
            with rasterio.open(ref) as ds:
                ref_arr = ds.read(1) > 0
            from scipy.ndimage import distance_transform_edt as dte
            dt_ref = dte(~ref_arr)
            d_of_my = dt_ref[mask]
            within3 = float((d_of_my <= 3.0).mean())
            # rank correlation of the two continuous surfaces (binary -> fine)
            from scipy.stats import spearmanr
            rho, _ = spearmanr(arr.ravel(), ref_arr.astype(np.float32).ravel())
            uniqueness[ref.name] = {
                "dots_within_3px_fraction": round(within3, 4),
                "rank_correlation_spearman": round(float(rho), 4),
            }

    # --- Audit sidecar -----------------------------------------------------
    with rasterio.open(zeros_path) as src:
        a = src.read(1)
        in_foot = a[foot]
        checks = {
            "single_band": src.count == 1,
            "dtype_float32": src.dtypes[0] == "float32",
            "dimensions_3730x3292": src.shape == (3730, 3292),
            "crs_epsg_32611": str(src.crs) == "EPSG:32611",
            "transform_matches_template": src.transform == template_grid[2],
            "in_footprint_all_finite": bool(np.isfinite(in_foot).all()),
            "in_footprint_range_0_1": bool((in_foot >= 0.0).all() and (in_foot <= 1.0).all()),
            "outside_footprint_zero": bool((a[~foot] == 0.0).all()),
            "zero_on_catalogue_leakage": on_cat == 0,
        }
    audit = {
        "experiment": "H1 stepover-jog damage-zone annulus blind-fault detector",
        "hypothesis": "H1",
        "mechanism": "damage-zone annulus 5-15 px off catalogue traces at high local fault density (stepover/jog proxy)",
        "created_utc": ts,
        "candidate_id": f"karage3-{SLUG}",
        "slug": SLUG,
        "content_digest8": digest8,
        "zeros_tif": zeros_name,
        "nan_tif": nan_name,
        "sha256_zeros": sha256_file(zeros_path),
        "sha256_nan": sha256_file(nan_path),
        "size_bytes_zeros": zeros_path.stat().st_size,
        "emitted_dots": int(n_emitted),
        "footprint_fraction": round(float(n_emitted) / float(foot.sum()), 6),
        "dots_on_catalogue_pixels": on_cat,
        "density_threshold_p75": round(density_threshold, 6),
        "submission_note": note,
        "note_length_chars": len(note),
        "geometry": {"crs": str(src.crs), "shape": [int(src.height), int(src.width)],
                     "transform": [round(float(x), 6) for x in template_grid[2][:6]],
                     "nodata": None},
        "checks": checks,
        "all_format_checks_passed": bool(all(checks.values())),
        "uniqueness_vs_local_registrations": uniqueness,
        "holdout_dti": None,
        "holdout_status": "NOT RUN: external/derived_sgmc_faults_100m_u8.tif and organizer-authenticated inputs required; no organizer-confirmed score.",
        "verdict": "FORMAT-VALID / UNIQUE-CANDIDATE / NOT CLEARED FOR SUBMISSION pending holdout + selector authorization.",
        "lane_rule": "stop if rank correlation with any registry raster > 0.90 or > 70% of dots within 3 px of a registry raster.",
    }
    sidecar = out_dir / f"gemsdoe32-{SLUG}-{ts}-{digest8}-audit.json"
    sidecar.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    zip_path = zeros_path.with_suffix(".zip")
    import zipfile
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(zeros_path, arcname=zeros_name)
    audit["zeros_zip"] = {"filename": zip_path.name, "sha256": sha256_file(zip_path),
                          "size_bytes": zip_path.stat().st_size}
    sidecar.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("WROTE", zeros_path)
    print("WROTE", nan_path)
    print("WROTE", zip_path)
    print("WROTE", sidecar)
    print(json.dumps({k: v for k, v in audit.items() if k not in ("geometry",)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
