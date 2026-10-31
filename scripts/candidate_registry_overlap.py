#!/usr/bin/env python3
"""Literal registry overlap for one or more candidate GeoTIFFs (protocol rule 1, both stages).

Reads every distinct-bytes raster in registry/complete_registry_manifest.json that is restored under
.cache/registry (hash-verified by scripts/restore_complete_registry.py). Each registry raster's KD-tree is
built ONCE and every candidate is scored against it in the same pass. For each raster on the SAME grid:
  * dot-overlap = share of candidate dots within 3 px (Euclidean, inclusive) of a registry dot;
  * binary rho  = Pearson correlation between the candidate and registry binary masks over the footprint.
Duplicate-stop if dot-overlap > 0.70 or |rho| > 0.90.

Self-exclusion: for a candidate that is a NAMED focus-site file (GEMSDOE<NN>), only that candidate's OWN
pinned copy in buffedlizard55-lab/GEMSDOE<NN> is skipped. Identical bytes in any other repo or path are
compared and NOT exempt.

Scope: the 2,444-entry manifest (1,997 unique bytes). The manifest declares literal_registry_complete=false,
so a PASS here is NOT a literal-registry proof. Registry rasters on a different grid are counted and reported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
RADIUS = 3.0


def dots_of(arr: np.ndarray) -> np.ndarray:
    ys, xs = np.nonzero(arr > 0)
    return np.column_stack([ys, xs]).astype(np.float64)


def focus_repo_for(path: Path) -> str | None:
    m = re.search(r"GEMSDOE(\d+)", path.name)
    return f"buffedlizard55-lab/GEMSDOE{m.group(1)}" if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("candidates", type=Path, nargs="+")
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()

    with rasterio.open(ROOT / ".cache/gems_data/sample_submission.tif") as t:
        foot = np.isfinite(t.read(1)) & (t.read_masks(1) > 0)
        grid = (t.crs, t.shape, t.transform)
    foot_n = int(foot.sum())
    fflat = foot.ravel()

    cands = []
    for c in a.candidates:
        with rasterio.open(c) as ds:
            if ds.count != 1 or (ds.crs, ds.shape, ds.transform) != grid:
                raise SystemExit(f"candidate grid mismatch: {c}")
            arr = np.where(foot, np.nan_to_num(ds.read(1), nan=0.0), 0.0) > 0
        dots = dots_of(arr)
        vec = arr.ravel()[fflat].astype(np.float64)
        vc = vec - vec.mean()
        cands.append(dict(path=c, sha=hashlib.sha256(c.read_bytes()).hexdigest(), dots=dots,
                          vc=vc, vnorm=float(np.sqrt((vc ** 2).sum())),
                          exclude=focus_repo_for(c), rows=[], skipped=[]))

    manifest = json.loads((ROOT / "registry/complete_registry_manifest.json").read_text())["rasters"]
    seen: set[str] = set()
    different_grid = 0
    unreadable = []
    compared = 0
    for m in manifest:
        # Per-candidate self-copy skip (own repo + own bytes only).
        active = []
        for cd in cands:
            if cd["exclude"] and f"{m['owner']}/{m['repo']}" == cd["exclude"] and m["sha256"] == cd["sha"]:
                cd["skipped"].append(m["path"])
            else:
                active.append(cd)
        if not active or m["sha256"] in seen:
            continue
        seen.add(m["sha256"])
        try:
            with rasterio.open(ROOT / m["local"]) as r:
                if (r.crs, r.shape, r.transform) != grid:
                    different_grid += 1
                    continue
                arr = np.nan_to_num(r.read(1), nan=0.0) > 0
        except Exception as e:  # noqa: BLE001 - reported, never hidden
            unreadable.append({"path": m["path"], "error": str(e)[:120]})
            continue
        if arr.sum() == 0:
            continue
        compared += 1
        rtree = cKDTree(dots_of(arr))
        rvec = arr.ravel()[fflat].astype(np.float64)
        rc = rvec - rvec.mean()
        rnorm = float(np.sqrt((rc ** 2).sum()))
        for cd in active:
            if len(cd["dots"]) == 0:
                continue
            dist, _ = rtree.query(cd["dots"], k=1)
            frac = float((dist <= RADIUS).mean())
            rho = float((cd["vc"] * rc).sum() / (cd["vnorm"] * rnorm)) if cd["vnorm"] > 0 and rnorm > 0 else None
            cd["rows"].append({"repo_path": m["path"], "local": m["local"], "sha256": m["sha256"],
                               "registry_dots": int(arr.sum()), "candidate_within_3px": round(frac, 6),
                               "binary_rho": round(rho, 6) if rho is not None else None})

    a.out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for cd in cands:
        rows = sorted(cd["rows"], key=lambda x: -x["candidate_within_3px"])
        max_frac = rows[0]["candidate_within_3px"] if rows else None
        max_rho = max((abs(r["binary_rho"]) for r in rows if r["binary_rho"] is not None), default=None)
        res = {
            "candidate": cd["path"].name,
            "candidate_sha256": cd["sha"],
            "candidate_dots": int(len(cd["dots"])),
            "self_copies_skipped": cd["skipped"],
            "exclude_repo": cd["exclude"],
            "registry_distinct_bytes": len(seen),
            "registry_rasters_compared": compared,
            "registry_rasters_different_grid": different_grid,
            "registry_unreadable": unreadable,
            "rule": {"dot_overlap_stop": 0.70, "abs_rho_stop": 0.90, "radius_px": RADIUS},
            "max_candidate_within_3px": max_frac,
            "max_abs_binary_rho": max_rho,
            "n_rasters_over_70pct": sum(1 for r in rows if r["candidate_within_3px"] > 0.70),
            "n_rasters_over_0p90_rho": sum(1 for r in rows if r["binary_rho"] is not None and abs(r["binary_rho"]) > 0.90),
            "n_registry_rasters_over_50pct_of_footprint": sum(1 for r in rows if r["registry_dots"] > 0.5 * foot_n),
            "duplicate_stop": bool((max_frac or 0) > 0.70 or (max_rho or 0) > 0.90),
            "top10": rows[:10],
            "scope": "hash-verified restored registry (manifest literal_registry_complete=false); not a literal-registry proof",
        }
        (a.out_dir / (cd["path"].stem + ".overlap.json")).write_text(json.dumps(res, indent=2, allow_nan=False) + "\n")
        summary.append({k: res[k] for k in ("candidate", "candidate_dots", "max_candidate_within_3px",
                                             "max_abs_binary_rho", "n_rasters_over_70pct",
                                             "n_registry_rasters_over_50pct_of_footprint", "duplicate_stop")})
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
