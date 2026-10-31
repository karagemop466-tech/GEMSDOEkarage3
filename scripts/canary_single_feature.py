#!/usr/bin/env python3
"""Leakage canary (protocol item 4): AUC of each feature ALONE against off-catalogue SGMC positives.

Positives = derived SGMC faults (external/derived_sgmc_faults_100m_u8.tif) lying > 3 px from labels.tif,
inside the template footprint. Negatives = all other footprint cells not within 3 px of any catalogue trace.
A single-feature AUC above 0.90 is treated as leakage until proven otherwise.
"""
import json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / ".cache" / "gems_data"
SENT = -1e38

def main(features):
    with rasterio.open(D / "sample_submission.tif") as t:
        foot = np.isfinite(t.read(1)) & (t.read_masks(1) > 0)
    with rasterio.open(D / "labels.tif") as l:
        cat = l.read(1) > 0
    with rasterio.open(D / "external" / "derived_sgmc_faults_100m_u8.tif") as s:
        sg = s.read(1) > 0
    near = distance_transform_edt(~cat) <= 3
    pos = sg & foot & ~near
    neg = foot & ~near & ~sg
    out = {}
    with rasterio.open(D / "training_features.tif") as ds:
        names = [d.split(" - ")[0] for d in ds.descriptions]
        for f in features:
            a = ds.read(names.index(f) + 1).astype(np.float64)
            a[a < SENT] = np.nan
            ok = (pos | neg) & np.isfinite(a)
            auc = roc_auc_score(pos[ok].astype(int), a[ok])
            out[f] = {"auc": round(float(max(auc, 1 - auc)), 4), "auc_signed": round(float(auc), 4),
                      "n_pos": int(pos[ok].sum()), "n_neg": int((neg & ok).sum())}
    return out

if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1:] or ["iso_grav_anom_vg", "iso_grav_anom_hg", "tmi_vg", "tmi_hg", "iso_grav_anom", "det_elev"]), indent=2))
