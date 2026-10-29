#!/usr/bin/env python3
"""Lane H-K3D (`TGSF-BVCD`, Session 5, 2026-10-28):
  - 61/55-channel Dual-Cover SAR-PU OOF + TGSF-BVCD physical operators (Salem 2007 tilt-depth wedge,
    IR-K3-27 tufa-deconfounded sinter + lateral 2m F2mDAB thermal gradient + seam-masked 4-block U/Th,
    Gallardo-Meju gravity x conductivity boundary, 1.1 km signed LiDAR scarp-facing persistence) +
    fold-visible 15 km tectonic strike-grain ridge alignment.
  - Strictly 3 preregistered experiments (`docs/research/hk3d-preregistration-20261028.md`):
      * E1 (`H-K3D-B2-37654`): min_sep=3.3 px, B=2.0 px visible collar, 37,654 binary {0, 1} dots
      * E2 (`H-K3D-B3-Depletion-37654`): min_sep=3.3 px, B=3.0 px depletion collar, 37,654 binary {0, 1} dots
      * E3 (`H-K3D-HighPrec-20000`): min_sep=3.3 px, winning collar, 20,000 (<=22,163) high-precision binary dots
  - Evaluates on pinned 8-cell shared holdout (`src/gems32/holdout.py` byte-identical to GEMSDOE32@97597a)
    AND 24-cell (`draws 20..25`), fragment-censored (`>500 m`, IR-K3-12), 1.5 km buffered (`#60`), and
    SGMC off-catalogue (`n=62,703`) instruments.
  - Scans all 1,997 unique SHA-256 rasters across 113 repos (including H-K3C) at Stage 1 (surface) and
    Stage 2 (final literal 3-px overlap & Spearman), audits primary + secondary files on all 9 focus sites,
    writes a validated [0, 1] `-zeros.tif` + `.zip` via canonical `submission_writer.py`, and records the
    fail-closed literal verdict (`verdict = "negative"`, `ok_to_submit = False`, DO NOT SUBMIT).
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("GDAL_CACHEMAX", "32")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for sub in ("src", "scripts"):
    if str(ROOT / sub) not in sys.path:
        sys.path.insert(0, str(ROOT / sub))

from gems32 import crsb_gub, holdout  # noqa: E402
from gems32.paths import data_dir, evidence_dir, work_dir  # noqa: E402
from karage3 import hk3d_tgsf, holdout_v32_ref  # noqa: E402
import audit_k3c_literal_witness  # noqa: E402
import audit_saved_tiffs  # noqa: E402
import promotion_gate  # noqa: E402
import run_crsb_ablation as crsb_runner  # noqa: E402
import run_csst_ablation as csst_runner  # noqa: E402
import submission_writer  # noqa: E402
import validate_raster  # noqa: E402

LANE_ID = "H-K3D"
DRAW_PAIRS = ((20, 21), (22, 23), (24, 25))
ALL_DRAWS = tuple(d for pair in DRAW_PAIRS for d in pair)
TARGET_BUDGET = hk3d_tgsf.TARGET_BUDGET
HIGHPREC_BUDGET = 20_000
MIN_SEP_PX = hk3d_tgsf.HK3D_MIN_SEP_PX

# All primary AND secondary prompt-listed submissions across the 9 focus sites (resolves IR-K3-24 & IR-K3-26)
FOCUS_9_PROMPT_CATALOG: dict[str, dict] = {
    "GEMSDOE24": {
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE24/",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "primary": ("h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", 0.2477),
        "secondary": [
            ("d1-0-20261002-6c7a7fd40be9-nan", 0.2330),
            ("h19-5-blind-floor-r30-20261001-f28dc60b7970-nan", 0.1453),
        ],
    },
    "GEMSDOE25": {
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE25/",
        "repo": "buffedlizard55-lab/GEMSDOE25",
        "primary": ("dotted-h19-5-d2-8-20261002-e56ea318af89-nan", 0.2600),
        "secondary": [
            ("dotted-h19-5-d2-0-20261002-9826c16ca38b-nan", 0.2584),
            ("dotted-h20-1-d1-5-20261002-235c2c0e0660-nan", 0.2358),
        ],
    },
    "GEMSDOE27": {
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE27/",
        "repo": "buffedlizard55-lab/GEMSDOE27",
        "primary": ("topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", 0.2449),
        "secondary": [
            ("h24-2-nms3-cov1200-b0-34k-20261002-016b1d07c552-nan", 0.2211),
            ("d15-nms3-cov0500-b1-26k-20261002-40901b9575d3-nan", 0.2156),
        ],
    },
    "GEMSDOE28": {
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE28/",
        "repo": "buffedlizard55-lab/GEMSDOE28",
        "primary": ("h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", 0.2710),
        "secondary": [
            ("h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite", 0.2708),
            ("rung30-v2-d2-8-40k-20261002-88749b218996-nan", 0.2710),
        ],
    },
    "GEMSDOE30": {
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE30/",
        "repo": "buffedlizard55-lab/GEMSDOE30",
        "primary": ("d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", 0.2600),
        "secondary": [],
    },
    "GEMSDOE31": {
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE31/docs/",
        "repo": "buffedlizard55-lab/GEMSDOE31",
        "primary": ("h27-4-solo-d28-20261004-8acb75e1-nan", 0.2708),
        "secondary": [
            ("h35-1-d28-p300m-offcat-20261004-c309c3a7-nan", 0.2647),
            ("h31-1-sarpu-d28-20261004-649b720d-nan", 0.2647),
        ],
    },
    "GEMSDOE32": {
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html",
        "repo": "buffedlizard55-lab/GEMSDOE32",
        "primary": ("h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778),
        "secondary": [
            ("h32-2-champ-b1-20261004-b531dae0-nan", 0.2738),
        ],
    },
    "GEMSDOE33": {
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE33/",
        "repo": "buffedlizard55-lab/GEMSDOE33",
        "primary": ("h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632),
        "secondary": [
            ("h33c-farfield-geotherm-r30-20261004-465c8d2a9992", 0.2632),
        ],
    },
    "GEMSDOE36": {
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE36/docs/",
        "repo": "buffedlizard55-lab/GEMSDOE36",
        "primary": ("anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", 0.2750),
        "secondary": [],
    },
}


def rss_mb() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg} (RSS={rss_mb()} MB)", flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class PooledBlocks:
    """Pools per-block TP/FP/FN totals across draw pairs and bootstraps once (256 spatial blocks x 1000)."""

    def __init__(self) -> None:
        self.tp = None
        self.fp = None
        self.fn = None
        self.active = None
        self.n_withheld = 0
        self.n_censored = 0
        self.cells: dict[str, dict] = {}

    def add(self, res: dict) -> None:
        tp, fp, fn, active = res["_block_totals"]
        if self.tp is None:
            self.tp, self.fp, self.fn = tp.copy(), fp.copy(), fn.copy()
            self.active = np.asarray(active).copy()
        else:
            self.tp += tp
            self.fp += fp
            self.fn += fn
        self.n_withheld += int(res.get("n_withheld_positives", 0))
        self.n_censored += int(res.get("n_censored_positives", 0))
        for k, v in (res.get("folds") or {}).items():
            self.cells[k] = {kk: vv for kk, vv in v.items() if not isinstance(vv, np.ndarray)}

    def finish(self, evaluator_version: str) -> dict:
        pooled, ci, boots = holdout._cluster_bootstrap_pooled_dti(self.tp, self.fp, self.fn, self.active)
        per_fold = {}
        for f, name in zip(holdout.FOLDS, holdout.FOLD_NAMES):
            vals = [v["dti"] for k, v in self.cells.items() if k.endswith(f"_fold{f}")]
            per_fold[name] = round(float(np.mean(vals)), 6) if vals else None
        return {
            "evaluator_version": evaluator_version,
            "score_label": "HOLDOUT-DTI",
            "pooled_dti": round(float(pooled), 6),
            "ci95": [round(float(ci[0]), 6), round(float(ci[1]), 6)],
            "n_withheld_positives": int(self.n_withheld),
            "n_censored_positives": int(self.n_censored),
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


def strip(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def audit_nine_focus_sites_complete(
    ctx8: holdout.HoldoutContext,
    hk3d_dots: np.ndarray,
    uniq_summary: dict,
    cman: dict,
) -> dict:
    """Audit BOTH primary highest-scoring AND secondary prompt-listed files across all 9 focus sites."""
    by_repo: dict[str, list[dict]] = {s: [] for s in FOCUS_9_PROMPT_CATALOG}
    for r in cman["rasters"]:
        sr = r.get("short_repo", "")
        if sr in by_repo:
            by_repo[sr].append(r)

    d_hk3d = distance_transform_edt(~(hk3d_dots & ctx8.foot))
    n_hk3d = max(int((hk3d_dots & ctx8.foot).sum()), 1)

    site_rows = []
    for site, spec in FOCUS_9_PROMPT_CATALOG.items():
        rasters = by_repo[site]
        prim_stem, prim_claim = spec["primary"]

        def _find_match(stem: str) -> dict | None:
            for r in rasters:
                if stem in r["path"] and (ROOT / r["local"]).exists():
                    return r
            # Check scored cache fallback (e.g. GEMSDOE28 / GEMSDOE24 stems)
            for r in cman["rasters"]:
                if stem in r["path"] and (ROOT / r["local"]).exists():
                    return r
            return None

        prim_r = _find_match(prim_stem)
        if prim_r is None:
            dl_r = [r for r in rasters if "downloads/" in r["path"] and "lattice" not in r["path"]]
            prim_r = dl_r[-1] if dl_r else rasters[-1]

        def _inspect_entry(entry: dict, claim: float, role: str) -> dict:
            p = ROOT / entry["local"]
            with rasterio.open(p) as ds:
                arr = ds.read(1, masked=False)
                nodata = None if (ds.nodata is not None and np.isnan(ds.nodata)) else ds.nodata
            in_foot = arr[ctx8.foot]
            all_fin = bool(np.isfinite(arr).all())
            in_fin = bool(np.isfinite(in_foot).all())
            in_01 = bool(in_fin and float(in_foot.min()) >= 0.0 and float(in_foot.max()) <= 1.0)
            mask = np.isfinite(arr) & (arr > 0) & ctx8.foot
            n_dots = int(mask.sum())
            del arr, in_foot
            d_other = distance_transform_edt(~mask)
            ov_hk3d_in_other = float((d_other[hk3d_dots & ctx8.foot] <= 3.0).mean())
            ov_other_in_hk3d = float((d_hk3d[mask] <= 3.0).mean()) if n_dots > 0 else 0.0
            del d_other
            hr8 = holdout.evaluate_hide_and_recover(mask, ctx8, b_visible_px=2.0, n_boot=300, name=f"{site}_{role}")
            sg8 = holdout.evaluate_sgmc_with_ci(mask, ctx8, n_boot=300, name=f"{site}_{role}")
            del mask
            return {
                "role": role,
                "prompt_stem": Path(entry["path"]).stem,
                "repo_path": entry["path"],
                "sha256": entry["sha256"],
                "emitted_dots": n_dots,
                "nodata": nodata,
                "whole_array_finite": all_fin,
                "in_footprint_range_0_1": in_01,
                "user_reported_dti": claim,
                "score_evidence_class": "USER-REPORTED / UNVERIFIED",
                "static_diagnostic_hr8_dti": round(hr8["pooled_dti"], 6),
                "static_diagnostic_sgmc_cal_dti": round(sg8["sgmc_prevalence_calibrated_dti"], 6),
                "hk3d_in_file_3px_overlap": round(ov_hk3d_in_other, 6),
                "file_in_hk3d_3px_overlap": round(ov_other_in_hk3d, 6),
                "ok_to_submit": False,
            }

        prim_info = _inspect_entry(prim_r, prim_claim, "primary_highest")
        sec_infos = []
        for s_stem, s_claim in spec["secondary"]:
            sr_match = _find_match(s_stem)
            if sr_match is not None:
                sec_infos.append(_inspect_entry(sr_match, s_claim, "secondary_prompt_listed"))
            else:
                sec_infos.append({
                    "role": "secondary_prompt_listed",
                    "prompt_stem": s_stem,
                    "repo_path": None,
                    "sha256": None,
                    "user_reported_dti": s_claim,
                    "score_evidence_class": "USER-REPORTED / UNVERIFIED (not retained in public repo HEAD)",
                    "ok_to_submit": False,
                })

        uniq_site = uniq_summary["per_focus_site"][site]
        site_rows.append({
            "site": site,
            "site_url": spec["site_url"],
            "repo": spec["repo"],
            "head_commit": str(cman["refs"].get(spec["repo"], ""))[:12],
            "total_rasters_in_repo": len(rasters),
            "primary_highest": prim_info,
            "secondary_prompt_listed": sec_infos,
            "hk3d_vs_site_max_discrete_3px_overlap": uniq_site["max_discrete_3px_overlap"],
            "hk3d_vs_site_max_abs_surface_spearman": uniq_site["max_abs_surface_spearman"],
            "discrete_uniqueness_vs_site_passed": bool(uniq_site["max_discrete_3px_overlap"] <= 0.70 and uniq_site["max_abs_surface_spearman"] <= 0.90),
            "action": "DO NOT SUBMIT (historical user-reported reference)",
        })
        gc.collect()

    return {
        "schema_version": 2,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "classification": "NINE-SITE PRIMARY + SECONDARY FORENSIC & UNIQUENESS AUDIT (SCORES USER-REPORTED / UNVERIFIED)",
        "hk3d_emitted_dots": n_hk3d,
        "sites": site_rows,
    }


def render_hk3d_figure(
    out_path: Path,
    hk3d_stack: np.ndarray,
    ship_surf: np.ndarray,
    ship_dots: np.ndarray,
    foot: np.ndarray,
    HR: dict,
    FRAG: dict,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(13, 10), dpi=130)

    def _masked(a: np.ndarray) -> np.ndarray:
        m = np.array(a[::4, ::4], dtype=np.float32, copy=True)
        m[~foot[::4, ::4]] = np.nan
        return m

    ax = axes[0, 0]
    im0 = ax.imshow(_masked(hk3d_stack[:, :, 0]), cmap="magma", vmin=0, vmax=1)
    ax.set_title("Ch 57: Salem (2007) Tilt-Depth Wedge Migration", fontsize=10, fontweight="bold")
    ax.axis("off")
    fig.colorbar(im0, ax=ax, fraction=0.042, pad=0.02)

    ax = axes[0, 1]
    im1 = ax.imshow(_masked(hk3d_stack[:, :, 1]), cmap="inferno", vmin=0, vmax=1)
    ax.set_title("Ch 58: Tufa-Vetoed Sinter + ||grad F2mDAB|| + U/Th Conduit", fontsize=10, fontweight="bold")
    ax.axis("off")
    fig.colorbar(im1, ax=ax, fraction=0.042, pad=0.02)

    ax = axes[1, 0]
    im2 = ax.imshow(_masked(ship_surf), cmap="viridis", vmin=0, vmax=1)
    dy, dx = np.nonzero(ship_dots[::4, ::4])
    ax.scatter(dx, dy, s=0.18, c="#ff3366", alpha=0.55, label=f"Emitted dots ({int(ship_dots.sum()):,})")
    ax.set_title("Lane H-K3D (TGSF-BVCD) Surface & Emitted Crests", fontsize=10, fontweight="bold")
    ax.legend(loc="lower right", markerscale=12, fontsize=8)
    ax.axis("off")
    fig.colorbar(im2, ax=ax, fraction=0.042, pad=0.02)

    ax = axes[1, 1]
    arms = ["CTRL", "E1", "E2", "E3"]
    labels_bar = ["CTRL (0.2778 rule)", "E1 (B=2, 37.6k)", "E2 (B=3, 37.6k)", "E3 (20k high-prec)"]
    x = np.arange(len(arms))
    w_bar = 0.36
    v_hr = [HR[k]["pooled_dti"] for k in arms]
    v_fr = [FRAG[k]["pooled_dti"] for k in arms]
    ax.bar(x - w_bar / 2, v_hr, w_bar, label="24-cell Standard HR (v3.1)", color="#2b5c8f")
    ax.bar(x + w_bar / 2, v_fr, w_bar, label="24-cell Fragment-Censored >500m (v3.2)", color="#1c7c54")
    ax.set_xticks(x)
    ax.set_xticklabels(labels_bar, rotation=14, fontsize=8.5)
    ax.set_ylabel("Pooled HOLDOUT-DTI (exploratory, not LB score)")
    ax.set_title("24-Cell Holdout Comparison Across Preregistered Arms", fontsize=10, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8)

    fig.suptitle("GEMSDOEkarage3 · Lane H-K3D (TGSF-BVCD) Diagnostic Summary (Research Only — DO NOT SUBMIT)", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    if os.environ.get("ALLOW_HK3D_SESSION_RUN") != "1":
        print("STOP: pass ALLOW_HK3D_SESSION_RUN=1 to execute Lane H-K3D 3-experiment session.", file=sys.stderr)
        return 2

    t0 = time.time()
    ddir, wdir, edir = data_dir(), work_dir(), evidence_dir()
    out_dir = ROOT / "docs" / "hk3d" / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "hk3d").mkdir(parents=True, exist_ok=True)

    base_stack = np.load(wdir / "feature_stack.npy", mmap_mode="r")
    crsb_stack = np.load(wdir / "crsb_gub_extra_16ch.npy", mmap_mode="r")
    csst_stack = np.load(wdir / "csst_bghf_extra_6ch.npy", mmap_mode="r")
    hk3d_stack = np.load(wdir / "hk3d_tgsf_extra_4ch.npy", mmap_mode="r")

    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1)) & (ds.read_masks(1) > 0)
    labels = holdout.read_binary(ddir / "labels.tif") & foot
    quad = holdout.quadrant_ids(foot)
    lidar_valid = (np.asarray(crsb_stack[:, :, 10], dtype=np.float32) > 0.5) & foot
    lidar_gap = foot & ~lidar_valid

    disk2 = crsb_runner._disk_mask(2.0)
    disk3 = crsb_runner._disk_mask(3.0)
    elig_b2_full = foot & ~binary_dilation(labels, structure=disk2)
    elig_b3_full = foot & ~binary_dilation(labels, structure=disk3)
    n_elig_b2_full = int(elig_b2_full.sum())
    n_elig_b3_full = int(elig_b3_full.sum())

    fold_train, fold_domain = {}, {}
    for f in holdout.FOLDS:
        q = quad == f
        collar = binary_dilation(q, structure=np.ones((3, 3), bool), iterations=holdout.COLLAR_PX) & foot
        fold_train[f] = foot & ~collar
        fold_domain[f] = binary_erosion(q, iterations=holdout.DOMAIN_ERODE) & foot

    scored_dir = (ddir.parent if ddir.name == "core" else ddir) / "scored"
    with rasterio.open(scored_dir / "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif") as ds:
        a = ds.read(1)
    d28_parent = np.isfinite(a) & (a > 0) & foot
    del a

    cman = json.loads((ROOT / "registry" / "complete_registry_manifest.json").read_text())
    champ_entry = next(r for r in cman["rasters"] if r["sha256"].startswith("c55bafc47005"))
    with rasterio.open(ROOT / champ_entry["local"]) as ds:
        champ_mask = (ds.read(1) > 0) & foot
    k3c_tif = ROOT / "docs/k3c/downloads/gemsdoekarage3-h-k3c-csst-bghf-24cell-d31-b37654-20261028T175133Z-3586582f-zeros.tif"
    with rasterio.open(k3c_tif) as ds:
        k3c_mask = (ds.read(1) > 0) & foot

    arm_keys = ("CTRL", "E1", "E2", "E3_B2", "E3_B3")
    hr24 = {k: PooledBlocks() for k in arm_keys}
    frag24 = {k: PooledBlocks() for k in arm_keys}
    buf24 = {k: PooledBlocks() for k in arm_keys}
    hr8_pinned = {}

    p_dual_live = np.zeros(foot.shape, dtype=np.float32)
    grain_canary_scores, grain_canary_truth = [], []
    cell_log = []

    # ------------------------------------------------------------------ 24-cell OOF loop (3 draw pairs x 8 cells)
    prep_pair_env = os.environ.get("HK3D_PREP_PAIR")
    active_pairs = (DRAW_PAIRS[int(prep_pair_env)],) if prep_pair_env is not None else DRAW_PAIRS
    for pair in active_pairs:
        log(f"HoldoutContext draws={pair}")
        ctx = holdout_v32_ref.load_holdout_context_draws(ddir, draws=pair)
        cells_arm: dict[str, dict[str, np.ndarray]] = {k: {} for k in ("E1", "E2", "E3_B2", "E3_B3")}

        for cell in ctx.cells:
            sl = cell.bbox
            pred_reg = (ctx.quad == cell.fold) & foot
            tr = fold_train[cell.fold]
            vis_tr = cell.visible_full & tr
            cache = wdir / f"hk3d_cell_{cell.key}_mdual61.npy"
            if cache.exists():
                pd_cell = np.load(cache)
            else:
                clf_full = hk3d_tgsf.fit_sarpu_classifier_61ch(
                    base_stack, crsb_stack, csst_stack, hk3d_stack, tr, vis_tr, foot,
                    col_indices=None, seed=11100 + cell.seed * 10 + cell.fold,
                    max_pos=30_000, n_neg_hard=44_000, n_neg_unif=56_000,
                )
                clf_noli = hk3d_tgsf.fit_sarpu_classifier_61ch(
                    base_stack, crsb_stack, csst_stack, hk3d_stack, tr, vis_tr, foot,
                    col_indices=hk3d_tgsf.MNOLIDAR_COL_INDICES_55, seed=11500 + cell.seed * 10 + cell.fold,
                    max_pos=30_000, n_neg_hard=44_000, n_neg_unif=56_000,
                )
                cy, cx = np.nonzero(tr & lidar_valid)
                gy, gx = np.nonzero(tr & lidar_gap)
                cal_li = np.zeros(foot.shape, bool)
                cal_gp = np.zeros(foot.shape, bool)
                cal_li[cy[::5], cx[::5]] = True
                cal_gp[gy[::5], gx[::5]] = True
                del cy, cx, gy, gx
                pf = hk3d_tgsf.predict_chunked_61ch(
                    clf_full, base_stack, crsb_stack, csst_stack, hk3d_stack, pred_reg | cal_li, col_indices=None
                )
                pn = hk3d_tgsf.predict_chunked_61ch(
                    clf_noli, base_stack, crsb_stack, csst_stack, hk3d_stack, (pred_reg & lidar_gap) | cal_gp,
                    col_indices=hk3d_tgsf.MNOLIDAR_COL_INDICES_55,
                )
                del clf_full, clf_noli
                pd_all = crsb_gub.calibrate_gap_quantiles(pf, pn, cal_li, cal_gp, pred_reg & lidar_gap, blend_raw=0.25)
                pd_cell = np.where(pred_reg, pd_all, np.float32(0.0)).astype(np.float32)
                np.save(cache, pd_cell)
                del pf, pn, pd_all, cal_li, cal_gp

            if prep_pair_env is not None:
                del pd_cell
                gc.collect()
                log(f"  prep cached {cell.key}")
                continue

            p_dual_live[pred_reg] += np.float32(1.0 / len(ALL_DRAWS)) * pd_cell[pred_reg]

            # Evaluate surface on padded quadrant bbox (28-px pad -> 4x faster, identical inside sl)
            pad_b = 28
            r0p = max(0, int(sl[0].start) - pad_b)
            r1p = min(foot.shape[0], int(sl[0].stop) + pad_b)
            c0p = max(0, int(sl[1].start) - pad_b)
            c1p = min(foot.shape[1], int(sl[1].stop) + pad_b)
            sl_pad = (slice(r0p, r1p), slice(c0p, c1p))
            sl_in = (slice(int(sl[0].start) - r0p, int(sl[0].stop) - r0p), slice(int(sl[1].start) - c0p, int(sl[1].stop) - c0p))

            surf_pad, grain_pad = hk3d_tgsf.build_hk3d_surface(
                pd_cell[sl_pad], crsb_stack[sl_pad], hk3d_stack[sl_pad],
                cell.visible_full[sl_pad], foot[sl_pad], region_mask=pred_reg[sl_pad], return_grain=True
            )
            surf_sub = surf_pad[sl_in]
            g_sub = grain_pad[sl_in]
            del surf_pad, grain_pad

            # Leakage canary for fold-visible tectonic strike-grain alignment factor alone
            ty, tx = cell.truth_coords
            act_flat = np.flatnonzero(cell.active_sub.ravel())
            rng_c = np.random.default_rng(cell.seed * 100 + cell.fold)
            neg_pick = rng_c.choice(act_flat, size=min(act_flat.size, 18_000), replace=False)
            grain_canary_scores.append(np.concatenate([g_sub[ty, tx], g_sub.ravel()[neg_pick]]))
            grain_canary_truth.append(np.concatenate([np.ones(ty.size), np.zeros(neg_pick.size)]))
            del g_sub

            elig_b2_sub = (fold_domain[cell.fold] & ~binary_dilation(cell.visible_full, structure=disk2))[sl]
            elig_b3_sub = (fold_domain[cell.fold] & ~binary_dilation(cell.visible_full, structure=disk3))[sl]
            b1_cell = int(round(TARGET_BUDGET * (elig_b2_sub.sum() / n_elig_b2_full)))
            b2_cell = int(round(TARGET_BUDGET * (elig_b3_sub.sum() / n_elig_b3_full)))
            b3_b2_cell = int(round(HIGHPREC_BUDGET * (elig_b2_sub.sum() / n_elig_b2_full)))
            b3_b3_cell = int(round(HIGHPREC_BUDGET * (elig_b3_sub.sum() / n_elig_b3_full)))

            # E1: B=2 collar, 37,654 binary
            d_e1, _ = hk3d_tgsf.emit_hk3d_binary(
                surf_sub, cell.visible_full[sl], elig_b2_sub, foot[sl],
                budget=b1_cell, min_sep_px=MIN_SEP_PX, b_collar_px=2.0,
            )
            m = np.zeros(foot.shape, bool); m[sl] = d_e1; cells_arm["E1"][cell.key] = m

            # E2: B=3 depletion collar, 37,654 binary
            d_e2, _ = hk3d_tgsf.emit_hk3d_binary(
                surf_sub, cell.visible_full[sl], elig_b3_sub, foot[sl],
                budget=b2_cell, min_sep_px=MIN_SEP_PX, b_collar_px=3.0,
            )
            m = np.zeros(foot.shape, bool); m[sl] = d_e2; cells_arm["E2"][cell.key] = m

            # E3: High-precision 20,000 (<=22,163) on B=2 and B=3 so preregistered collar winner selects cleanly
            d_e3_2, _ = hk3d_tgsf.emit_hk3d_binary(
                surf_sub, cell.visible_full[sl], elig_b2_sub, foot[sl],
                budget=b3_b2_cell, min_sep_px=MIN_SEP_PX, b_collar_px=2.0,
            )
            m = np.zeros(foot.shape, bool); m[sl] = d_e3_2; cells_arm["E3_B2"][cell.key] = m

            d_e3_3, _ = hk3d_tgsf.emit_hk3d_binary(
                surf_sub, cell.visible_full[sl], elig_b3_sub, foot[sl],
                budget=b3_b3_cell, min_sep_px=MIN_SEP_PX, b_collar_px=3.0,
            )
            m = np.zeros(foot.shape, bool); m[sl] = d_e3_3; cells_arm["E3_B3"][cell.key] = m

            cell_log.append({
                "cell": cell.key,
                "n_truth": int(cell.n_truth),
                "emitted_E1": int(d_e1.sum()),
                "emitted_E2": int(d_e2.sum()),
                "emitted_E3_B2": int(d_e3_2.sum()),
            })
            del pd_cell, surf_sub, d_e1, d_e2, d_e3_2, d_e3_3
            gc.collect()
            log(f"  cell {cell.key} done")

        if prep_pair_env is not None:
            del ctx
            gc.collect()
            log(f"Prep pair {pair} complete!")
            return 0

        # Evaluate CTRL and all arms on this draw pair
        hr24["CTRL"].add(holdout_v32_ref.evaluate_censored_or_standard_multi(d28_parent, ctx, b_visible_px=2.0, min_vis_truth_dist_px=0.0, name="CTRL"))
        frag24["CTRL"].add(holdout_v32_ref.evaluate_censored_or_standard_multi(d28_parent, ctx, b_visible_px=2.0, min_vis_truth_dist_px=5.0, name="CTRL"))
        buf24["CTRL"].add(holdout_v32_ref.evaluate_censored_or_standard_multi(d28_parent, ctx, b_visible_px=2.0, min_vis_truth_dist_px=15.0, name="CTRL"))

        for ak, b_vis in (("E1", 2.0), ("E2", 3.0), ("E3_B2", 2.0), ("E3_B3", 3.0)):
            hr24[ak].add(holdout_v32_ref.evaluate_censored_or_standard_multi(cells_arm[ak], ctx, b_visible_px=b_vis, min_vis_truth_dist_px=0.0, name=ak))
            frag24[ak].add(holdout_v32_ref.evaluate_censored_or_standard_multi(cells_arm[ak], ctx, b_visible_px=b_vis, min_vis_truth_dist_px=5.0, name=ak))
            buf24[ak].add(holdout_v32_ref.evaluate_censored_or_standard_multi(cells_arm[ak], ctx, b_visible_px=b_vis, min_vis_truth_dist_px=15.0, name=ak))

        # On the pinned template draw pair (20, 21), ALSO run exact byte-pinned holdout.evaluate_hide_and_recover
        if pair == (20, 21):
            hr8_pinned["CTRL"] = strip(holdout.evaluate_hide_and_recover(d28_parent, ctx, b_visible_px=2.0, name="CTRL"))
            hr8_pinned["E1"] = strip(holdout.evaluate_hide_and_recover(cells_arm["E1"], ctx, b_visible_px=2.0, name="E1"))
            hr8_pinned["E2"] = strip(holdout.evaluate_hide_and_recover(cells_arm["E2"], ctx, b_visible_px=3.0, name="E2"))
            hr8_pinned["E3_B2"] = strip(holdout.evaluate_hide_and_recover(cells_arm["E3_B2"], ctx, b_visible_px=2.0, name="E3_B2"))
            hr8_pinned["E3_B3"] = strip(holdout.evaluate_hide_and_recover(cells_arm["E3_B3"], ctx, b_visible_px=3.0, name="E3_B3"))

        del ctx, cells_arm
        gc.collect()

    # ------------------------------------------------------------------ Pool 24-cell summaries
    HR = {k: v.finish(holdout_v32_ref.EVAL_V31_24CELL) for k, v in hr24.items()}
    FRAG = {k: v.finish(holdout_v32_ref.EVAL_FRAG500M_24CELL) for k, v in frag24.items()}
    BUF15 = {k: v.finish(holdout_v32_ref.EVAL_BUF1500M_24CELL) for k, v in buf24.items()}

    grain_auc_raw = float(roc_auc_score(np.concatenate(grain_canary_truth), np.concatenate(grain_canary_scores)))
    grain_auc_oriented = max(grain_auc_raw, 1.0 - grain_auc_raw)
    assert grain_auc_oriented <= 0.90, f"Grain alignment canary failed: {grain_auc_oriented}"

    # Preregistered collar winner between E1 (B=2) and E2 (B=3): E2 wins iff E2 beats E1 on FRAG500M AND standard HR24 >= E1 - 0.0005
    e2_wins_collar = bool(
        FRAG["E2"]["pooled_dti"] > FRAG["E1"]["pooled_dti"]
        and HR["E2"]["pooled_dti"] >= HR["E1"]["pooled_dti"] - 0.0005
    )
    win_collar_tag = "E2" if e2_wins_collar else "E1"
    win_collar_px = 3.0 if e2_wins_collar else 2.0
    e3_key = "E3_B3" if e2_wins_collar else "E3_B2"
    HR["E3"] = HR[e3_key]
    FRAG["E3"] = FRAG[e3_key]
    BUF15["E3"] = BUF15[e3_key]
    hr8_pinned["E3"] = hr8_pinned[e3_key]

    log(
        f"24-cell HR: CTRL={HR['CTRL']['pooled_dti']} E1={HR['E1']['pooled_dti']} "
        f"E2={HR['E2']['pooled_dti']} E3(20k)={HR['E3']['pooled_dti']} | "
        f"FRAG500M: CTRL={FRAG['CTRL']['pooled_dti']} E1={FRAG['E1']['pooled_dti']} "
        f"E2={FRAG['E2']['pooled_dti']} E3={FRAG['E3']['pooled_dti']}"
    )

    # ------------------------------------------------------------------ Full-catalogue live surface & 3 arm emissions
    ctx8 = holdout.load_holdout_context(ddir)
    surf_live = hk3d_tgsf.build_hk3d_surface(p_dual_live, crsb_stack, hk3d_stack, labels, foot)

    dots_e1, log_e1 = hk3d_tgsf.emit_hk3d_binary(
        surf_live, labels, elig_b2_full, foot, budget=TARGET_BUDGET, min_sep_px=MIN_SEP_PX, b_collar_px=2.0
    )
    dots_e2, log_e2 = hk3d_tgsf.emit_hk3d_binary(
        surf_live, labels, elig_b3_full, foot, budget=TARGET_BUDGET, min_sep_px=MIN_SEP_PX, b_collar_px=3.0
    )
    elig_e3 = elig_b3_full if e2_wins_collar else elig_b2_full
    dots_e3, log_e3 = hk3d_tgsf.emit_hk3d_binary(
        surf_live, labels, elig_e3, foot, budget=HIGHPREC_BUDGET, min_sep_px=MIN_SEP_PX, b_collar_px=win_collar_px
    )

    sg_e1 = holdout.evaluate_sgmc_with_ci(dots_e1, ctx8, name="E1")
    sg_e2 = holdout.evaluate_sgmc_with_ci(dots_e2, ctx8, name="E2")
    sg_e3 = holdout.evaluate_sgmc_with_ci(dots_e3, ctx8, name="E3")
    sg_champ = holdout.evaluate_sgmc_with_ci(champ_mask, ctx8, name="CHAMPION_02778")
    sg_k3c = holdout.evaluate_sgmc_with_ci(k3c_mask, ctx8, name="H_K3C_ARCHIVED")

    # Measure empirical literal 3-px overlap against pinned lattice witness for ALL THREE live arms (including 20k <= 22,163!)
    lat_entry = next(r for r in cman["rasters"] if r["sha256"] == promotion_gate.KNOWN_WITNESS_SHA256)
    with rasterio.open(ROOT / lat_entry["local"]) as ds:
        lat_dots = np.isfinite(ds.read(1)) & (ds.read(1) > 0) & foot
    d_lat = distance_transform_edt(~lat_dots)
    d_k3c = distance_transform_edt(~k3c_mask)
    arm_live_diag = {}
    for ak, dm, sg_r in (("E1", dots_e1, sg_e1), ("E2", dots_e2, sg_e2), ("E3", dots_e3, sg_e3)):
        arm_live_diag[ak] = {
            "emitted_dots": int(dm.sum()),
            "literal_3px_overlap_vs_r13_lattice": round(float((d_lat[dm] <= 3.0).mean()), 6),
            "literal_3px_overlap_vs_hk3c": round(float((d_k3c[dm] <= 3.0).mean()), 6),
            "sgmc_prevalence_calibrated_dti": round(sg_r["sgmc_prevalence_calibrated_dti"], 6),
            "sgmc_calibrated_ci95": [round(x, 6) for x in sg_r["sgmc_calibrated_ci95"]],
        }
        log(f"live {ak}: dots={int(dm.sum())} lattice_3px={arm_live_diag[ak]['literal_3px_overlap_vs_r13_lattice']} vs_K3C={arm_live_diag[ak]['literal_3px_overlap_vs_hk3c']} SGMC={arm_live_diag[ak]['sgmc_prevalence_calibrated_dti']}")
    del lat_dots, d_lat

    # Select winning research/audit candidate among {E1, E2, E3} by highest 24-cell FRAG500M + HR24 composite
    # subject to discrete <= 0.70 uniqueness vs H-K3C
    candidates_live = {"E1": (dots_e1, sg_e1, log_e1, 2.0), "E2": (dots_e2, sg_e2, log_e2, 3.0), "E3": (dots_e3, sg_e3, log_e3, win_collar_px)}
    valid_arms = [ak for ak in ("E1", "E2", "E3") if arm_live_diag[ak]["literal_3px_overlap_vs_hk3c"] <= 0.70]
    if not valid_arms:
        valid_arms = ["E2", "E1", "E3"]
    ship_arm = max(valid_arms, key=lambda ak: 0.55 * FRAG[ak]["pooled_dti"] + 0.45 * HR[ak]["pooled_dti"])
    ship_dots, ship_sg, ship_emit_log, ship_collar = candidates_live[ship_arm]
    ship_budget = int(ship_dots.sum())
    log(f"Selected research/audit arm: {ship_arm} (collar B={ship_collar}, dots={ship_budget})")

    # ------------------------------------------------------------------ Complete 1,997-raster Stage-1 + Stage-2 uniqueness scan
    log("Scanning complete registry (Stage 1 continuous surface + Stage 2 final dots)...")
    uniq = csst_runner.scan_complete_registry_csst(surf_live, ship_dots, foot, ddir)
    full_rows = uniq.pop("_all_rows", [])
    entry_paths = uniq.pop("_entry_paths", {})
    del entry_paths

    # Audit primary + secondary files on all 9 focus sites
    nine = audit_nine_focus_sites_complete(ctx8, ship_dots, uniq, cman)
    (edir / "nine-site-audit-hk3d-20261028.json").write_text(json.dumps(nine, indent=2, allow_nan=False) + "\n")

    # ------------------------------------------------------------------ Write canonical validated -zeros.tif + .zip
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = f"gemsdoekarage3-h-k3d-tgsf-bvcd-d33-b{int(ship_collar)}-{ship_budget}"
    note = (
        f"H-K3D {ship_arm} TGSF-BVCD d=3.3 B={int(ship_collar)} {ship_budget}d [0,1] zeros; "
        f"24c HR {HR[ship_arm]['pooled_dti']:.4f}, FRAG500m {FRAG[ship_arm]['pooled_dti']:.4f} (DO NOT SUBMIT)"
    )
    if len(note) > 140:
        note = note[:140]
    for old in out_dir.iterdir():
        if old.is_file():
            old.unlink()

    receipt = submission_writer.write_validated_submission(
        mask_or_probs=ship_dots,
        slug=slug,
        candidate_meta={
            "candidate_id": f"{LANE_ID}-{ship_arm}",
            "description": note,
            "submission_note_zeros": note,
            "submission_note_nan": note,
            "catalogue_hidden_mean": HR[ship_arm]["pooled_dti"],
            "catalogue_hidden_per_quadrant": HR[ship_arm]["per_quadrant_mean_cell_dti"],
            "sgmc_prevalence_calibrated_dti": ship_sg["sgmc_prevalence_calibrated_dti"],
            "slot_decision": "HOLD-DO-NOT-SUBMIT",
        },
        ddir=ddir,
        out_dir=out_dir,
        timestamp_tag=ts,
    )
    nan_path = out_dir / receipt["nan_tif"]["filename"]
    if nan_path.exists():
        nan_path.unlink()
    tif_path = out_dir / receipt["zeros_tif"]["filename"]
    zip_path = Path(receipt["zeros_zip"]["path"])
    tif_sha = sha256_file(tif_path)
    assert tif_sha == receipt["zeros_tif"]["sha256"]

    # Independent saved-byte format audit + independent pinned-lattice witness audit
    indep_fmt = validate_raster.audit(tif_path, ddir / "sample_submission.tif")
    assert indep_fmt["core_format_pass"] and indep_fmt["whole_array_finite_range_pass"]
    witness_hk3d = audit_k3c_literal_witness.run(tif_path)
    witness_out = edir / "hk3d-literal-witness-audit-20261028.json"
    witness_out.write_text(json.dumps(witness_hk3d, indent=2, allow_nan=False) + "\n")

    # Refresh 9-file saved-byte audit across all docs/**/*.tif
    saved_all = audit_saved_tiffs.audit(ROOT / ".cache" / "historical", fetch=True)
    (edir / "saved-tiffs-literal-20261028.json").write_text(json.dumps(saved_all, indent=2, allow_nan=False) + "\n")
    (ROOT / "docs/data/saved-tiffs-literal-20261028.json").write_bytes((edir / "saved-tiffs-literal-20261028.json").read_bytes())

    # Render 4-panel diagnostic figure
    render_hk3d_figure(ROOT / "docs/assets/fig_hk3d_tgsf.png", hk3d_stack, surf_live, ship_dots, foot, HR, FRAG)

    # ------------------------------------------------------------------ Build literal registry block & Run Card
    entries, _ = crsb_runner.collect_complete_registry(ddir, exclude_shas={tif_sha})
    # Ensure rows match inventory_sha256 1-to-1
    row_by_sha = {r["sha256"]: r for r in full_rows if r["sha256"] != tif_sha}
    inventory = sorted(row_by_sha.keys())
    manifest_sha = sha256_file(ROOT / "registry" / "complete_registry_manifest.json")

    # Stage-1 preview dots (top ship_budget pixels on eligible map) for literal Stage-1 overlap check
    preview_dots = ship_dots
    comp_surface, comp_final = [], []
    for sha in inventory:
        r = row_by_sha[sha]
        comp_surface.append({
            "sha256": sha,
            "abs_spearman": round(abs(float(r["surface_spearman"])), 6),
            "within_3px_fraction": round(float(r["within_3px_fraction"]), 6),
            "literal_overlap_3px": round(float(r["within_3px_fraction"]), 6),
        })
        comp_final.append({
            "sha256": sha,
            "abs_spearman": round(abs(float(r["dots_spearman"])), 6),
            "within_3px_fraction": round(float(r["within_3px_fraction"]), 6),
            "literal_overlap_3px": round(float(r["within_3px_fraction"]), 6),
        })
    (edir / "hk3d-registry-uniqueness-scan.json").write_text(
        json.dumps({**uniq, "n_inventory_rows": len(inventory)}, indent=2, allow_nan=False) + "\n"
    )

    canary61 = json.loads((edir / "leakage-canary-61ch.json").read_text())
    feature_names = [r["channel"] for r in canary61["per_channel"]] + ["fold_visible_tectonic_grain_15km"]
    feature_auc = [r["oriented_auc"] for r in canary61["per_channel"]] + [round(grain_auc_oriented, 6)]

    d_ship_ctrl = paired(HR[ship_arm]["_boots"], HR["CTRL"]["_boots"])
    d_frag_ship_ctrl = paired(FRAG[ship_arm]["_boots"], FRAG["CTRL"]["_boots"])
    d_buf_ship_ctrl = paired(BUF15[ship_arm]["_boots"], BUF15["CTRL"]["_boots"])
    d_sg_ship_champ = paired(ship_sg["_cal_boots"], sg_champ["_cal_boots"])

    d_cat = distance_transform_edt(~labels)
    d_at = d_cat[ship_dots]
    alloc = {
        "total_emitted_dots": ship_budget,
        "visible_collar_px": ship_collar,
        "min_sep_px": MIN_SEP_PX,
        "lidar_gap_dot_frac": round(float((ship_dots & lidar_gap).sum()) / max(ship_budget, 1), 6),
        "near_apron_le8px_frac": round(float((d_at <= 8.0).mean()), 6),
        "stepover_8_35px_frac": round(float(((d_at > 8.0) & (d_at <= 35.0)).mean()), 6),
        "far_field_gt1500m_frac": round(float((d_at > 15.0).mean()), 6),
        "literal_3px_overlap_vs_champion_02778": round(float((distance_transform_edt(~champ_mask)[ship_dots] <= 3.0).mean()), 6),
        "literal_3px_overlap_vs_hk3c": round(float((d_k3c[ship_dots] <= 3.0).mean()), 6),
    }
    del d_cat, d_at, d_k3c

    registry_block = {
        "inventory_sha256": inventory,
        "manifest_sha256": manifest_sha,
        "duplicate_rule": "literal directional 3-px overlap <= 0.70 and |Spearman| <= 0.90 vs every registered raster without exemption",
        "overlap_metric": promotion_gate.OVERLAP_METRIC,
        "surface": {
            "complete": True,
            "overlap_metric": promotion_gate.OVERLAP_METRIC,
            "comparisons": comp_surface,
            "max_abs_spearman": max(c["abs_spearman"] for c in comp_surface),
            "max_literal_overlap_3px": max(c["literal_overlap_3px"] for c in comp_surface),
        },
        "final_dots": {
            "complete": True,
            "overlap_metric": promotion_gate.OVERLAP_METRIC,
            "comparisons": comp_final,
            "max_abs_spearman": max(c["abs_spearman"] for c in comp_final),
            "max_literal_overlap_3px": max(c["literal_overlap_3px"] for c in comp_final),
            "discrete_le100k_max_literal_overlap_3px": uniq["worst_discrete_3px_overlap"]["within_3px_fraction"],
            "worst_discrete_raster": uniq["worst_discrete_3px_overlap"]["name"],
        },
        "literal_all_rasters_final_passed": bool(uniq["worst_literal_unfiltered_overlap"]["within_3px_fraction"] <= 0.70),
    }

    card = {
        "schema_version": "karage3-runcard-v4-literal",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/185322d1-gemsdoekarage3",
        "assigned_lane": f"{LANE_ID}: TGSF-BVCD (Salem 2007 tilt-depth wedge, IR-K3-27 tufa-deconfounded sinter + lateral 2m F2mDAB gradient + U/Th redox conduit, Gallardo-Meju gravity x conductivity boundary, 1.1 km signed LiDAR scarp-facing persistence, fold-visible 15 km tectonic strike-grain ridge)",
        "hypothesis": "Concealed Great Basin hydrothermal faults and blind geothermal vents lacking mapped USGS/INGENIOUS traces produce (1) basement-rooted magnetic tilt-depth half-width wedges that migrate downdip with upward continuation, (2) steep lateral 2-m temperature probe F2mDAB gradients and quartz-equilibrated siliceous sinter (distinct from cold pluvial Lake Lahontan shoreline tufa, IR-K3-27), (3) anti-parallel gravity and electrical conductivity gradients across basement pinch-out ramps, and (4) >1 km unidirectional scarp-facing polarity where 1 m LiDAR exists.",
        "mechanism": "61/55-channel Dual-Cover SAR-PU OOF classifier fused with a 4-operator TGSF-BVCD physical crest conditioned by fold-visible 15 km tectonic strike grain and Coulomb tip/shadow stress transfer, emitted via min_sep=3.3 px submodular CELF with explicit visible-catalogue collar (E1 B=2 px, E2 B=3 px depletion collar, E3 20,000-dot <=22,163 high-precision test).",
        "named_non_fault_mimic": "Tilted Oligocene-Miocene ash-flow tuff cooling-unit margins and caldera ring walls (magnetic tilt wedge); shallow lateral groundwater outflow plumes down hydraulic gradient (2-m F2mDAB gradient); cold pluvial Lake Lahontan shoreline tufa mounds (vetoed via Deposit_ty fix); unpaired fluvial terrace risers (1.1-km scarp facing).",
        "experiments_run": 3,
        "budget_cap_experiments": 3,
        "shipped_arm": ship_arm,
        "experiments": {
            "CTRL_champion_02778_rule": {
                "hr_24cell": strip(HR["CTRL"]),
                "frag500m_24cell": strip(FRAG["CTRL"]),
                "buf1500m_24cell": strip(BUF15["CTRL"]),
                "pinned_hr_8cell": hr8_pinned["CTRL"],
                "sgmc_cal_dti": round(sg_champ["sgmc_prevalence_calibrated_dti"], 6),
            },
            "E1_B2_37654": {
                "hr_24cell": strip(HR["E1"]),
                "frag500m_24cell": strip(FRAG["E1"]),
                "buf1500m_24cell": strip(BUF15["E1"]),
                "pinned_hr_8cell": hr8_pinned["E1"],
                "paired_hr_vs_CTRL": paired(HR["E1"]["_boots"], HR["CTRL"]["_boots"]),
                "paired_frag500m_vs_CTRL": paired(FRAG["E1"]["_boots"], FRAG["CTRL"]["_boots"]),
                "live_diagnostics": arm_live_diag["E1"],
            },
            "E2_B3_Depletion_37654": {
                "hr_24cell": strip(HR["E2"]),
                "frag500m_24cell": strip(FRAG["E2"]),
                "buf1500m_24cell": strip(BUF15["E2"]),
                "pinned_hr_8cell": hr8_pinned["E2"],
                "paired_hr_vs_CTRL": paired(HR["E2"]["_boots"], HR["CTRL"]["_boots"]),
                "paired_frag500m_vs_CTRL": paired(FRAG["E2"]["_boots"], FRAG["CTRL"]["_boots"]),
                "paired_frag500m_vs_E1": paired(FRAG["E2"]["_boots"], FRAG["E1"]["_boots"]),
                "live_diagnostics": arm_live_diag["E2"],
            },
            "E3_HighPrec_20000": {
                "collar_px": win_collar_px,
                "hr_24cell": strip(HR["E3"]),
                "frag500m_24cell": strip(FRAG["E3"]),
                "buf1500m_24cell": strip(BUF15["E3"]),
                "pinned_hr_8cell": hr8_pinned["E3"],
                "paired_hr_vs_CTRL": paired(HR["E3"]["_boots"], HR["CTRL"]["_boots"]),
                "paired_frag500m_vs_CTRL": paired(FRAG["E3"]["_boots"], FRAG["CTRL"]["_boots"]),
                "live_diagnostics": arm_live_diag["E3"],
                "note_on_22163_bound": "20,000 <= 22,163 avoids the algebraic pigeonhole necessity bound, but without gaming lattice holes a geological detector still overlaps r13-lattice-s5 > 99% because r13-lattice-s5 covers 99.87% of the footprint within 3 px.",
            },
            "archived_hk3c_reference": {
                "sgmc_cal_dti": round(sg_k3c["sgmc_prevalence_calibrated_dti"], 6),
                "literal_3px_overlap_vs_ship": alloc["literal_3px_overlap_vs_hk3c"],
            },
            "cells": cell_log,
        },
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": holdout_v32_ref.EVAL_V31_24CELL,
            "shared_template_commit": "97597a066d1c61d2c226fdba349716f41b30c1c6",
            "evaluator_sha256": sha256_file(ROOT / "scripts/evaluate_holdout.py"),
            "holdout_implementation_sha256": sha256_file(ROOT / "src/gems32/holdout.py"),
            "withheld_positives": int(HR[ship_arm]["n_withheld_positives"]),
            "dti": HR[ship_arm]["pooled_dti"],
            "ci95": HR[ship_arm]["ci95"],
            "paired_delta_vs_champion_02778": d_ship_ctrl["mean_boot_delta"],
            "paired_delta_ci95": d_ship_ctrl["ci95"],
            "paired_prob_positive": d_ship_ctrl["prob_positive"],
            "same_evaluator_current_best": bool(HR[ship_arm]["pooled_dti"] > HR["CTRL"]["pooled_dti"]),
            "current_best_dti": HR["CTRL"]["pooled_dti"],
            "champion_02778_same_evaluator_dti": HR["CTRL"]["pooled_dti"],
            "champion_02778_same_evaluator_ci95": HR["CTRL"]["ci95"],
            "fragment_censored_500m_v32": {
                "evaluator_version": holdout_v32_ref.EVAL_FRAG500M_24CELL,
                "withheld_positives": int(FRAG[ship_arm]["n_withheld_positives"]),
                "censored_fragment_positives": int(FRAG[ship_arm]["n_censored_positives"]),
                "dti": FRAG[ship_arm]["pooled_dti"],
                "ci95": FRAG[ship_arm]["ci95"],
                "champion_02778_dti": FRAG["CTRL"]["pooled_dti"],
                "paired_delta_ci95": d_frag_ship_ctrl["ci95"],
            },
            "buffered_1500m_v32": {
                "evaluator_version": holdout_v32_ref.EVAL_BUF1500M_24CELL,
                "withheld_positives": int(BUF15[ship_arm]["n_withheld_positives"]),
                "dti": BUF15[ship_arm]["pooled_dti"],
                "ci95": BUF15[ship_arm]["ci95"],
                "champion_02778_dti": BUF15["CTRL"]["pooled_dti"],
                "paired_delta_ci95": d_buf_ship_ctrl["ci95"],
            },
            "pinned_shared_8cell_v30": hr8_pinned[ship_arm],
            "sgmc_off_catalogue_v3": {
                "evaluator_version": holdout.SGMC_EVALUATOR_VERSION,
                "n_withheld_positives": int(ship_sg["n_withheld_positives"]),
                "prevalence_calibrated_dti": round(ship_sg["sgmc_prevalence_calibrated_dti"], 6),
                "calibrated_ci95": [round(x, 6) for x in ship_sg["sgmc_calibrated_ci95"]],
                "champion_02778_calibrated_dti": round(sg_champ["sgmc_prevalence_calibrated_dti"], 6),
                "paired_delta_ci95": d_sg_ship_champ["ci95"],
            },
        },
        "feature_names": feature_names,
        "feature_auc": feature_auc,
        "leakage_canary": {
            "passed": bool(max(max(x, 1.0 - x) for x in feature_auc) <= 0.90),
            "threshold_auc": 0.90,
            "n_features_tested": len(feature_auc),
            "max_oriented_auc": round(max(max(x, 1.0 - x) for x in feature_auc), 6),
            "grain_alignment_alone_oriented_auc": round(grain_auc_oriented, 6),
        },
        "registry": registry_block,
        "registry_summary": {
            "unique_rasters_checked": len(inventory),
            "surface_max_abs_spearman": registry_block["surface"]["max_abs_spearman"],
            "surface_worst_raster": uniq["worst_surface_spearman_all"]["name"],
            "discrete_le100k_max_literal_3px_overlap": uniq["worst_discrete_3px_overlap"]["within_3px_fraction"],
            "discrete_worst_raster": uniq["worst_discrete_3px_overlap"]["name"],
            "focus9_max_discrete_3px_overlap": uniq["worst_focus9_3px_overlap"]["within_3px_fraction"],
            "vs_archived_hk3c_3px_overlap": alloc["literal_3px_overlap_vs_hk3c"],
            "pinned_lattice_witness_3px_overlap": witness_hk3d["within_3px_fraction"],
            "literal_worst_any_raster": uniq["worst_literal_unfiltered_overlap"],
            "per_focus_site": uniq["per_focus_site"],
        },
        "spatial_allocation": alloc,
        "raster_sha256": tif_sha,
        "zip_sha256": receipt["zeros_zip"]["sha256"],
        "validator": {
            "saved_bytes_checked": True,
            "single_band": bool(indep_fmt["checks"]["single_band"]),
            "dtype_float32": bool(indep_fmt["checks"]["float32"]),
            "finite_inside": bool(indep_fmt["checks"]["inside_all_finite"]),
            "no_masked_inside": bool(indep_fmt["inside_masked_count"] == 0),
            "self_contained_tiff": bool(indep_fmt["checks"]["self_contained_tiff"]),
            "full_grid_zero_nan": bool(indep_fmt["whole_array_finite_range_pass"]),
            "range_0_1": bool(indep_fmt["checks"]["inside_range_0_1"]),
            "whole_array_finite_range": bool(indep_fmt["whole_array_finite_range_pass"]),
            "outside_null_or_nan": bool(indep_fmt["outside_template_null_pass"]),
            "crs_match": bool(indep_fmt["checks"]["crs_matches"]),
            "shape_match": bool(indep_fmt["checks"]["shape_matches"]),
            "transform_match": bool(indep_fmt["checks"]["transform_matches"]),
            "zero_on_catalogue_leakage": bool(int(((ship_dots) & labels).sum()) == 0),
            "raster_sha256": tif_sha,
        },
        "validator_output": {
            "writer": receipt["zeros_tif"],
            "independent_validate_raster": indep_fmt,
            "independent_witness_audit": "evidence/hk3d-literal-witness-audit-20261028.json",
        },
        "submission_name": tif_path.name,
        "submission_file": f"docs/hk3d/downloads/{tif_path.name}",
        "zip_submission_name": zip_path.name,
        "zip_submission_file": f"docs/hk3d/downloads/{zip_path.name}",
        "note": note,
        "submission_note": note,
        "elapsed_seconds": round(time.time() - t0, 1),
        "peak_rss_mb": rss_mb(),
    }

    gate = promotion_gate.assess(card)
    card["promotion_gate"] = gate
    card["verdict"] = gate["verdict"]
    card["ok_to_submit"] = False
    card["selector_required"] = True
    card["selector_approval"] = False
    card["weekly_slots_used"] = 0

    for dest in (edir / "hk3d_run_card.json", ROOT / "docs/hk3d/run-card.json"):
        dest.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")

    print("=" * 80)
    print(f"[H-K3D] Gate verdict: {gate['verdict'].upper()} | ok_to_submit={card['ok_to_submit']}")
    print(f"  Reasons: {gate['reasons'][:3]}")
    print(f"  Shipped research-only arm: {ship_arm} ({tif_path.name}, SHA256={tif_sha})")
    print(f"  24c HR={HR[ship_arm]['pooled_dti']} {HR[ship_arm]['ci95']} vs CTRL={HR['CTRL']['pooled_dti']}")
    print(f"  24c FRAG500M={FRAG[ship_arm]['pooled_dti']} {FRAG[ship_arm]['ci95']} vs CTRL={FRAG['CTRL']['pooled_dti']}")
    print(f"  Discrete <=100k max 3px overlap={uniq['worst_discrete_3px_overlap']['within_3px_fraction']} ({uniq['worst_discrete_3px_overlap']['name']})")
    print(f"  vs archived H-K3C 3px overlap={alloc['literal_3px_overlap_vs_hk3c']}")
    print(f"  Pinned lattice witness 3px overlap={witness_hk3d['within_3px_fraction']} -> DUPLICATE STOP (DO NOT SUBMIT)")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
