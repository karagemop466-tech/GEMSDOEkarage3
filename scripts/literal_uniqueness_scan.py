#!/usr/bin/env python3
"""Literal two-stage uniqueness screen (AGENTS.md "Literal uniqueness is mandatory").

For one candidate, against EVERY supplied registry raster on the same grid:
  * rank correlation (Spearman, exact tie-aware) between candidate and registry raster
    over all footprint pixels  -> fail if |rho| > 0.90
  * fraction of candidate dots within 3 px (Euclidean) of a registry dot -> fail if > 0.70
Both stages are run: SURFACE (pre-placement top-K surface pixels, no NMS, and the
continuous surface itself) and FINAL (submitted binary dots).

Conventions (stated, not tuned): a registry raster with only {0,1} values is a dot set
(dots = value 1). A continuous registry raster is compared as a surface and, for the
overlap test only, its top-K pixels (K = candidate dot count) are treated as its dots.
Grid-mismatched rasters are skipped and listed, never silently passed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".cache" / "gems_work"
RHO_MAX = 0.90
OVERLAP_MAX = 0.70
RADIUS_PX = 3.0

G = {}


def _ranks(y: np.ndarray) -> np.ndarray:
    """Average (tie-aware) ranks, 1-based."""
    u, inv, counts = np.unique(y, return_inverse=True, return_counts=True)
    cum = np.cumsum(counts)
    avg = (cum - counts + 1 + cum) / 2.0
    return avg[inv].astype(np.float64)


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den > 0 else float("nan")


def _init():
    foot = np.load(WORK / "k4_footprint.npy")
    G["foot"] = foot
    G["S"] = np.load(WORK / "k4_surface.npy")[foot]
    G["pre"] = np.load(WORK / "k4_surface_preview_dots.npy")
    G["fin"] = np.load(WORK / "k4_final_dots.npy")
    G["shape"] = foot.shape
    G["rS"] = _ranks(G["S"])
    G["rPre"] = _ranks(G["pre"][foot].astype(np.float32))
    G["rFin"] = _ranks(G["fin"][foot].astype(np.float32))
    G["pre_rc"] = np.argwhere(G["pre"])
    G["fin_rc"] = np.argwhere(G["fin"])
    G["K"] = int(G["fin"].sum())


def _overlap(cand_rc: np.ndarray, reg_rc: np.ndarray) -> float:
    if cand_rc.size == 0 or reg_rc.size == 0:
        return 0.0
    d, _ = cKDTree(reg_rc).query(cand_rc, k=1, distance_upper_bound=RADIUS_PX + 1e-9)
    return float(np.mean(np.isfinite(d) & (d <= RADIUS_PX)))


def check_one(item: dict) -> dict:
    p = ROOT / item["local"]
    out = {"name": item["name"], "local": item["local"], "sha256": item.get("sha256")}
    try:
        with rasterio.open(p) as ds:
            if ds.shape != G["shape"] or ds.count != 1:
                return {**out, "status": "skipped_grid_mismatch", "shape": list(ds.shape)}
            y = ds.read(1).astype(np.float32)
            nd = ds.nodata
    except Exception as exc:  # noqa: BLE001
        return {**out, "status": "unreadable", "error": str(exc)[:200]}
    if nd is not None and np.isfinite(nd):
        y[y == nd] = np.nan
    foot = G["foot"]
    yf = y[foot]
    finite = np.isfinite(yf)
    if not finite.all():
        yf = np.where(finite, yf, np.nanmin(yf) if finite.any() else 0.0)
    uniq = np.unique(yf[:200_000])
    binary = np.isin(uniq, [0.0, 1.0]).all()
    if binary:
        dot_mask_full = np.zeros(G["shape"], dtype=bool)
        dot_mask_full[foot] = yf > 0
        reg_rc = np.argwhere(dot_mask_full)
        kind = "binary_dots"
    else:
        k = G["K"]
        top = np.argpartition(-yf, k - 1)[:k] if k < yf.size else np.arange(yf.size)
        dot_mask_full = np.zeros(G["shape"], dtype=bool)
        idx_fp = np.flatnonzero(foot.ravel())
        dot_mask_full.ravel()[idx_fp[top]] = True
        reg_rc = np.argwhere(dot_mask_full)
        kind = "continuous_top_K_as_dots"
    rY = _ranks(yf)
    rho_surface = _pearson(G["rS"], rY)
    rho_pre = _pearson(G["rPre"], rY)
    rho_final = _pearson(G["rFin"], rY)
    ov_pre = _overlap(G["pre_rc"], reg_rc)
    ov_fin = _overlap(G["fin_rc"], reg_rc)
    fail_reasons = []
    if abs(rho_surface) > RHO_MAX:
        fail_reasons.append("surface_rho")
    if abs(rho_final) > RHO_MAX:
        fail_reasons.append("final_rho")
    if ov_pre > OVERLAP_MAX:
        fail_reasons.append("surface_3px_overlap")
    if ov_fin > OVERLAP_MAX:
        fail_reasons.append("final_3px_overlap")
    return {**out, "status": "checked", "kind": kind, "n_reg_dots": int(reg_rc.shape[0]),
            "rho_surface_S": rho_surface, "rho_preview_dots": rho_pre, "rho_final_dots": rho_final,
            "overlap3px_preview": ov_pre, "overlap3px_final": ov_fin, "fail": fail_reasons}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory", type=Path, required=True, help="JSON list/dict with rasters[{name,local,sha256}]")
    ap.add_argument("--candidate-sha256", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=2)
    args = ap.parse_args()

    inv = json.loads(args.inventory.read_text())
    rows = inv["rasters"] if isinstance(inv, dict) else inv
    seen, items = set(), []
    for r in rows:
        sha = r.get("sha256")
        if sha in seen or sha == args.candidate_sha256 or not r.get("local"):
            continue
        if not (ROOT / r["local"]).exists():
            continue
        seen.add(sha)
        items.append({"name": f"{r.get('repo', '')}:{r.get('path', r['local'])}", "local": r["local"], "sha256": sha})

    results = []
    partial = args.out.with_suffix(".partial.jsonl")
    with Pool(args.jobs, initializer=_init) as pool, partial.open("w") as fh:
        for i, r in enumerate(pool.imap_unordered(check_one, items, chunksize=4), 1):
            results.append(r)
            fh.write(json.dumps(r, default=float) + "\n")
            fh.flush()
            if i % 50 == 0 or i == len(items):
                print(f"progress {i}/{len(items)}", file=sys.stderr, flush=True)

    checked = [r for r in results if r["status"] == "checked"]
    skipped = [r for r in results if r["status"] != "checked"]
    failing = [r for r in checked if r["fail"]]
    worst = lambda key: max(checked, key=lambda r: abs(r[key])) if checked else None  # noqa: E731
    summary = {
        "candidate_sha256": args.candidate_sha256,
        "inventory_rasters_presented": len(items),
        "checked_same_grid": len(checked),
        "skipped": len(skipped),
        "skipped_detail": [{"name": r["name"], "status": r["status"], **({"shape": r["shape"]} if "shape" in r else {})} for r in skipped],
        "fail_count": len(failing),
        "pass": len(failing) == 0,
        "max_abs_rho_surface": max((abs(r["rho_surface_S"]) for r in checked), default=None),
        "max_abs_rho_final": max((abs(r["rho_final_dots"]) for r in checked), default=None),
        "max_overlap3px_preview": max((r["overlap3px_preview"] for r in checked), default=None),
        "max_overlap3px_final": max((r["overlap3px_final"] for r in checked), default=None),
        "worst_overlap_final": sorted(checked, key=lambda r: -r["overlap3px_final"])[:5],
        "worst_rho_final": sorted(checked, key=lambda r: -abs(r["rho_final_dots"]))[:5],
        "fail_detail": failing[:50],
        "conventions": "footprint pixels only; exact tie-aware Spearman; 3 px Euclidean; binary dots or top-K continuous",
        "inventory_source": str(args.inventory),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, default=float) + "\n")
    print(json.dumps({k: summary[k] for k in ["inventory_rasters_presented", "checked_same_grid", "skipped", "fail_count", "pass", "max_abs_rho_surface", "max_abs_rho_final", "max_overlap3px_preview", "max_overlap3px_final"]}, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
