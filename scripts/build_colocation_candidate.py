#!/usr/bin/env python3
"""H1 candidate: three-field co-located gradient ridges (magnetic + gravity + topographic slope).

PRE-REGISTERED (written before the first run, 2026-10-31 UTC; do not edit to fit results):

* Hypothesis: a buried or non-catalogue fault should produce a horizontal-gradient maximum in
  more than one independent geophysical field at the same place. Requiring agreement in
  tmi_hg (band 3), iso_grav_anom_hg (band 18) and det_elev_slope (band 19) should suppress
  single-field artefacts.
* Score field: S = min over the three bands of the robust z-score (median / 1.4826*MAD inside the
  footprint, clipped at 0) of each band after a 1-pixel Gaussian smooth.
* Ridge: keep a pixel only if S equals the 3x3 local maximum of S (non-maximum suppression).
* Budget: the top N = 37,654 ridge pixels by S (amended, see A1). N is matched to the GEMSDOE32 0.2778 file so the
  comparison is dot-budget matched. No dot is placed on a USGS/INGENIOUS catalogue cell
  (labels.tif), the same convention as the shared writer.
* Forbidden inputs: derived_sgmc_faults_100m_u8.tif and any catalogue-derived band. SGMC is the
  off-catalogue evaluation target, so using it as an input would make that metric circular.
* Named non-fault mimics: lithologic contacts that show up in magnetic and gravity fields at once,
  alluvial-fan and erosional slope breaks, and road embankments (external/tiger_road_distance_m.tif
  is NOT used here; it is only a mimic to check against later).

AMENDMENT A1 (2026-10-31, made after the first run failed and BEFORE any holdout or SGMC
evaluation of this candidate): the first run found only 12,177 NMS ridge pixels with S > 0, below
the 37,654 budget. The ridge rule was NOT loosened. The budget is reduced to all available ridge
pixels, and this reduction is reported as a deviation (dot budget no longer matched to the 0.2778
file). The original budget rule is kept in the record as the failed first attempt.

Output: a binary candidate written through the shared writer scripts/submission_writer.py into
docs/quarantine/colocation-h1/ (NOT the download folder). Clearance is decided separately.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, maximum_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from submission_writer import write_validated_submission  # noqa: E402
from gems32.paths import data_dir  # noqa: E402

N_DOTS = 37654
BANDS = {"tmi_hg": 3, "iso_grav_anom_hg": 18, "det_elev_slope": 19}
NODATA_LIMIT = 1e37
OUT_DIR = ROOT / "docs" / "quarantine" / "colocation-h1"
SLUG = "colocation-h1"
NOTE_NAN = "H1 3-field co-located gradient ridges, no catalogue cells, A1 budget. Holdout pending."


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
        assert ds.count == 19 and ds.shape == foot.shape
        for name, idx in BANDS.items():
            desc = ds.descriptions[idx - 1]
            assert desc.startswith(name), (name, desc)  # band identity check
            raw = ds.read(idx).astype(np.float64)
            ok = np.isfinite(raw) & (np.abs(raw) < NODATA_LIMIT)
            valid &= ok
            fields[name] = (raw, ok, desc)

    z_stack = []
    for name, (raw, ok, _desc) in fields.items():
        sm = gaussian_filter(np.where(valid, raw, 0.0), sigma=1.0)
        z_stack.append(robust_z(sm, valid))
    S = np.min(np.stack(z_stack), axis=0)
    S = np.where(valid & ~labels, S, 0.0)

    ridge = (S > 0) & (S >= maximum_filter(S, size=3))
    cand_idx = np.flatnonzero(ridge)
    order = cand_idx[np.argsort(S.ravel()[cand_idx])[::-1]]
    n_use = min(N_DOTS, int(order.size))  # amendment A1: budget = min(37654, available)
    if n_use < 1000:
        raise RuntimeError(f"too few ridge pixels ({order.size}) for a meaningful candidate")
    mask = np.zeros(foot.shape, dtype=np.float32)
    mask.ravel()[order[:n_use]] = 1.0

    meta = {
        "candidate_id": "colocation-h1",
        "hypothesis": "H1 three-field co-located horizontal-gradient ridges (tmi_hg, iso_grav_anom_hg, det_elev_slope)",
        "description": "Pre-registered in scripts/build_colocation_candidate.py; min robust-z over three bands; NMS 3x3; top 37654 ridge pixels; labels excluded.",
        "submission_note_zeros": NOTE_NAN,
        "submission_note_nan": NOTE_NAN,
        "slot_decision": "HOLD-DO-NOT-SUBMIT",
        "bands_used": {k: {"band": v, "desc": fields[k][2]} for k, v in BANDS.items()},
        "n_ridge_candidates": int(order.size),
        "n_dots": int(n_use),
        "budget_target": int(N_DOTS),
        "deviation": "AMENDMENT A1: budget reduced to available ridge pixels (first run had 12177 < 37654)" if n_use < N_DOTS else None,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = write_validated_submission(mask, slug=SLUG, candidate_meta=meta, ddir=ddir, out_dir=OUT_DIR,
                                        timestamp_tag="20261031T000000Z")
    (OUT_DIR / "bundle.json").write_text(json.dumps(bundle, indent=2, default=str) + "\n")
    print(json.dumps(bundle, indent=2, default=str))
    return bundle


if __name__ == "__main__":
    main()
