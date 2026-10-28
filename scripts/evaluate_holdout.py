#!/usr/bin/env python3
"""Canonical Protocol Rule 2 holdout evaluator CLI & helper (`evaluate_holdout.py`).

Delegates strictly to `gems32.holdout` (no private fork) to evaluate a GeoTIFF or `.npy` mask/field
using BOTH:
  1. `HOLDOUT-DTI` (`GEMSDOE32-HIDE-RECOVER-v3.0`): whole-segment withheld faults with 1.5 km collar,
     visible-only masking + visible-only `B` gate, exact pooled DTI (alpha=0.2, beta=0.8, 300 m
     triangular kernel) and 256-block spatial cluster-bootstrap 95% CI.
  2. `HOLDOUT-DTI` (`GEMSDOE32-SGMC-CAL-v3.0`): off-catalogue USGS SGMC faults (>300 m from `labels.tif`)
     with 256-block spatial cluster-bootstrap 95% CI.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout, metric  # noqa: E402
from gems32.paths import data_dir  # noqa: E402


def _strip_internal(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _evaluate_soft_hide_and_recover(arr: np.ndarray, ctx: holdout.HoldoutContext, b_visible_px: float, name: str) -> dict:
    """Exact soft [0, 1] Hide-and-Recover DTI (fixes IR-37 silent >0 binarization on continuous rasters)."""
    h, w = ctx.foot.shape
    grid_n = 16
    n_blocks = grid_n * grid_n
    tp_blk = np.zeros(n_blocks, dtype=np.float64)
    fp_blk = np.zeros(n_blocks, dtype=np.float64)
    fn_blk = np.zeros(n_blocks, dtype=np.float64)
    fy, fx = np.nonzero(ctx.foot)
    active_blocks = np.unique(holdout._spatial_block_index(fy, fx, (h, w), grid_n))
    dy_off, dx_off, kw_off = metric._OFF

    folds: dict[str, dict] = {}
    for cell in ctx.cells:
        sl = cell.bbox
        r0, c0 = int(sl[0].start), int(sl[1].start)
        active = cell.active_sub.copy()
        if b_visible_px > 0.0 and cell.d_vis_sub is not None:
            active &= cell.d_vis_sub > b_visible_px
        p_sub = np.where(active & np.isfinite(arr[sl]), np.clip(arr[sl], 0.0, 1.0), 0.0).astype(np.float64)
        n_t = cell.n_truth
        ty_sub, tx_sub = cell.truth_coords
        t_blk = holdout._spatial_block_index(ty_sub + r0, tx_sub + c0, (h, w), grid_n)
        mass = float(p_sub.sum())
        if n_t == 0 or mass == 0.0:
            if n_t > 0:
                np.add.at(fn_blk, t_blk, 1.0)
            folds[cell.key] = {"dti": 0.0, "tp": 0.0, "fp": mass if n_t == 0 else 0.0, "fn": float(n_t), "n_truth": n_t, "emitted_mass": mass}
            continue
        sh, sw = p_sub.shape
        t_cred = np.zeros(n_t, dtype=np.float64)
        for dy, dx, kk in zip(dy_off, dx_off, kw_off):
            ny, nx = ty_sub + int(dy), tx_sub + int(dx)
            ok = (ny >= 0) & (ny < sh) & (nx >= 0) & (nx < sw)
            if ok.any():
                t_cred[ok] = np.maximum(t_cred[ok], p_sub[ny[ok], nx[ok]] * kk)
        tp = float(t_cred.sum())
        fn = float(n_t) - tp
        np.add.at(tp_blk, t_blk, t_cred)
        np.add.at(fn_blk, t_blk, 1.0 - t_cred)

        py_sub, px_sub = np.nonzero(p_sub > 0.0)
        p_blk = holdout._spatial_block_index(py_sub + r0, px_sub + c0, (h, w), grid_n)
        fp_w = p_sub[py_sub, px_sub] * (1.0 - cell.k_dg_sub[py_sub, px_sub]).astype(np.float64)
        fp = float(fp_w.sum())
        np.add.at(fp_blk, p_blk, fp_w)
        dti_c = float(tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS))
        folds[cell.key] = {"dti": dti_c, "coverage": float(tp / n_t), "tp": tp, "fp": fp, "fn": fn, "n_truth": n_t, "emitted_mass": mass}

    pooled, ci95, _ = holdout._cluster_bootstrap_pooled_dti(tp_blk, fp_blk, fn_blk, active_blocks, n_boot=1000, seed=20261026)
    per_quad = {holdout.FOLD_NAMES[f]: float(np.mean([folds[f"draw{ds}_fold{f}"]["dti"] for ds in holdout.DRAWS])) for f in holdout.FOLDS}
    return {
        "candidate_id": name,
        "evaluator_version": holdout.HIDE_RECOVER_EVALUATOR_VERSION,
        "score_label": "HOLDOUT-DTI",
        "prediction_mode": "soft_0_1",
        "b_visible_px": float(b_visible_px),
        "n_withheld_positives": int(sum(v["n_truth"] for v in folds.values())),
        "n_spatial_clusters": int(active_blocks.size),
        "n_bootstrap_reps": 1000,
        "pooled_dti": pooled,
        "ci95_cluster_bootstrap": ci95,
        "fold_mean_dti": float(np.mean([v["dti"] for v in folds.values()])),
        "per_quadrant_dti": per_quad,
        "folds": folds,
    }


def evaluate_path(path: Path, b_visible_px: float = 0.0, ddir: Path | None = None, name: str | None = None) -> dict:
    ddir = ddir or data_dir()
    ctx = holdout.load_holdout_context(ddir)
    cand_name = name or path.stem
    suf = path.suffix.lower()
    if suf == ".npz":
        with np.load(path) as zf:
            cells = {k: np.asarray(zf[k], dtype=bool) for k in zf.files}
        hr = _strip_internal(holdout.evaluate_hide_and_recover(cells, ctx, b_visible_px=b_visible_px, name=cand_name))
        return {
            "candidate_id": cand_name,
            "path": str(path),
            "mode": "per_cell_oof_npz",
            "hide_and_recover": hr,
        }
    if suf == ".npy":
        arr = np.load(path)
    else:
        with rasterio.open(path) as ds:
            arr = ds.read(1)
    if arr.shape != ctx.foot.shape:
        raise ValueError(f"Expected grid shape {ctx.foot.shape}, got {arr.shape}")
    in_active = np.where(ctx.foot & ~ctx.labels & np.isfinite(arr), arr, 0.0)
    if (in_active < 0.0).any() or (in_active > 1.0).any():
        raise ValueError("Predictions inside active footprint must lie in [0, 1]")
    is_binary = bool(np.all((in_active == 0.0) | (in_active == 1.0)))
    mask = np.isfinite(arr) & (arr > 0) & ctx.foot
    if is_binary:
        hr = _strip_internal(holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=b_visible_px, name=cand_name))
        sg = _strip_internal(holdout.evaluate_sgmc_with_ci(mask, ctx, name=cand_name))
    else:
        hr = _evaluate_soft_hide_and_recover(in_active, ctx, b_visible_px=b_visible_px, name=cand_name)
        sg = _strip_internal(holdout.evaluate_sgmc_with_ci(in_active >= 0.5, ctx, name=cand_name))
        sg["note_soft_input"] = "SGMC fast EDT evaluated at p >= 0.5; Hide-and-Recover evaluated with exact soft [0, 1] kernel."
    legacy = holdout.evaluate_candidate_holdout(mask if is_binary else (in_active >= 0.5), ctx, name=cand_name)
    return {
        "candidate_id": cand_name,
        "path": str(path),
        "prediction_mode": "binary_0_1" if is_binary else "soft_0_1",
        "emitted_pixels": int(mask.sum()),
        "emitted_total_mass": round(float(in_active.sum()), 4),
        "hide_and_recover": hr,
        "sgmc_off_catalogue": sg,
        "legacy_summary": {
            "catalogue_hidden_mean": legacy["catalogue_hidden_mean"],
            "sgmc_prevalence_calibrated_dti": legacy["sgmc_prevalence_calibrated_dti"],
            "drift_corrected_holdout_mean": legacy["drift_corrected_holdout_mean"],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("candidate", type=Path, help="GeoTIFF, .npy mask, or .npz per-cell fold predictions")
    ap.add_argument("--b-visible-px", type=float, default=0.0, help="Visible-only B exclusion radius in pixels")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    res = evaluate_path(args.candidate, b_visible_px=args.b_visible_px, ddir=args.data_dir or data_dir(), name=args.name)
    txt = json.dumps(res, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
