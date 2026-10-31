#!/usr/bin/env python3
"""Leakage canary (experiment 2 of the Parallel-Run Protocol).

Scores every footprint pixel with a SINGLE catalogue-derived feature and
measures AUC against the spatially-blocked hide-and-recover withheld positives.
A single feature with AUC > 0.90 is leakage until proven otherwise.

Feature: proximity to the mapped catalogue (negative EDT distance to labels.tif
traces). The candidate places dots strictly OFF catalogue traces, so if this
feature alone predicts hidden positives near-perfectly, the dots are a catalogue
proxy rather than an off-catalogue target.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from karage3.holdout import load_holdout_context  # noqa: E402 (shared tool, no fork)

# GEMS_DATA_DIR points at scratch inputs; labels + sample_submission live there.
# derived_sgmc_faults_100m_u8.tif is required by the context builder but unused
# by this canary; a zeros placeholder satisfies the open.


def auc(pos_scores, neg_scores):
    """Mann-Whitney U AUC with tie correction via average ranks."""
    pos = np.asarray(pos_scores, dtype=np.float64)
    neg = np.asarray(neg_scores, dtype=np.float64)
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    all_s = np.concatenate([pos, neg])
    ranks = rankdata(all_s, method="average")
    n_pos, n_neg = pos.size, neg.size
    sum_pos_ranks = ranks[:n_pos].sum()
    return float((sum_pos_ranks - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def main() -> int:
    ddir = Path("/tmp/gems_data")
    labels_path = ddir / "labels.tif"
    sgm_dir = ddir / "external"
    sgm_dir.mkdir(parents=True, exist_ok=True)
    sgm_path = sgm_dir / "derived_sgmc_faults_100m_u8.tif"
    if not sgm_path.exists():
        with rasterio.open(ddir / "sample_submission.tif") as tmpl:
            prof = tmpl.profile
            arr = tmpl.read(1)
        prof.update(driver="GTiff", count=1, dtype="uint8", nodata=0,
                    compress="deflate")
        with rasterio.open(sgm_path, "w", **prof) as ds:
            ds.write(np.zeros(arr.shape, dtype=np.uint8), 1)

    ctx = load_holdout_context(ddir, hide_frac=0.20)

    # Pool withheld positives across all draws and folds (truth_coords are
    # relative to each cell's bbox; unbias to full-grid coords).
    pos_y, pos_x = [], []
    for cell in ctx.cells:
        if cell.n_truth == 0:
            continue
        ys, xs = cell.truth_coords
        pos_y.append(ys + cell.bbox[0].start)
        pos_x.append(xs + cell.bbox[1].start)
    pos_y = np.concatenate(pos_y); pos_x = np.concatenate(pos_x)
    n_pos = int(pos_y.size)
    print(f"withheld positives: {n_pos}")

    with rasterio.open(labels_path) as ds:
        labels = ds.read(1) > 0
    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    cat = labels & foot
    near = distance_transform_edt(~cat).astype(np.float64)  # 0 on catalogue
    score = -near  # higher = closer to catalogue (potential leakage direction)

    rng = np.random.default_rng(7)
    neg_pool_y, neg_pool_x = np.nonzero(foot & ~cat)
    take = min(400_000, neg_pool_y.size)
    idx = rng.integers(0, neg_pool_y.size, size=take)
    neg_y, neg_x = neg_pool_y[idx], neg_pool_x[idx]

    pos_s = score[pos_y, pos_x]
    neg_s = score[neg_y, neg_x]
    a = auc(pos_s, neg_s)
    print(f"canary AUC (proximity-to-catalogue vs withheld positives): {a:.4f}")
    print(f"positive score mean {pos_s.mean():.2f}, negative sample mean {neg_s.mean():.2f}")

    verdict = "LEAKAGE" if a > 0.90 else "OK"
    print(f"verdict: {verdict} (threshold 0.90)")
    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "feature": "negative_EDT_distance_to_catalogue_traces",
        "n_withheld_positives": n_pos,
        "n_negative_sample": int(take),
        "auc": a,
        "leakage_threshold": 0.90,
        "verdict": verdict,
        "note": "single-feature leakage canary; not a score and not a promotion signal",
    }
    Path("evidence/leakage-canary-single-feature-20261031.json").write_text(
        __import__("json").dumps(out, indent=2) + "\n")
    return 0 if verdict == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
