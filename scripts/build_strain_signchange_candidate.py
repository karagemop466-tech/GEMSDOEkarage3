#!/usr/bin/env python3
"""H2 candidate: dilatation sign-change lineaments weighted by shear rate (geodetic strain).

PRE-REGISTERED before the first run (2026-10-31 UTC). Do not edit to fit results.

* Hypothesis: a strike-slip or oblique fault that is active or recently active splits the
  dilatation field into a positive and a negative lobe. The zero-crossing line of the dilatation
  (geod_dilaterate, band 8) therefore marks the fault. Requiring high shear rate (geod_shearrate,
  band 7) at the crossing separates fault-like crossings from crossings in flat deformation fields.
* Crossing: a pixel is a crossing if the sign of the 1-px Gaussian-smoothed dilatation differs
  from the sign of a 4-neighbour (east or south). Crossing magnitude = max(|d|) of the pair.
* Score S = crossing indicator * robust-z(smoothed shear rate, clipped at 0).
* Budget: top min(37654, available) pixels by S, excluding USGS/INGENIOUS catalogue cells
  (labels.tif). No SGMC input. Named non-fault mimic: subsidence or groundwater-withdrawal
  deformation bowls and their edges, which also give dilatation sign changes.
* Forbidden inputs: derived_sgmc_faults_100m_u8.tif and catalogue-derived bands (SGMC is the
  off-catalogue evaluation target).

Output: binary candidate via the shared writer into docs/quarantine/strain-signchange-h2/.
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
SHEAR_BAND, DIL_BAND = 7, 8
NODATA_LIMIT = 1e37
OUT_DIR = ROOT / "docs" / "quarantine" / "strain-signchange-h2"
SLUG = "strain-signchange-h2"
NOTE = "H2 dilatation sign-change lineaments x shear rate, no catalogue cells, pre-registered. Holdout pending."


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

    with rasterio.open(ddir / "training_features.tif") as ds:
        assert ds.descriptions[SHEAR_BAND - 1].startswith("geod_shearrate")
        assert ds.descriptions[DIL_BAND - 1].startswith("geod_dilaterate")
        shear = ds.read(SHEAR_BAND).astype(np.float64)
        dil = ds.read(DIL_BAND).astype(np.float64)
    valid = foot & np.isfinite(shear) & np.isfinite(dil) & (np.abs(shear) < NODATA_LIMIT) & (np.abs(dil) < NODATA_LIMIT)

    fill_s = float(np.median(shear[valid]))
    fill_d = float(np.median(dil[valid]))
    sm_s = gaussian_filter(np.where(valid, shear, fill_s), sigma=1.0)
    sm_d = gaussian_filter(np.where(valid, dil, fill_d), sigma=1.0)
    # Demean the dilatation so its zero-crossing is a sign change of the anomaly, not the field.
    sm_d = sm_d - np.median(sm_d[valid])

    cross = np.zeros(foot.shape, dtype=bool)
    mag = np.zeros(foot.shape, dtype=np.float64)
    # East neighbour
    s_e = np.sign(sm_d[:, :-1]) != np.sign(sm_d[:, 1:])
    m_e = np.maximum(np.abs(sm_d[:, :-1]), np.abs(sm_d[:, 1:]))
    cross[:, :-1] |= s_e
    mag[:, :-1] = np.maximum(mag[:, :-1], np.where(s_e, m_e, 0.0))
    # South neighbour
    s_s = np.sign(sm_d[:-1, :]) != np.sign(sm_d[1:, :])
    m_s = np.maximum(np.abs(sm_d[:-1, :]), np.abs(sm_d[1:, :]))
    cross[:-1, :] |= s_s
    mag[:-1, :] = np.maximum(mag[:-1, :], np.where(s_s, m_s, 0.0))

    z_shear = robust_z(sm_s, valid)
    S = np.where(cross & valid & ~labels, z_shear * (1.0 + mag / (np.nanmax(mag) + 1e-12)), 0.0)

    cand = np.flatnonzero(S > 0)
    order = cand[np.argsort(S.ravel()[cand])[::-1]]
    n_use = min(N_DOTS, int(order.size))
    if n_use < 1000:
        raise RuntimeError(f"too few crossing pixels ({order.size}) for a meaningful candidate")
    mask = np.zeros(foot.shape, dtype=np.float32)
    mask.ravel()[order[:n_use]] = 1.0

    meta = {
        "candidate_id": "strain-signchange-h2",
        "hypothesis": "H2 dilatation sign-change lineaments weighted by shear rate (geod_dilaterate x geod_shearrate)",
        "description": "Pre-registered in scripts/build_strain_signchange_candidate.py; top min(37654, available) by score; labels excluded.",
        "submission_note_zeros": NOTE,
        "submission_note_nan": NOTE,
        "slot_decision": "HOLD-DO-NOT-SUBMIT",
        "n_crossing_candidates": int(order.size),
        "n_dots": int(n_use),
        "budget_target": int(N_DOTS),
        "deviation": "budget reduced to available crossings" if n_use < N_DOTS else None,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = write_validated_submission(mask, slug=SLUG, candidate_meta=meta, ddir=ddir, out_dir=OUT_DIR,
                                        timestamp_tag="20261031T010000Z")
    (OUT_DIR / "bundle.json").write_text(json.dumps(bundle, indent=2, default=str) + "\n")
    print(json.dumps(bundle, indent=2, default=str))
    return bundle


if __name__ == "__main__":
    main()
