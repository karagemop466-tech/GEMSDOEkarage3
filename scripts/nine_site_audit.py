#!/usr/bin/env python3
"""Nine-site audit + candidate audit -> docs/data/nine-site-summary.json.

Every number in the output is produced here from bytes on disk, labelled by evidence class:
  * HOLDOUT-DTI   : scripts/evaluate_holdout.py (shared evaluator, GEMSDOE32-HIDE-RECOVER-v3.0
                    and GEMSDOE32-SGMC-CAL-v3.0), with withheld-positive count and 95% cluster CI.
  * USER-REPORTED : scores typed by the user in the request (never organizer-confirmed here).
  * FORMAT        : scripts/validate_raster.py audit against data/sample_submission.tif.
  * OVERLAP       : 3-px candidate-side dot overlap computed here (Euclidean, <= 3 px).
Organizer scores are never written by this script.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from scripts.evaluate_holdout import evaluate_path  # noqa: E402
from scripts.validate_raster import audit as format_audit  # noqa: E402

DDIR = ROOT / "data"
REG = json.loads((ROOT / "registry/focus9_registry.json").read_text())["site_bests"]

# User-reported scores and the exact submission names the user supplied (USER-REPORTED).
USER_REPORTED = {
    "GEMSDOE24": ("h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", 0.2477),
    "GEMSDOE25": ("dotted-h19-5-d2-8-20261002-e56ea318af89-nan", 0.2600),
    "GEMSDOE27": ("topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", 0.2449),
    "GEMSDOE28": ("h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", 0.2710),
    "GEMSDOE30": ("d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", 0.2600),
    "GEMSDOE31": ("h27-4-solo-d28-20261004-8acb75e1-nan", 0.2708),
    "GEMSDOE32": ("h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778),
    "GEMSDOE33": ("h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632),
    "GEMSDOE36": ("anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", 0.2750),
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dots_rc(path: Path) -> tuple[np.ndarray, int]:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    fin = np.isfinite(a)
    rc = np.argwhere(fin & (a > 0))
    return rc, int(rc.shape[0])


def nan_count(path: Path) -> int:
    with rasterio.open(path) as ds:
        return int(np.isnan(ds.read(1)).sum())


def exact_subset_fraction(cand_rc: np.ndarray, ref_rc: np.ndarray) -> float:
    """Fraction of candidate dots that are exactly (same pixel) present in the reference dots."""
    if cand_rc.size == 0:
        return 0.0
    ref = set(map(tuple, ref_rc.tolist()))
    return float(sum(1 for t in map(tuple, cand_rc.tolist()) if t in ref) / len(cand_rc))


def overlap3(cand_rc: np.ndarray, ref_rc: np.ndarray) -> float:
    if cand_rc.size == 0 or ref_rc.size == 0:
        return 0.0
    d, _ = cKDTree(ref_rc).query(cand_rc, k=1)
    return float(np.mean(d <= 3.0))


def site_entries() -> list[dict]:
    rows = []
    for site, v in REG.items():
        local = ROOT / ".cache/registry" / v["repo"].split("/")[1] / v["path"]
        rows.append({"id": site, "kind": "focus-site", "path": local, "repo_path": v["path"],
                     "repo": v["repo"], "repo_head": v["repo_head"], "submission_id": v["submission_id"],
                     "user_reported_name": USER_REPORTED[site][0], "user_reported_score": USER_REPORTED[site][1]})
    cands = {
        "CAND-k4-offcat-ridge-20k": ROOT / "docs/downloads/gemsdoe32-karage3-k4-offcat-ridge-20k-20261029T183711Z-2a6558a3-zeros.tif",
        "CAND-geoconduit-hybrid": ROOT / "docs/downloads/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif",
        "CAND-unique-offcat (earlier)": ROOT / "docs/downloads/karage3-unique-offcat-20261029T180337Z-6a8c2368-zeros.tif",
    }
    for cid, p in cands.items():
        rows.append({"id": cid, "kind": "candidate", "path": p, "repo_path": str(p.relative_to(ROOT))})
    return rows


def main() -> int:
    entries = site_entries()
    out_rows = []
    rc_cache = {}
    for e in entries:
        p = e["path"]
        if not p.exists():
            raise SystemExit(f"missing file for {e['id']}: {p}")
        rc, n = dots_rc(p)
        rc_cache[e["id"]] = rc
        fmt = format_audit(p, DDIR / "sample_submission.tif")
        hold = evaluate_path(p, ddir=DDIR, name=e["id"])
        hr = hold["hide_and_recover"]
        sg = hold["sgmc_off_catalogue"]
        row = {
            "id": e["id"], "kind": e["kind"], "file": str(e["repo_path"]), "sha256": sha256(p),
            "bytes": p.stat().st_size, "dots": n, "nan_count_all_pixels": nan_count(p),
            "repo": e.get("repo"), "repo_head": e.get("repo_head"), "submission_id": e.get("submission_id"),
            "user_reported_name": e.get("user_reported_name"), "user_reported_score": e.get("user_reported_score"),
            "format": {k: fmt.get(k) for k in ["core_format_pass", "inside_nonfinite_count", "inside_min",
                                               "inside_max", "outside_template_null_pass",
                                               "whole_array_finite_range_pass", "checks"]},
            "holdout_dti": {"label": "HOLDOUT-DTI", "evaluator": hr["evaluator_version"],
                            "value": hr["pooled_dti"], "ci95": hr["ci95_cluster_bootstrap"],
                            "n_withheld_positives": hr["n_withheld_positives"]},
            "sgmc_calibrated_dti": {"label": "HOLDOUT-DTI", "evaluator": sg["evaluator_version"],
                                    "value": sg["sgmc_prevalence_calibrated_dti"],
                                    "ci95": sg["sgmc_calibrated_ci95"],
                                    "n_withheld_positives": sg["n_withheld_positives"]},
        }
        out_rows.append(row)

    # Pairwise candidate-side 3 px overlap (dots of row i within 3 px of dots of row j).
    ids = [r["id"] for r in out_rows]
    overlap = {}
    for i in ids:
        overlap[i] = {}
        for j in ids:
            if i == j:
                continue
            overlap[i][j] = round(overlap3(rc_cache[i], rc_cache[j]), 6)
    exact = {i: {j: round(exact_subset_fraction(rc_cache[i], rc_cache[j]), 6) for j in ids if j != i} for i in ids}
    for r in out_rows:
        r["exact_dot_subset_of_other_focus_site"] = {j: v for j, v in exact[r["id"]].items() if j.startswith("GEMSDOE") and v > 0}
        peers = {j: v for j, v in overlap[r["id"]].items() if j.startswith("GEMSDOE") or j.startswith("CAND")}
        focus_peers = {j: v for j, v in overlap[r["id"]].items() if j.startswith("GEMSDOE")}
        r["max_overlap3px_vs_other_focus_sites"] = max(focus_peers.values()) if focus_peers else None
        r["max_overlap3px_vs_other_focus_sites_site"] = (max(focus_peers, key=focus_peers.get) if focus_peers else None)
        r["max_overlap3px_vs_all_in_this_audit"] = max(peers.values()) if peers else None

    doc = {
        "schema": "nine-site-summary/1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evaluator_versions": ["GEMSDOE32-HIDE-RECOVER-v3.0", "GEMSDOE32-SGMC-CAL-v3.0"],
        "label_policy": "HOLDOUT-DTI (local proxy, not organizer). USER-REPORTED scores are copied from the request. No organizer receipt exists in this repo.",
        "uniqueness_threshold": {"rank_corr_max": 0.90, "overlap3px_max": 0.70, "note": "Literal full-registry screen is a separate script (literal_uniqueness_scan.py)."},
        "rows": out_rows,
        "pairwise_overlap3px": overlap,
        "pairwise_exact_dot_subset": exact,
    }
    out = ROOT / "docs/data/nine-site-summary.json"
    out.write_text(json.dumps(doc, indent=2, allow_nan=False) + "\n")
    print(f"wrote {out} rows={len(out_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
