#!/usr/bin/env python3
"""Lane K3-CCL (Catalogue-Completion Learner) — holdout experiments, 2026-10-28.

Runs at most three preregistered experiments on the shared GEMSDOE32-HIDE-RECOVER-v3.0
evaluator (8 cells = 4 quadrants x draws 20, 21; whole components withheld; 15-px collar):

  E1  CCL-GEOM   physics stack + LiDAR + visible-catalogue geometry; Poisson-disk greedy d=2.8
  E2  CCL-CREST  same surface; crest (ridge-normal NMS) pixels offered first, then fill
  E3  PHYS-ONLY  ablation: same learner without catalogue-geometry features (tests the mechanism)

Every arm emits exactly the same per-cell dot budget as the frozen control (the champion bytes
gated at B=2 inside each cell), so the comparison is budget-matched.  The control is the
archived CHAMPION_02778 baseline (0.099202) and is re-scored here as an evaluator-parity check.
Paired deltas use the evaluator's fixed-seed spatial-block bootstrap (identical resamples).

Outputs evidence/ccl_experiments.json.  Scores are HOLDOUT-DTI, never leaderboard scores.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.features import CHANNELS  # noqa: E402
from karage3 import ccl  # noqa: E402

DDIR = ROOT / ".cache" / "gems_data"
STACK = ROOT / ".cache" / "gems_work" / "feature_stack.npy"
CHAMP = ROOT / ".cache/ledger/GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
B_PX = 2.0
SEP = 2.8


def load_lidar() -> np.ndarray:
    with rasterio.open(DDIR / "external" / "lidar_scarp_features_u8.tif") as ds:
        return np.stack([ds.read(b) for b in ccl.LIDAR_BANDS.values()]).astype(np.uint8)


def paired(a: dict, b: dict) -> dict:
    d = a["_boots"] - b["_boots"]
    return {"delta_point": float(a["pooled_dti"] - b["pooled_dti"]),
            "delta_ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            "p_delta_le_0": float((d <= 0).mean())}


def strip(r: dict) -> dict:
    return {k: v for k, v in r.items() if not k.startswith("_")}


def main() -> int:
    # Archived runner: do not reach any filesystem writes or candidate placement.
    raise SystemExit('STOP: historical experiment runner is disabled; no assigned lane, '
                     'shared holdout defects and the literal duplicate-stop remain unresolved.')
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "evidence" / "ccl_experiments.json"))
    args = ap.parse_args()
    from scripts.protocol_preflight import require_shared_protocol_ready
    require_shared_protocol_ready()
    t0 = time.time()
    stack = np.load(STACK, mmap_mode="r")
    lidar = load_lidar()
    sc2 = np.asarray(stack[:, :, CHANNELS.index("strike_cos")])
    ss2 = np.asarray(stack[:, :, CHANNELS.index("strike_sin")])
    ctx = holdout.load_holdout_context(DDIR)
    foot, labels, quad = ctx.foot, ctx.labels, ctx.quad
    with rasterio.open(CHAMP) as ds:
        champ = (ds.read(1) > 0) & foot
    print(f"context ready {time.time()-t0:.0f}s", flush=True)

    names_g = ccl.feature_names(True, CHANNELS)
    arms = {"E1_CCL_GEOM": {}, "E2_CCL_CREST": {}, "E3_PHYS_ONLY": {}}
    budgets, canary_rows, importances = {}, [], {}
    for cell in ctx.cells:
        tc = time.time()
        rng = np.random.default_rng(20261028 + cell.fold + 100 * cell.seed)
        vis = ctx.visible_by_cell[cell.key]
        q = quad == cell.fold
        collar = ndimage.binary_dilation(q, structure=np.ones((3, 3), bool), iterations=holdout.COLLAR_PX) & foot
        hidden = labels & ~vis
        geom = ccl.catalogue_geometry(vis, sc2, ss2)
        dvis = np.expm1(geom[..., 0])
        pos = hidden & ~collar & (dvis > 1)                       # == hidden_train components
        neg_pool = foot & ~collar & ~labels & (dvis > 1)
        ys, xs, y = ccl.sample_training(rng, pos, neg_pool)
        Xg = ccl.gather(stack, lidar, geom, ys, xs)
        m_geom = ccl.fit(Xg, y)
        m_phys = ccl.fit(Xg[:, :-len(ccl.GEOM_NAMES)], y)

        sl = cell.bbox
        region = np.zeros_like(foot)
        region[sl] = cell.active_sub & (cell.d_vis_sub > B_PX)
        # budget = control's emitted count inside the scored cell (same gating as the evaluator)
        budget = int((champ[sl] & cell.active_sub & (cell.d_vis_sub > B_PX)).sum())
        budgets[cell.key] = budget
        s_geom = ccl.predict_region(m_geom, stack, lidar, geom, region)
        s_phys = ccl.predict_region(m_phys, stack, lidar, None, region)
        arms["E1_CCL_GEOM"][cell.key] = ccl.greedy_dots(s_geom, region, budget, SEP)
        crest = np.zeros_like(foot)
        crest[sl] = ccl.crest_mask(s_geom[sl])
        arms["E2_CCL_CREST"][cell.key] = ccl.greedy_dots(s_geom, region, budget, SEP, crest=crest)
        arms["E3_PHYS_ONLY"][cell.key] = ccl.greedy_dots(s_phys, region, budget, SEP)

        # leakage canary on this cell's withheld truth: every single feature + the full model
        truth = np.zeros_like(foot)
        truth[sl][cell.truth_coords] = True
        ty, tx = np.nonzero(truth)
        ny, nx = np.nonzero(region & ~truth)
        k = min(ny.size, 20 * ty.size)
        sel = rng.choice(ny.size, k, replace=False)
        cy, cx = np.concatenate([ty, ny[sel]]), np.concatenate([tx, nx[sel]])
        cyv = np.concatenate([np.ones(ty.size), np.zeros(k)])
        Xc = ccl.gather(stack, lidar, geom, cy, cx)
        row = {"cell": cell.key, "n_truth": int(ty.size)}
        for j, nm in enumerate(names_g):
            col = Xc[:, j]
            row[nm] = float(roc_auc_score(cyv, col)) if np.ptp(col) > 0 else 0.5
        row["MODEL_CCL_GEOM"] = float(roc_auc_score(cyv, s_geom[cy, cx]))
        row["MODEL_PHYS_ONLY"] = float(roc_auc_score(cyv, s_phys[cy, cx]))
        canary_rows.append(row)
        print(f"{cell.key}: budget={budget} pos={int(y.sum())} auc_geom={row['MODEL_CCL_GEOM']:.3f} "
              f"auc_phys={row['MODEL_PHYS_ONLY']:.3f} {time.time()-tc:.0f}s", flush=True)
        del geom, dvis, s_geom, s_phys, Xg

    res = {"CONTROL_CHAMPION_B2": holdout.evaluate_hide_and_recover(champ, ctx, b_visible_px=B_PX, name="CONTROL")}
    for a, cells in arms.items():
        res[a] = holdout.evaluate_hide_and_recover(cells, ctx, b_visible_px=B_PX, name=a)
    for a, r in res.items():
        print(f"{a}: HOLDOUT-DTI {r['pooled_dti']:.6f} CI {np.round(r['ci95_cluster_bootstrap'], 4).tolist()}", flush=True)

    feats = names_g + ["MODEL_CCL_GEOM", "MODEL_PHYS_ONLY"]
    canary = {}
    for nm in feats:
        w = np.array([r["n_truth"] for r in canary_rows], float)
        raw = float(np.average([r[nm] for r in canary_rows], weights=w))
        canary[nm] = {"raw_auc": raw, "oriented_auc": max(raw, 1 - raw),
                      "passed": bool(max(raw, 1 - raw) <= 0.90)}
    out = {
        "schema_version": 1,
        "lane": "K3-CCL Catalogue-Completion Learner",
        "evaluator_version": holdout.HIDE_RECOVER_EVALUATOR_VERSION,
        "score_label": "HOLDOUT-DTI",
        "b_visible_px": B_PX, "min_sep_px": SEP,
        "budget_rule": "per-cell dot budget = control (champion bytes) count after identical B=2 gating",
        "per_cell_budget": budgets,
        "results": {a: strip(r) for a, r in res.items()},
        "paired_vs_control": {a: paired(res[a], res["CONTROL_CHAMPION_B2"]) for a in arms},
        "paired_E1_vs_E3_mechanism": paired(res["E1_CCL_GEOM"], res["E3_PHYS_ONLY"]),
        "paired_E2_vs_E1": paired(res["E2_CCL_CREST"], res["E1_CCL_GEOM"]),
        "leakage_canary": {"rule": "oriented single-feature AUC on withheld truth > 0.90 => leakage; "
                                   "model AUCs reported for context (not single features)",
                           "features": canary,
                           "single_feature_max": max(canary[n]["oriented_auc"] for n in names_g),
                           "passed": all(canary[n]["passed"] for n in names_g)},
        "seconds": round(time.time() - t0, 1),
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("paired_vs_control", "paired_E1_vs_E3_mechanism", "paired_E2_vs_E1")}, indent=1))
    print("canary single-feature max", out["leakage_canary"]["single_feature_max"], "passed", out["leakage_canary"]["passed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
