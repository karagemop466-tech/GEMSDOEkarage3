"""Evaluation helpers wrapping the vendored shared evaluator (no private evaluator fork)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score

from .holdout import (HoldoutContext, evaluate_sgmc_with_ci,
                      evaluate_visible_only_holdout, load_holdout_context)


def load_context(ddir: Path) -> HoldoutContext:
    return load_holdout_context(ddir)


def read_mask(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def canary_auc(surface: np.ndarray, ctx: HoldoutContext, name: str) -> dict:
    """Leakage canary: surface ALONE vs withheld truth, per holdout cell (active domain only).
    AUC > 0.90 anywhere is leakage-suspect per protocol rule 4."""
    aucs = {}
    for cell in ctx.cells:
        sl = cell.bbox
        active = cell.active_sub
        y = np.zeros(active.shape, dtype=np.int8)
        y[cell.truth_coords] = 1
        s = np.asarray(surface[sl], dtype=np.float32)[active]
        t = y[active]
        if t.sum() == 0 or t.sum() == t.size or np.ptp(s) == 0:
            aucs[cell.key] = None
            continue
        aucs[cell.key] = float(roc_auc_score(t, s))
    vals = [v for v in aucs.values() if v is not None]
    return dict(
        feature=name, per_cell=aucs,
        auc_mean=float(np.mean(vals)) if vals else None,
        auc_max=float(np.max(vals)) if vals else None,
        leakage_suspect=bool(vals and max(vals) > 0.90),
        rule="AUC > 0.90 = leakage until proven otherwise (protocol rule 4)",
    )


def evaluate_mask(mask: np.ndarray, ctx: HoldoutContext, name: str,
                  b_collar_px: float = 2.0) -> dict:
    """Uniform instrument bundle for every candidate/control:
    visible-only pooled HOLDOUT-DTI (B-gate from visible faults only) + SGMC off-catalogue."""
    vis = evaluate_visible_only_holdout(mask, ctx, b_collar_px=b_collar_px, name=name)
    sg = evaluate_sgmc_with_ci(mask, ctx, name=name)
    sg.pop("_cal_boots", None)
    return dict(
        candidate_id=name,
        dots=int((mask & ctx.foot).sum()),
        on_catalogue_dots=int((mask & ctx.labels).sum()),
        visible_only=vis,
        sgmc=sg,
    )


def distance_to_catalogue_hist(mask: np.ndarray, labels: np.ndarray) -> dict:
    d = distance_transform_edt(~labels)
    dd = d[mask]
    return dict(
        d0=int((dd == 0).sum()), d_le1=int((dd <= 1.0).sum()),
        d_le2=int((dd <= 2.0).sum()), d_le3=int((dd <= 3.0).sum()),
        d_gt3=int((dd > 3.0).sum()), median_d=float(np.median(dd)) if dd.size else None,
    )


def pairwise_dot_stats(a: np.ndarray, b: np.ndarray) -> dict:
    """Set relations between two dot masks (exact-pixel level)."""
    inter = int((a & b).sum())
    return dict(
        a_dots=int(a.sum()), b_dots=int(b.sum()), intersection=inter,
        symdiff=int((a ^ b).sum()),
        a_subset_b=bool(inter == int(a.sum())), b_subset_a=bool(inter == int(b.sum())),
        jaccard=float(inter / max(int((a | b).sum()), 1)),
    )
