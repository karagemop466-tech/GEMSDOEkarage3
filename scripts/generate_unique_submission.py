#!/usr/bin/env python3
"""
Generate a unique, competition-format GeoTIFF submission for the DOE GEMS competition.

Implements a geothermal prospectivity detector targeting off-catalogue faults
(missing from USGS/INGENIOUS catalogue) using a combination of:

  1. Seismicity (ieq_n100a15) — earthquake density, strongest fault proxy (diff=+181.6)
  2. Bouguer gravity anomaly (iso_grav_anom) — basin/fracture signature
  3. Elevation (det_elev) — geothermal systems concentrate in low basins
  4. Shear strain rate (geod_shearrate) — active deformation (diff=+2.8)

Visible catalogue faults are masked pixel-exactly (labels.tif). All pixels within
3 px of any existing focus-site submission dot or the karage3-unique-offcat dots
are excluded to guarantee literal uniqueness. The output is clamped to [0, 1],
zero outside the footprint, no NaN anywhere, EPSG:32611, 3730×3292, 100 m.

This is a static binary diagnostic (HOLDOUT-DTI only), NOT a leaderboard estimate.
No submission slot is authorized by running this script.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems32.paths import data_dir, work_dir  # noqa: E402
from gems32.submission import require_binary_mask, write_submission_pair  # noqa: E402

EXPECTED_HEIGHT = 3730
EXPECTED_WIDTH = 3292

# --- Novel hypothesis slate (ranked by expected DTI improvement / cost) ---
HYPOTHESES = [
    {
        "rank": 1,
        "name": "H1-seismic-gravity-basin-conduit",
        "layers": ["ieq_n100a15", "iso_grav_anom", "det_elev", "geod_shearrate"],
        "signature": "Seismicity + negative gravity + low elevation + shear: blind fault conduits "
                     "beneath young cover, no mapped surface trace.",
        "off_catalogue_rationale": "Seismicity reveals active slip on unmapped faults; gravity lows "
                                   "marks fractured basins; these detect structures absent from USGS/INGENIOUS traces.",
        "non_fault_mimic": "Unfaulted sedimentary basins, volcanic calderas, groundwater drawdown.",
        "cost": "Low — uses existing 19-band feature stack, no external data.",
        "expected_dti": "Moderate improvement over off-catalogue-only detectors.",
    },
    {
        "rank": 2,
        "name": "H2-dilation-shear-stepover",
        "layers": ["geod_dilaterate", "geod_shearrate", "det_elev_slope"],
        "signature": "Co-located high dilation and shear at step-overs / relay ramps between mapped faults.",
        "off_catalogue_rationale": "Step-over zones create permeability without being individually catalogued as faults.",
        "non_fault_mimic": "Landslide scarps, glacial features, road cuts.",
        "cost": "Low — uses existing bands.",
        "expected_dti": "Low-moderate; step-overs are sparse so budget-limited.",
    },
    {
        "rank": 3,
        "name": "H3-radiometric-alteration-halo",
        "layers": ["geodawn_rad_u8 (K/eTh/eU)", "det_elev_slope"],
        "signature": "Potassium enrichment + thorium depletion in alteration halos around concealed faults.",
        "off_catalogue_rationale": "Hydrothermal alteration halos extend beyond mapped fault traces.",
        "non_fault_mimic": "Lithologic contacts, soil moisture, surficial deposits.",
        "cost": "Moderate — requires external radiometric grid resampling.",
        "expected_dti": "Moderate; alteration is a direct geothermal indicator.",
    },
    {
        "rank": 4,
        "name": "H4-block-invariant-magnetic-lineament",
        "layers": ["rtp", "acquisition_block_id_100m"],
        "signature": "Magnetic lineaments that persist across GeoDAWN acquisition block boundaries (not processing seams).",
        "off_catalogue_rationale": "Block-invariant lineaments are real structures; processing seams stop at block edges.",
        "non_fault_mimic": "Survey-line artifacts, lithologic contacts.",
        "cost": "Moderate — requires acquisition block grid + edge persistence analysis.",
        "expected_dti": "Low-moderate.",
    },
    {
        "rank": 5,
        "name": "H5-young-volcanic-vent-intersection",
        "layers": ["geodawn_extensions_u8", "tmi_vg", "det_elev"],
        "signature": "Young volcanic vents (cones/domes) intersected by fault traces.",
        "off_catalogue_rationale": "Quaternary volcanic vents may be absent from the USGS fault catalogue.",
        "non_fault_mimic": "Erosional remnants, non-volcanic cones.",
        "cost": "High — requires volcanic feature extraction not currently implemented.",
        "expected_dti": "Uncertain; volcanic vents are rare in the footprint.",
    },
]

TOP = HYPOTHESES[0]  # Assigned lane: H1


def normalize(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Min-max normalize finite in-footprint values to [0, 1]; NaN outside stays NaN."""
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    valid = foot & np.isfinite(arr)
    if not valid.any():
        return out
    v = arr[valid]
    lo, hi = float(np.percentile(v, 2)), float(np.percentile(v, 98))
    if hi <= lo:
        hi = lo + 1.0
    out[valid] = np.clip((arr[valid] - lo) / (hi - lo), 0.0, 1.0)
    return out


def load_band(bname: str, bands_dir: Path, foot: np.ndarray) -> np.ndarray:
    path = bands_dir / f"{int(bname.split('_')[0]):02d}_{bname}.npy" if bname[0].isdigit() else bands_dir / bname
    if not path.exists():
        # Try by name
        for p in bands_dir.glob(f"*_{bname}.npy"):
            path = p
            break
    arr = np.load(path)
    arr = arr.astype(np.float32)
    arr[~foot] = np.nan
    arr[~np.isfinite(arr)] = np.nan
    return arr


def main() -> int:
    ddir = data_dir()
    wdir = work_dir()
    bands_dir = wdir / "bands"
    foot = np.load(bands_dir / "_footprint.npy")
    labels = np.load(bands_dir / "_labels.npy")
    print(f"[grid] {EXPECTED_HEIGHT}x{EXPECTED_WIDTH} footprint={int(foot.sum()):,} labels={int(labels.sum()):,}")

    # ---- Load feature bands for H1 (seismic-gravity-basin-conduit) ----
    bands = {}
    for bname in ["ieq_n100a15", "iso_grav_anom", "det_elev", "geod_shearrate", "cond_surf"]:
        bands[bname] = load_band(bname, bands_dir, foot)

    # ---- Prospectivity score (H1 mechanism) ----
    # Seismicity (positive), gravity anomaly magnitude (negative anomaly = basin), 
    # low elevation (basin), shear rate (deformation)
    seis = normalize(bands["ieq_n100a15"], foot)
    grav = normalize(bands["iso_grav_anom"], foot)
    elev = normalize(bands["det_elev"], foot)
    shear = normalize(bands["geod_shearrate"], foot)
    cond = normalize(bands["cond_surf"], foot)

    # Composite: seismicity-weighted, gravity-low + elevation-low + shear-high
    # Invert gravity and elevation so low values = high prospectivity
    grav_inv = 1.0 - grav
    elev_inv = 1.0 - elev
    score = (0.40 * seis + 0.25 * grav_inv + 0.20 * elev_inv + 0.15 * shear)
    score[~foot] = np.nan

    # ---- Mask: visible catalogue faults pixel-exactly ----
    visible = labels > 0
    visible_buf = distance_transform_edt(~visible) <= 1.0  # 1 px buffer (~100 m)
    eligible = foot & ~visible & ~visible_buf

    # ---- Uniqueness: exclude within 3 px of every existing submission dot ----
    # 1) karage3-unique-offcat existing dots
    existing_paths = [
        ROOT / "docs/downloads/karage3-unique-offcat-20261029T180337Z-6a8c2368-zeros.tif",
    ]
    # 2) Focus-site historical submissions from scored cache
    scored_dir = ddir / "scored"
    if scored_dir.exists():
        existing_paths.extend(sorted(scored_dir.glob("*.tif")))

    exclusion = np.zeros(foot.shape, dtype=bool)
    for p in existing_paths:
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
            dots = (a > 0.5) & np.isfinite(a)
            if dots.shape == foot.shape:
                # 3-px dilation of existing dots
                dt = distance_transform_edt(~dots)
                exclusion |= (dt <= 3.0)
                print(f"[uniqueness] {p.name}: {int(dots.sum())} dots, {int(exclusion.sum())} px excluded so far")

    eligible = eligible & ~exclusion
    print(f"[uniqueness] eligible off-catalogue pixels: {int(eligible.sum()):,}")

    # ---- Select top N pixels ----
    N = 12000
    cand = score[eligible]
    if cand.size < N:
        print(f"[WARN] only {cand.size} eligible pixels, using all")
        N = cand.size
    thr = np.nanpercentile(score[eligible], 100 * (1 - N / max(eligible.sum(), 1)))
    mask = eligible & (score >= thr)
    # Cap at exactly N
    n_pos = int(mask.sum())
    if n_pos > N:
        idx = np.random.default_rng(20261029).choice(np.flatnonzero(mask), size=N, replace=False)
        mask2 = np.zeros_like(mask)
        mask2.flat[idx] = True
        mask = mask2
    print(f"[emit] selected {int(mask.sum()):,} dots (target {N})")

    # ---- Write validated submission pair ----
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = "karage3-h1-seismic-gravity-basin"
    note = (
        "Unique off-catalogue geothermal detector: seismic+gravity+elevation+shear prospectivity, "
        "12k dots >3px from all prior focus-site submissions, targets faults missing from USGS/INGENIOUS"
    )
    if len(note) > 140:
        note = note[:137] + "..."

    meta = {
        "candidate_id": f"{slug}-{ts}",
        "description": "H1 seismic-gravity-basin-conduit off-catalogue detector; static binary diagnostic",
        "submission_note_zeros": note,
        "submission_note_nan": note,
        "catalogue_hidden_mean": None,
        "catalogue_hidden_per_quadrant": {},
        "sgmc_prevalence_calibrated_dti": None,
        "drift_corrected_holdout_mean": None,
        "drift_corrected_per_quadrant": {},
        "predicted_leaderboard_dti": None,
        "ei_drift_corrected": None,
        "slot_decision": "HOLD-DO-NOT-SUBMIT",
    }

    bundle = write_submission_pair(
        mask=mask,
        foot=foot,
        labels=labels,
        template_tif=ddir / "sample_submission.tif",
        out_dir=ROOT / "docs/downloads",
        slug=slug,
        timestamp_tag=ts,
        candidate_meta=meta,
    )

    # ---- Save hypothesis + run metadata ----
    run_meta = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypothesis": TOP,
        "mechanism": "Seismicity reveals active slip on unmapped faults; gravity lows mark fractured basins; "
                     "low elevation and shear strain localize blind geothermal conduits off the catalogue.",
        "named_non_fault_mimic": "Unfaulted sedimentary basins, volcanic calderas, groundwater drawdown, lithologic contacts.",
        "score_label": "HOLDOUT-DTI (static diagnostic; not a leaderboard estimate)",
        "emitted_pixels": int(mask.sum()),
        "bundle": bundle,
        "uniqueness_checked_vs": [str(p) for p in existing_paths if p.exists()],
    }
    run_path = ROOT / "evidence" / f"unique-submission-h1-{ts}.json"
    run_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.write_text(json.dumps(run_meta, indent=2, default=str))
    print(f"[run] metadata written to {run_path}")
    print(f"[done] zeros.tif: {bundle['zeros_tif']['filename']}")
    print(f"[done] sha256: {bundle['zeros_tif']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
