#!/usr/bin/env python3
"""Audit the nine focus-site top files: exact bytes, organizer-format gate, range/NaN census,
pairwise within-3 px overlap, and HOLDOUT-DTI from the shared hide-and-recover evaluator.

Inputs : data/focus_registry.json (pinned repo refs + SHA-256 of the "-nan" site files), .cache/focus9/ (fetched by
         scripts/fetch_focus9_files.py, SHA-256 verified there), .cache/gems_data (core data).
Outputs: evidence/focus9-audit-20261030.json

Labels: owner-reported scores are USER-REPORTED. HOLDOUT-DTI is a local catalogue-holdout proxy
(evaluator version, withheld-positive count and 95% CI included). Neither is an organizer receipt.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32 import holdout  # noqa: E402  (shared evaluator, unmodified)
import check_format  # noqa: E402  (shared organizer-format gate, unmodified)

DDIR = ROOT / ".cache" / "gems_data"
FOCUS = ROOT / ".cache" / "focus9"
# data/focus_registry.json holds the "-nan" file per site, matching the submission IDs in the
# user's leaderboard list. registry/focus9_registry.json lists different "-allfinite" byte variants
# with different SHA-256 values; that disagreement is recorded as an irregularity, not resolved here.
REG = json.loads((ROOT / "data" / "focus_registry.json").read_text())
OUT = ROOT / "evidence" / "focus9-audit-20261030.json"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def census(path: Path, foot: np.ndarray) -> dict:
    with rasterio.open(path) as ds:
        a = ds.read(1, masked=False).astype(np.float64)
        meta = {"dtype": ds.dtypes[0], "count": ds.count, "nodata": ds.nodata,
                "crs": str(ds.crs), "shape": list(ds.shape),
                "same_grid_as_template": bool(ds.shape == foot.shape and ds.transform == TEMPLATE_T)}
    inside = a[foot]
    outside = a[~foot]
    finite_in = np.isfinite(inside)
    rng_bad = finite_in & ((inside < 0) | (inside > 1))
    return {
        **meta,
        "inside_footprint": {
            "cells": int(inside.size),
            "nan_or_nonfinite": int((~finite_in).sum()),
            "out_of_range_0_1": int(rng_bad.sum()),
            "min": float(np.nanmin(inside)) if finite_in.any() else None,
            "max": float(np.nanmax(inside)) if finite_in.any() else None,
            "positive_cells(>0)": int((inside > 0).sum()),
            "cells_equal_1": int((inside == 1).sum()),
            "binary_0_or_1_only": bool(np.isin(inside[finite_in], [0.0, 1.0]).all()),
        },
        "outside_footprint": {
            "cells": int(outside.size),
            "nan": int(np.isnan(outside).sum()),
            "zero": int((outside == 0).sum()),
            "other_finite": int((np.isfinite(outside) & (outside != 0)).sum()),
        },
    }


def binary_dots(path: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1, masked=False)
    return (np.nan_to_num(a, nan=0.0)[foot] > 0)


TEMPLATE_T = None


def main() -> int:
    global TEMPLATE_T
    t0 = time.time()
    tmpl = DDIR / "sample_submission.tif"
    with rasterio.open(tmpl) as ds:
        foot = np.isfinite(ds.read(1))
        TEMPLATE_T = ds.transform
    ctx = holdout.load_holdout_context(DDIR)
    assert np.array_equal(ctx.foot, foot)

    files = REG["sites"]
    rows = []
    masks_full = {}
    for r in files:
        p = FOCUS / Path(r["path"]).name
        sha_ok = sha256(p) == r["sha256"]
        fmt_report = check_format.inspect(p, tmpl)
        cen = census(p, foot)
        row = {
            "site": r["site"],
            "file": p.name,
            "repo": r["repo"],
            "repo_ref": r["ref"],
            "path_in_repo": r["path"],
            "sha256": r["sha256"],
            "sha256_matches_registry": bool(sha_ok),
            "bytes": p.stat().st_size,
            "owner_reported_score": float(r["historical_claim"]),
            "owner_reported_score_label": "USER-REPORTED (unverified)",
            "format_gate_pass_official": bool(fmt_report["format_gate_pass"]),
            "format_checks_failed": [k for k, v in fmt_report["checks"].items() if v is not True],
            "census": cen,
        }
        # Binary-only files can be scored by the shared evaluator; soft files are not scored (issue #37).
        if cen["inside_footprint"]["binary_0_or_1_only"] and cen["inside_footprint"]["nan_or_nonfinite"] == 0:
            with rasterio.open(p) as ds:
                arr = ds.read(1, masked=False)
            m = np.zeros(foot.shape, bool)
            m[foot] = arr[foot] == 1
            masks_full[p.name] = m
            row["holdout_eligible"] = True
        else:
            row["holdout_eligible"] = False
            row["holdout_block_reason"] = "non-binary or non-finite inside footprint: shared evaluator rejects (no implicit thresholding)"
        rows.append(row)
        print(f"{r['site']:<10} fmt={row['format_gate_pass_official']} holdout_eligible={row['holdout_eligible']}", flush=True)

    # HOLDOUT-DTI for eligible files (shared evaluator; per-file hide-and-recover, binary input)
    for row in rows:
        if not row["holdout_eligible"]:
            continue
        ev = holdout.evaluate_hide_and_recover(masks_full[row["file"]], ctx, name=row["site"])
        row["holdout_dti"] = {
            "label": "HOLDOUT-DTI",
            "evaluator_version": ev["evaluator_version"],
            "pooled_dti": ev["pooled_dti"],
            "ci95_cluster_bootstrap": ev["ci95_cluster_bootstrap"],
            "n_withheld_positives": ev["n_withheld_positives"],
            "emitted_cells": int(masks_full[row["file"]].sum()),
        }
        print(f"{row['site']:<10} HOLDOUT-DTI={ev['pooled_dti']:.4f} n={ev['n_withheld_positives']}", flush=True)

    # Pairwise within-3 px overlap among the nine site-best files (binary dots only).
    site_rows = rows
    dots = {}
    for r in site_rows:
        d = binary_dots(FOCUS / r["file"], foot)
        dots[r["site"]] = d
    names = [r["site"] for r in site_rows]
    pair = {}
    for a in names:
        pair[a] = {}
        da = dots[a]
        for b in names:
            if a == b:
                pair[a][b] = 1.0
                continue
            db = dots[b]
            if da.sum() == 0 or db.sum() == 0:
                pair[a][b] = None
                continue
            full_a = np.zeros(foot.shape, bool)
            full_a[foot] = da
            full_b = np.zeros(foot.shape, bool)
            full_b[foot] = db
            dist_b = distance_transform_edt(~full_b)
            pair[a][b] = float((dist_b[full_a] <= 3).mean())
        print("overlap row", a, flush=True)

    out = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence_class": {"owner_reported_score": "USER-REPORTED", "holdout": "HOLDOUT-DTI (local proxy, not organizer)",
                           "leaderboard": "ORGANIZER-CONFIRMED: none for these files"},
        "evaluator": holdout.HIDE_RECOVER_EVALUATOR_VERSION,
        "rows": rows,
        "pairwise_within3px_fraction_of_row_dots_in_column_file": pair,
        "note": "Pairwise overlap is the fraction of the ROW file's positive cells within 3 px (Chebyshev-free, Euclidean) of the COLUMN file's positive cells.",
        "elapsed_s": round(time.time() - t0, 1),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=float) + "\n")
    print("wrote", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
