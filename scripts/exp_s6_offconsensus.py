#!/usr/bin/env python3
"""Experiment S6-E1: off-consensus, label-free magnetic ridge candidate.

Hypothesis (one sentence): ridge crests of the total-magnetic-intensity horizontal
gradient (``tmi_hg``, Blakely & Simpson 1986 style non-maximum suppression along
the gradient direction) that lie OUTSIDE the 3-px neighbourhood of every dot in the
nine focus-site submissions carry some off-catalogue fault signal that the
near-duplicate consensus cluster does not sample.

Design constraints (all enforced in code, all reported in the run card):
* Label-free: the ridge score uses only ``tmi_hg`` (band 3). Catalogue labels are
  used ONLY to exclude known-fault pixels, which the official scorer also masks.
* Lane: no tilt, Euler, SGMC, LiDAR, or temperature feature (see the registry
  of earlier lanes in docs/research/*.md).
* Budget: 37,654 binary dots (GEMSDOE32 budget), 0 dots inside the nine focus
  files' 3-px neighbourhoods (so every focus-file literal overlap is 0.0 by
  construction), and no dots on exact known-fault pixels.
* Format: float32, EPSG:32611, template transform, NaN outside the footprint
  and 0/1 inside — the same convention as the organizer sample_submission.tif.

Outputs (never a submission authorization):
* evidence/experiments/s6-e1/<name>.tif     candidate raster (kept out of docs/ so the
                                             retained-TIFF saved-byte audit is unaffected)
* evidence/exp-s6-e1-offconsensus.json      run card (HOLDOUT-DTI labels, overlaps,
                                             leakage canary, validator, gate verdict)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32.paths import data_dir  # noqa: E402
from karage3.holdout import evaluate_hide_and_recover, evaluate_sgmc_with_ci, load_holdout_context  # noqa: E402
from focus_site_audit import FOCUS_SITES, dots_of, literal_overlap, _json_safe  # noqa: E402

N_DOTS = 37654
NAME = "gemsdoekarage3-s6-offcons-tmihg-ridge-37654-20261029.tif"
TMI_HG_BAND = 3  # "tmi_hg - Total magnetic intensity horizontal gradient" (verified against band descriptions)
LATTICE_REL = "scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
BEST_NINE_SGMC = ("GEMSDOE27", 0.102422)  # highest raw SGMC DTI among the nine (see audit JSON)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ridge_mask(g: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Non-maximum suppression of |grad| along its own gradient direction (Canny-style)."""
    gf = np.where(valid, g, 0.0)
    gy, gx = np.gradient(gf)
    mag = np.hypot(gy, gx)
    ok = mag > 1e-12
    oy = np.zeros(g.shape, np.int8)
    ox = np.zeros(g.shape, np.int8)
    oy[ok] = np.clip(np.rint(gy[ok] / mag[ok]), -1, 1).astype(np.int8)
    ox[ok] = np.clip(np.rint(gx[ok] / mag[ok]), -1, 1).astype(np.int8)
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    keep = np.ones(g.shape, bool)
    for sgn in (1, -1):
        ny = np.clip(yy + sgn * oy, 0, H - 1)
        nx = np.clip(xx + sgn * ox, 0, W - 1)
        keep &= gf >= gf[ny, nx]
    return keep & ok & valid & (gf > 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tif-out", type=Path, default=ROOT / "evidence" / "experiments" / "s6-e1" / NAME)
    ap.add_argument("--card", type=Path, default=ROOT / "evidence" / "exp-s6-e1-offconsensus.json")
    args = ap.parse_args()

    ddir = data_dir()
    with rasterio.open(ddir / "sample_submission.tif") as s:
        template = s.read(1)
        profile = dict(driver="GTiff", count=1, dtype="float32", crs=s.crs, transform=s.transform,
                       width=s.width, height=s.height, nodata=np.nan,
                       compress="deflate", predictor=3)  # float predictor; matches repo-scale file sizes
    fp = np.isfinite(template)
    with rasterio.open(ddir / "training_features.tif") as s:
        g_raw = s.read(TMI_HG_BAND).astype(np.float64)
        assert s.descriptions[TMI_HG_BAND - 1].startswith("tmi_hg"), s.descriptions[TMI_HG_BAND - 1]
    with rasterio.open(ddir / "labels.tif") as s:
        known = s.read(1) > 0
    valid = fp & np.isfinite(g_raw)

    ridge = ridge_mask(g_raw, valid)
    focus_union = np.zeros(fp.shape, bool)
    focus_dots = {}
    for site in FOCUS_SITES:
        with rasterio.open(ROOT / ".cache" / "focus" / f"{site}.tif") as fsrc:
            d = dots_of(fsrc.read(1).astype(np.float32))
        focus_dots[site] = d
        focus_union |= d
    dist_focus = distance_transform_edt(~focus_union)
    free = valid & (dist_focus > 3.0) & ~known
    cand = ridge & free
    n_avail = int(cand.sum())
    n_sel = min(N_DOTS, n_avail)
    idx = np.flatnonzero(cand)
    order = idx[np.argsort(-g_raw.ravel()[idx], kind="stable")][:n_sel]
    sel = np.zeros(fp.shape, bool)
    sel.ravel()[order] = True

    out = np.full(fp.shape, np.nan, np.float32)
    out[fp] = 0.0
    out[sel] = 1.0
    args.tif_out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(args.tif_out, "w", **profile) as dst:
        dst.write(out, 1)
    raw_bytes_sha = sha256_file(args.tif_out)

    # ---- validator: re-read the saved bytes -------------------------------------
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

    # ---- overlap vs the nine focus files and the registered calibration lattice ---
    dots = sel
    overlap_focus = {s: round(literal_overlap(dots, focus_dots[s]), 6) for s in FOCUS_SITES}
    with rasterio.open(ddir / LATTICE_REL) as s:
        lat = s.read(1)
    lat_dots = dots_of(lat)
    overlap_lattice = round(literal_overlap(dots, lat_dots), 6)
    lat_cov = float(((distance_transform_edt(~lat_dots) <= 3.0 + 1e-9) & fp).sum() / fp.sum())

    # ---- holdout estimates (same evaluator, same context) -------------------------
    ctx = load_holdout_context(ddir)
    sg = evaluate_sgmc_with_ci(dots & fp, ctx, name="S6-E1")
    hr = evaluate_hide_and_recover(dots & fp, ctx, name="S6-E1")

    # ---- leakage canary: each single feature alone on the SGMC holdout -----------
    truth = np.zeros(fp.shape, bool)
    ty, tx = ctx.sgmc_truth_coords
    truth[ty, tx] = True
    pool = valid & ~known
    rng = np.random.default_rng(20261029)
    pos_idx = np.flatnonzero(truth & pool)
    neg_all = np.flatnonzero(pool & ~truth)
    neg_idx = rng.choice(neg_all, size=min(pos_idx.size * 4, neg_all.size), replace=False)
    yv = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
    sc = np.r_[g_raw.ravel()[pos_idx], g_raw.ravel()[neg_idx]]
    auc_tmi_hg = float(roc_auc_score(yv, sc))
    canary = {"tmi_hg_alone_auc_sgmc": round(auc_tmi_hg, 6), "max_oriented_auc": round(max(auc_tmi_hg, 1 - auc_tmi_hg), 6),
              "threshold": 0.90, "pass": bool(max(auc_tmi_hg, 1 - auc_tmi_hg) <= 0.90),
              "n_pos": int(pos_idx.size), "n_neg": int(neg_idx.size)}

    best_name, best_val = BEST_NINE_SGMC
    card = {
        "experiment": "S6-E1",
        "lane": "off-consensus label-free magnetic ridge (tmi_hg NMS), exclusion of nine focus-file 3-px neighbourhoods",
        "hypothesis": "Off-consensus ridge crests of tmi_hg carry off-catalogue fault signal not sampled by the nine near-duplicate focus submissions.",
        "mechanism": "Non-maximum suppression of tmi_hg along its gradient picks magnetic-gradient crests; crests remote from the focus cluster add recall where the focus cluster has none.",
        "named_non_fault_mimic": "Magnetic contrasts from intrusions, basin-margin volcanics, and cultural metal (not faults) produce the same tmi_hg crests.",
        "ranking_rule": "top-N by tmi_hg among ridge pixels outside focus 3-px neighbourhoods and off known-fault pixels",
        "n_dots": int(sel.sum()),
        "ridge_pixels_total": int(ridge.sum()),
        "ridge_pixels_available_after_exclusions": n_avail,
        "budget_limited_by_availability": bool(n_avail < N_DOTS),
        "raster": {"file": f"evidence/experiments/s6-e1/{NAME}", "sha256": raw_bytes_sha, "bytes": args.tif_out.stat().st_size,
                   "nodata": "NaN outside footprint; 0 inside; 1 = dot"},
        "validator": v,
        "uniqueness_vs_focus_nine_literal_3px_max": round(max(overlap_focus.values()), 6),
        "uniqueness_vs_focus_nine_by_site": overlap_focus,
        "uniqueness_vs_r13_lattice_literal_3px": overlap_lattice,
        "lattice_footprint_coverage_3px": round(lat_cov, 6),
        "lattice_rule_pass_70pct": bool(overlap_lattice <= 0.70),
        "holdout_sgmc_offcatalogue_raw": {
            "evidence_class": "HOLDOUT-DTI", "evaluator_version": sg["evaluator_version"],
            "withheld_positives": int(sg["n_withheld_positives"]),
            "dti": round(float(sg["sgmc_raw_pooled_dti"]), 6),
            "ci95": [round(float(x), 6) for x in sg["sgmc_raw_ci95"]],
            "same_evaluator_best_of_nine": {"site": best_name, "dti": best_val},
            "note": "Off-catalogue proxy; the nine focus files score 0.094-0.102 on it. Not the hidden leaderboard.",
        },
        "holdout_hide_and_recover_catalogue": {
            "evidence_class": "HOLDOUT-DTI", "evaluator_version": hr["evaluator_version"],
            "withheld_positives": int(hr["n_withheld_positives"]),
            "dti": round(float(hr["pooled_dti"]), 6),
            "ci95": [round(float(x), 6) for x in hr["ci95_cluster_bootstrap"]],
            "note": "Catalogue-recovery proxy. Official scoring masks known catalogue faults, so this proxy is misaligned with the target; reported for transparency only.",
        },
        "feature_auc_canary": canary,
        "official_masking_source": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
        "official_metric_source": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "leaderboard_estimate": "NOT ESTIMABLE — no ORGANIZER-CONFIRMED receipt and no validated proxy that reproduces the reported focus-site ranking",
        "verdict": "negative",
        "ok_to_submit": False,
        "submission_name": NAME,
        "note": "Off-consensus tmi_hg ridge, 37,654 dots, 0 focus-site 3px overlap; blocked by lattice rule.",
        "blockers": [],
    }
    blockers = []
    if not v["validator_pass"]:
        blockers.append("local validator failed")
    if not card_lattice_pass(overlap_lattice):
        blockers.append(f"literal 3px overlap with registered calibration lattice r13-lattice-s5 = {overlap_lattice:.4%} > 70% (no non-hole-gaming dot set of N >= ~22,164 can pass; see README)")
    blockers.append("registry inventory not literal-complete (registry/complete_registry_manifest.json literal_registry_complete=false)")
    blockers.append("no ORGANIZER-CONFIRMED receipt; leaderboard score not estimable")
    blockers.append("shared holdout template has open upstream defects (GEMSDOE32 issues #42, #60, #66)")
    card["blockers"] = blockers

    args.card.parent.mkdir(parents=True, exist_ok=True)
    args.card.write_text(json.dumps(_json_safe(card), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"dots": card["n_dots"], "validator_pass": v["validator_pass"],
                      "max_focus_overlap": card["uniqueness_vs_focus_nine_literal_3px_max"],
                      "lattice_overlap": overlap_lattice, "sgmc_raw": card["holdout_sgmc_offcatalogue_raw"]["dti"],
                      "sgmc_ci": card["holdout_sgmc_offcatalogue_raw"]["ci95"], "canary_auc": canary["tmi_hg_alone_auc_sgmc"],
                      "sha256": raw_bytes_sha}, indent=2))
    print(f"wrote {args.tif_out}\nwrote {args.card}")
    return 0


def card_lattice_pass(x: float) -> bool:
    return x <= 0.70


if __name__ == "__main__":
    raise SystemExit(main())
