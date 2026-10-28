#!/usr/bin/env python3
"""Lane H-K3C (2026-10-28): 24-cell power-expanded holdout, Kostrov strain-deficit prior, budget operating point.

Preregistration: docs/research/k3c-preregistration-20261028.md  (locked before this script ran).

Reuses the shared template tools only (Protocol Rule 2):
  - .cache/gems_work/{feature_stack,crsb_gub_extra_16ch,csst_bghf_extra_6ch}.npy
  - gems32.holdout (load_holdout_context(draws=...), evaluate_hide_and_recover, evaluate_sgmc_with_ci,
    _cluster_bootstrap_pooled_dti) and run_crsb_ablation.evaluate_detached_and_censored
  - gems32.csst_bghf (fit_stratified_sarpu_classifier, predict_chunked_57ch, build_csst_surface, emit_csst_submodular)
  - scripts/submission_writer.py, scripts/promotion_gate.py, run_csst_ablation.scan_complete_registry_csst

Memory: draw pairs are processed one HoldoutContext (8 cells) at a time; per-block TP/FP/FN totals are pooled
over all 24 cells and bootstrapped once (256 spatial blocks x 1000 reps), so the CI is the exact analogue of the
8-cell evaluator with three times the withheld positives.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("GDAL_CACHEMAX", "32")

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for sub in ("src", "scripts"):
    if str(ROOT / sub) not in sys.path:
        sys.path.insert(0, str(ROOT / sub))

from gems32 import crsb_gub, csst_bghf, holdout  # noqa: E402
from gems32.paths import data_dir, evidence_dir, work_dir  # noqa: E402
from karage3 import strain_deficit  # noqa: E402
import promotion_gate  # noqa: E402
import run_crsb_ablation as crsb_runner  # noqa: E402
import run_csst_ablation as csst_runner  # noqa: E402
import submission_writer  # noqa: E402

LANE_ID = "H-K3C"
DRAW_PAIRS = ((20, 21), (22, 23), (24, 25))
ALL_DRAWS = tuple(d for pair in DRAW_PAIRS for d in pair)
EVALUATOR_VERSION_24 = "GEMSDOE32-HIDE-RECOVER-v3.1-24cell"
TARGET_BUDGET = csst_bghf.TARGET_BUDGET
B_COLLAR_PX = csst_bghf.B_COLLAR_PX
AXIAL_SEP_PX = csst_bghf.AXIAL_MIN_SEP_PX
E3_BUDGETS = (30_000, 44_090)
ARMS_E12 = ("CTRL", "E1", "E2")


def rss_mb() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg} (RSS={rss_mb()} MB)", flush=True)


class Pooled:
    """Accumulates per-block TP/FP/FN over many contexts; one bootstrap at the end."""

    def __init__(self) -> None:
        self.tp = None
        self.fp = None
        self.fn = None
        self.active = None
        self.n_withheld = 0
        self.cells: dict[str, dict] = {}

    def add(self, res: dict, key: str = "_block_totals", n_key: str = "n_withheld_positives") -> None:
        tp, fp, fn, active = res[key]
        if self.tp is None:
            self.tp, self.fp, self.fn = tp.copy(), fp.copy(), fn.copy()
            self.active = np.asarray(active).copy()
        else:
            self.tp += tp
            self.fp += fp
            self.fn += fn
        self.n_withheld += int(res.get(n_key, 0))
        for k, v in (res.get("folds") or {}).items():
            self.cells[k] = {kk: vv for kk, vv in v.items() if not isinstance(vv, np.ndarray)}

    def finish(self) -> dict:
        pooled, ci, boots = holdout._cluster_bootstrap_pooled_dti(self.tp, self.fp, self.fn, self.active)
        per_fold = {}
        for f, name in zip(holdout.FOLDS, holdout.FOLD_NAMES):
            vals = [v["dti"] for k, v in self.cells.items() if k.endswith(f"_fold{f}")]
            per_fold[name] = round(float(np.mean(vals)), 6) if vals else None
        return {
            "pooled_dti": round(float(pooled), 6),
            "ci95": [round(float(ci[0]), 6), round(float(ci[1]), 6)],
            "n_withheld_positives": int(self.n_withheld),
            "n_cells": len(self.cells),
            "per_quadrant_mean_cell_dti": per_fold,
            "_boots": boots,
        }


def paired(a: np.ndarray, b: np.ndarray) -> dict:
    d = np.asarray(a, np.float64) - np.asarray(b, np.float64)
    return {
        "mean_boot_delta": round(float(d.mean()), 6),
        "ci95": [round(float(np.percentile(d, 2.5)), 6), round(float(np.percentile(d, 97.5)), 6)],
        "prob_positive": round(float((d > 0).mean()), 4),
    }


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    t0 = time.time()
    ddir, wdir, edir = data_dir(), work_dir(), evidence_dir()
    out_dir = ROOT / "docs" / "k3c" / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "k3c").mkdir(parents=True, exist_ok=True)

    base_stack = np.load(wdir / "feature_stack.npy", mmap_mode="r")
    crsb_stack = np.load(wdir / "crsb_gub_extra_16ch.npy", mmap_mode="r")
    csst_stack = np.load(wdir / "csst_bghf_extra_6ch.npy", mmap_mode="r")

    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    labels = holdout.read_binary(ddir / "labels.tif") & foot
    quad = holdout.quadrant_ids(foot)
    lidar_valid = (np.asarray(crsb_stack[:, :, 10], dtype=np.float32) > 0.5) & foot
    lidar_gap = foot & ~lidar_valid
    disk2 = crsb_runner._disk_mask(B_COLLAR_PX)
    elig_full = foot & ~binary_dilation(labels, structure=disk2)
    n_elig_full = int(elig_full.sum())

    fold_train, fold_domain = {}, {}
    for f in holdout.FOLDS:
        q = quad == f
        collar = binary_dilation(q, structure=np.ones((3, 3), bool), iterations=holdout.COLLAR_PX) & foot
        fold_train[f] = foot & ~collar
        fold_domain[f] = binary_erosion(q, iterations=holdout.DOMAIN_ERODE) & foot

    # Champion-rule control inputs (D2.8 parent, gated per cell by visible B=2 inside the evaluator; IR-K3-09)
    scored_dir = (ddir.parent if ddir.name == "core" else ddir) / "scored"
    with rasterio.open(scored_dir / "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif") as ds:
        a = ds.read(1)
    d28_parent = np.isfinite(a) & (a > 0) & foot
    del a
    cman = json.loads((ROOT / "registry" / "complete_registry_manifest.json").read_text())
    champ_entry = next(r for r in cman["rasters"] if r["sha256"].startswith("c55bafc47005"))
    with rasterio.open(ROOT / champ_entry["local"]) as ds:
        champ_mask = (ds.read(1) > 0) & foot

    # Pooled accumulators: hide-and-recover (HR) and detached>=600m (DET) for every arm
    hr = {k: Pooled() for k in ARMS_E12 + tuple(f"E3_{b}" for b in E3_BUDGETS)}
    det = {k: Pooled() for k in hr}
    p_dual_live = np.zeros(foot.shape, dtype=np.float32)
    prior_canary_scores, prior_canary_truth = [], []
    cell_log = []

    # ------------------------------------------------------------------ pass over 3 draw pairs (24 cells)
    for pair in DRAW_PAIRS:
        log(f"HoldoutContext draws={pair}")
        ctx = holdout.load_holdout_context(ddir, draws=pair)
        e1_cells, e2_cells = {}, {}
        e3_cells = {b: {} for b in E3_BUDGETS}
        for cell in ctx.cells:
            sl = cell.bbox
            pred_reg = (ctx.quad == cell.fold) & foot
            tr = fold_train[cell.fold]
            vis_tr = cell.visible_full & tr
            cache = wdir / f"csst_cell_{cell.key}_mdual57.npy"
            if cache.exists():
                pd_cell = np.load(cache)
            else:
                clf_full = csst_bghf.fit_stratified_sarpu_classifier(
                    base_stack, crsb_stack, csst_stack, tr, vis_tr, foot, col_indices=None,
                    seed=9100 + cell.seed * 10 + cell.fold)
                clf_noli = csst_bghf.fit_stratified_sarpu_classifier(
                    base_stack, crsb_stack, csst_stack, tr, vis_tr, foot,
                    col_indices=csst_bghf.MNOLIDAR_COL_INDICES_52, seed=9500 + cell.seed * 10 + cell.fold)
                cy, cx = np.nonzero(tr & lidar_valid)
                gy, gx = np.nonzero(tr & lidar_gap)
                cal_li = np.zeros(foot.shape, bool)
                cal_gp = np.zeros(foot.shape, bool)
                cal_li[cy[::5], cx[::5]] = True
                cal_gp[gy[::5], gx[::5]] = True
                del cy, cx, gy, gx
                pf = csst_bghf.predict_chunked_57ch(clf_full, base_stack, crsb_stack, csst_stack, pred_reg | cal_li, col_indices=None)
                pn = csst_bghf.predict_chunked_57ch(clf_noli, base_stack, crsb_stack, csst_stack, (pred_reg & lidar_gap) | cal_gp,
                                                    col_indices=csst_bghf.MNOLIDAR_COL_INDICES_52)
                del clf_full, clf_noli
                pd_all = crsb_gub.calibrate_gap_quantiles(pf, pn, cal_li, cal_gp, pred_reg & lidar_gap, blend_raw=0.25)
                pd_cell = np.where(pred_reg, pd_all, np.float32(0.0)).astype(np.float32)
                np.save(cache, pd_cell)
                del pf, pn, pd_all, cal_li, cal_gp
            p_dual_live[pred_reg] += np.float32(1.0 / len(ALL_DRAWS)) * pd_cell[pred_reg]

            elig_sub = (fold_domain[cell.fold] & ~binary_dilation(cell.visible_full, structure=disk2))[sl]
            b_cell = int(round(TARGET_BUDGET * (elig_sub.sum() / n_elig_full)))

            # E1: shipped CSST-BGHF EXP-3 surface
            s_e1 = csst_bghf.build_csst_surface(pd_cell, crsb_stack, csst_stack, cell.visible_full, foot,
                                                region_mask=pred_reg, mode="exp3_coulomb_maxenv")
            d_sub, _ = csst_bghf.emit_csst_submodular(s_e1[sl], cell.visible_full[sl], elig_sub, foot[sl],
                                                       budget=b_cell, min_sep_px=AXIAL_SEP_PX)
            m = np.zeros(foot.shape, bool)
            m[sl] = d_sub
            e1_cells[cell.key] = m

            # E2: E1 surface x fold-visible strain-deficit prior (H-K3C-1)
            prior = strain_deficit.strain_deficit_prior(base_stack, cell.visible_full, foot)
            s_e2 = np.clip(s_e1 * prior, 0.0, 1.0).astype(np.float32)
            d_sub, _ = csst_bghf.emit_csst_submodular(s_e2[sl], cell.visible_full[sl], elig_sub, foot[sl],
                                                       budget=b_cell, min_sep_px=AXIAL_SEP_PX)
            m = np.zeros(foot.shape, bool)
            m[sl] = d_sub
            e2_cells[cell.key] = m

            # Leakage canary for the prior alone (hidden truth vs other active pixels), subsampled
            ty, tx = cell.truth_coords
            act = cell.active_sub
            pr_sub = prior[sl]
            neg = np.flatnonzero(act.ravel())
            rng = np.random.default_rng(cell.seed * 100 + cell.fold)
            neg = rng.choice(neg, size=min(neg.size, 20_000), replace=False)
            prior_canary_scores.append(np.concatenate([pr_sub[ty, tx], pr_sub.ravel()[neg]]))
            prior_canary_truth.append(np.concatenate([np.ones(ty.size), np.zeros(neg.size)]))

            # E3 budgets are emitted for BOTH surfaces now (cheap) and selected by the preregistered rule later
            for b in E3_BUDGETS:
                b_c = int(round(b * (elig_sub.sum() / n_elig_full)))
                e3_cells[b][cell.key] = {}
                for tag, surf in (("E1", s_e1), ("E2", s_e2)):
                    d_sub, _ = csst_bghf.emit_csst_submodular(surf[sl], cell.visible_full[sl], elig_sub, foot[sl],
                                                               budget=b_c, min_sep_px=AXIAL_SEP_PX)
                    m = np.zeros(foot.shape, bool)
                    m[sl] = d_sub
                    e3_cells[b][cell.key][tag] = m
            cell_log.append({"cell": cell.key, "budget": b_cell, "n_truth": int(cell.n_truth),
                             "prior_median_at_dots_e2": round(float(np.median(prior[e2_cells[cell.key]])), 4)})
            del pd_cell, s_e1, s_e2, prior, pr_sub
            gc.collect()
            log(f"  cell {cell.key} done")

        # Evaluate this context's 8 cells for every arm and pool block totals
        res = holdout.evaluate_hide_and_recover(d28_parent, ctx, b_visible_px=B_COLLAR_PX, name="CTRL")
        hr["CTRL"].add(res)
        det["CTRL"].add(crsb_runner.evaluate_detached_and_censored(d28_parent, ctx, b_visible_px=B_COLLAR_PX)["detached_600m"], n_key="n_withheld_positives")
        for tag, cells in (("E1", e1_cells), ("E2", e2_cells)):
            res = holdout.evaluate_hide_and_recover(cells, ctx, b_visible_px=B_COLLAR_PX, name=tag)
            hr[tag].add(res)
            det[tag].add(crsb_runner.evaluate_detached_and_censored(cells, ctx, b_visible_px=B_COLLAR_PX)["detached_600m"], n_key="n_withheld_positives")
        # E3 pooled per (budget, surface) — keep both surfaces' totals separately
        for b in E3_BUDGETS:
            for tag in ("E1", "E2"):
                key = f"E3_{b}"
                k2 = f"{key}_{tag}"
                hr.setdefault(k2, Pooled())
                det.setdefault(k2, Pooled())
                cells = {ck: cv[tag] for ck, cv in e3_cells[b].items()}
                res = holdout.evaluate_hide_and_recover(cells, ctx, b_visible_px=B_COLLAR_PX, name=k2)
                hr[k2].add(res)
                det[k2].add(crsb_runner.evaluate_detached_and_censored(cells, ctx, b_visible_px=B_COLLAR_PX)["detached_600m"], n_key="n_withheld_positives")
        del ctx, e1_cells, e2_cells, e3_cells
        gc.collect()
        log(f"draw pair {pair} evaluated")

    # ------------------------------------------------------------------ pooled 24-cell results
    HR = {k: v.finish() for k, v in hr.items() if v.tp is not None}
    DET = {k: v.finish() for k, v in det.items() if v.tp is not None}
    canary_auc = float(roc_auc_score(np.concatenate(prior_canary_truth), np.concatenate(prior_canary_scores)))
    canary_oriented = max(canary_auc, 1.0 - canary_auc)
    log(f"24-cell HR: CTRL={HR['CTRL']['pooled_dti']} E1={HR['E1']['pooled_dti']} E2={HR['E2']['pooled_dti']} | prior canary AUC={canary_oriented:.4f}")

    # ------------------------------------------------------------------ live (full-catalogue) emission
    ctx8 = holdout.load_holdout_context(ddir)  # template 8-cell context for SGMC-cal + 9-site audit
    s_live_e1 = csst_bghf.build_csst_surface(p_dual_live, crsb_stack, csst_stack, labels, foot, mode="exp3_coulomb_maxenv")
    prior_live, parts = strain_deficit.strain_deficit_prior(base_stack, labels, foot, return_parts=True)
    s_live_e2 = np.clip(s_live_e1 * prior_live, 0.0, 1.0).astype(np.float32)
    live = {}
    for tag, surf in (("E1", s_live_e1), ("E2", s_live_e2)):
        dots, elog = csst_bghf.emit_csst_submodular(surf, labels, elig_full, foot, budget=TARGET_BUDGET, min_sep_px=AXIAL_SEP_PX)
        sg = holdout.evaluate_sgmc_with_ci(dots, ctx8, name=tag)
        live[tag] = {"dots": dots, "sg": sg, "emit_log": elog}
        log(f"live {tag}: dots={int(dots.sum())} SGMC-cal={sg['sgmc_prevalence_calibrated_dti']:.6f}")
    champ_sg = holdout.evaluate_sgmc_with_ci(champ_mask, ctx8, name="CHAMPION_02778")

    # Preregistered selection: E2 ships iff paired HR delta > 0 AND SGMC-cal(E2) >= SGMC-cal(E1)
    d_e2_e1 = paired(HR["E2"]["_boots"], HR["E1"]["_boots"])
    e2_wins = bool(d_e2_e1["mean_boot_delta"] > 0 and live["E2"]["sg"]["sgmc_prevalence_calibrated_dti"] >= live["E1"]["sg"]["sgmc_prevalence_calibrated_dti"])
    best_surf_tag = "E2" if e2_wins else "E1"
    # E3: budget choice on the winning surface; ship a different budget only if its paired CI lower bound > 0
    e3_rows = {}
    ship_budget = TARGET_BUDGET
    for b in E3_BUDGETS:
        k2 = f"E3_{b}_{best_surf_tag}"
        dd = paired(HR[k2]["_boots"], HR[best_surf_tag]["_boots"])
        e3_rows[str(b)] = {"hr": {kk: vv for kk, vv in HR[k2].items() if kk != "_boots"},
                           "detached_600m": {kk: vv for kk, vv in DET[k2].items() if kk != "_boots"},
                           "paired_vs_37654": dd}
    best_b = max(E3_BUDGETS, key=lambda b: HR[f"E3_{b}_{best_surf_tag}"]["pooled_dti"])
    if HR[f"E3_{best_b}_{best_surf_tag}"]["pooled_dti"] > HR[best_surf_tag]["pooled_dti"] and e3_rows[str(best_b)]["paired_vs_37654"]["ci95"][0] > 0:
        ship_budget = best_b
    ship_surf = s_live_e2 if best_surf_tag == "E2" else s_live_e1
    if ship_budget != TARGET_BUDGET:
        ship_dots, ship_log = csst_bghf.emit_csst_submodular(ship_surf, labels, elig_full, foot, budget=ship_budget, min_sep_px=AXIAL_SEP_PX)
        ship_sg = holdout.evaluate_sgmc_with_ci(ship_dots, ctx8, name="SHIP")
    else:
        ship_dots, ship_log, ship_sg = live[best_surf_tag]["dots"], live[best_surf_tag]["emit_log"], live[best_surf_tag]["sg"]
    ship_hr_key = best_surf_tag if ship_budget == TARGET_BUDGET else f"E3_{ship_budget}_{best_surf_tag}"
    log(f"SHIP: surface={best_surf_tag} budget={ship_budget} dots={int(ship_dots.sum())}")

    # ------------------------------------------------------------------ registry uniqueness scan (surface + final dots)
    log("registry uniqueness scan")
    uniq = csst_runner.scan_complete_registry_csst(ship_surf, ship_dots, foot, ddir)
    nine = crsb_runner.audit_nine_focus_sites(ctx8, ship_surf, ship_dots, uniq)
    for sr in nine.get("sites", []):
        if isinstance(sr.get("nodata"), float) and np.isnan(sr["nodata"]):
            sr["nodata"] = None
    (edir / "nine-site-audit-k3c-20261028.json").write_text(json.dumps(nine, indent=2, default=str) + "\n")

    d_cat = distance_transform_edt(~labels)
    d_at = d_cat[ship_dots]
    alloc = {
        "total_emitted_dots": int(ship_dots.sum()),
        "lidar_gap_dot_frac": round(float((ship_dots & lidar_gap).sum()) / max(int(ship_dots.sum()), 1), 6),
        "near_apron_2_8px_frac": round(float((d_at <= 8.0).mean()), 6),
        "stepover_8_35px_frac": round(float(((d_at > 8.0) & (d_at <= 35.0)).mean()), 6),
        "far_field_gt1500m_frac": round(float((d_at > 15.0).mean()), 6),
        "overlap_3px_vs_champion_02778": round(float((distance_transform_edt(~champ_mask)[ship_dots] <= 3.0).mean()), 6),
        "overlap_3px_vs_e1_live": round(float((distance_transform_edt(~live["E1"]["dots"])[ship_dots] <= 3.0).mean()), 6),
        "prior_live_median_at_dots": round(float(np.median(prior_live[ship_dots])), 4),
        "prior_live_quantiles_footprint": [round(float(x), 4) for x in np.percentile(prior_live[foot], [5, 25, 50, 75, 95])],
        "strain_median_ratio": round(float(parts["median_ratio"]), 6),
    }
    del d_cat, d_at

    # ------------------------------------------------------------------ write validated GeoTIFF + ZIP
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = f"h-k3c-{'strain-deficit' if best_surf_tag == 'E2' else 'csst-bghf-24cell'}-d31-b{ship_budget}"
    note = (f"H-K3C {best_surf_tag}: CSST-BGHF{' x Kostrov strain-deficit prior' if best_surf_tag == 'E2' else ''} "
            f"d=3.1 B=2 {ship_budget}d [0,1] zeros; 24-cell HR {HR[ship_hr_key]['pooled_dti']:.4f}")
    assert len(note) <= 140, len(note)
    for old in out_dir.iterdir():
        if old.is_file():
            old.unlink()
    receipt = submission_writer.write_validated_submission(
        mask_or_probs=ship_dots, slug=slug,
        candidate_meta={
            "candidate_id": f"{LANE_ID}-{best_surf_tag}-B{ship_budget}",
            "description": note,
            "submission_note_zeros": note, "submission_note_nan": note,
            "catalogue_hidden_mean": HR[ship_hr_key]["pooled_dti"],
            "catalogue_hidden_per_quadrant": HR[ship_hr_key]["per_quadrant_mean_cell_dti"],
            "sgmc_prevalence_calibrated_dti": ship_sg["sgmc_prevalence_calibrated_dti"],
            "slot_decision": "SEE_RUN_CARD",
        },
        ddir=ddir, out_dir=out_dir, timestamp_tag=ts, prefix="gemsdoekarage3")
    nan_path = out_dir / receipt["nan_tif"]["filename"]
    if nan_path.exists():
        nan_path.unlink()  # never leave a NaN-outside hazard file downloadable
    tif_path = out_dir / receipt["zeros_tif"]["filename"]
    zip_path = Path(receipt["zeros_zip"]["path"])
    tif_sha = sha256_file(tif_path)
    assert tif_sha == receipt["zeros_tif"]["sha256"]

    # Independent re-read of the saved bytes
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        saved = {
            "count": ds.count, "dtype": str(ds.dtypes[0]), "crs": str(ds.crs), "shape": list(ds.shape),
            "transform": list(ds.transform)[:6], "nodata": ds.nodata,
        }
    saved.update({
        "all_finite_full_grid": bool(np.isfinite(arr).all()),
        "min": float(arr.min()), "max": float(arr.max()),
        "n_positive": int((arr > 0).sum()),
        "positives_on_catalogue": int(((arr > 0) & labels).sum()),
        "positives_equal_emitted": bool(int((arr > 0).sum()) == int(ship_dots.sum())),
    })
    del arr

    # ------------------------------------------------------------------ LLI live projection (NOT a score)
    lli = {"status": "not_run"}
    try:
        cmd = [sys.executable, str(ROOT / "scripts" / "project_lli.py"), str(tif_path), "--out", str(edir / "k3c_lli_projection.json")]
        pr = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        lli = {"status": "ok" if pr.returncode == 0 else f"exit {pr.returncode}", "stderr_tail": pr.stderr[-800:]}
        if (edir / "k3c_lli_projection.json").exists():
            lli["result"] = json.loads((edir / "k3c_lli_projection.json").read_text())
    except Exception as exc:  # noqa: BLE001
        lli = {"status": f"error: {exc}"}

    # ------------------------------------------------------------------ gates, run card
    canary57 = json.loads((edir / "leakage-canary-57ch.json").read_text())
    feature_auc = [r["oriented_auc"] for r in canary57["per_channel"]] + [round(canary_oriented, 6)]
    d_ship_ctrl = paired(HR[ship_hr_key]["_boots"], HR["CTRL"]["_boots"])
    d_e1_ctrl = paired(HR["E1"]["_boots"], HR["CTRL"]["_boots"])
    d_det_ship_ctrl = paired(DET[ship_hr_key]["_boots"], DET["CTRL"]["_boots"])
    d_sg_ship_champ = paired(ship_sg["_cal_boots"], champ_sg["_cal_boots"])

    def strip(d: dict) -> dict:
        return {k: v for k, v in d.items() if not k.startswith("_")}

    entries, _ = crsb_runner.collect_complete_registry(ddir)
    inventory = sorted(entries.keys())
    manifest_sha = sha256_file(ROOT / "registry" / "complete_registry_manifest.json")
    # Build per-raster comparison rows for the gate from the scan (surface Spearman + null-calibrated overlap)
    comp_surface, comp_final = [], []
    rows_by_sha = {}
    for r in uniq.get("top15_by_abs_surface_spearman", []) + uniq.get("top15_discrete_by_overlap", []):
        rows_by_sha[r["sha256"]] = r
    # full rows were not retained by the scan helper; re-derive from its complete row list if available
    full_rows = uniq.pop("_all_rows", [])
    entry_paths = uniq.pop("_entry_paths", {})
    # Null-calibrated excess overlap needs p0 (that raster's own 3-px footprint coverage) only when the
    # literal overlap exceeds 0.70, because (obs - p0)/(1 - p0) <= obs for obs <= 1.
    for r in full_rows:
        obs = float(r["within_3px_fraction"])
        if obs > 0.70 and r["sha256"] in entry_paths:
            with rasterio.open(entry_paths[r["sha256"]]) as ds:
                oa = ds.read(1)
            od = np.isfinite(oa) & (oa > 0) & foot
            del oa
            p0 = float((distance_transform_edt(~od)[foot] <= 3.0).mean()) if od.any() else 0.0
            del od
            r["p0"] = round(p0, 6)
            r["excess_overlap_3px"] = round(max(0.0, (obs - p0) / max(1.0 - p0, 1e-6)), 6)
        else:
            r["p0"] = None
            r["excess_overlap_3px"] = round(obs, 6)
    (edir / "k3c-registry-uniqueness-scan.json").write_text(json.dumps({**uniq, "all_rows": full_rows}, indent=2, default=str) + "\n")
    for r in full_rows:
        comp_surface.append({"sha256": r["sha256"], "abs_spearman": abs(r["surface_spearman"]), "overlap_3px": 0.0})
        comp_final.append({"sha256": r["sha256"], "abs_spearman": abs(r["dots_spearman"]),
                           "overlap_3px": r["excess_overlap_3px"], "literal_overlap_3px": r["within_3px_fraction"],
                           "footprint_3px_coverage_p0": r["p0"]})
    registry_block = {
        "inventory_sha256": inventory,
        "manifest_sha256": manifest_sha,
        "duplicate_rule": "null-calibrated excess overlap (obs - p0)/(1 - p0) <= 0.70 vs every registry raster; literal values reported alongside (IR-K3-17)",
        "surface": {"complete": bool(comp_surface) and len(comp_surface) == len(inventory),
                    "comparisons": comp_surface,
                    "max_abs_spearman": max((c["abs_spearman"] for c in comp_surface), default=1.0),
                    "max_overlap_3px": 0.0},
        "final_dots": {"complete": bool(comp_final) and len(comp_final) == len(inventory),
                       "comparisons": comp_final,
                       "max_abs_spearman": max((c["abs_spearman"] for c in comp_final), default=1.0),
                       "max_overlap_3px": max((c["overlap_3px"] for c in comp_final), default=1.0),
                       "max_literal_overlap_3px": max((c["literal_overlap_3px"] for c in comp_final), default=1.0),
                       "discrete_le100k_max_literal_overlap_3px": uniq["worst_discrete_3px_overlap"]["within_3px_fraction"],
                       "worst_discrete_raster": uniq["worst_discrete_3px_overlap"]["name"]},
        "literal_all_rasters_final_passed": bool(uniq["worst_literal_unfiltered_overlap"]["within_3px_fraction"] <= 0.70),
        "null_calibrated_all_rasters_final_passed": bool(max((c["overlap_3px"] for c in comp_final), default=1.0) <= 0.70),
    }

    card = {
        "schema_version": "karage3-runcard-v3",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/2d8508cc-gemsdoekarage3",
        "assigned_lane": f"{LANE_ID}: CSST-BGHF blind-conduit detector re-measured on a 24-cell holdout, Kostrov strain-deficit regional prior (H-K3C-1), budget operating point",
        "hypothesis": "Geodetic strain (Band 04 geod_2ndinv) that is not accounted for by visible catalogued fault length must be accommodated by unmapped faults; re-allocating the CSST-BGHF dot budget toward strain-deficit regions raises recovery of off-catalogue faults.",
        "mechanism": "Kostrov (1974) moment balance: prior = clip((S/(D+0.25) / median)^0.5, 0.5, 2.0) with S = footprint rank of Band 04 and D = 10-km Gaussian density of the fold-visible catalogue; multiplies the CSST-BGHF EXP-3 surface before min_sep 3.1 px CELF emission with a B=2 px visible collar.",
        "named_non_fault_mimic": "Viscoelastic post-seismic relaxation of the 1915 Pleasant Valley and 1954 Dixie Valley-Fairview Peak sequences (elevated strain rate without permanent fault loading); distributed Walker Lane block rotation.",
        "experiments_run": 3, "budget_cap_experiments": 3,
        "experiments": {
            "E1_power_24cell": {"CTRL_champion_rule": strip(HR["CTRL"]), "E1_csst_bghf": strip(HR["E1"]),
                                "paired_E1_minus_CTRL": d_e1_ctrl,
                                "detached_600m": {"CTRL": strip(DET["CTRL"]), "E1": strip(DET["E1"])}},
            "E2_strain_deficit": {"E2": strip(HR["E2"]), "paired_E2_minus_E1": d_e2_e1,
                                  "detached_600m_E2": strip(DET["E2"]),
                                  "sgmc_cal_live": {"E1": round(live["E1"]["sg"]["sgmc_prevalence_calibrated_dti"], 6),
                                                    "E2": round(live["E2"]["sg"]["sgmc_prevalence_calibrated_dti"], 6),
                                                    "champion_02778": round(champ_sg["sgmc_prevalence_calibrated_dti"], 6)},
                                  "prior_alone_oriented_auc": round(canary_oriented, 6),
                                  "e2_passes_preregistered_rule": e2_wins},
            "E3_budget": {"surface": best_surf_tag, "rows": e3_rows, "shipped_budget": ship_budget},
            "cells": cell_log,
        },
        "holdout": {
            "evidence_class": "HOLDOUT-DTI", "evaluator_version": EVALUATOR_VERSION_24,
            "withheld_positives": int(HR[ship_hr_key]["n_withheld_positives"]),
            "dti": HR[ship_hr_key]["pooled_dti"], "ci95": HR[ship_hr_key]["ci95"],
            "paired_delta_vs_champion_02778": d_ship_ctrl["mean_boot_delta"],
            "paired_delta_ci95": d_ship_ctrl["ci95"], "paired_prob_positive": d_ship_ctrl["prob_positive"],
            "same_evaluator_current_best": bool(HR[ship_hr_key]["pooled_dti"] > HR["CTRL"]["pooled_dti"]),
            "champion_02778_same_evaluator_dti": HR["CTRL"]["pooled_dti"],
            "champion_02778_same_evaluator_ci95": HR["CTRL"]["ci95"],
            "detached_600m": {"dti": DET[ship_hr_key]["pooled_dti"], "ci95": DET[ship_hr_key]["ci95"],
                              "champion_02778_dti": DET["CTRL"]["pooled_dti"], "paired_delta_ci95": d_det_ship_ctrl["ci95"]},
            "sgmc_off_catalogue_v3": {"evaluator_version": holdout.SGMC_EVALUATOR_VERSION,
                                      "n_withheld_positives": int(ship_sg["n_withheld_positives"]),
                                      "prevalence_calibrated_dti": round(ship_sg["sgmc_prevalence_calibrated_dti"], 6),
                                      "calibrated_ci95": [round(x, 6) for x in ship_sg["sgmc_calibrated_ci95"]],
                                      "champion_02778_calibrated_dti": round(champ_sg["sgmc_prevalence_calibrated_dti"], 6),
                                      "paired_delta_ci95": d_sg_ship_champ["ci95"]},
        },
        "feature_auc": feature_auc,
        "leakage_canary": {"passed": bool(max(max(x, 1 - x) for x in feature_auc) <= 0.90), "threshold_auc": 0.90,
                           "n_features_tested": len(feature_auc), "max_oriented_auc": round(max(max(x, 1 - x) for x in feature_auc), 6),
                           "strain_deficit_prior_alone_auc": round(canary_oriented, 6)},
        "registry": registry_block,
        "registry_summary": {
            "unique_rasters_checked": uniq["n_unique_rasters_checked"],
            "surface_max_abs_spearman": abs(uniq["worst_surface_spearman_all"]["surface_spearman"]),
            "surface_worst_raster": uniq["worst_surface_spearman_all"]["name"],
            "discrete_le100k_max_literal_3px_overlap": uniq["worst_discrete_3px_overlap"]["within_3px_fraction"],
            "discrete_worst_raster": uniq["worst_discrete_3px_overlap"]["name"],
            "focus9_max_3px_overlap": uniq["worst_focus9_3px_overlap"]["within_3px_fraction"],
            "literal_worst_any_raster": uniq["worst_literal_unfiltered_overlap"],
            "lattice_null_calibration": uniq["space_filling_lattice_null_calibration"],
            "over70_blankets": uniq["continuous_or_ultradense_over_70pct"],
            "per_focus_site": uniq["per_focus_site"],
        },
        "spatial_allocation": alloc,
        "live_ledger_projection": lli,
        "raster_sha256": tif_sha, "zip_sha256": receipt["zeros_zip"]["sha256"],
        "validator": {
            "saved_bytes_checked": True,
            "single_band": bool(saved["count"] == 1),
            "finite_inside": bool(receipt["zeros_tif"]["checks"]["in_footprint_all_finite"]),
            "full_grid_zero_nan": bool(saved["all_finite_full_grid"]),
            "range_0_1": bool(saved["min"] >= 0.0 and saved["max"] <= 1.0),
            "whole_array_finite_range": bool(saved["all_finite_full_grid"] and saved["min"] >= 0.0 and saved["max"] <= 1.0),
            "crs_match": bool(saved["crs"] == "EPSG:32611"),
            "shape_match": bool(saved["shape"] == [3730, 3292]),
            "transform_match": bool(np.allclose(saved["transform"], [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0])),
            "zero_on_catalogue_leakage": bool(saved["positives_on_catalogue"] == 0),
            "raster_sha256": tif_sha,
        },
        "validator_output": {"writer": receipt["zeros_tif"], "independent_reread": saved},
        "submission_name": tif_path.name, "submission_file": f"docs/k3c/downloads/{tif_path.name}",
        "zip_submission_name": zip_path.name, "zip_submission_file": f"docs/k3c/downloads/{zip_path.name}",
        "note": note, "submission_note": note,
        "elapsed_seconds": round(time.time() - t0, 1), "peak_rss_mb": rss_mb(),
    }
    card["shipped_arm"] = best_surf_tag
    card["e2_result"] = "promote-candidate" if e2_wins else "negative"
    if best_surf_tag == "E1":
        card["tested_hypothesis_E2"], card["tested_mechanism_E2"] = card["hypothesis"], card["mechanism"]
        card["hypothesis"] = ("Shipped arm E1 = CSST-BGHF (Coulomb-shadow + Baranov leach + Euler N0 + bajada hinge features, Dual-57 stratified "
                              "SAR-PU OOF surface, CELF emission min_sep 3.1 px, B=2 px visible collar). The tested H-K3C-1 strain-deficit prior (E2) "
                              "was NEGATIVE and is not in the shipped file.")
        card["mechanism"] = "Blind-conduit operators (docs/research/csst-bghf-preregistration-20261028.md) with submodular CELF budget allocation; E1 re-measured on 24 cells."
    gate = promotion_gate.assess(card)
    card["promotion_gate"] = gate
    card["verdict"] = gate["verdict"]
    card["ok_to_submit"] = bool(gate["verdict"] == "promote")
    card["selector_required"] = True
    for p in (edir / "k3c_run_card.json", ROOT / "docs" / "k3c" / "run-card.json"):
        p.write_text(json.dumps(card, indent=2, default=str) + "\n")
    print("=" * 78)
    print(f"VERDICT: {gate['verdict'].upper()} reasons={gate['reasons']}")
    print(f"  24-cell HR  CTRL={HR['CTRL']['pooled_dti']} E1={HR['E1']['pooled_dti']} E2={HR['E2']['pooled_dti']} ship={HR[ship_hr_key]['pooled_dti']} {HR[ship_hr_key]['ci95']}")
    print(f"  paired ship-CTRL {d_ship_ctrl}")
    print(f"  file {tif_path.name} sha256={tif_sha}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
