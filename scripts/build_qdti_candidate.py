#!/usr/bin/env python3
"""Build the H-QDTI research raster from ALL catalogue labels (same method as scripts/qdti_holdout.py).

Method (identical to the holdout experiment, but fitted on the full visible catalogue):
  * features: official training_features.tif (19 bands) + 4-px Gaussian context (label-free);
  * emission: logistic regression, positives = footprint pixels within 3 px of a catalogue fault,
    negatives = footprint pixels farther than 3 px from a catalogue fault;
  * selection: top pre-registered fraction (default 0.10) of the footprint EXCLUDING catalogue
    pixels (known faults are masked by the organizer rule, so they are never emitted);
  * output: single-band float32 GeoTIFF on the official sample grid (EPSG:32611, 100 m, 3292x3730),
    values exactly 0 or 1 inside the footprint, NaN outside (organizer rule: "null or nan").

This file is a RESEARCH ARTIFACT. Its holdout estimate comes from the per-cell out-of-fold run
(evidence/qdti-holdout-20261030.json), not from this file, which was fitted on all labels.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from qdti_holdout import NEAR_PX, fit_predict, load_features  # noqa: E402  (same method, not forked)

DDIR = ROOT / ".cache" / "gems_data"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.10)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--meta", type=Path, required=True)
    args = ap.parse_args()

    with rasterio.open(DDIR / "sample_submission.tif") as tpl:
        foot = np.isfinite(tpl.read(1))
        profile = tpl.profile.copy()
    with rasterio.open(DDIR / "labels.tif") as lab:
        labels = (lab.read(1) == 1) & foot
    names, feats, foot2 = load_features(DDIR)
    assert np.array_equal(foot, foot2)

    dist = distance_transform_edt(~labels)
    pos = foot & (dist <= NEAR_PX)
    neg = foot & (dist > NEAR_PX)
    q = fit_predict(feats, foot, pos, neg, seed=4242)

    active = foot & ~labels
    vals = q[active]
    k = max(1, int(round(args.frac * vals.size)))
    thr = np.partition(vals, vals.size - k)[vals.size - k]
    emit = (q >= thr) & active
    out = np.full(foot.shape, np.nan, dtype=np.float32)
    out[foot] = 0.0
    out[emit] = 1.0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    profile.update(dtype="float32", count=1, nodata=np.nan, compress="lzw", driver="GTiff")
    with rasterio.open(args.out, "w", **profile) as dst:
        dst.write(out, 1)
        dst.set_band_description(1, "H-QDTI top-%.0f%% emission (1=emit, NaN outside footprint)" % (args.frac * 100))

    sha = hashlib.sha256(args.out.read_bytes()).hexdigest()
    meta = {
        "file": args.out.name,
        "sha256": sha,
        "bytes": args.out.stat().st_size,
        "method": "H-QDTI logistic emission on label-free bands; top-fraction binary; catalogue pixels excluded",
        "frac_of_active_domain": args.frac,
        "emitted_cells": int(emit.sum()),
        "catalogue_cells_emitted": int((emit & labels).sum()),
        "footprint_cells": int(foot.sum()),
        "features": names,
        "threshold_q": float(thr),
    }
    args.meta.parent.mkdir(parents=True, exist_ok=True)
    args.meta.write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
