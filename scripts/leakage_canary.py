#!/usr/bin/env python3
"""Single-feature leakage canary (protocol rule 4).

Each feature is tested ALONE against the SGMC off-catalogue truth used by the shared
evaluator (cells > 3 px from the catalogue; positives = USGS SGMC fault cells there).
Single-feature AUC > 0.90 means leakage until proven otherwise.

Note: this canary cannot detect selection bias from choosing a feature after seeing
these AUCs. The report lists every band so that selection is visible.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    d = args.data_dir
    with rasterio.open(d / "sample_submission.tif") as t:
        F = np.isfinite(t.read(1))
    with rasterio.open(d / "existing_faults.tif") as t:
        C = t.read(1) == 1
    with rasterio.open(d / "external" / "derived_sgmc_faults_100m_u8.tif") as t:
        S = t.read(1) == 1
    with rasterio.open(d / "external" / "lidar_scarp_features_u8.tif") as t:
        names = list(t.descriptions)
        B = t.read().astype(np.float64)
    mask = F & (distance_transform_edt(~C) > 3.0)
    y = S[mask]
    report = {"truth": "USGS SGMC fault cells, off-catalogue (>3 px) inside template footprint",
              "n_cells": int(mask.sum()), "n_positive": int(y.sum()), "features": {}}
    for i, n in enumerate(names):
        x = B[i][mask]
        if np.std(x) == 0:
            report["features"][n] = {"auc": None, "note": "constant"}
            continue
        report["features"][n] = {"auc": float(roc_auc_score(y, x))}
    report["max_auc"] = max(v["auc"] for v in report["features"].values() if v["auc"] is not None)
    report["step_max_auc"] = report["features"]["step_max"]["auc"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
