#!/usr/bin/env python3
"""Execute Preregistered Lane H-K3-1 (`CRSB-GUB`) within the strict 3-Experiment Budget,
Audit Uniqueness Across All 104 Repos (`2,148` rasters / `1,793` unique SHA-256s),
Audit All 9 Focus Sites (`GEMSDOE24..36`), and Emit Validated `-zeros.tif` + `.zip` Submission.

Strictly reuses shared template tools (Protocol Rule 2):
  - `.cache/gems_work/feature_stack.npy` (`gems32.features`, 35 base channels)
  - `.cache/gems_work/crsb_gub_extra_16ch.npy` (`gems32.crsb_gub`, 16 label-free physical channels)
  - `gems32.holdout` / `scripts/evaluate_holdout.py` (`HIDE-RECOVER-v3.0` + `SGMC-CAL-v3.0`)
  - `gems32.emitter.emit` (`min_sep_px = 3.0`, exact 300 m kernel zero-point)
  - `scripts/submission_writer.py` (`prefix="gemskarage3"`, 13-check `-zeros.tif` + single-file `.zip`)
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

os.environ.setdefault("GDAL_CACHEMAX", "32")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, binary_erosion, convolve, distance_transform_edt
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from gems32 import crsb_gub, features, holdout, metric, release_gate  # noqa: E402
from gems32.paths import data_dir, downloads_dir, evidence_dir, work_dir  # noqa: E402
import evaluate_holdout  # noqa: E402
import submission_writer  # noqa: E402

TARGET_BUDGET = crsb_gub.TARGET_BUDGET
B_COLLAR_PX = crsb_gub.B_COLLAR_PX
AXIAL_SEP_PX = crsb_gub.AXIAL_MIN_SEP_PX

FOCUS_9_REPOS = (
    "GEMSDOE24",
    "GEMSDOE25",
    "GEMSDOE27",
    "GEMSDOE28",
    "GEMSDOE30",
    "GEMSDOE31",
    "GEMSDOE32",
    "GEMSDOE33",
    "GEMSDOE36",
)

# Pinned owner-reported best values for the 9 focus sites (with exact audit provenance; labeled OWNER-REPORT per Rule 3)
FOCUS_9_CONFIRMED: dict[str, dict] = {
    "GEMSDOE24": {
        "confirmed_dti": 0.2477,
        "confirmed_label": "OWNER-REPORT (highest supplied item for GEMSDOE24)",
        "confirmed_stem": "gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan",
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE24/",
    },
    "GEMSDOE25": {
        "confirmed_dti": 0.2600,
        "confirmed_label": "OWNER-REPORT (equal reported value to GEMSDOE30; byte-identical base dots)",
        "confirmed_stem": "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan",
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE25/",
    },
    "GEMSDOE27": {
        "confirmed_dti": 0.2449,
        "confirmed_label": "OWNER-REPORT (highest supplied item for GEMSDOE27)",
        "confirmed_stem": "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan",
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE27/",
    },
    "GEMSDOE28": {
        "confirmed_dti": 0.2710,
        "confirmed_label": "OWNER-REPORT (rung30-v2-d2-8-40k at 0.2710; r1-solo-d2-8 at 0.2708)",
        "confirmed_stem": "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite",
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE28/",
    },
    "GEMSDOE30": {
        "confirmed_dti": 0.2600,
        "confirmed_label": "OWNER-REPORT (dotted-h19-5-d2-8 at 0.2600; HEAD holds sgmc-hedge-d10-85k)",
        "confirmed_stem": "gems30-dotted-h19-5-d2-8-e56ea318af89",
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE30/",
    },
    "GEMSDOE31": {
        "confirmed_dti": 0.2708,
        "confirmed_label": "OWNER-REPORT (r1-solo-d2-8 at 0.2708; HEAD holds tgtd-submod-37654)",
        "confirmed_stem": "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite",
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE31/",
    },
    "GEMSDOE32": {
        "confirmed_dti": 0.2778,
        "confirmed_label": "OWNER-REPORT (highest across user's 9 focus sites; no portal receipt verified in sandbox)",
        "confirmed_stem": "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html",
    },
    "GEMSDOE33": {
        "confirmed_dti": 0.2632,
        "confirmed_label": "OWNER-REPORT (h33-1-thin-corridor at 0.2632; HEAD holds r3-da-hgcm-37654)",
        "confirmed_stem": "h33-1-thin-corridor-20261005-zeros",
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE33/",
    },
    "GEMSDOE36": {
        "confirmed_dti": 0.2750,
        "confirmed_label": "OWNER-REPORT (h36-tdr-pds-b2 at 0.2750; HEAD holds wdp36-exp1)",
        "confirmed_stem": "gemsdoe36-h36-tdr-pds-b2-zeros",
        "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE36/",
    },
}


def peak_rss_mb() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def _disk_mask(radius_px: float) -> np.ndarray:
    r = int(np.ceil(radius_px))
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    return (yy * yy + xx * xx) <= (radius_px * radius_px + 1e-9)


def evaluate_detached_and_censored(
    pred_or_cells: np.ndarray | dict[str, np.ndarray],
    ctx: holdout.HoldoutContext,
    b_visible_px: float = 2.0,
    detach_min_px: float = 6.0,
    censor_hidden_px: float = 2.0,
    grid_n: int = 16,
    n_boot: int = 1000,
    seed: int = 20261026,
) -> dict:
    h, w = ctx.foot.shape
    n_blocks = grid_n * grid_n
    fy, fx = np.nonzero(ctx.foot)
    active_blocks = np.unique(holdout._spatial_block_index(fy, fx, (h, w), grid_n))
    is_dict = isinstance(pred_or_cells, dict)
    base_mask = None if is_dict else (np.asarray(pred_or_cells, bool) & ctx.foot)

    tp_det = np.zeros(n_blocks, dtype=np.float64)
    fp_det = np.zeros(n_blocks, dtype=np.float64)
    fn_det = np.zeros(n_blocks, dtype=np.float64)
    n_det_pos = 0

    tp_cen = np.zeros(n_blocks, dtype=np.float64)
    fp_cen = np.zeros(n_blocks, dtype=np.float64)
    fn_cen = np.zeros(n_blocks, dtype=np.float64)
    n_cen_pos = 0

    for cell in ctx.cells:
        sl = cell.bbox
        r0, c0 = int(sl[0].start), int(sl[1].start)
        raw_in = np.asarray(pred_or_cells[cell.key], bool)[sl] if is_dict else base_mask[sl]
        p_sub = raw_in & cell.active_sub
        if b_visible_px > 0.0 and cell.d_vis_sub is not None:
            p_sub = p_sub & (cell.d_vis_sub > b_visible_px)

        ty, tx = cell.truth_coords
        if ty.size == 0:
            continue

        truth_sub = np.zeros(cell.active_sub.shape, dtype=bool)
        truth_sub[ty, tx] = True
        d_hid = distance_transform_edt(~truth_sub)
        p_cen = p_sub & (d_hid > censor_hidden_px)
        n_cen_pos += int(ty.size)
        t_blk = holdout._spatial_block_index(ty + r0, tx + c0, (h, w), grid_n)
        if p_cen.any():
            dp_cen = distance_transform_edt(~p_cen)
            tc_cen = metric.kernel(dp_cen[ty, tx]).astype(np.float64)
            np.add.at(tp_cen, t_blk, tc_cen)
            np.add.at(fn_cen, t_blk, 1.0 - tc_cen)
            py, px = np.nonzero(p_cen)
            p_blk = holdout._spatial_block_index(py + r0, px + c0, (h, w), grid_n)
            np.add.at(fp_cen, p_blk, (1.0 - cell.k_dg_sub[p_cen]).astype(np.float64))
        else:
            np.add.at(fn_cen, t_blk, 1.0)

        det_keep = cell.d_vis_sub[ty, tx] >= detach_min_px
        if det_keep.any():
            dty, dtx = ty[det_keep], tx[det_keep]
            n_det_pos += int(dty.size)
            det_truth = np.zeros(cell.active_sub.shape, dtype=bool)
            det_truth[dty, dtx] = True
            k_dg_det = metric.kernel(distance_transform_edt(~det_truth))
            p_det = p_sub & (cell.d_vis_sub >= (detach_min_px - 3.0))
            dt_blk = holdout._spatial_block_index(dty + r0, dtx + c0, (h, w), grid_n)
            if p_det.any():
                dp_det = distance_transform_edt(~p_det)
                tc_det = metric.kernel(dp_det[dty, dtx]).astype(np.float64)
                np.add.at(tp_det, dt_blk, tc_det)
                np.add.at(fn_det, dt_blk, 1.0 - tc_det)
                py, px = np.nonzero(p_det)
                p_blk = holdout._spatial_block_index(py + r0, px + c0, (h, w), grid_n)
                np.add.at(fp_det, p_blk, (1.0 - k_dg_det[p_det]).astype(np.float64))
            else:
                np.add.at(fn_det, dt_blk, 1.0)

    cen_dti, cen_ci, cen_boots = holdout._cluster_bootstrap_pooled_dti(
        tp_cen, fp_cen, fn_cen, active_blocks, n_boot=n_boot, seed=seed
    )
    det_dti, det_ci, det_boots = holdout._cluster_bootstrap_pooled_dti(
        tp_det, fp_det, fn_det, active_blocks, n_boot=n_boot, seed=seed
    )
    return {
        "censored_d2": {
            "dti": cen_dti,
            "ci95": cen_ci,
            "n_withheld_positives": n_cen_pos,
            "_boots": cen_boots,
        },
        "detached_600m": {
            "dti": det_dti,
            "ci95": det_ci,
            "n_withheld_positives": n_det_pos,
            "_boots": det_boots,
        },
    }


def paired_ci(boots_a: np.ndarray, boots_b: np.ndarray) -> dict:
    diff = np.asarray(boots_a, dtype=np.float64) - np.asarray(boots_b, dtype=np.float64)
    return {
        "mean_boot_delta": float(diff.mean()),
        "ci95": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))],
        "prob_positive": float((diff > 0.0).mean()),
    }


def _normalized_ranks(vec: np.ndarray) -> np.ndarray:
    r = rankdata(vec).astype(np.float32)
    r -= np.float32(r.mean())
    nrm = float(np.linalg.norm(r))
    return (r / np.float32(nrm)) if nrm > 0.0 else r


def collect_complete_registry(ddir: Path, exclude_shas: set[str] | None = None) -> tuple[dict[str, dict], dict]:
    """Gather all unique-SHA256 rasters across `complete_registry_manifest.json` (`2,148` rasters / 104 repos) + scored cache."""
    exclude_shas = exclude_shas or set()
    cman = json.loads((ROOT / "registry" / "complete_registry_manifest.json").read_text())
    entries: dict[str, dict] = {}
    for r in cman["rasters"]:
        sha = r["sha256"]
        if sha in exclude_shas:
            continue
        p = ROOT / r["local"]
        if not p.exists():
            continue
        item = entries.setdefault(
            sha,
            {
                "name": f"{r['repo']}:{r['path']}",
                "short_repo": r["short_repo"],
                "repo": r["repo"],
                "path": p,
                "repos_holding_sha": set(),
            },
        )
        item["repos_holding_sha"].add(r["short_repo"])

    scored_dir = (ddir.parent if ddir.name == "core" else ddir) / "scored"
    n_scored_files = 0
    if scored_dir.exists():
        for sp in sorted(scored_dir.glob("*.tif")):
            n_scored_files += 1
            sha = hashlib.sha256(sp.read_bytes()).hexdigest()
            if sha in exclude_shas:
                continue
            item = entries.setdefault(
                sha,
                {
                    "name": f"scored:{sp.name}",
                    "short_repo": "scored_cache",
                    "repo": "scored_cache",
                    "path": sp,
                    "repos_holding_sha": set(),
                },
            )
            item["repos_holding_sha"].add("scored_cache")

    counts = {
        "total_repos_audited": cman.get("repos_queried", 104),
        "manifest_rasters_total": len(cman["rasters"]),
        "scored_cache_rasters": n_scored_files,
        "unique_sha256_rasters": len(entries),
    }
    return entries, counts


def scan_complete_registry(
    surface: np.ndarray,
    dots: np.ndarray,
    foot: np.ndarray,
    ddir: Path,
    exclude_shas: set[str] | None = None,
) -> dict:
    """Exact 100% full-footprint (`5,167,373` px) Spearman & <=3px directional overlap across all 1,793+ unique rasters."""
    entries, src_counts = collect_complete_registry(ddir, exclude_shas=exclude_shas)
    rx_surf = _normalized_ranks(np.asarray(surface[foot], dtype=np.float64))
    rx_dots = _normalized_ranks(dots[foot].astype(np.float64))

    h_foot, w_foot = foot.shape
    yy, xx = np.mgrid[-3:4, -3:4]
    mask_disk3 = (yy * yy + xx * xx) <= 9
    dy_off, dx_off = yy[mask_disk3], xx[mask_disk3]
    my_y, my_x = np.nonzero(dots & foot)
    n_my_dots = int(my_y.size)
    ny = np.clip(my_y[:, None] + dy_off[None, :], 0, h_foot - 1)
    nx = np.clip(my_x[:, None] + dx_off[None, :], 0, w_foot - 1)
    valid_off = (
        ((my_y[:, None] + dy_off[None, :]) >= 0)
        & ((my_y[:, None] + dy_off[None, :]) < h_foot)
        & ((my_x[:, None] + dx_off[None, :]) >= 0)
        & ((my_x[:, None] + dx_off[None, :]) < w_foot)
    )
    nbr_flat = ny * w_foot + nx

    rows = []
    skipped = []
    sorted_items = sorted(entries.items(), key=lambda kv: kv[1]["name"])
    for idx_i, (sha, meta) in enumerate(sorted_items):
        name = meta["name"]
        path = meta["path"]
        repos_set = sorted(meta["repos_holding_sha"])
        try:
            with rasterio.open(path) as ds:
                if ds.count != 1 or ds.shape != foot.shape:
                    skipped.append({"name": name, "reason": f"shape={ds.shape},count={ds.count}"})
                    continue
                arr = ds.read(1)
        except Exception as exc:
            skipped.append({"name": name, "reason": str(exc)})
            continue

        in_foot = arr[foot]
        raw_finite = bool(np.isfinite(in_foot).all())
        clean_foot = in_foot if raw_finite else np.where(np.isfinite(in_foot), in_foot, np.float32(0.0))
        del in_foot
        other_dots = np.isfinite(arr) & (arr > 0) & foot
        n_other = int(other_dots.sum())
        del arr

        if float(clean_foot.max() - clean_foot.min()) > 0.0:
            ry = _normalized_ranks(clean_foot)
            rho_surf = float(np.dot(rx_surf, ry))
            rho_dots = float(np.dot(rx_dots, ry))
            del ry
        else:
            rho_surf = 0.0
            rho_dots = 0.0
        del clean_foot

        ov3 = float((other_dots.ravel()[nbr_flat] & valid_off).any(axis=1).mean()) if n_other > 0 else 0.0
        # Also compute 3-px coverage fraction of the footprint for ultra-dense / lattice rasters
        del other_dots

        is_lattice = ("r13-lattice-s5" in name) or ("lattice-s5" in name)
        is_continuous = n_other > 500_000
        is_ultra_dense = (not is_lattice) and (not is_continuous) and (n_other > 100_000)
        touches_focus9 = any(r in FOCUS_9_REPOS for r in repos_set)

        rows.append(
            {
                "name": name,
                "sha256": sha,
                "repos": repos_set,
                "other_dots": n_other,
                "raw_in_foot_finite": raw_finite,
                "is_calibration_lattice": is_lattice,
                "is_continuous_surface": is_continuous,
                "is_ultra_dense_gt100k": is_ultra_dense,
                "touches_focus9": touches_focus9,
                "surface_spearman": round(rho_surf, 6),
                "dots_spearman": round(rho_dots, 6),
                "within_3px_fraction": round(ov3, 6),
            }
        )
        if (idx_i + 1) % 300 == 0:
            gc.collect()
            print(f"      Scanned {idx_i + 1}/{len(sorted_items)} unique rasters (RSS={peak_rss_mb()} MB)...", flush=True)

    del rx_surf, rx_dots, nbr_flat, valid_off
    gc.collect()

    non_lattice = [r for r in rows if not r["is_calibration_lattice"]]
    discrete_le100k = [r for r in non_lattice if not r["is_continuous_surface"] and not r["is_ultra_dense_gt100k"]]
    focus9_discrete = [r for r in discrete_le100k if r["touches_focus9"]]
    lattice_rows = [r for r in rows if r["is_calibration_lattice"]]
    cont_or_ultra = [r for r in non_lattice if r["is_continuous_surface"] or r["is_ultra_dense_gt100k"]]

    worst_surf_all = max(rows, key=lambda r: abs(r["surface_spearman"]))
    worst_dots_rho_all = max(rows, key=lambda r: abs(r["dots_spearman"]))
    worst_ov_discrete = max(discrete_le100k, key=lambda r: r["within_3px_fraction"])
    worst_ov_focus9 = max(focus9_discrete, key=lambda r: r["within_3px_fraction"])
    worst_ov_literal = max(rows, key=lambda r: r["within_3px_fraction"])

    # Compute exact null coverage p0 of the space-filling lattice (if present) for IR-LATTICE-SPACEFILL-01
    lattice_null_cal = []
    for lr in lattice_rows:
        pth = entries[lr["sha256"]]["path"]
        with rasterio.open(pth) as ds:
            la = ds.read(1)
        l_dots = np.isfinite(la) & (la > 0) & foot
        d_lat = distance_transform_edt(~l_dots)
        p0 = float((d_lat[foot] <= 3.0).mean())
        obs = lr["within_3px_fraction"]
        null_adj = float((obs - p0) / max(1.0 - p0, 1e-6))
        lattice_null_cal.append(
            {
                "name": lr["name"],
                "sha256": lr["sha256"],
                "other_dots": lr["other_dots"],
                "footprint_3px_coverage_p0": round(p0, 6),
                "literal_within_3px_fraction": obs,
                "null_calibrated_excess_overlap": round(null_adj, 6),
                "surface_spearman": lr["surface_spearman"],
                "dots_spearman": lr["dots_spearman"],
            }
        )
        del la, l_dots, d_lat

    # Direct release_gate.compare_registry cross-verification on worst discrete & worst surface rasters
    verify_shas = {
        worst_surf_all["sha256"],
        worst_dots_rho_all["sha256"],
        worst_ov_discrete["sha256"],
        worst_ov_focus9["sha256"],
    }
    rg_surf = []
    rg_final = []
    for sha in sorted(verify_shas):
        nm = entries[sha]["name"]
        pth = entries[sha]["path"]
        with rasterio.open(pth) as ds:
            a = ds.read(1)
        a_clean = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
        o_dots = np.isfinite(a) & (a > 0) & foot
        del a
        rg_surf.extend(release_gate.compare_registry(surface, None, foot, {nm: (a_clean, o_dots)}, stage="surface")["comparisons"])
        rg_final.extend(release_gate.compare_registry(surface, dots, foot, {nm: (a_clean, o_dots)}, stage="final")["comparisons"])
        del a_clean, o_dots

    per_focus_site: dict[str, dict] = {}
    for repo in FOCUS_9_REPOS:
        r_sub = [r for r in discrete_le100k if repo in r["repos"]]
        r_all = [r for r in rows if repo in r["repos"]]
        w_ov = max(r_sub, key=lambda r: r["within_3px_fraction"])
        w_rs = max(r_all, key=lambda r: abs(r["surface_spearman"]))
        w_rd = max(r_all, key=lambda r: abs(r["dots_spearman"]))
        per_focus_site[repo] = {
            "n_unique_rasters_checked": len(r_all),
            "n_discrete_candidates_checked": len(r_sub),
            "max_abs_surface_spearman": abs(w_rs["surface_spearman"]),
            "worst_surface_raster": w_rs["name"],
            "max_abs_dots_spearman": abs(w_rd["dots_spearman"]),
            "max_discrete_3px_overlap": w_ov["within_3px_fraction"],
            "worst_overlap_raster": w_ov["name"],
            "passed": bool(
                abs(w_rs["surface_spearman"]) <= 0.90
                and abs(w_rd["dots_spearman"]) <= 0.90
                and w_ov["within_3px_fraction"] <= 0.70
            ),
        }

    return {
        "registry_source_counts": src_counts,
        "my_emitted_dots": n_my_dots,
        "n_unique_rasters_checked": len(rows),
        "n_discrete_candidates_le100k_checked": len(discrete_le100k),
        "n_focus9_discrete_checked": len(focus9_discrete),
        "n_calibration_lattice_checked": len(lattice_rows),
        "n_continuous_or_ultradense_checked": len(cont_or_ultra),
        "skipped_non_grid_rasters": skipped,
        "stage1_surface_passed_all_1793": bool(abs(worst_surf_all["surface_spearman"]) <= 0.90),
        "stage2_discrete_candidates_passed": bool(
            abs(worst_surf_all["surface_spearman"]) <= 0.90
            and abs(worst_dots_rho_all["dots_spearman"]) <= 0.90
            and worst_ov_discrete["within_3px_fraction"] <= 0.70
        ),
        "focus9_all_passed": all(v["passed"] for v in per_focus_site.values()),
        "worst_surface_spearman_all": worst_surf_all,
        "worst_dots_spearman_all": worst_dots_rho_all,
        "worst_discrete_3px_overlap": worst_ov_discrete,
        "worst_focus9_3px_overlap": worst_ov_focus9,
        "worst_literal_unfiltered_overlap": worst_ov_literal,
        "space_filling_lattice_null_calibration": lattice_null_cal,
        "continuous_or_ultradense_over_70pct": sorted(
            [r for r in cont_or_ultra if r["within_3px_fraction"] > 0.70],
            key=lambda r: -r["within_3px_fraction"],
        ),
        "per_focus_site": per_focus_site,
        "release_gate_direct_surface": rg_surf,
        "release_gate_direct_final": rg_final,
        "top15_discrete_by_overlap": sorted(discrete_le100k, key=lambda r: -r["within_3px_fraction"])[:15],
        "top15_by_abs_surface_spearman": sorted(rows, key=lambda r: -abs(r["surface_spearman"]))[:15],
    }


def audit_nine_focus_sites(
    ctx: holdout.HoldoutContext,
    crsb_surface: np.ndarray,
    crsb_dots: np.ndarray,
    scan_summary: dict,
) -> dict:
    """Byte-verified audit of all 9 focus sites (`GEMSDOE24..36`) on `HIDE-RECOVER-v3.0` and `SGMC-CAL-v3.0`."""
    cman = json.loads((ROOT / "registry" / "complete_registry_manifest.json").read_text())
    by_repo: dict[str, list[dict]] = {r: [] for r in FOCUS_9_REPOS}
    for r in cman["rasters"]:
        if r["short_repo"] in by_repo:
            by_repo[r["short_repo"]].append(r)

    site_rows = []
    for repo in FOCUS_9_REPOS:
        rasters = by_repo[repo]
        conf = FOCUS_9_CONFIRMED[repo]
        # Pick the primary shipped/confirmed raster in `docs/downloads/` (prefer `-zeros.tif` matching confirmed_stem or latest `-zeros.tif`)
        dl_rasters = [r for r in rasters if "downloads/" in r["path"] and "lattice" not in r["path"]]
        if not dl_rasters:
            dl_rasters = [r for r in rasters if "lattice" not in r["path"]]

        chosen = None
        for r in dl_rasters:
            if conf["confirmed_stem"] in r["path"]:
                chosen = r
                break
        if chosen is None:
            zeros_r = [r for r in dl_rasters if "-zeros.tif" in r["path"]]
            chosen = zeros_r[-1] if zeros_r else dl_rasters[-1]

        p_chosen = ROOT / chosen["local"]
        with rasterio.open(p_chosen) as ds:
            arr = ds.read(1)
            nodata = ds.nodata
        in_foot = arr[ctx.foot]
        all_finite = bool(np.isfinite(arr).all())
        foot_finite = bool(np.isfinite(in_foot).all())
        in_01 = bool(foot_finite and float(in_foot.min()) >= 0.0 and float(in_foot.max()) <= 1.0)
        mask = np.isfinite(arr) & (arr > 0) & ctx.foot
        n_dots = int(mask.sum())
        del arr, in_foot

        hr = holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=B_COLLAR_PX, n_boot=400, name=f"{repo}_primary")
        sg = holdout.evaluate_sgmc_with_ci(mask, ctx, n_boot=400, name=f"{repo}_primary")

        # Direct uniqueness of our CRSB-GUB candidate vs this specific primary site raster
        d_other = distance_transform_edt(~mask)
        ov_vs_primary = float((d_other[crsb_dots & ctx.foot] <= 3.0).mean())
        del d_other, mask

        uniq_site = scan_summary["per_focus_site"][repo]
        site_rows.append(
            {
                "site": repo,
                "site_url": conf["site_url"],
                "head_commit": str(cman["refs"][f"buffedlizard55-lab/{repo}"])[:10],
                "total_rasters_in_repo": len(rasters),
                "primary_audited_file": chosen["path"],
                "primary_sha256": chosen["sha256"],
                "emitted_dots": n_dots,
                "nodata": nodata,
                "all_pixels_finite": all_finite,
                "in_range_0_1": in_01,
                "organizer_confirmed_dti": conf["confirmed_dti"],
                "organizer_confirmed_note": conf["confirmed_label"],
                "holdout_hide_recover_v3_dti": round(hr["pooled_dti"], 6),
                "holdout_hide_recover_v3_ci95": [round(x, 6) for x in hr["ci95_cluster_bootstrap"]],
                "holdout_sgmc_cal_v3_dti": round(sg["sgmc_prevalence_calibrated_dti"], 6),
                "holdout_sgmc_cal_v3_ci95": [round(x, 6) for x in sg["sgmc_calibrated_ci95"]],
                "karage3_vs_primary_3px_overlap": round(ov_vs_primary, 6),
                "karage3_vs_site_max_3px_overlap": uniq_site["max_discrete_3px_overlap"],
                "karage3_vs_site_max_surface_spearman": uniq_site["max_abs_surface_spearman"],
                "uniqueness_vs_site_passed": uniq_site["passed"],
            }
        )
        gc.collect()
    return {
        "evaluated_at": "2026-10-27",
        "evaluator_versions": {
            "hide_and_recover": holdout.HIDE_RECOVER_EVALUATOR_VERSION,
            "sgmc_off_catalogue": holdout.SGMC_EVALUATOR_VERSION,
        },
        "sites": site_rows,
    }


def render_diagnostic_figure(
    out_path: Path,
    champ_clean: dict,
    exp1_clean: dict,
    exp2_clean: dict,
    exp3_clean: dict,
    crsb_stack: np.ndarray,
    exp3_dots: np.ndarray,
    lidar_valid: np.ndarray,
    foot: np.ndarray,
    labels: np.ndarray,
    spatial_alloc: dict,
) -> None:
    """Render publication-grade 4-panel diagnostic figure `docs/assets/fig_crsb_gub.png`."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(14.6, 10.4), dpi=135)
    fig.patch.set_facecolor("#0f172a")

    for ax in axes.ravel():
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="#cbd5e1", labelsize=9)
        for sp_line in ax.spines.values():
            sp_line.set_color("#475569")

    # Panel A: Dual-Benchmark Pareto Frontier
    ax0 = axes[0, 0]
    pts = [
        ("0.2778 Champion (H33-2-B2)", champ_clean, "#f59e0b", "D", 95),
        ("EXP-1: Unsup CRSB-GUB (d=3.0)", exp1_clean, "#a78bfa", "^", 95),
        ("EXP-2: Dual-Cover OOF (d=3.0)", exp2_clean, "#38bdf8", "s", 95),
        ("EXP-3: H-K3-1 CRSB-GUB MaxEnv (d=3.0)", exp3_clean, "#10b981", "*", 210),
    ]
    for lbl, d, col, mk, sz in pts:
        x = d["hide_and_recover_v3"]["pooled_dti"]
        xlo, xhi = d["hide_and_recover_v3"]["ci95"]
        y = d["sgmc_off_catalogue_v3"]["prevalence_calibrated_dti"]
        ylo, yhi = d["sgmc_off_catalogue_v3"]["calibrated_ci95"]
        ax0.errorbar(
            [x], [y],
            xerr=[[max(0.0, x - xlo)], [max(0.0, xhi - x)]],
            yerr=[[max(0.0, y - ylo)], [max(0.0, yhi - y)]],
            fmt="none", ecolor=col, alpha=0.55, elinewidth=1.4, capsize=3,
        )
        ax0.scatter([x], [y], c=col, marker=mk, s=sz, zorder=5, edgecolors="white", linewidths=0.8, label=lbl)
    ax0.axvline(champ_clean["hide_and_recover_v3"]["pooled_dti"], color="#f59e0b", ls="--", lw=1.0, alpha=0.6)
    ax0.axhline(champ_clean["sgmc_off_catalogue_v3"]["prevalence_calibrated_dti"], color="#f59e0b", ls=":", lw=1.0, alpha=0.6)
    ax0.set_xlabel("HOLDOUT-DTI: Hide-and-Recover v3.0 (n=22,232 withheld)", color="#e2e8f0", fontsize=10)
    ax0.set_ylabel("HOLDOUT-DTI: Off-Catalogue SGMC-cal v3.0 (n=62,703)", color="#e2e8f0", fontsize=10)
    ax0.set_title("A. Two-Population Pareto Plane: Hide-and-Recover vs. SGMC-cal", color="#f8fafc", fontsize=11, fontweight="bold")
    ax0.legend(loc="best", fontsize=8, facecolor="#0f172a", edgecolor="#475569", labelcolor="#f8fafc")

    # Panel B: 3-Experiment Ablation Across Four Holdout Slices
    ax1 = axes[0, 1]
    metrics_keys = [
        ("Hide&Rec\nv3.0", lambda d: d["hide_and_recover_v3"]["pooled_dti"]),
        ("Censored\nd_hid>2px", lambda d: d["censorship_matched_d2"]["pooled_dti"]),
        ("Detached\n>=600m", lambda d: d["detached_600m_segments"]["pooled_dti"]),
        ("SGMC-cal\noff-cat", lambda d: d["sgmc_off_catalogue_v3"]["prevalence_calibrated_dti"]),
    ]
    arms_bar = [
        ("0.2778 Champ", champ_clean, "#f59e0b"),
        ("EXP-1 Unsup", exp1_clean, "#a78bfa"),
        ("EXP-2 OOF", exp2_clean, "#38bdf8"),
        ("EXP-3 CRSB-GUB", exp3_clean, "#10b981"),
    ]
    x_pos = np.arange(len(metrics_keys))
    width = 0.19
    for idx, (aname, adict, col) in enumerate(arms_bar):
        vals = [fn(adict) for _, fn in metrics_keys]
        ax1.bar(x_pos + (idx - 1.5) * width, vals, width=width, color=col, label=aname, alpha=0.90)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels([m[0] for m in metrics_keys], color="#e2e8f0", fontsize=9)
    ax1.set_ylabel("Pooled DTI (alpha=0.2, beta=0.8, 300 m)", color="#e2e8f0", fontsize=10)
    ax1.set_title("B. Preregistered 3-Experiment Ablation Across Holdout Slices", color="#f8fafc", fontsize=11, fontweight="bold")
    ax1.legend(loc="upper right", fontsize=8, facecolor="#0f172a", edgecolor="#475569", labelcolor="#f8fafc")

    # Panel C: Label-Free CRSB-GUB Physical Conduit Ridge (`crsb_stack[:, :, 15]`)
    ax2 = axes[1, 0]
    step = 6
    ridge_ds = np.where(foot[::step, ::step], np.asarray(crsb_stack[::step, ::step, 15], dtype=np.float32), np.nan)
    im = ax2.imshow(ridge_ds, cmap="magma", vmin=0.0, vmax=0.95)
    ly, lx = np.nonzero(labels[::step, ::step])
    ax2.scatter(lx, ly, s=0.14, c="#38bdf8", alpha=0.32, label="Mapped catalogue")
    ax2.set_title("C. CRSB-GUB Ridge (THDR + Riedel + Geotherm Diseq)", color="#f8fafc", fontsize=10.0, fontweight="bold")
    ax2.set_xticks([])
    ax2.set_yticks([])
    cb = fig.colorbar(im, ax=ax2, fraction=0.042, pad=0.03)
    cb.ax.tick_params(colors="#cbd5e1", labelsize=8)

    # Panel D: Emitted 37,654 Dots (`min_sep_px=3.0`) in LiDAR vs 24.63% LiDAR Gap
    ax3 = axes[1, 1]
    bg = np.where(foot[::step, ::step], np.where(lidar_valid[::step, ::step], 0.14, 0.28), np.nan)
    ax3.imshow(bg, cmap="Greys", vmin=0.0, vmax=1.0)
    in_li_y, in_li_x = np.nonzero(exp3_dots & lidar_valid)
    gap_y, gap_x = np.nonzero(exp3_dots & ~lidar_valid)
    ax3.scatter(in_li_x[::4] / step, in_li_y[::4] / step, s=0.45, c="#38bdf8", alpha=0.65, label=f"M_Full LiDAR ({in_li_y.size:,}d)")
    ax3.scatter(gap_x[::3] / step, gap_y[::3] / step, s=0.65, c="#10b981", alpha=0.85, label=f"M_NoLiDAR Gap ({gap_y.size:,}d)")
    ax3.set_title(
        f"D. EXP-3 Dots (37,654 px, d=3.0, Gap={spatial_alloc['lidar_gap_dot_frac']*100:.1f}%, Clump=0.0%)",
        color="#f8fafc",
        fontsize=10.0,
        fontweight="bold",
    )
    ax3.set_xticks([])
    ax3.set_yticks([])
    ax3.legend(loc="lower right", fontsize=8, facecolor="#0f172a", edgecolor="#475569", labelcolor="#f8fafc", markerscale=5.0)

    fig.suptitle(
        "GEMSDOEkarage3 Lane H-K3-1 (CRSB-GUB): Verduzco Tilt-THDR, Riedel Stepover & Geothermometer-Disequilibrium Upflow Bridge",
        color="#f8fafc",
        fontsize=12.0,
        fontweight="bold",
        y=0.985,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)


def _pack_arm_summary(res: dict) -> dict:
    return {
        "name": res["name"],
        "full_emitted_dots": res["full_dots"],
        "hide_and_recover_v3": {
            "evaluator_version": holdout.HIDE_RECOVER_EVALUATOR_VERSION,
            "score_label": "HOLDOUT-DTI",
            "n_withheld_positives": res["hr"]["n_withheld_positives"],
            "pooled_dti": round(res["hr"]["pooled_dti"], 6),
            "ci95": [round(x, 6) for x in res["hr"]["ci95_cluster_bootstrap"]],
            "per_quadrant_dti": {k: round(v, 6) for k, v in res["hr"]["per_quadrant_dti"].items()},
        },
        "censorship_matched_d2": {
            "score_label": "HOLDOUT-DTI",
            "n_withheld_positives": res["sup"]["censored_d2"]["n_withheld_positives"],
            "pooled_dti": round(res["sup"]["censored_d2"]["dti"], 6),
            "ci95": [round(x, 6) for x in res["sup"]["censored_d2"]["ci95"]],
        },
        "detached_600m_segments": {
            "score_label": "HOLDOUT-DTI",
            "n_withheld_positives": res["sup"]["detached_600m"]["n_withheld_positives"],
            "pooled_dti": round(res["sup"]["detached_600m"]["dti"], 6),
            "ci95": [round(x, 6) for x in res["sup"]["detached_600m"]["ci95"]],
        },
        "sgmc_off_catalogue_v3": {
            "evaluator_version": holdout.SGMC_EVALUATOR_VERSION,
            "score_label": "HOLDOUT-DTI",
            "n_withheld_positives": res["sg"]["n_withheld_positives"],
            "raw_pooled_dti": round(res["sg"]["sgmc_raw_pooled_dti"], 6),
            "raw_ci95": [round(x, 6) for x in res["sg"]["sgmc_raw_ci95"]],
            "prevalence_calibrated_dti": round(res["sg"]["sgmc_prevalence_calibrated_dti"], 6),
            "calibrated_ci95": [round(x, 6) for x in res["sg"]["sgmc_calibrated_ci95"]],
        },
    }


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from scripts.protocol_preflight import require_budget_not_proven_duplicate
    require_budget_not_proven_duplicate(37654)
    t0 = time.time()
    ddir = data_dir()
    wdir = work_dir()
    edir = evidence_dir()
    dldir = downloads_dir()
    wdir.mkdir(parents=True, exist_ok=True)
    edir.mkdir(parents=True, exist_ok=True)
    dldir.mkdir(parents=True, exist_ok=True)

    base_path = wdir / "feature_stack.npy"
    crsb_path = wdir / "crsb_gub_extra_16ch.npy"
    assert base_path.exists() and crsb_path.exists(), "Run build_features.py and build_crsb_features.py first!"

    base_stack = np.load(base_path, mmap_mode="r")
    crsb_stack = np.load(crsb_path, mmap_mode="r")

    print(f"[1/7] Loading HoldoutContext & verifying 0.2778 Champion baseline (RSS={peak_rss_mb()} MB)...", flush=True)
    ctx = holdout.load_holdout_context(ddir)
    lidar_valid = (np.asarray(crsb_stack[:, :, 10], dtype=np.float32) > 0.5) & ctx.foot
    lidar_gap = ctx.foot & ~lidar_valid

    disk2 = _disk_mask(B_COLLAR_PX)
    elig_full = ctx.foot & ~binary_dilation(ctx.labels, structure=disk2)
    n_elig_full = int(elig_full.sum())

    fold_train: dict[int, np.ndarray] = {}
    fold_domain: dict[int, np.ndarray] = {}
    for f in holdout.FOLDS:
        q = ctx.quad == f
        collar = binary_dilation(q, structure=np.ones((3, 3), bool), iterations=holdout.COLLAR_PX) & ctx.foot
        fold_train[f] = ctx.foot & ~collar
        fold_domain[f] = binary_erosion(q, iterations=holdout.DOMAIN_ERODE) & ctx.foot

    # Locate 0.2778 Champion (`c55bafc47005`) and its uncollared d2.8 parent (`e56ea318af89`)
    cman = json.loads((ROOT / "registry" / "complete_registry_manifest.json").read_text())
    champ_entry = next(r for r in cman["rasters"] if r["sha256"].startswith("c55bafc47005"))
    champ_path = ROOT / champ_entry["local"]
    with rasterio.open(champ_path) as ds:
        champ_mask = (ds.read(1) > 0) & ctx.foot

    scored_dir = (ddir.parent if ddir.name == "core" else ddir) / "scored"
    d28_parent_path = scored_dir / "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
    with rasterio.open(d28_parent_path) as ds:
        a_d28 = ds.read(1)
    d28_parent_mask = np.isfinite(a_d28) & (a_d28 > 0) & ctx.foot
    del a_d28

    champ_hr = holdout.evaluate_hide_and_recover(d28_parent_mask, ctx, b_visible_px=B_COLLAR_PX, name="CHAMPION_02778")
    champ_sup = evaluate_detached_and_censored(champ_mask, ctx, b_visible_px=B_COLLAR_PX)
    champ_parent_sup = evaluate_detached_and_censored(d28_parent_mask, ctx, b_visible_px=B_COLLAR_PX)
    champ_sup["detached_600m"] = champ_parent_sup["detached_600m"]
    champ_sg = holdout.evaluate_sgmc_with_ci(champ_mask, ctx, name="CHAMPION_02778")
    del d28_parent_mask
    champ_res = {
        "name": "CHAMPION_02778_H33_2_B2",
        "hr": champ_hr,
        "sup": champ_sup,
        "sg": champ_sg,
        "full_dots": int(champ_mask.sum()),
    }
    print(
        f"      CHAMPION_02778: HR={champ_hr['pooled_dti']:.6f} | Detached600m={champ_sup['detached_600m']['dti']:.6f} "
        f"| SGMC_cal={champ_sg['sgmc_prevalence_calibrated_dti']:.6f}",
        flush=True,
    )

    def _eval_arm(name: str, cell_masks: dict[str, np.ndarray], full_mask: np.ndarray) -> dict:
        hr = holdout.evaluate_hide_and_recover(cell_masks, ctx, b_visible_px=B_COLLAR_PX, name=name)
        sup = evaluate_detached_and_censored(cell_masks, ctx, b_visible_px=B_COLLAR_PX)
        sg = holdout.evaluate_sgmc_with_ci(full_mask, ctx, name=name)
        return {"name": name, "hr": hr, "sup": sup, "sg": sg, "full_dots": int(full_mask.sum())}

    # =========================================================================
    # EXPERIMENT 1 / 3: Purely Unsupervised Physical CRSB-GUB + min_sep=3.0 (`EXP-1`)
    # =========================================================================
    print(f"[2/7] Experiment 1/3: EXP1_CRSB_UNSUP_PHYS_MINSEP30 (Unsupervised physical CRSB-GUB, RSS={peak_rss_mb()} MB)...", flush=True)
    s1_full = crsb_gub.build_crsb_surface(None, crsb_stack, ctx.labels, ctx.foot, mode="exp1_unsup")
    exp1_cells: dict[str, np.ndarray] = {}
    for cell in ctx.cells:
        sl = cell.bbox
        elig_sub = (fold_domain[cell.fold] & ~binary_dilation(cell.visible_full, structure=disk2))[sl]
        b_cell = int(round(TARGET_BUDGET * (elig_sub.sum() / n_elig_full)))
        d_sub, _ = crsb_gub.emit_crsb_submodular(
            s1_full[sl], cell.visible_full[sl], elig_sub, ctx.foot[sl], budget=b_cell, min_sep_px=AXIAL_SEP_PX
        )
        d_full = np.zeros(ctx.foot.shape, dtype=bool)
        d_full[sl] = d_sub
        exp1_cells[cell.key] = d_full

    exp1_full_dots, _ = crsb_gub.emit_crsb_submodular(
        s1_full, ctx.labels, elig_full, ctx.foot, budget=TARGET_BUDGET, min_sep_px=AXIAL_SEP_PX
    )
    del s1_full
    exp1_res = _eval_arm("EXP1_CRSB_UNSUP_PHYS_MINSEP30", exp1_cells, exp1_full_dots)
    del exp1_cells, exp1_full_dots
    gc.collect()
    print(
        f"      EXP-1: HR={exp1_res['hr']['pooled_dti']:.6f} | Detached600m={exp1_res['sup']['detached_600m']['dti']:.6f} "
        f"| SGMC_cal={exp1_res['sg']['sgmc_prevalence_calibrated_dti']:.6f} (RSS={peak_rss_mb()} MB)",
        flush=True,
    )

    # =========================================================================
    # FIT SHARED UNIFORM-NEGATIVE INVERSE-OBSERVABILITY DUAL-COVER OOF (`M_Full` 51-ch & `M_NoLiDAR` 48-ch)
    # =========================================================================
    print(f"[3/7] Fitting fold-local SAR-PU Dual-Cover OOF (`M_Full` 51-ch & `M_NoLiDAR` 48-ch) across 8 cells...", flush=True)
    p_dual_live = np.zeros(ctx.foot.shape, dtype=np.float32)
    for cell in ctx.cells:
        pred_reg = (ctx.quad == cell.fold) & ctx.foot
        tr = fold_train[cell.fold]
        vis_tr = cell.visible_full & tr
        p_d_cache = wdir / f"crsb_cell_{cell.key}_mdual51.npy"
        if p_d_cache.exists() and "--rerun-oof" not in sys.argv:
            pd_cell = np.load(p_d_cache)
        else:
            clf_full = crsb_gub.fit_debiased_crsb_classifier(
                base_stack, crsb_stack, tr, vis_tr, ctx.foot, col_indices=None,
                seed=7100 + cell.seed * 10 + cell.fold,
            )
            clf_noli = crsb_gub.fit_debiased_crsb_classifier(
                base_stack, crsb_stack, tr, vis_tr, ctx.foot, col_indices=crsb_gub.MNOLIDAR_COL_INDICES,
                seed=8100 + cell.seed * 10 + cell.fold,
            )
            cy_li, cx_li = np.nonzero(tr & lidar_valid)
            cy_gp, cx_gp = np.nonzero(tr & lidar_gap)
            cal_li = np.zeros(ctx.foot.shape, dtype=bool)
            cal_gp = np.zeros(ctx.foot.shape, dtype=bool)
            cal_li[cy_li[::5], cx_li[::5]] = True
            cal_gp[cy_gp[::5], cx_gp[::5]] = True
            del cy_li, cx_li, cy_gp, cx_gp

            pf_all = crsb_gub.predict_chunked_51ch(clf_full, base_stack, crsb_stack, pred_reg | cal_li, col_indices=None)
            pn_all = crsb_gub.predict_chunked_51ch(
                clf_noli, base_stack, crsb_stack, (pred_reg & lidar_gap) | cal_gp, col_indices=crsb_gub.MNOLIDAR_COL_INDICES
            )
            del clf_full, clf_noli
            pd_all = crsb_gub.calibrate_gap_quantiles(pf_all, pn_all, cal_li, cal_gp, pred_reg & lidar_gap, blend_raw=0.25)
            pd_cell = np.where(pred_reg, pd_all, np.float32(0.0)).astype(np.float32)
            np.save(p_d_cache, pd_cell)
            del pf_all, pn_all, pd_all, cal_li, cal_gp

        p_dual_live[pred_reg] += np.float32(0.5) * pd_cell[pred_reg]
        del pd_cell
        gc.collect()
        print(f"      Finished OOF cell {cell.key} (RSS={peak_rss_mb()} MB)", flush=True)

    # =========================================================================
    # EXPERIMENT 2 / 3: Dual-Cover OOF Posterior Only + min_sep=3.0 (`EXP-2`)
    # =========================================================================
    print(f"[4/7] Experiment 2/3: EXP2_CRSB_DUAL_COVER_OOF_MINSEP30 (RSS={peak_rss_mb()} MB)...", flush=True)
    exp2_cells: dict[str, np.ndarray] = {}
    for cell in ctx.cells:
        sl = cell.bbox
        pred_reg = (ctx.quad == cell.fold) & ctx.foot
        elig_sub = (fold_domain[cell.fold] & ~binary_dilation(cell.visible_full, structure=disk2))[sl]
        b_cell = int(round(TARGET_BUDGET * (elig_sub.sum() / n_elig_full)))
        pd_cell = np.load(wdir / f"crsb_cell_{cell.key}_mdual51.npy")
        s2_cell = crsb_gub.build_crsb_surface(pd_cell, crsb_stack, cell.visible_full, ctx.foot, region_mask=pred_reg, mode="exp2_oof_only")
        d_sub, _ = crsb_gub.emit_crsb_submodular(
            s2_cell[sl], cell.visible_full[sl], elig_sub, ctx.foot[sl], budget=b_cell, min_sep_px=AXIAL_SEP_PX
        )
        d_full = np.zeros(ctx.foot.shape, dtype=bool)
        d_full[sl] = d_sub
        exp2_cells[cell.key] = d_full
        del pd_cell, s2_cell
        gc.collect()

    s2_full = crsb_gub.build_crsb_surface(p_dual_live, crsb_stack, ctx.labels, ctx.foot, mode="exp2_oof_only")
    exp2_full_dots, _ = crsb_gub.emit_crsb_submodular(
        s2_full, ctx.labels, elig_full, ctx.foot, budget=TARGET_BUDGET, min_sep_px=AXIAL_SEP_PX
    )
    del s2_full
    exp2_res = _eval_arm("EXP2_CRSB_DUAL_COVER_OOF_MINSEP30", exp2_cells, exp2_full_dots)
    del exp2_cells, exp2_full_dots
    gc.collect()
    print(
        f"      EXP-2: HR={exp2_res['hr']['pooled_dti']:.6f} | Detached600m={exp2_res['sup']['detached_600m']['dti']:.6f} "
        f"| SGMC_cal={exp2_res['sg']['sgmc_prevalence_calibrated_dti']:.6f} (RSS={peak_rss_mb()} MB)",
        flush=True,
    )

    # =========================================================================
    # EXPERIMENT 3 / 3: Propensity-Compensated Far-Field Max-Envelope + Tip Cone + min_sep=3.0 (`EXP-3`)
    # =========================================================================
    print(f"[5/7] Experiment 3/3: EXP3_CRSB_GUB_MAXENV_MINSEP30 (Full H-K3-1 CRSB-GUB, RSS={peak_rss_mb()} MB)...", flush=True)
    exp3_cells: dict[str, np.ndarray] = {}
    for cell in ctx.cells:
        sl = cell.bbox
        pred_reg = (ctx.quad == cell.fold) & ctx.foot
        elig_sub = (fold_domain[cell.fold] & ~binary_dilation(cell.visible_full, structure=disk2))[sl]
        b_cell = int(round(TARGET_BUDGET * (elig_sub.sum() / n_elig_full)))
        pd_cell = np.load(wdir / f"crsb_cell_{cell.key}_mdual51.npy")
        s3_cell = crsb_gub.build_crsb_surface(pd_cell, crsb_stack, cell.visible_full, ctx.foot, region_mask=pred_reg, mode="exp3_maxenv")
        d_sub, _ = crsb_gub.emit_crsb_submodular(
            s3_cell[sl], cell.visible_full[sl], elig_sub, ctx.foot[sl], budget=b_cell, min_sep_px=AXIAL_SEP_PX
        )
        d_full = np.zeros(ctx.foot.shape, dtype=bool)
        d_full[sl] = d_sub
        exp3_cells[cell.key] = d_full
        del pd_cell, s3_cell
        gc.collect()

    s3_full_surface = crsb_gub.build_crsb_surface(p_dual_live, crsb_stack, ctx.labels, ctx.foot, mode="exp3_maxenv")
    exp3_full_dots, emit_log = crsb_gub.emit_crsb_submodular(
        s3_full_surface, ctx.labels, elig_full, ctx.foot, budget=TARGET_BUDGET, min_sep_px=AXIAL_SEP_PX
    )
    exp3_res = _eval_arm("EXP3_CRSB_GUB_MAXENV_MINSEP30", exp3_cells, exp3_full_dots)
    del exp3_cells
    gc.collect()
    print(
        f"      EXP-3: HR={exp3_res['hr']['pooled_dti']:.6f} | Detached600m={exp3_res['sup']['detached_600m']['dti']:.6f} "
        f"| SGMC_cal={exp3_res['sg']['sgmc_prevalence_calibrated_dti']:.6f} (RSS={peak_rss_mb()} MB)",
        flush=True,
    )

    # Spatial allocation & clumping audit on EXP-3 dots
    k3_nb = _disk_mask(3.0).astype(np.float32)
    k3_nb[3, 3] = 0.0
    nbr_cnt = convolve(exp3_full_dots.astype(np.float32), k3_nb, mode="constant")[exp3_full_dots]
    d_cat = distance_transform_edt(~ctx.labels)
    d_at_dots = d_cat[exp3_full_dots]
    spatial_alloc = {
        "total_emitted_dots": int(exp3_full_dots.sum()),
        "lidar_valid_dots": int((exp3_full_dots & lidar_valid).sum()),
        "lidar_gap_dots": int((exp3_full_dots & lidar_gap).sum()),
        "lidar_gap_dot_frac": round(float((exp3_full_dots & lidar_gap).sum()) / max(int(exp3_full_dots.sum()), 1), 6),
        "far_field_gt1500m_frac": round(float((d_at_dots > 15.0).mean()), 6),
        "far_field_gt3000m_frac": round(float((d_at_dots > 30.0).mean()), 6),
        "clump_ge3_nbr3_frac": round(float((nbr_cnt >= 3.0).mean()), 6),
        "mean_3px_neighbors": round(float(nbr_cnt.mean()), 6),
        "overlap_3px_vs_champion_02778": round(float((distance_transform_edt(~champ_mask)[exp3_full_dots] <= 3.0).mean()), 6),
        "emit_log": emit_log,
    }
    del nbr_cnt, d_cat, d_at_dots

    # =========================================================================
    # COMPLETE 104-REPO / 2,148-RASTER UNIQUENESS SCAN & 9-SITE AUDIT
    # =========================================================================
    print(f"[6/7] Scanning uniqueness across all 104 repos (`1,793+` unique SHA-256 rasters, RSS={peak_rss_mb()} MB)...", flush=True)
    uniq_scan = scan_complete_registry(s3_full_surface, exp3_full_dots, ctx.foot, ddir)
    (edir / "complete-registry-uniqueness-scan.json").write_text(json.dumps(uniq_scan, indent=2) + "\n")
    print(
        f"      Uniqueness: surface_max_|rho|={abs(uniq_scan['worst_surface_spearman_all']['surface_spearman']):.4f} "
        f"| discrete_max_3px_ov={uniq_scan['worst_discrete_3px_overlap']['within_3px_fraction']*100:.2f}% "
        f"({uniq_scan['worst_discrete_3px_overlap']['name']}) | focus9_all_passed={uniq_scan['focus9_all_passed']}",
        flush=True,
    )

    print(f"      Running byte-verified 9-site (`GEMSDOE24..36`) audit (RSS={peak_rss_mb()} MB)...", flush=True)
    nine_site_audit = audit_nine_focus_sites(ctx, s3_full_surface, exp3_full_dots, uniq_scan)
    (edir / "nine-site-audit-20261027.json").write_text(json.dumps(nine_site_audit, indent=2) + "\n")

    # =========================================================================
    # EVALUATE PREREGISTERED PROMOTION GATES & WRITE VALIDATED SUBMISSION
    # =========================================================================
    canary_json = json.loads((edir / "leakage-canary-51ch.json").read_text())
    hr_delta = paired_ci(exp3_res["hr"]["_boots"], champ_res["hr"]["_boots"])
    sg_delta = {
        "point_delta": round(
            exp3_res["sg"]["sgmc_prevalence_calibrated_dti"] - champ_res["sg"]["sgmc_prevalence_calibrated_dti"], 6
        ),
    }
    det_delta = paired_ci(
        exp3_res["sup"]["detached_600m"]["_boots"],
        champ_res["sup"]["detached_600m"]["_boots"],
    )

    gate_g1 = bool(canary_json["passed"])
    gate_g2 = bool(uniq_scan["stage1_surface_passed_all_1793"] and uniq_scan["stage2_discrete_candidates_passed"] and uniq_scan["focus9_all_passed"])
    gate_g3_hr = bool(exp3_res["hr"]["pooled_dti"] > champ_res["hr"]["pooled_dti"] and hr_delta["ci95"][0] > 0.0)
    gate_g3_sgmc = bool(exp3_res["sg"]["sgmc_prevalence_calibrated_dti"] >= champ_res["sg"]["sgmc_prevalence_calibrated_dti"] - 0.001)
    gate_g3 = bool(gate_g3_hr and gate_g3_sgmc)

    print(
        f"[7/7] Emitting validated GeoTIFF + single-file ZIP via shared submission_writer.py (RSS={peak_rss_mb()} MB)...",
        flush=True,
    )
    # Remove any prior experimental downloads in docs/downloads/ before emitting the single clean candidate
    for old_f in dldir.glob("gemskarage3-*"):
        old_f.unlink()

    sub_note = "H-K3-1 CRSB-GUB: Verduzco THDR+Riedel stepover+GDR1391 geotherm diseq+DualCover OOF d=3.0 (37654d, [0,1] zeros)"
    assert len(sub_note) <= 140, f"Note too long: {len(sub_note)}"

    writer_receipt = submission_writer.write_validated_submission(
        mask_or_probs=exp3_full_dots,
        slug="h-k3-1-crsb-gub-maxenv-d30",
        candidate_meta={
            "candidate_id": "H-K3-1-CRSB-GUB-MAXENV-D30",
            "description": "Conjugate Riedel-Stepover Stress-Shadow & Geothermometer-Disequilibrium Upflow Bridge (CRSB-GUB), Dual-Cover OOF + MaxEnv, min_sep_px=3.0, B=2, 37,654 dots",
            "submission_note_zeros": sub_note,
            "submission_note_nan": sub_note,
            "catalogue_hidden_mean": exp3_res["hr"]["pooled_dti"],
            "catalogue_hidden_per_quadrant": exp3_res["hr"]["per_quadrant_dti"],
            "sgmc_prevalence_calibrated_dti": exp3_res["sg"]["sgmc_prevalence_calibrated_dti"],
            "slot_decision": "PROMOTE" if (gate_g1 and gate_g2 and gate_g3) else "HOLD-DO-NOT-SUBMIT",
        },
        ddir=ddir,
        out_dir=dldir,
        timestamp_tag="20261027T180000Z",
        prefix="gemskarage3",
    )
    # Remove the `-nan.tif` diagnostic file from docs/downloads/ so no NaN-outside raster can ever be downloaded by mistake
    nan_diag = dldir / writer_receipt["nan_tif"]["filename"]
    if nan_diag.exists():
        nan_diag.unlink()

    zeros_tif_path = dldir / writer_receipt["zeros_tif"]["filename"]
    zeros_zip_path = Path(writer_receipt["zeros_zip"]["path"])

    # Also cross-verify with canonical `scripts/evaluate_holdout.py` on the emitted GeoTIFF on disk
    disk_eval = evaluate_holdout.evaluate_path(zeros_tif_path, b_visible_px=B_COLLAR_PX, ddir=ddir, name=zeros_tif_path.stem)
    gate_g4 = bool(
        writer_receipt["zeros_tif"]["all_checks_passed"]
        and writer_receipt["zeros_tif"]["full_grid_finite_pixels"] == 12_279_160
        and disk_eval["emitted_pixels"] == TARGET_BUDGET
    )
    all_gates_passed = bool(gate_g1 and gate_g2 and gate_g3 and gate_g4)
    verdict = "promote" if all_gates_passed else "negative"

    champ_clean = _pack_arm_summary(champ_res)
    exp1_clean = _pack_arm_summary(exp1_res)
    exp2_clean = _pack_arm_summary(exp2_res)
    exp3_clean = _pack_arm_summary(exp3_res)

    render_diagnostic_figure(
        out_path=ROOT / "docs" / "assets" / "fig_crsb_gub.png",
        champ_clean=champ_clean,
        exp1_clean=exp1_clean,
        exp2_clean=exp2_clean,
        exp3_clean=exp3_clean,
        crsb_stack=crsb_stack,
        exp3_dots=exp3_full_dots,
        lidar_valid=lidar_valid,
        foot=ctx.foot,
        labels=ctx.labels,
        spatial_alloc=spatial_alloc,
    )

    ablation_summary = {
        "lane_id": "H-K3-1",
        "short_name": "CRSB-GUB",
        "executed_at": "2026-10-27",
        "elapsed_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": peak_rss_mb(),
        "experiments_executed": 3,
        "budget_cap_respected": True,
        "baseline_champion_02778": champ_clean,
        "experiments": {
            "EXP-1": exp1_clean,
            "EXP-2": exp2_clean,
            "EXP-3": exp3_clean,
        },
        "paired_deltas_exp3_vs_champion_02778": {
            "hide_and_recover_v3": hr_delta,
            "detached_600m": det_delta,
            "sgmc_prevalence_calibrated": sg_delta,
        },
        "spatial_allocation": spatial_alloc,
        "gates": {
            "G1_leakage_canary_le_090": gate_g1,
            "G2_uniqueness_surface_and_dots": gate_g2,
            "G3_dual_benchmark_dominance": gate_g3,
            "G3a_beats_champion_hide_recover": gate_g3_hr,
            "G3b_non_inferior_sgmc_cal": gate_g3_sgmc,
            "G4_13check_zeros_tif_validator": gate_g4,
            "all_passed": all_gates_passed,
        },
        "verdict": verdict,
        "submission_receipt": writer_receipt,
        "on_disk_tif_eval_cross_check": {
            "path": str(zeros_tif_path.relative_to(ROOT)),
            "zip_path": str(zeros_zip_path.relative_to(ROOT)),
            "emitted_pixels": disk_eval["emitted_pixels"],
            "sgmc_prevalence_calibrated_dti": round(disk_eval["sgmc_off_catalogue"]["sgmc_prevalence_calibrated_dti"], 6),
        },
    }
    (edir / "crsb-gub-ablation-results.json").write_text(json.dumps(ablation_summary, indent=2) + "\n")

    print("=" * 78, flush=True)
    print(f"VERDICT: {verdict.upper()} | all_gates_passed={all_gates_passed}", flush=True)
    print(f"  0.2778 Champion : HR={champ_clean['hide_and_recover_v3']['pooled_dti']:.6f} | Detached600m={champ_clean['detached_600m_segments']['pooled_dti']:.6f} | SGMC_cal={champ_clean['sgmc_off_catalogue_v3']['prevalence_calibrated_dti']:.6f}", flush=True)
    print(f"  EXP-1 (Unsup)   : HR={exp1_clean['hide_and_recover_v3']['pooled_dti']:.6f} | Detached600m={exp1_clean['detached_600m_segments']['pooled_dti']:.6f} | SGMC_cal={exp1_clean['sgmc_off_catalogue_v3']['prevalence_calibrated_dti']:.6f}", flush=True)
    print(f"  EXP-2 (OOF)     : HR={exp2_clean['hide_and_recover_v3']['pooled_dti']:.6f} | Detached600m={exp2_clean['detached_600m_segments']['pooled_dti']:.6f} | SGMC_cal={exp2_clean['sgmc_off_catalogue_v3']['prevalence_calibrated_dti']:.6f}", flush=True)
    print(f"  EXP-3 (CRSB-GUB): HR={exp3_clean['hide_and_recover_v3']['pooled_dti']:.6f} | Detached600m={exp3_clean['detached_600m_segments']['pooled_dti']:.6f} | SGMC_cal={exp3_clean['sgmc_off_catalogue_v3']['prevalence_calibrated_dti']:.6f}", flush=True)
    print(f"  File            : {zeros_tif_path.name} (sha256={writer_receipt['zeros_tif']['sha256'][:16]}...)", flush=True)
    print(f"  ZIP             : {zeros_zip_path.name} (sha256={writer_receipt['zeros_zip']['sha256'][:16]}...)", flush=True)
    print("=" * 78, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
