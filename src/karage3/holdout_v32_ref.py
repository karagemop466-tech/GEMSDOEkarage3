"""Reference multi-draw, zero-truth-FP-conserving (#41), and fragment/buffer-censored (IR-K3-12 / #60)
holdout helpers built cleanly atop the pinned `gems32.holdout` / `gems32.metric` / `gems32.submission`
primitives without modifying any byte of `registry/shared_template_97597a.json`.

Important honesty note: these local reference diagnostics do NOT replace an upstream fix in
`buffedlizard55-lab/GEMSDOE32`; `scripts/promotion_gate.py` still treats the pinned shared holdout
as provisional until fixed upstream, and literal registry overlap remains binding independently.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, label

from gems32 import holdout
from gems32.metric import ALPHA, BETA, EPS, kernel
from gems32.submission import require_binary_mask

EVAL_V31_24CELL = "GEMSDOE32-HIDE-RECOVER-v3.1-24cell-fpconserved"
EVAL_FRAG500M_24CELL = "GEMSDOE32-HIDE-RECOVER-FRAG500M-v3.2-24cell"
EVAL_BUF1500M_24CELL = "GEMSDOE32-HIDE-RECOVER-BUF1500M-v3.2-24cell"


def _ctx_draws(ctx: holdout.HoldoutContext) -> tuple[int, ...]:
    seen: list[int] = []
    for cell in ctx.cells:
        if cell.seed not in seen:
            seen.append(cell.seed)
    return tuple(seen) if seen else holdout.DRAWS


def load_holdout_context_draws(
    ddir: Path,
    draws: tuple[int, ...] = holdout.DRAWS,
    hide_frac: float = 0.20,
) -> holdout.HoldoutContext:
    """Build `HoldoutContext` for an arbitrary tuple of draw seeds (e.g., `(20, 21)`, `(22, 23)`, `(24, 25)`)."""
    if tuple(draws) == tuple(holdout.DRAWS):
        return holdout.load_holdout_context(ddir, hide_frac=hide_frac)

    ext_dir = (ddir.parent if ddir.name == "core" else ddir) / "external"
    if not ext_dir.exists():
        ext_dir = ddir / "external"
    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    labels = holdout.read_binary(ddir / "labels.tif") & foot
    with rasterio.open(ext_dir / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgm = ds.read(1) > 0
    near = binary_dilation(labels, iterations=holdout.NEAR_LABEL_PX)
    sgmc_off = sgm & ~labels & ~near & foot

    quad = holdout.quadrant_ids(foot)
    comp, n_comp = label(labels, structure=np.ones((3, 3), int))
    comp_size = np.bincount(comp.ravel(), minlength=n_comp + 1)
    all_ids = np.arange(1, n_comp + 1)

    quad_bboxes: dict[int, tuple[slice, slice]] = {}
    collars: dict[int, np.ndarray] = {}
    domains: dict[int, np.ndarray] = {}
    for fold in holdout.FOLDS:
        q = quad == fold
        rows = np.flatnonzero(q.any(axis=1))
        cols = np.flatnonzero(q.any(axis=0))
        r0 = max(0, int(rows[0]) - 6)
        r1 = min(foot.shape[0], int(rows[-1]) + 7)
        c0 = max(0, int(cols[0]) - 6)
        c1 = min(foot.shape[1], int(cols[-1]) + 7)
        quad_bboxes[fold] = (slice(r0, r1), slice(c0, c1))
        collars[fold] = binary_dilation(q, structure=np.ones((3, 3), bool), iterations=holdout.COLLAR_PX) & foot
        domains[fold] = binary_erosion(q, iterations=holdout.DOMAIN_ERODE)

    cells: list[holdout.PreparedCell] = []
    for seed in draws:
        for fold in holdout.FOLDS:
            rng = np.random.default_rng(10_000 * (seed + 1) + fold)
            q = quad == fold
            collar = collars[fold]
            domain = domains[fold]
            touch_collar = np.isin(all_ids, np.unique(comp[collar & labels]))
            in_test = np.isin(all_ids, np.unique(comp[q & labels]))
            test_ids = all_ids[in_test]
            train_ids = all_ids[~touch_collar]
            hid_test = holdout._pick_components(rng, comp_size, test_ids, hide_frac * float((labels & q).sum()))
            hid_train = holdout._pick_components(rng, comp_size, train_ids, hide_frac * float(comp_size[train_ids].sum()))
            hidden_full = np.isin(comp, hid_test)
            hidden_train = np.isin(comp, hid_train)
            visible = labels & ~hidden_full & ~hidden_train

            sl = quad_bboxes[fold]
            active_sub = domain[sl] & ~visible[sl]
            truth_sub = (hidden_full[sl] & domain[sl]) & active_sub
            t_coords = np.nonzero(truth_sub)
            n_t = int(t_coords[0].size)
            dg_sub = distance_transform_edt(~truth_sub)
            k_dg_sub = kernel(dg_sub)
            vis_sub = visible[sl].copy()
            d_vis_sub = (
                distance_transform_edt(~vis_sub).astype(np.float32)
                if vis_sub.any()
                else np.full(vis_sub.shape, 999.0, dtype=np.float32)
            )
            cells.append(
                holdout.PreparedCell(
                    key=f"draw{seed}_fold{fold}",
                    fold=fold,
                    seed=seed,
                    bbox=sl,
                    active_sub=active_sub,
                    truth_coords=t_coords,
                    k_dg_sub=k_dg_sub,
                    n_truth=n_t,
                    visible_sub=vis_sub,
                    d_visible_sub=d_vis_sub,
                    visible_full=visible.copy(),
                )
            )

    sgmc_active = foot & ~labels
    sgmc_truth = sgmc_off & sgmc_active
    sgmc_truth_coords = np.nonzero(sgmc_truth)
    sgmc_n_truth = int(sgmc_truth_coords[0].size)
    sgmc_k_dg = kernel(distance_transform_edt(~sgmc_truth))
    sgmc_quad_truth_coords: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    sgmc_quad_n_truth: dict[int, int] = {}
    for fold in holdout.FOLDS:
        qt = sgmc_truth & (quad == fold)
        tc = np.nonzero(qt)
        sgmc_quad_truth_coords[fold] = tc
        sgmc_quad_n_truth[fold] = int(tc[0].size)

    visible_by_cell = {cell.key: cell.visible_full for cell in cells if cell.visible_full is not None}
    return holdout.HoldoutContext(
        foot=foot,
        labels=labels,
        sgmc_off=sgmc_off,
        near_visible=near,
        quad=quad,
        quad_bboxes=quad_bboxes,
        cells=cells,
        sgmc_truth_coords=sgmc_truth_coords,
        sgmc_k_dg=sgmc_k_dg,
        sgmc_n_truth=sgmc_n_truth,
        sgmc_quad_truth_coords=sgmc_quad_truth_coords,
        sgmc_quad_n_truth=sgmc_quad_n_truth,
        visible_by_cell=visible_by_cell,
    )


def evaluate_censored_or_standard_multi(
    pred_or_cells: np.ndarray | dict[str, np.ndarray],
    ctx: holdout.HoldoutContext,
    b_visible_px: float = 0.0,
    min_vis_truth_dist_px: float = 0.0,
    grid_n: int = 16,
    n_boot: int = 1000,
    seed: int = 20261026,
    name: str = "candidate",
) -> dict:
    """Evaluate binary predictions across arbitrary `draws` with optional `min_vis_truth_dist_px` censoring.

    - When `min_vis_truth_dist_px == 0.0`: standard Hide-and-Recover with zero-truth FP conservation (#41).
    - When `min_vis_truth_dist_px == 5.0`: Fragment-censored (`> 500 m`) Hide-and-Recover (IR-K3-12).
    - When `min_vis_truth_dist_px == 15.0`: Buffered (`> 1.5 km`) truth-to-visible Hide-and-Recover (#60).
    """
    if not np.isfinite(b_visible_px) or b_visible_px < 0:
        raise ValueError("b_visible_px must be finite and nonnegative")
    h, w = ctx.foot.shape
    n_blocks = grid_n * grid_n
    tp_blk = np.zeros(n_blocks, dtype=np.float64)
    fp_blk = np.zeros(n_blocks, dtype=np.float64)
    fn_blk = np.zeros(n_blocks, dtype=np.float64)

    fy, fx = np.nonzero(ctx.foot)
    active_blocks = np.unique(holdout._spatial_block_index(fy, fx, (h, w), grid_n))

    is_cell_dict = isinstance(pred_or_cells, dict)
    base_mask = None if is_cell_dict else require_binary_mask(pred_or_cells, ctx.foot)
    if is_cell_dict and set(pred_or_cells) != {cell.key for cell in ctx.cells}:
        raise ValueError("OOF keys must exactly match the holdout cells")

    folds: dict[str, dict] = {}
    n_censored = 0
    for cell in ctx.cells:
        sl = cell.bbox
        r0, c0 = int(sl[0].start), int(sl[1].start)
        if is_cell_dict:
            raw_cell = np.asarray(pred_or_cells[cell.key])
            domain = ctx.foot if raw_cell.shape == (h, w) else ctx.foot[sl]
            raw_cell = require_binary_mask(raw_cell, domain)
            sub_in = raw_cell[sl] if raw_cell.shape == (h, w) else raw_cell
        else:
            sub_in = base_mask[sl]

        ty_all, tx_all = cell.truth_coords
        if min_vis_truth_dist_px > 0.0 and ty_all.size > 0:
            d_vt = cell.d_vis_sub[ty_all, tx_all]
            keep = d_vt > float(min_vis_truth_dist_px)
            frag_m = ~keep
            n_censored += int(frag_m.sum())
            ty_nf, tx_nf = ty_all[keep], tx_all[keep]
        else:
            frag_m = np.zeros(0, dtype=bool)
            ty_nf, tx_nf = ty_all, tx_all

        gate = cell.active_sub
        if b_visible_px > 0.0 and cell.d_vis_sub is not None:
            gate = gate & (cell.d_vis_sub > b_visible_px)
        if frag_m.any():
            frag_grid = np.zeros(cell.active_sub.shape, dtype=bool)
            frag_grid[ty_all[frag_m], tx_all[frag_m]] = True
            gate = gate & (distance_transform_edt(~frag_grid) > holdout.NEAR_LABEL_PX)

        p_sub = sub_in & gate
        n_emit = int(p_sub.sum())
        n_t = int(ty_nf.size)

        # Conserve false positives even if n_t == 0 (#41 fix)
        if n_t == 0:
            if n_emit > 0:
                py_sub, px_sub = np.nonzero(p_sub)
                p_blk = holdout._spatial_block_index(py_sub + r0, px_sub + c0, (h, w), grid_n)
                np.add.at(fp_blk, p_blk, 1.0)
            folds[cell.key] = {"dti": 0.0, "tp": 0.0, "fp": float(n_emit), "fn": 0.0, "n_truth": 0, "emitted": n_emit}
            continue

        t_blk = holdout._spatial_block_index(ty_nf + r0, tx_nf + c0, (h, w), grid_n)
        if n_emit == 0:
            np.add.at(fn_blk, t_blk, 1.0)
            folds[cell.key] = {"dti": 0.0, "tp": 0.0, "fp": 0.0, "fn": float(n_t), "n_truth": n_t, "emitted": 0}
            continue

        if min_vis_truth_dist_px > 0.0:
            nf_grid = np.zeros(cell.active_sub.shape, dtype=bool)
            nf_grid[ty_nf, tx_nf] = True
            k_dg = kernel(distance_transform_edt(~nf_grid))
        else:
            k_dg = cell.k_dg_sub

        dp_sub = distance_transform_edt(~p_sub)
        t_cred = kernel(dp_sub[ty_nf, tx_nf]).astype(np.float64)
        tp = float(t_cred.sum())
        fn = float(n_t) - tp
        np.add.at(tp_blk, t_blk, t_cred)
        np.add.at(fn_blk, t_blk, 1.0 - t_cred)

        py_sub, px_sub = np.nonzero(p_sub)
        p_blk = holdout._spatial_block_index(py_sub + r0, px_sub + c0, (h, w), grid_n)
        fp_weights = (1.0 - k_dg[p_sub]).astype(np.float64)
        fp = float(fp_weights.sum())
        np.add.at(fp_blk, p_blk, fp_weights)

        dti_c = float(tp / (tp + ALPHA * fp + BETA * fn + EPS))
        folds[cell.key] = {
            "dti": dti_c,
            "coverage": float(tp / n_t),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "n_truth": n_t,
            "emitted": n_emit,
        }

    pooled, ci95, boots = holdout._cluster_bootstrap_pooled_dti(
        tp_blk, fp_blk, fn_blk, active_blocks, n_boot=n_boot, seed=seed
    )
    draws_present = _ctx_draws(ctx)
    per_quad = {
        holdout.FOLD_NAMES[f]: float(np.mean([folds[f"draw{ds}_fold{f}"]["dti"] for ds in draws_present]))
        for f in holdout.FOLDS
    }
    ver = (
        EVAL_BUF1500M_24CELL
        if min_vis_truth_dist_px >= 15.0
        else (EVAL_FRAG500M_24CELL if min_vis_truth_dist_px > 0.0 else EVAL_V31_24CELL)
    )
    return {
        "candidate_id": name,
        "evaluator_version": ver,
        "score_label": "HOLDOUT-DTI",
        "b_visible_px": float(b_visible_px),
        "min_vis_truth_dist_px": float(min_vis_truth_dist_px),
        "n_censored_positives": int(n_censored),
        "n_withheld_positives": int(sum(v["n_truth"] for v in folds.values())),
        "n_spatial_clusters": int(active_blocks.size),
        "n_bootstrap_reps": int(n_boot),
        "pooled_dti": pooled,
        "ci95_cluster_bootstrap": ci95,
        "fold_mean_dti": float(np.mean([v["dti"] for v in folds.values()])),
        "per_quadrant_dti": per_quad,
        "folds": folds,
        "_block_totals": (tp_blk, fp_blk, fn_blk, active_blocks),
        "_boots": boots,
    }
