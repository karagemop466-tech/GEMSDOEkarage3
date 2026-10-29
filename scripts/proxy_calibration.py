#!/usr/bin/env python3
"""Calibrate the shared holdout proxies against USER-REPORTED leaderboard values.

Why this exists: the same binary raster can score very differently under the two
pinned evaluator variants in ``src/gems32/holdout.py``:

* ``hide_and_recover`` (``GEMSDOE32-HIDE-RECOVER-v3.0``, b_visible_px=0): no
  catalogue-distance gate on emitted pixels.
* ``visible_gated`` (``GEMSDOE32-HOLDOUT-v3-visible-gated``, b_gate_px=2): emitted
  pixels within 2 px of VISIBLE catalogue faults are removed before scoring.

This script scores each registry raster (fetched by its pinned repo/ref/path and
verified by SHA-256 against ``registry/complete_registry_manifest.json``) under both
variants and reports the rank agreement with the user-reported leaderboard values.

Labels: holdout numbers are HOLDOUT-DTI (evaluator version, n withheld positives,
95% cluster-bootstrap CI). Reported values are USER-REPORTED / UNVERIFIED (copied from
the supplied prompt, not organizer receipts). Nothing here is a leaderboard estimate.

Usage: python scripts/proxy_calibration.py [--out evidence/proxy-calibration-20261029.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir  # noqa: E402
from gems32.submission import require_binary_mask  # noqa: E402
from scripts.restore_data import fetch, sha256_file  # noqa: E402

MANIFEST = ROOT / "registry" / "complete_registry_manifest.json"
REGISTRY_CACHE = ROOT / ".cache" / "registry"

# (repo, path inside repo, USER-REPORTED value or None, short label)
# Values are copied verbatim from the supplied prompt's leaderboard inventory.
CALIBRATION_SET = [
    ("buffedlizard55-lab/GEMSDOE32", "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", 0.2778, "GEMSDOE32 h33-h33-2 zeros"),
    ("buffedlizard55-lab/GEMSDOE36", "docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif", 0.2750, "GEMSDOE36 anderson-pinn zeros"),
    ("buffedlizard55-lab/GEMSDOE28", "docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", 0.2710, "GEMSDOE28 h36-1 rung30 nan"),
    ("buffedlizard55-lab/GEMSDOE28", "docs/downloads/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif", 0.2708, "GEMSDOE28 h27-4-r1 solo nan"),
    ("buffedlizard55-lab/GEMSDOE31", "docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif", 0.2708, "GEMSDOE31 h27-4 solo nan"),
    ("buffedlizard55-lab/GEMSDOE33", "docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif", 0.2632, "GEMSDOE33 h33d analog-tip"),
    ("buffedlizard55-lab/GEMSDOE25", "docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600, "GEMSDOE25 dotted d2.8 nan"),
    ("buffedlizard55-lab/GEMSDOE30", "docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif", 0.2600, "GEMSDOE30 d28-poisson"),
    ("buffedlizard55-lab/GEMSDOE24", "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477, "GEMSDOE24 dotted d1.5 nan"),
    ("buffedlizard55-lab/GEMSDOE27", "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", 0.2449, "GEMSDOE27 topo-gap nan"),
    ("buffedlizard55-lab/19GEMSDOE", "docs/downloads/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif", 0.1922, "19GEMSDOE h19-5 powerlaw nan"),
    ("buffedlizard55-lab/19GEMSDOE", "docs/downloads/gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif", 0.1894, "19GEMSDOE h19-4 nan"),
    ("buffedlizard55-lab/16GEMSDOE", "docs/downloads/gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif", 0.1855, "16GEMSDOE h16-1 nan"),
    ("buffedlizard55-lab/GEMSDOE10", "docs/downloads/gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif", 0.1839, "GEMSDOE10 h28 dotted-ridge"),
    ("buffedlizard55-lab/8GEMSDOE", "docs/downloads/8GEMSDOE_Hedge-v2_submission.tif", 0.1563, "8GEMSDOE Hedge-v2"),
    ("buffedlizard55-lab/GEMSDOE10", "docs/downloads/gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif", 0.1280, "GEMSDOE10 h25 ctx-ridge"),
    ("buffedlizard55-lab/13GEMSDOE", "docs/downloads/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif", 0.0904, "13GEMSDOE lattice-s5 nan-outside"),
    ("buffedlizard55-lab/GEMSDOE9", "docs/downloads/gemsdoe9-PLACEHOLDER-2314b599.tif", 0.0107, "GEMSDOE9 PLACEHOLDER 2314b599"),
]


def manifest_index() -> dict[tuple[str, str], dict]:
    rows = json.loads(MANIFEST.read_text())["rasters"]
    idx: dict[tuple[str, str], dict] = {}
    for r in rows:
        idx.setdefault((r["repo"], r["path"]), r)
    return idx


def offcat_official_formula(mask: np.ndarray, ctx) -> dict:
    """ANALYSIS-ONLY variant (not part of the shared evaluator in src/gems32/holdout.py).

    Official distance-weighted Tversky formula (DrivenData problem page 967): TP_w = sum_g max_x p(x)k(d(x,g));
    FP_w = sum_x p(x)[1 - max_g k(d(x,g))]; FN_w = sum_g[1 - max_x p(x)k(d(x,g))];
    DTI = TP_w/(TP_w + 0.2 FP_w + 0.8 FN_w), k(d) = max(1 - d/3, 0), d in 100 m pixels.
    Truth G is the template's off-catalogue SGMC set (ctx.sgmc_off): a free official PROXY for the
    expert-labelled off-catalogue test faults. Predictions on catalogue pixels are NOT masked, as in the text.
    Label: PROXY-OFFCAT. Not HOLDOUT-DTI, not a leaderboard estimate.
    """
    from scipy.ndimage import distance_transform_edt

    from gems32.metric import ALPHA, BETA, EPS, kernel

    P = np.asarray(mask, bool) & ctx.foot
    G = np.asarray(ctx.sgmc_off, bool) & ctx.foot
    if not G.any() or not P.any():
        return {"dti": 0.0, "n_truth_px": int(G.sum()), "emitted_pixels": int(P.sum())}
    k_g = kernel(distance_transform_edt(~P)[G])     # nearest dot to every truth pixel
    k_p = kernel(distance_transform_edt(~G)[P])     # nearest truth pixel to every dot
    tp = float(k_g.sum())
    fn = float((1.0 - k_g).sum())
    fp = float((1.0 - k_p).sum())
    return {
        "dti": float(tp / (tp + ALPHA * fp + BETA * fn + EPS)),
        "tp_w": tp, "fp_w": fp, "fn_w": fn,
        "n_truth_px": int(G.sum()), "emitted_pixels": int(P.sum()),
    }


def score_mask(mask: np.ndarray, ctx) -> dict:
    hr = holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=0.0, name="calib")
    vg = holdout.evaluate_visible_gated_holdout(mask, ctx, name="calib")
    oc = offcat_official_formula(mask, ctx)
    return {
        "offcat_official_formula": {
            "evaluator_version": "ANALYSIS-ONLY offcat-official-formula (scripts/proxy_calibration.py)",
            "pooled_dti": oc["dti"],
            "n_truth_px": oc["n_truth_px"],
            "label": "PROXY-OFFCAT",
        },
        "hide_recover_b0": {
            "evaluator_version": hr["evaluator_version"],
            "pooled_dti": hr["pooled_dti"],
            "ci95": hr["ci95_cluster_bootstrap"],
            "n_withheld_positives": hr["n_withheld_positives"],
            "label": "HOLDOUT-DTI",
        },
        "visible_gated_b2": {
            "evaluator_version": vg["evaluator_version"],
            "pooled_dti": vg["pooled_dti"],
            "ci95": vg["ci95"],
            "n_withheld_positives": vg["n_withheld_positives"],
            "label": "HOLDOUT-DTI",
        },
        "emitted_pixels": int(mask.sum()),
    }


def load_mask(path: Path, ctx) -> np.ndarray:
    with rasterio.open(path) as ds:
        arr = ds.read(1)
    return require_binary_mask(arr, ctx.foot)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "proxy-calibration-20261029.json")
    args = ap.parse_args()

    ddir = data_dir()
    ctx = holdout.load_holdout_context(ddir)
    idx = manifest_index()
    rows = []
    for repo, path, reported, label in CALIBRATION_SET:
        entry = {"label": label, "repo": repo, "path": path, "reported_score_USER_REPORTED": reported}
        m = idx.get((repo, path))
        if m is None:
            entry["status"] = "NOT_IN_MANIFEST"
            rows.append(entry)
            continue
        dest = REGISTRY_CACHE / repo / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not (dest.exists() and sha256_file(dest) == m["sha256"]):
            fetch(repo, m["ref"], path, dest)
        got = sha256_file(dest)
        entry["sha256"] = got
        entry["sha256_matches_manifest"] = got == m["sha256"]
        entry["ref"] = m["ref"]
        if got != m["sha256"]:
            entry["status"] = "HASH_MISMATCH"
            rows.append(entry)
            continue
        try:
            mask = load_mask(dest, ctx)
        except ValueError as exc:  # non-binary content is recorded, never thresholded
            entry["status"] = f"REJECTED_BY_BINARY_CONTRACT: {exc}"
            rows.append(entry)
            continue
        entry["status"] = "scored"
        entry.update(score_mask(mask, ctx))
        rows.append(entry)

    scored = [r for r in rows if r.get("status") == "scored"]
    rep = np.array([r["reported_score_USER_REPORTED"] for r in scored], float)
    corr = {}
    for key in ("hide_recover_b0", "visible_gated_b2", "offcat_official_formula"):
        proxy = np.array([r[key]["pooled_dti"] for r in scored], float)
        rho, p = spearmanr(rep, proxy)
        corr[key] = {"spearman_rho_vs_USER_REPORTED": float(rho), "p_value": float(p), "n": len(scored)}

    out = {
        "schema": "proxy-calibration-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evaluator_sources": "src/gems32/holdout.py (evaluate_hide_and_recover, evaluate_visible_gated_holdout)",
        "holdout_context": {"data_dir": str(ddir), "n_cells": len(ctx.cells)},
        "labels": {
            "scores": "HOLDOUT-DTI (evaluator version, n withheld positives, 95% cluster-bootstrap CI)",
            "reported": "USER-REPORTED / UNVERIFIED (copied from supplied prompt; not organizer receipts)",
        },
        "rank_agreement": corr,
        "rows": rows,
        "caveat": "Rank agreement with unverified user-reported values; n is small; not a leaderboard estimate.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    for r in rows:
        if r.get("status") == "scored":
            print(f"{r['label']:34s} reported={r['reported_score_USER_REPORTED']:.4f}  "
                  f"b0={r['hide_recover_b0']['pooled_dti']:.4f}  gated_b2={r['visible_gated_b2']['pooled_dti']:.4f}")
        else:
            print(f"{r['label']:34s} {r.get('status')}")
    print(json.dumps(corr, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
