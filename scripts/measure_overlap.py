#!/usr/bin/env python3
"""Measure literal uniqueness of one candidate GeoTIFF against reference rasters.

Definitions (stated so a reviewer can re-derive them):
  * footprint  = cells where the organizer template sample_submission.tif is finite
                 (template NaN = outside the scored area).
  * dots       = candidate cells inside the footprint with value > 0.
  * overlap    = fraction of candidate dots whose Euclidean distance to the nearest
                 reference dot (reference cells > 0 inside footprint) is <= 3 px.
  * spearman   = rank correlation over all footprint cells (ties averaged).

This is a LOCAL measurement. It is not an organizer receipt and it does not by itself
authorize a submission. Missing references are reported, never ignored.

Usage:
  python scripts/measure_overlap.py CANDIDATE.tif --template T.tif --ref NAME=PATH [--ref ...] --out OUT.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path):
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype(np.float64)
        return arr, ds.crs, ds.shape, ds.transform


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--ref", action="append", default=[], help="NAME=PATH (repeatable)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    tmpl, tcrs, tshape, ttf = load(args.template)
    footprint = np.isfinite(tmpl)
    cand, ccrs, cshape, ctf = load(args.candidate)
    geom_ok = (ccrs == tcrs) and (cshape == tshape) and (ctf == ttf)
    cand_dots = (cand > 0) & footprint
    cand_dots_idx = np.nonzero(cand_dots)
    n_dots = int(cand_dots.sum())
    cand_fp = np.where(footprint, cand, np.nan)[footprint]

    results = []
    for spec in args.ref:
        name, _, path_s = spec.partition("=")
        path = Path(path_s)
        ref, rcrs, rshape, rtf = load(path)
        ref_dots = (ref > 0) & footprint
        if not ref_dots.any():
            results.append({"name": name, "error": "reference has no positive dots inside footprint"})
            continue
        dist = distance_transform_edt(~ref_dots)
        within = int((dist[cand_dots_idx] <= 3.0).sum()) if n_dots else 0
        ref_fp = np.where(footprint, ref, np.nan)[footprint]
        rho = float(spearmanr(cand_fp, ref_fp, nan_policy="omit").statistic)
        results.append({
            "name": name,
            "path": str(path),
            "sha256": sha256_file(path),
            "ref_dots": int(ref_dots.sum()),
            "cand_dots_within_3px": within,
            "overlap_fraction": (within / n_dots) if n_dots else None,
            "spearman_footprint": rho,
            "literal_fail_overlap_gt_0p70": bool(n_dots and within / n_dots > 0.70),
            "literal_fail_spearman_gt_0p90": bool(abs(rho) > 0.90),
        })

    out = {
        "candidate": str(args.candidate),
        "candidate_sha256": sha256_file(args.candidate),
        "template": str(args.template),
        "template_sha256": sha256_file(args.template),
        "geometry_matches_template": bool(geom_ok),
        "footprint_cells": int(footprint.sum()),
        "candidate_dots": n_dots,
        "references": results,
        "max_overlap_fraction": max((r["overlap_fraction"] for r in results if r.get("overlap_fraction") is not None), default=None),
        "any_literal_fail": bool(any(r.get("literal_fail_overlap_gt_0p70") or r.get("literal_fail_spearman_gt_0p90") or "error" in r for r in results)),
        "measurement_scope": "only the references passed with --ref; NOT a complete registry audit",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps(out, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
