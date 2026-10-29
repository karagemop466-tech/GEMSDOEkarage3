#!/usr/bin/env python3
"""Experiment S6-E2: LiDAR scarp-step x coherence ridge candidate (new lane).

Hypothesis: pixels where the LiDAR scarp step (``step_max``) is strong AND the
local lineament coherence (``coh100``) is high mark fault scarps that are not
sampled by the nine focus submissions. Ranking uses only those two LiDAR bands.

Novelty caveat (reported in the run card): step_max and coh100 are NOT new inputs.
They appear in earlier lanes (src/karage3/ccl.py, hk3d_tgsf.py, surfaces_k3.py).
This run tests one product surface, step_max x coh100, not a new layer.

Duplicate protocol (scripts/dup_check_s6.py): the candidate's literal 3-px overlap with
the calibration lattice exceeds 70%, which triggers DUPLICATE_STOP. Proxy numbers are
logged for the record and are not used to advance this candidate.

Lane rules (enforced in code, reported in the run card):
* Feature set: ``step_max`` and ``coh100`` from lidar_scarp_features_u8.tif, read
  BY BAND DESCRIPTION (IR-K3-01: band index assumptions are wrong in sister repos).
* No magnetic, tilt, Euler, SGMC, radiometric or temperature input to the ranking.
* Excluded: pixels within 3 px of any focus-file dot, and known-fault pixels.
* Budget: 37,654 binary dots, same format as S6-E1 (NaN outside, 0/1 inside).
* Cultural-mimic control: fraction of selected dots within 100 m of mapped roads
  (tiger_road_distance_m.tif) is reported; road-side scarps are a named mimic.

Outputs (never a submission authorisation):
* evidence/experiments/s6-e2/<name>.tif
* evidence/exp-s6-e2-lidar-lineament.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32.paths import data_dir  # noqa: E402
from karage3.holdout import evaluate_hide_and_recover, evaluate_sgmc_with_ci, load_holdout_context  # noqa: E402
from focus_site_audit import FOCUS_SITES, dots_of, literal_overlap, _json_safe  # noqa: E402

N_DOTS = 37654
NAME = "gemsdoekarage3-s6-lidar-step-coh-37654-20261029.tif"
LATTICE_REL = "scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LIDAR_REL = "external/lidar_scarp_features_u8.tif"
ROAD_REL = "external/tiger_road_distance_m.tif"
BEST_NINE_SGMC = ("GEMSDOE27", 0.102422)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def band_by_name(src, name: str) -> np.ndarray:
    names = list(src.descriptions)
    if name not in names:
        raise KeyError(f"band '{name}' not in {names}")
    return src.read(names.index(name) + 1).astype(np.float64)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tif-out", type=Path, default=ROOT / "evidence" / "experiments" / "s6-e2" / NAME)
    ap.add_argument("--card", type=Path, default=ROOT / "evidence" / "exp-s6-e2-lidar-lineament.json")
    args = ap.parse_args()

    ddir = data_dir()
    with rasterio.open(ddir / "sample_submission.tif") as s:
        template = s.read(1)
        profile = dict(driver="GTiff", count=1, dtype="float32", crs=s.crs, transform=s.transform,
                       width=s.width, height=s.height, nodata=np.nan, compress="deflate", predictor=3)
    fp = np.isfinite(template)
    with rasterio.open(ddir / "labels.tif") as s:
        known = s.read(1) > 0
    with rasterio.open(ddir / LIDAR_REL) as s:
        step = band_by_name(s, "step_max")
        coh = band_by_name(s, "coh100")
        valid_band = band_by_name(s, "valid") > 0
    with rasterio.open(ddir / ROAD_REL) as s:
        road_m = s.read(1).astype(np.float64)

    valid = fp & valid_band
    score = np.where(valid, step * coh, -np.inf)  # step*coherence, 0..255^2 scale

    focus_union = np.zeros(fp.shape, bool)
    for site in FOCUS_SITES:
        with rasterio.open(ROOT / ".cache" / "focus" / f"{site}.tif") as fsrc:
            focus_union |= dots_of(fsrc.read(1).astype(np.float32))
    dist_focus = distance_transform_edt(~focus_union)
    free = valid & (dist_focus > 3.0) & ~known & (score > 0)
    idx = np.flatnonzero(free.ravel())
    n_sel = min(N_DOTS, idx.size)
    order = idx[np.argsort(-score.ravel()[idx], kind="stable")][:n_sel]
    sel = np.zeros(fp.shape, bool)
    sel.ravel()[order] = True

    out = np.full(fp.shape, np.nan, np.float32)
    out[fp] = 0.0
    out[sel] = 1.0
    args.tif_out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(args.tif_out, "w", **profile) as dst:
        dst.write(out, 1)
    file_sha = sha256_file(args.tif_out)

    with rasterio.open(args.tif_out) as s:
        saved = s.read(1)
        v = dict(
            crs_match=str(s.crs) == str(profile["crs"]),
            shape_match=(s.height, s.width) == fp.shape,
            transform_match=tuple(s.transform)[:6] == tuple(profile["transform"])[:6],
            single_band=s.count == 1,
            float32=s.dtypes[0] == "float32",
            nan_inside_footprint=int((~np.isfinite(saved) & fp).sum()),
            values_in_0_1_inside=bool(np.isin(saved[fp], [0.0, 1.0]).all()),
            nonzero_outside_footprint=int((np.nan_to_num(saved, nan=0.0)[~fp] != 0).sum()),
            dots=int((saved == 1).sum()),
        )
    v["validator_pass"] = bool(v["crs_match"] and v["shape_match"] and v["transform_match"] and v["single_band"]
                               and v["float32"] and v["nan_inside_footprint"] == 0
                               and v["values_in_0_1_inside"] and v["nonzero_outside_footprint"] == 0)

    dots = sel
    overlap_focus = {site: round(literal_overlap(dots, dots_of(_read_focus(site))), 6) for site in FOCUS_SITES}
    with rasterio.open(ddir / LATTICE_REL) as s:
        lat = s.read(1)
    overlap_lattice = round(literal_overlap(dots, dots_of(lat)), 6)

    road_near = float((road_m[dots] <= 100.0).mean()) if dots.any() else None
    road_near_fp = float((road_m[fp] <= 100.0).mean())

    ctx = load_holdout_context(ddir)
    sg = evaluate_sgmc_with_ci(dots & fp, ctx, name="S6-E2")
    hr = evaluate_hide_and_recover(dots & fp, ctx, name="S6-E2")

    truth = np.zeros(fp.shape, bool)
    ty, tx = ctx.sgmc_truth_coords
    truth[ty, tx] = True
    pool = valid & ~known
    rng = np.random.default_rng(20261029)
    pos_idx = np.flatnonzero(truth & pool)
    neg_all = np.flatnonzero(pool & ~truth)
    neg_idx = rng.choice(neg_all, size=min(pos_idx.size * 4, neg_all.size), replace=False)
    yv = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
    sc = np.r_[score.ravel()[pos_idx], score.ravel()[neg_idx]]
    auc = float(roc_auc_score(yv, sc))
    canary = {"step_x_coh_alone_auc_sgmc": round(auc, 6), "max_oriented_auc": round(max(auc, 1 - auc), 6),
              "threshold": 0.90, "pass": bool(max(auc, 1 - auc) <= 0.90),
              "n_pos": int(pos_idx.size), "n_neg": int(neg_idx.size)}

    best_name, best_val = BEST_NINE_SGMC
    sgmc_dti = float(sg["sgmc_raw_pooled_dti"])
    focus_band_low = 0.0943  # lowest raw SGMC DTI among the nine (audit JSON, GEMSDOE28)
    in_band = sgmc_dti >= focus_band_low
    card = {
        "experiment": "S6-E2",
        "lane": "LiDAR scarp step x lineament coherence (step_max * coh100), no magnetic/gravity/temperature input",
        "novelty": "NOT NOVEL as an input: step_max and coh100 are used in src/karage3/ccl.py, hk3d_tgsf.py and surfaces_k3.py. Tests one product surface only.",
        "hypothesis": "LiDAR scarp steps that are also laterally coherent mark fault scarps that the nine focus submissions do not sample.",
        "mechanism": "Coherent step-edges in the 1 m DEM-derived composite are the surface expression of normal-fault scarps.",
        "named_non_fault_mimic": "Road cut banks, levees, canal and fence lineaments and agricultural terraces produce coherent steps; road-distance control is reported.",
        "features_by_band_name": ["step_max", "coh100", "valid"],
        "n_dots": int(sel.sum()),
        "available_after_exclusions": int(idx.size),
        "budget_limited_by_availability": bool(idx.size < N_DOTS),
        "raster": {"file": f"evidence/experiments/s6-e2/{NAME}", "sha256": file_sha, "bytes": args.tif_out.stat().st_size,
                   "nodata": "NaN outside footprint; 0 inside; 1 = dot"},
        "validator": v,
        "uniqueness_vs_focus_nine_literal_3px_max": round(max(overlap_focus.values()), 6),
        "uniqueness_vs_focus_nine_by_site": overlap_focus,
        "uniqueness_vs_r13_lattice_literal_3px": overlap_lattice,
        "lattice_rule_pass_70pct": bool(overlap_lattice <= 0.70),
        "cultural_mimic_control": {"share_dots_within_100m_of_road": round(road_near, 6) if road_near is not None else None,
                                   "share_footprint_within_100m_of_road": round(road_near_fp, 6)},
        "holdout_sgmc_offcatalogue_raw": {
            "evidence_class": "HOLDOUT-DTI", "evaluator_version": sg["evaluator_version"],
            "withheld_positives": int(sg["n_withheld_positives"]),
            "dti": round(sgmc_dti, 6), "ci95": [round(float(x), 6) for x in sg["sgmc_raw_ci95"]],
            "same_evaluator_best_of_nine": {"site": best_name, "dti": best_val},
            "note": "Off-catalogue proxy. Not the hidden leaderboard.",
        },
        "holdout_hide_and_recover_catalogue": {
            "evidence_class": "HOLDOUT-DTI", "evaluator_version": hr["evaluator_version"],
            "withheld_positives": int(hr["n_withheld_positives"]),
            "dti": round(float(hr["pooled_dti"]), 6),
            "ci95": [round(float(x), 6) for x in hr["ci95_cluster_bootstrap"]],
            "note": "Catalogue proxy misaligned with official masking (IR-S6-02). Reported for transparency only.",
        },
        "feature_auc_canary": canary,
        "leaderboard_estimate": "NOT ESTIMABLE - no ORGANIZER-CONFIRMED receipt and no validated proxy that reproduces the reported focus-site ranking",
        "in_focus_band_proxy": bool(in_band),
        "duplicate_check": {"file": "evidence/dup-check-s6.json", "verdict": "DUPLICATE_STOP",
                            "trigger": "literal 3-px overlap with registered calibration lattice r13-lattice-s5 > 70%"},
        "verdict": "DUPLICATE_STOP (lattice overlap > 70%). Proxy number logged for the record only; not used to advance this candidate.",
        "ok_to_submit": False,
        "submission_name": NAME,
        "official_metric_source": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "official_masking_source": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
    }
    args.card.write_text(json.dumps(_json_safe(card), indent=2) + "\n")
    print(json.dumps({k: card[k] for k in ("n_dots", "uniqueness_vs_focus_nine_literal_3px_max",
                                            "uniqueness_vs_r13_lattice_literal_3px", "holdout_sgmc_offcatalogue_raw",
                                            "feature_auc_canary", "verdict")}, indent=2))
    return 0


def _read_focus(site: str) -> np.ndarray:
    with rasterio.open(ROOT / ".cache" / "focus" / f"{site}.tif") as fsrc:
        return fsrc.read(1).astype(np.float32)


if __name__ == "__main__":
    raise SystemExit(main())
