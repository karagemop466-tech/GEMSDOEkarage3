#!/usr/bin/env python3
"""Locally measurable audit of the nine focus-site historical TIFFs.

Everything here is verifiable offline from the pinned mirror copies already
committed to docs/downloads/. Score claims are owner-reported / unverified and
are labeled as such; nothing is written as an organizer score or leaderboard
estimate.

Measured per file:
  G1 format (gems32/karage3 submission audit, both -nan and -zeros conventions)
  dot count, footprint fraction, on-catalogue pixels
  HOLDOUT-DTI catalogue hide-and-recover (GEMSDOE32-HIDE-RECOVER-v3.0,
  22,232 withheld positives, 95% cluster-bootstrap CI)

Measured pairwise (both directions): fraction of file A's dots within 3 px of
file B's dots  -> the uniqueness-vs-focus-sites column.

Usage:
  GEMS_DATA_DIR=/tmp/gems_data python3 scripts/measure_focus9_local.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from karage3 import holdout  # noqa: E402
from karage3.submission import audit_geotiff  # noqa: E402

yy, xx = np.ogrid[-3:4, -3:4]
DISK3_TRUE = ((yy * yy + xx * xx) <= 9)

FOCUS = [
    ("GEMSDOE24", "docs/downloads/GEMSDOE24-gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", "0.2477"),
    ("GEMSDOE25", "docs/downloads/GEMSDOE25-gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", "0.2600"),
    ("GEMSDOE27", "docs/downloads/GEMSDOE27-gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", "0.2449"),
    ("GEMSDOE28", "docs/downloads/GEMSDOE28-gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", "0.2710"),
    ("GEMSDOE30", "docs/downloads/GEMSDOE30-gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif", "0.2600"),
    ("GEMSDOE31", "docs/downloads/GEMSDOE31-gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif", "0.2708"),
    ("GEMSDOE32", "docs/downloads/GEMSDOE32-gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", "0.2778"),
    ("GEMSDOE33", "docs/downloads/GEMSDOE33-GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif", "0.2632"),
    ("GEMSDOE36", "docs/downloads/GEMSDOE36-gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif", "0.2750"),
]


def load(path):
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        meta = {"driver": ds.driver, "count": int(ds.count), "dtype": str(ds.dtypes[0]),
                "crs": str(ds.crs), "transform": [round(float(x), 6) for x in ds.transform][:6],
                "nodata": None if ds.nodata is None else float(ds.nodata)}
    # Template-mask convention: footprint = finite cells of sample_submission (NaN outside bounds).
    with rasterio.open(ROOT / "docs/downloads/sample_submission.tif") as tpl:
        tpl_arr = tpl.read(1)
    foot = np.isfinite(tpl_arr)
    dots = (arr > 0.5) & np.isfinite(arr) & foot
    return arr, foot, dots, meta


def within3_frac(dots_a, dots_b):
    dil = binary_dilation(dots_b, structure=DISK3_TRUE)
    if not dots_a.any():
        return 0.0
    return float(dil[dots_a].mean())


def _clean(obj):
    """Recursively replace non-finite floats with None so JSON dump is strict."""
    if isinstance(obj, float):
        return obj if np.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def main() -> int:
    from gems32.paths import data_dir  # noqa: E402
    ddir = Path("/tmp/gems_data")
    ctx = holdout.load_holdout_context(ddir)
    with rasterio.open(ddir / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & ctx.foot

    rows = []
    dot_arrays = {}
    for site, path, reported in FOCUS:
        p = ROOT / path
        arr, foot, dots, meta = load(p)
        dot_arrays[site] = dots
        try:
            fmt_nan = audit_geotiff(p, ctx.foot, labels, mode="nan", template_tif=ddir / "sample_submission.tif")
            print(f"[dbg] {site} nan OK", flush=True)
        except ValueError as exc:
            fmt_nan = {"error": str(exc)}
            print(f"[dbg] {site} nan FAIL: {exc}", flush=True)
        try:
            fmt_z = audit_geotiff(p, ctx.foot, labels, mode="zeros", template_tif=ddir / "sample_submission.tif")
            print(f"[dbg] {site} zeros OK", flush=True)
        except ValueError as exc:
            fmt_z = {"error": str(exc)}
            print(f"[dbg] {site} zeros FAIL: {exc}", flush=True)
        hr = holdout.evaluate_hide_and_recover(dots, ctx, name=site)
        rows.append({
            "site": site,
            "path": str(p),
            "sha256": fmt_nan.get("sha256") or fmt_z.get("sha256"),
            "reported_score": reported,
            "reported_score_label": "USER-REPORTED / UNVERIFIED (no organizer receipt in this repo)",
            "geometry": meta,
            "format_nan": {k: fmt_nan.get(k) for k in ("filename", "mode", "all_checks_passed", "checks",
                                                       "emitted_positive_pixels", "footprint_fraction",
                                                       "on_catalogue_positive_pixels", "in_footprint_min", "in_footprint_max")},
            "format_zeros": {k: fmt_z.get(k) for k in ("filename", "mode", "all_checks_passed", "checks",
                                                       "emitted_positive_pixels", "footprint_fraction",
                                                       "on_catalogue_positive_pixels")},
            "dots": int(dots.sum()),
            "footprint_fraction": round(float(dots.sum()) / float(ctx.foot.sum()), 6),
            "on_catalogue_dots": int((dots & labels).sum()),
            "holdout_dti": {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": hr["evaluator_version"],
                "pooled_dti": hr["pooled_dti"],
                "ci95": hr["ci95_cluster_bootstrap"],
                "n_withheld_positives": hr["n_withheld_positives"],
                "n_spatial_clusters": hr["n_spatial_clusters"],
                "fold_mean_dti": hr["fold_mean_dti"],
                "per_quadrant_dti": hr["per_quadrant_dti"],
                "label_note": "catalogue-holdout diagnostic; NOT a leaderboard estimate and NOT organizer-confirmed",
            },
        })

    # Pairwise uniqueness vs the other eight focus sites (both directions).
    n = len(rows)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            rows[i][f"within3_of_{rows[j]['site']}"] = round(
                within3_frac(dot_arrays[rows[i]["site"]], dot_arrays[rows[j]["site"]]), 6)
        rows[i]["max_within3_vs_any_focus_site"] = round(
            max(rows[i][f"within3_of_{rows[j]['site']}"] for j in range(n) if j != i), 6)
        rows[i]["unique_vs_focus_sites"] = bool(
            all(rows[i][f"within3_of_{rows[j]['site']}"] <= 0.70 for j in range(n) if j != i))

    best = max(rows, key=lambda r: r["reported_score"])
    out = {
        "schema": "GEMSDOEkarage3-FOCUS9-LOCAL-MEASUREMENT-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "template": "docs/downloads/sample_submission.tif (EPSG:32611, 3730x3292, 100 m, footprint 5,167,373 px)",
        "catalogue_labels": "docs/downloads/labels.tif (60,988 catalogue-positive pixels)",
        "holdout_evaluator": "GEMSDOE32-HIDE-RECOVER-v3.0 (catalogue, 22,232 withheld positives, cluster-bootstrap 95% CI)",
        "offline_note": "organizer SGMC grid and full registry rasters are not available offline (DrivenData login required); SGMC off-catalogue and full-registry uniqueness not measured here",
        "highest_reported": {"site": best["site"], "value": best["reported_score"]},
        "rows": rows,
    }
    out_path = ROOT / "evidence" / f"focus9-local-measurement-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(_clean(out), indent=2))
    print(json.dumps({
        r["site"]: {
            "reported": r["reported_score"],
            "dots": r["dots"],
            "holdout_dti": round(r["holdout_dti"]["pooled_dti"], 5),
            "ci95": r["holdout_dti"]["ci95"],
            "max_within3_vs_focus": r["max_within3_vs_any_focus_site"],
            "unique_vs_focus_sites": r["unique_vs_focus_sites"],
            "format_nan_pass": r["format_nan"]["all_checks_passed"],
            "format_zeros_pass": r["format_zeros"]["all_checks_passed"],
        } for r in rows
    }, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
