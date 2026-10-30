#!/usr/bin/env python3
"""H-QDTI fold-local holdout experiment (lane: label-free geophysical emission + DTI-break-even area).

Hypothesis (pre-registered in docs/research/hqdti-preregistration-20261030.md):
  A per-pixel logistic emission model q(x) trained only on VISIBLE catalogue faults, using
  label-free geophysical bands (official training_features.tif, 19 bands) plus 4-px Gaussian
  context of the same bands, ranks pixels by their chance of lying within 300 m of a fault.
  Emitting the top-f fraction of the active domain (binary 0/1) should beat a random mask of the
  same area on the shared hide-and-recover holdout.

Protocol (all shared tools, no private metric or evaluator):
  * withheld truth, collars, masks and pooled DTI come from gems32.holdout (GEMSDOE32-HIDE-RECOVER-v3.0);
  * per-cell OOF masks are produced by a model fitted inside each cell, using only that cell's
    visible catalogue (ctx.visible_by_cell) and excluding a 15-px collar around every withheld
    fault from the negatives;
  * single-feature leakage canary: AUC of each feature alone on the withheld truth (must be < 0.90).

Usage: python scripts/qdti_holdout.py --data-dir .cache/gems_data --out evidence/qdti-holdout-20261030.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt, gaussian_filter
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402  (shared evaluator, unmodified)

FRACS = (0.005, 0.01, 0.02, 0.05, 0.10)  # pre-registered emitted-area fractions of the active domain
SMOOTH_SIGMA_PX = 4.0
NEAR_PX = 3          # 300 m kernel radius
COLLAR_NEG_PX = 15   # negatives exclude 15 px around every withheld fault
N_POS = 60_000
N_NEG = 120_000


def load_features(ddir: Path):
    """Return (names, feats[F, n_foot] float32, foot[H,W] bool, idx[H,W] int64 of footprint index)."""
    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    names, cols = [], []
    with rasterio.open(ddir / "training_features.tif") as ds:
        for b in range(1, ds.count + 1):
            a = ds.read(b).astype(np.float32)
            a[a < -1e38] = np.nan
            names.append(ds.descriptions[b - 1] or f"band{b}")
            vals = a[foot]
            fill = np.nanmedian(vals)
            a = np.where(np.isfinite(a), a, fill).astype(np.float32)
            q25, q75 = np.nanpercentile(a[foot], [25, 75])
            scale = (q75 - q25) if (q75 - q25) > 0 else 1.0
            z = np.clip((a - fill) / scale, -6, 6).astype(np.float32)
            cols.append(z[foot])
            # 4-px Gaussian context, normalized convolution inside the footprint
            wsum = gaussian_filter(foot.astype(np.float32), SMOOTH_SIGMA_PX, mode="constant")
            sm = gaussian_filter(np.where(foot, z, 0).astype(np.float32), SMOOTH_SIGMA_PX, mode="constant")
            cols.append((sm / np.maximum(wsum, 1e-6))[foot].astype(np.float32))
            names.append(f"{names[-1]}__smooth{int(SMOOTH_SIGMA_PX)}px")
    feats = np.stack(cols, axis=0).astype(np.float32)
    return names, feats, foot


def fit_predict(feats, foot, pos_mask_full, neg_mask_full, seed: int):
    """Fit logistic emission on sampled positives/negatives; return q over the full grid (0 outside foot)."""
    rng = np.random.default_rng(seed)
    flat_pos = np.flatnonzero(pos_mask_full[foot])
    flat_neg = np.flatnonzero(neg_mask_full[foot])
    if flat_pos.size == 0 or flat_neg.size == 0:
        raise ValueError("empty training class")
    p = rng.choice(flat_pos, size=min(N_POS, flat_pos.size), replace=False)
    n = rng.choice(flat_neg, size=min(N_NEG, flat_neg.size), replace=False)
    idx = np.concatenate([p, n])
    y = np.concatenate([np.ones(p.size), np.zeros(n.size)])
    clf = LogisticRegression(C=1.0, max_iter=300, class_weight="balanced")
    clf.fit(feats[:, idx].T, y)
    score = clf.decision_function(feats.T).astype(np.float32)
    q = np.zeros(foot.shape, np.float32)
    q[foot] = score
    return q


def cell_training_masks(ctx, cell):
    visible = ctx.visible_by_cell[cell.key]
    hidden_all = ctx.labels & ~visible & ctx.foot
    near_vis = distance_transform_edt(~visible) <= NEAR_PX
    collar = binary_dilation(hidden_all, structure=np.ones((3, 3), bool), iterations=COLLAR_NEG_PX)
    pos = near_vis & ctx.foot
    neg = ctx.foot & ~near_vis & ~collar
    return pos, neg, visible


def cell_active(ctx, cell):
    dom = np.zeros(ctx.foot.shape, bool)
    dom[cell.bbox] = cell.active_sub
    return dom


def fraction_mask(q, active, frac):
    vals = q[active]
    k = max(1, int(round(frac * vals.size)))
    thr = np.partition(vals, vals.size - k)[vals.size - k]
    return (q >= thr) & active


def canary(feats, names, ctx):
    """Per-feature AUC on withheld truth vs domain negatives (outside collar), pooled over cells."""
    out = {n: [] for n in names}
    rng = np.random.default_rng(7)
    for cell in ctx.cells:
        if cell.n_truth == 0:
            continue
        dom = cell_active(ctx, cell)
        visible = ctx.visible_by_cell[cell.key]
        hidden_all = ctx.labels & ~visible & ctx.foot
        collar = binary_dilation(hidden_all, structure=np.ones((3, 3), bool), iterations=COLLAR_NEG_PX)
        truth = (hidden_all & dom)
        neg = dom & ~collar
        pos_idx = np.flatnonzero(truth[ctx.foot])
        neg_idx = np.flatnonzero(neg[ctx.foot])
        if pos_idx.size < 50 or neg_idx.size < 50:
            continue
        pi = rng.choice(pos_idx, size=min(20000, pos_idx.size), replace=False)
        ni = rng.choice(neg_idx, size=min(20000, neg_idx.size), replace=False)
        ii = np.concatenate([pi, ni])
        yy = np.concatenate([np.ones(pi.size), np.zeros(ni.size)])
        for j, n in enumerate(names):
            out[n].append(float(roc_auc_score(yy, feats[j, ii])))
    summary = {n: float(np.mean(v)) if v else None for n, v in out.items()}
    worst = max(((v, n) for n, v in summary.items() if v is not None), default=(None, None))
    # Two-sided: a feature that is strongly ANTI-correlated also signals leakage if |AUC-0.5| is extreme.
    flags = [n for n, v in summary.items() if v is not None and max(v, 1 - v) > 0.90]
    return {"per_feature_mean_auc": summary, "max_single_feature_auc": worst[0], "max_feature": worst[1],
            "features_above_0.90_two_sided": flags, "leakage_flag": bool(flags)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n-boot", type=int, default=1000)
    args = ap.parse_args()

    t0 = time.time()
    ctx = holdout.load_holdout_context(args.data_dir)
    names, feats, foot = load_features(args.data_dir)
    assert foot.shape == ctx.foot.shape and np.array_equal(foot, ctx.foot)
    print(f"context+features ready in {time.time()-t0:.1f}s; features={feats.shape}", flush=True)

    can = canary(feats, names, ctx)
    print("leakage canary max single-feature AUC:", can["max_single_feature_auc"], can["max_feature"], flush=True)

    masks = {f: {} for f in FRACS}
    rand_masks = {f: {} for f in FRACS}
    rng = np.random.default_rng(20261030)
    cell_info = []
    for ci, cell in enumerate(ctx.cells):
        pos, neg, visible = cell_training_masks(ctx, cell)
        q = fit_predict(feats, foot, pos, neg, seed=1000 + ci)
        active = cell_active(ctx, cell)
        for f in FRACS:
            masks[f][cell.key] = fraction_mask(q, active, f)
            rp = np.zeros(foot.shape, bool)
            ai = np.flatnonzero(active)
            k = int(masks[f][cell.key].sum())
            rp.flat[rng.choice(ai, size=k, replace=False)] = True
            rand_masks[f][cell.key] = rp
        cell_info.append({"key": cell.key, "n_truth": cell.n_truth, "n_train_pos": int(pos[foot].sum()),
                          "n_train_neg": int(neg[foot].sum())})
        print(f"cell {cell.key}: n_truth={cell.n_truth}", flush=True)

    results = {}
    for f in FRACS:
        ev = holdout.evaluate_hide_and_recover(masks[f], ctx, n_boot=args.n_boot, name=f"qdti-top{f}")
        rr = holdout.evaluate_hide_and_recover(rand_masks[f], ctx, n_boot=args.n_boot, name=f"random-top{f}")
        results[str(f)] = {
            "qdti": {k: ev[k] for k in ("pooled_dti", "ci95_cluster_bootstrap", "n_withheld_positives",
                                        "evaluator_version", "fold_mean_dti", "per_quadrant_dti")},
            "random_same_area": {k: rr[k] for k in ("pooled_dti", "ci95_cluster_bootstrap",
                                                    "n_withheld_positives", "evaluator_version")},
        }
        print(f"frac {f}: qdti={ev['pooled_dti']:.4f} random={rr['pooled_dti']:.4f}", flush=True)

    out = {
        "experiment": "H-QDTI fold-local logistic emission, DTI break-even area sweep",
        "score_label": "HOLDOUT-DTI",
        "evaluator_version": holdout.HIDE_RECOVER_EVALUATOR_VERSION,
        "features": names,
        "smooth_sigma_px": SMOOTH_SIGMA_PX,
        "pre_registered_fractions": list(FRACS),
        "cells": cell_info,
        "leakage_canary": can,
        "results_by_fraction": results,
        "elapsed_s": round(time.time() - t0, 1),
        "not_organizer_confirmed": True,
        "selection_caveat": "Best fraction is chosen on the holdout; report as optimistic.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, default=float) + "\n")
    print("wrote", args.out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
