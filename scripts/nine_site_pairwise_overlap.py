#!/usr/bin/env python3
"""Pairwise dot-overlap (within 3 px, both directions) among the nine focus-site files, plus byte identity.

Writes docs/data/nine-site-pairwise-20261031.json. Uses the same 3 px rule as candidate_registry_overlap.py.
Also reports Spearman rank correlation of the user-reported leaderboard values against the measured
SGMC-calibrated holdout values (9 points), as a consistency check, not a calibration.
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nine_site_holdout_table import SITES  # noqa: E402

def dots(path):
    with rasterio.open(path) as ds:
        a = np.nan_to_num(ds.read(1), nan=0.0) > 0
    return np.column_stack(np.nonzero(a)).astype(float)

def main():
    paths = {s: ROOT / "docs/downloads" / f for s, f, _ in SITES}
    D = {s: dots(p) for s, p in paths.items()}
    T = {s: cKDTree(D[s]) for s in D}
    sha = {s: hashlib.sha256(p.read_bytes()).hexdigest() for s, p in paths.items()}
    names = [s for s, _, _ in SITES]
    M = {}
    for a in names:
        for b in names:
            if a == b:
                continue
            d, _ = T[b].query(D[a], k=1)
            M[f"{a}->{b}"] = round(float((d <= 3.0).mean()), 4)
    rep = {s: r for s, _, r in SITES}
    # Holdout values from the table written by nine_site_holdout_table.py
    hold = json.loads((ROOT / "docs/data/nine-site-holdout-20261031.json").read_text())
    sg = {r["site"]: r["holdout_sgmc_calibrated"]["calibrated_dti"] for r in hold["rows"]}
    rho, p = spearmanr([sg[s] for s in names], [rep[s] for s in names])
    out = {
        "scope": "nine focus-site files in docs/downloads (pairwise, within 3 px, fraction of ROW dots near COLUMN dots)",
        "sha256": sha,
        "byte_identical_pairs": [[a, b] for i, a in enumerate(names) for b in names[i+1:] if sha[a] == sha[b]],
        "pairwise_within_3px": M,
        "max_pairwise_within_3px_per_site": {a: max(M[f"{a}->{b}"] for b in names if b != a) for a in names},
        "spearman_user_reported_vs_sgmc_calibrated": {"rho": round(float(rho), 4), "p": round(float(p), 4), "n": 9,
                                                      "note": "consistency check on 9 points only"},
    }
    (ROOT / "docs/data/nine-site-pairwise-20261031.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in ("byte_identical_pairs", "max_pairwise_within_3px_per_site", "spearman_user_reported_vs_sgmc_calibrated")}, indent=2))

if __name__ == "__main__":
    main()
