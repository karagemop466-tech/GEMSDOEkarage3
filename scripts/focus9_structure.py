#!/usr/bin/env python3
"""Structural audit of the nine focus-site GeoTIFFs against the catalogue labels.

Purpose (2026-10-30 review): test two mechanisms that the repo has stated but not
measured: (a) how the positive pixels of each focus file distribute by distance to
the catalogue traces, and (b) whether the claimed chain of exact-pixel inheritance
(GEMSDOE24 -> 25 -> 31 -> 32) holds.

Scoring context (verified 2026-10-30):
- DrivenData page 967 defines DTI over pixel probabilities with a 300 m (3 px) kernel.
- DrivenData staff forum post (community.drivendata.org, topic 11516) says pixels
  corresponding to known USGS/INGENIOUS faults are masked / excluded from evaluation.
  Pixels with distance 0 to the catalogue are therefore excluded from scoring; pixels
  at distance 1-3 px are NOT excluded and can contribute false-positive mass.

This script reports structure only. It computes NO DTI, NO score and NO estimate of the
leaderboard value. Output is a research receipt, not a submission approval.
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
DATA = ROOT / ".cache" / "gems_data"
FOCUS = ROOT / ".cache" / "focus9"
OUT = ROOT / "evidence" / "focus9-structure-20261030.json"
REGISTRY = ROOT / "data" / "focus_registry.json"

SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def footprint() -> np.ndarray:
    with rasterio.open(DATA / "sample_submission.tif") as ds:
        arr = ds.read(1)
        mask = ds.read_masks(1)
    return np.isfinite(arr) & (mask != 0)


def catalogue(foot: np.ndarray) -> np.ndarray:
    with rasterio.open(DATA / "labels.tif") as ds:
        if ds.shape != foot.shape:
            raise ValueError("labels grid differs from template")
        lab = ds.read(1)
    return (lab == 1) & foot


def positives(path: Path, foot: np.ndarray) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        if ds.count != 1 or ds.shape != foot.shape:
            raise ValueError(f"{path.name}: band/shape mismatch")
        a = ds.read(1, masked=False).astype(np.float64)
        crs, transform = str(ds.crs), tuple(ds.transform)[:6]
        dtype = ds.dtypes[0]
    inside = a[foot]
    info = {
        "file": path.name,
        "sha256": sha256(path),
        "dtype": dtype,
        "crs": crs,
        "transform_first6": list(transform),
        "in_footprint_nan_count": int(np.isnan(inside).sum()),
        "in_footprint_values_binary": bool(np.all(np.isfinite(inside) & ((inside == 0) | (inside == 1)))),
        "in_footprint_min": float(np.nanmin(inside)),
        "in_footprint_max": float(np.nanmax(inside)),
        "outside_footprint_nonzero_or_finite": int((np.isfinite(a) & ~foot & (a != 0)).sum()),
        "outside_footprint_nan_count": int((np.isnan(a) & ~foot).sum()),
    }
    pos = np.isfinite(a) & (a > 0) & foot
    return pos, info


def main() -> int:
    foot = footprint()
    cat = catalogue(foot)
    dist_cat = distance_transform_edt(~cat)
    registry = json.loads(REGISTRY.read_text())
    by_site = {}
    for row in registry["sites"]:
        if row["site"] in SITES:
            by_site[row["site"]] = row
    if set(by_site) != set(SITES):
        raise SystemExit(f"registry missing sites: {sorted(set(SITES) - set(by_site))}")

    rows, sets = [], {}
    for site in SITES:
        local = FOCUS / Path(by_site[site]["path"]).name
        if not local.exists():
            raise SystemExit(f"missing {local}; run scripts/fetch_focus9_files.py")
        if sha256(local) != by_site[site]["sha256"]:
            raise SystemExit(f"hash mismatch for {local.name}")
        pos, info = positives(local, foot)
        d = dist_cat[pos]
        n = int(pos.sum())
        on_cat = int((d == 0).sum())
        rows.append({
            "site": site,
            "repo": by_site[site]["repo"],
            "repo_ref": by_site[site]["ref"],
            "registry_path": by_site[site]["path"],
            **info,
            "positive_pixels_in_footprint": n,
            "positive_on_catalogue_d0_masked_by_organizer_rule": on_cat,
            "positive_1px_to_2px_from_catalogue": int(((d > 1) & (d <= 2)).sum()),
            "positive_0px_to_1px_from_catalogue_unmasked": int(((d > 0) & (d <= 1)).sum()),
            "positive_2px_to_3px_from_catalogue": int(((d > 2) & (d <= 3)).sum()),
            "positive_beyond_3px_from_catalogue": int((d > 3).sum()),
            "fraction_on_catalogue": (on_cat / n) if n else None,
            "fraction_unmasked_within_3px_of_catalogue": (int(((d > 0) & (d <= 3)).sum()) / n) if n else None,
        })
        sets[site] = pos

    # Literal 3-px rule (organizer-style kernel radius 3 px): share of dots of A within 3 px of any dot of B.
    within3 = {}
    dist_to = {b: distance_transform_edt(~sets[b]) for b in SITES}
    for a in SITES:
        n_a = int(sets[a].sum())
        for b in SITES:
            if a == b or n_a == 0:
                continue
            within3.setdefault(a, {})[b] = round(float((dist_to[b][sets[a]] <= 3.0).sum() / n_a), 6)

    # Exact pixel-set inheritance: is each file a subset of another? Jaccard on positive pixels.
    names = SITES
    jac = {}
    subset_of = {}
    for a in names:
        for b in names:
            if a == b:
                continue
            inter = int((sets[a] & sets[b]).sum())
            union = int((sets[a] | sets[b]).sum())
            jac.setdefault(a, {})[b] = round(inter / union, 6) if union else None
            if inter == int(sets[a].sum()) and int(sets[a].sum()) > 0:
                subset_of.setdefault(a, []).append(b)

    # USER-REPORTED values copied from the request (not organizer receipts). Used only to
    # describe how the structure lines up with the reported numbers; n = 9, exploratory.
    reported = {"GEMSDOE24": 0.2477, "GEMSDOE25": 0.2600, "GEMSDOE27": 0.2449,
                "GEMSDOE28": 0.2710, "GEMSDOE30": 0.2600, "GEMSDOE31": 0.2708,
                "GEMSDOE32": 0.2778, "GEMSDOE33": 0.2632, "GEMSDOE36": 0.2750}
    ring = {r["site"]: r["positive_0px_to_1px_from_catalogue_unmasked"] + r["positive_1px_to_2px_from_catalogue"]
            for r in rows}
    from scipy.stats import spearmanr
    rho, pval = spearmanr([ring[s_] for s_ in SITES], [-reported[s_] for s_ in SITES])
    ring_vs_reported = {
        "label": "USER-REPORTED scores x structure; exploratory, n=9, one file family; NOT a score estimate",
        "ring_0_to_2px_dots": ring,
        "user_reported_score": reported,
        "spearman_ring_vs_reported_score": round(float(rho), 4),
        "spearman_p_value": round(float(pval), 6),
    }

    result = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "classification": "STRUCTURE AUDIT - NOT A SCORE, NOT AN ESTIMATE, NOT A SUBMISSION APPROVAL",
        "template": {"file": "sample_submission.tif", "footprint_cells": int(foot.sum())},
        "catalogue": {"file": "labels.tif", "value": 1, "cells_in_footprint": int(cat.sum()),
                      "sha256": sha256(DATA / "labels.tif")},
        "masking_source": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
        "files": rows,
        "ring_vs_reported": ring_vs_reported,
        "pairwise_jaccard_positive_pixels": jac,
        "pairwise_share_of_row_dots_within_3px_of_column_dots": within3,
        "is_subset_of": subset_of,
        "verdict": "negative",
        "ok_to_submit": False,
        "experiments_run": 0,
        "weekly_slots_used": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for r in rows:
        print(f"{r['site']:10s} pos={r['positive_pixels_in_footprint']:6d} "
              f"d0={r['positive_on_catalogue_d0_masked_by_organizer_rule']:5d} "
              f"d(0,1]={r['positive_0px_to_1px_from_catalogue_unmasked']:6d} "
              f"d(1,2]={r['positive_1px_to_2px_from_catalogue']:6d} "
              f"d(2,3]={r['positive_2px_to_3px_from_catalogue']:6d} "
              f"d>3={r['positive_beyond_3px_from_catalogue']:6d} nan_in={r['in_footprint_nan_count']}")
    print("subset_of:", json.dumps(subset_of))
    print("ring 0-2px vs USER-REPORTED score: spearman rho =", ring_vs_reported["spearman_ring_vs_reported_score"],
          "p =", ring_vs_reported["spearman_p_value"], "(exploratory, n=9)")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
