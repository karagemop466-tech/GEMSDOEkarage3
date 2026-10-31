#!/usr/bin/env python3
"""H1-expanded (experiment 3 of 3): the same three-field co-location score at the full dot budget.

PRE-REGISTERED before the first run (2026-10-31 UTC). Do not edit to fit results.

* Purpose: H1 (scripts/build_colocation_candidate.py) was budget-limited (12,177 dots, after
  non-maximum suppression). Its holdout is confounded by dot count. This run tests whether the
  co-location score carries signal at the full 37,654-dot budget.
* Score S exactly as H1: min over bands 3, 18, 19 of the robust z-score of the 1-px smoothed field,
  clipped at 0, excluding USGS/INGENIOUS catalogue cells (labels.tif).
* Change from H1: NO non-maximum suppression. Budget = top 37,654 cells by S among cells with S > 0.
* Forbidden inputs: derived_sgmc_faults_100m_u8.tif, catalogue-derived bands.
* Promotion criteria (decided now, applied after evaluation; a candidate must clear ALL):
    1. format gate pass (check_format.py, NaN outside, values in [0,1]);
    2. HOLDOUT-DTI (pooled, hide-and-recover) above the nine-site maximum 0.0967;
    3. SGMC-calibrated HOLDOUT-DTI above the nine-site maximum 0.0644;
    4. nine-site overlap at or below 0.70 and |Spearman| at or below 0.90 for every focus raster;
    5. budget-matched random control (37,654 dots) is below the candidate on both metrics.
  Criterion 4 is not the full registry rule: the 13GEMSDOE lattice is reported separately and fails
  it for any footprint-spanning file (see evidence/uniqueness-colocation/).
Output: quarantine folder docs/quarantine/colocation-h1-expanded/ (never the download folder).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from submission_writer import write_validated_submission  # noqa: E402
from gems32.paths import data_dir  # noqa: E402

N_DOTS = 37654
BANDS = {"tmi_hg": 3, "iso_grav_anom_hg": 18, "det_elev_slope": 19}
NODATA_LIMIT = 1e37
OUT_DIR = ROOT / "docs" / "quarantine" / "colocation-h1-expanded"
SLUG = "colocation-h1-expanded"
NOTE = "H1 3-field co-location score at full 37654 budget, no NMS, no catalogue cells. Holdout pending."


def robust_z(x: np.ndarray, valid: np.ndarray) -> np.ndarray:
    med = np.median(x[valid])
    mad = np.median(np.abs(x[valid] - med)) * 1.4826
    if not np.isfinite(mad) or mad <= 0:
        raise ValueError("degenerate band: MAD is zero")
    return np.clip((x - med) / mad, 0.0, None)


def main() -> dict:
    ddir = data_dir()
    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(ddir / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot

    fields = {}
    valid = foot.copy()
    with rasterio.open(ddir / "training_features.tif") as ds:
        for name, idx in BANDS.items():
            assert ds.descriptions[idx - 1].startswith(name)
            raw = ds.read(idx).astype(np.float64)
            ok = np.isfinite(raw) & (np.abs(raw) < NODATA_LIMIT)
            valid &= ok
            fields[name] = raw
    z_stack = [robust_z(gaussian_filter(np.where(valid, raw, 0.0), sigma=1.0), valid) for raw in fields.values()]
    S = np.where(valid & ~labels, np.min(np.stack(z_stack), axis=0), 0.0)

    cand = np.flatnonzero(S.ravel() > 0)
    order = cand[np.argsort(S.ravel()[cand])[::-1]]
    n_use = min(N_DOTS, int(order.size))
    mask = np.zeros(foot.shape, dtype=np.float32)
    mask.ravel()[order[:n_use]] = 1.0

    meta = {
        "candidate_id": "colocation-h1-expanded",
        "hypothesis": "H1 three-field co-location score at full budget (no NMS)",
        "description": "Pre-registered in scripts/build_colocation_expanded_candidate.py; top 37654 cells with S>0; labels excluded.",
        "submission_note_zeros": NOTE,
        "submission_note_nan": NOTE,
        "slot_decision": "HOLD-DO-NOT-SUBMIT",
        "n_positive_S_cells": int(order.size),
        "n_dots": int(n_use),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = write_validated_submission(mask, slug=SLUG, candidate_meta=meta, ddir=ddir, out_dir=OUT_DIR,
                                        timestamp_tag="20261031T020000Z")
    (OUT_DIR / "bundle.json").write_text(json.dumps(bundle, indent=2, default=str) + "\n")
    print(json.dumps({k: v for k, v in bundle.items() if isinstance(v, (str, int, float))}, indent=2))
    return bundle


if __name__ == "__main__":
    main()
