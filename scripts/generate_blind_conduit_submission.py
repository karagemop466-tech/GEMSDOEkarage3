#!/usr/bin/env python3
"""
Generate a UNIQUE, competition-format GeoTIFF submission for the DOE GEMS
competition, targeting faults MISSING from the USGS/INGENIOUS catalogue.

Novel hypothesis (this repo's assigned lane, rank #1 of the H-slate):
  H-blind-stepover-conduit — blind stepover / relay-ramp conduit detector.
  Layers: catalogue fault traces (labels.tif) only, converted into derivative
  structural transforms (trace endpoints, stepover/relay proximity, distance
  off mapped trace).
  Signature: clusters of fault-trace endpoints (stepover/relay zones) at
  200-600 m off the mapped trace — where blind, unmapped fault strands most
  plausibly connect mapped segments and host geothermal conduits.
  Off-catalogue rationale: dots are placed strictly OFF catalogue traces,
  in the blind-strand corridor between/beside mapped segments; catalogue
  faults are masked pixel-exactly, so no dot can credit a known fault.
  Named non-fault mimic: erosion gullies, alluvial-fan distributaries and
  linear cultural features (roads) that also end near mapped traces.
  Difference vs existing work: every focus-site file (GEMSDOE24/25/27/28/30/
  31/32/33/36) places dots ON or within 2 px of catalogue traces (the shared
  dotted-ridge family); this detector deliberately avoids them and is forced
  to be >3 px from every focus-site dot, so it is a unique emission.

Output: -nan.tif (NaN outside footprint; official "null or nan outside
bounds" convention) and -zeros.tif (every cell finite in [0,1]; immune to a
strict whole-array range check), a .zip, and a 12-point audit sidecar. Both
variants are single-band float32, EPSG:32611, 3730x3292, 100 m, matching
docs/downloads/sample_submission.tif exactly.

This is a HOLDOUT-DTI diagnostic only. No leaderboard estimate is claimed
(the local catalogue holdout does not track organizer scores), and no
submission slot is authorized by running this script.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from karage3 import holdout  # noqa: E402
from karage3.submission import audit_geotiff, write_submission_pair  # noqa: E402

DOWNLOADS = ROOT / "docs" / "downloads"
TEMPLATE = DOWNLOADS / "sample_submission.tif"
LABELS = DOWNLOADS / "labels.tif"
DDIR = Path("/tmp/gems_data")  # offline data dir (organizer SGMC grid unavailable)

# ---- Hypothesis slate (ranked by expected DTI improvement / implementation cost) ----
HYPOTHESES = [
    {
        "rank": 1,
        "name": "H-blind-stepover-conduit",
        "layers": ["labels.tif (catalogue traces -> endpoint/junction structure, distance off trace)"],
        "signature": "Clusters of fault-trace endpoints (stepover/relay zones) 200-600 m off the mapped "
                     "trace; blind, unmapped strands connecting mapped segments.",
        "off_catalogue_rationale": "Dots are strictly off catalogue traces in the blind-strand corridor; "
                                   "no credit can flow to known USGS/INGENIOUS faults.",
        "non_fault_mimic": "Erosion gullies, alluvial-fan distributaries, road/linear cultural lineaments.",
        "cost": "Low — uses only the local catalogue grid; no external data.",
        "expected_dti": "Low-moderate; sparse structural targets, no geothermal band available offline.",
        "selected": True,
    },
    {
        "rank": 2,
        "name": "H-seismic-gravity-basin-conduit",
        "layers": ["ieq_n100a15", "iso_grav_anom", "det_elev", "geod_shearrate"],
        "signature": "Seismicity + negative gravity + low elevation + shear: blind conduits beneath cover.",
        "off_catalogue_rationale": "Seismicity reveals slip on unmapped faults; gravity lows mark fractured basins.",
        "non_fault_mimic": "Unfaulted sedimentary basins, volcanic calderas, groundwater drawdown.",
        "cost": "Low — but needs the 19-band training stack (not available offline; DrivenData login required).",
        "expected_dti": "Moderate; direct geothermal proxy, but not runnable in this offline session.",
        "selected": False,
    },
    {
        "rank": 3,
        "name": "H-radiometric-alteration-halo",
        "layers": ["geodawn_rad_u8 (K/eTh/eU)", "det_elev_slope"],
        "signature": "Potassium enrichment / thorium depletion in alteration halos around concealed faults.",
        "off_catalogue_rationale": "Hydrothermal alteration halos extend beyond mapped fault traces.",
        "non_fault_mimic": "Lithologic contacts, soil moisture, surficial deposits.",
        "cost": "Moderate — needs external radiometric grid resampled to the template.",
        "expected_dti": "Moderate; alteration is a direct geothermal indicator.",
        "selected": False,
    },
    {
        "rank": 4,
        "name": "H-block-invariant-magnetic-lineament",
        "layers": ["rtp", "acquisition_block_id_100m"],
        "signature": "Magnetic lineaments persisting across GeoDAWN acquisition-block boundaries (not seams).",
        "off_catalogue_rationale": "Real structures persist across blocks; processing seams stop at block edges.",
        "non_fault_mimic": "Survey-line artifacts, lithologic contacts.",
        "cost": "Moderate — needs acquisition-block grid + persistence analysis.",
        "expected_dti": "Low-moderate.",
        "selected": False,
    },
    {
        "rank": 5,
        "name": "H-young-volcanic-vent-intersection",
        "layers": ["geodawn_extensions_u8", "tmi_vg", "det_elev"],
        "signature": "Quaternary volcanic vents (cones/domes) intersected by fault traces.",
        "off_catalogue_rationale": "Young vents may be absent from the USGS fault catalogue.",
        "non_fault_mimic": "Erosional remnants, non-volcanic cones.",
        "cost": "High — volcanic feature extraction not implemented.",
        "expected_dti": "Uncertain; vents are rare in the footprint.",
        "selected": False,
    },
]
TOP = HYPOTHESES[0]

DISK7 = np.array(
    [[0, 0, 0, 1, 0, 0, 0],
     [0, 0, 1, 1, 1, 0, 0],
     [0, 1, 1, 1, 1, 1, 0],
     [1, 1, 1, 1, 1, 1, 1],
     [0, 1, 1, 1, 1, 1, 0],
     [0, 0, 1, 1, 1, 0, 0],
     [0, 0, 0, 1, 0, 0, 0]], dtype=bool)
DISK3 = np.array(
    [[0, 0, 1, 1, 1, 0, 0],
     [0, 1, 1, 1, 1, 1, 0],
     [1, 1, 1, 1, 1, 1, 1],
     [1, 1, 1, 1, 1, 1, 1],
     [1, 1, 1, 1, 1, 1, 1],
     [0, 1, 1, 1, 1, 1, 0],
     [0, 0, 1, 1, 1, 0, 0]], dtype=bool)


yy, xx = np.ogrid[-3:4, -3:4]
DISK3_TRUE = ((yy * yy + xx * xx) <= 9)


def within3_frac(dots_a, dots_b):
    """Fraction of dots_a within 3 px (Euclidean) of dots_b — matches the registry audit's disk3."""
    dil = binary_dilation(dots_b, structure=DISK3_TRUE)
    return float(dil[dots_a].mean()) if dots_a.any() else 0.0


def nonmax_suppress(score, eligible, min_sep_px, cap):
    """Greedy score-ordered non-maximum suppression with a minimum separation.

    Uses a KD-tree over already-chosen dots so each candidate check is O(log n)
    instead of recomputing a full-grid distance transform per pick.
    """
    order = np.flatnonzero(eligible & np.isfinite(score))
    order = order[np.argsort(-score.ravel()[order], kind="stable")]
    chosen_xy = []
    chosen = np.zeros(score.shape, dtype=bool)
    tree = None
    for idx in order:
        y, x = int(idx // score.shape[1]), int(idx % score.shape[1])
        if tree is not None:
            dist, _ = tree.query(np.array([y, x]), k=1)
            if dist < min_sep_px:
                continue
        chosen[y, x] = True
        chosen_xy.append((y, x))
        tree = cKDTree(np.array(chosen_xy, dtype=float))
        if len(chosen_xy) >= cap:
            break
    return chosen


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with rasterio.open(TEMPLATE) as tpl:
        foot = np.isfinite(tpl.read(1)) & (tpl.read_masks(1) > 0)
        profile_base = tpl.profile.copy()
    with rasterio.open(LABELS) as ds:
        labels = (ds.read(1) > 0) & foot
    ctx = holdout.load_holdout_context(DDIR)

    print(f"[grid] footprint={int(foot.sum()):,} catalogue={int(labels.sum()):,}")

    # ---- Structural transforms of the catalogue (derivative layers only) ----
    # neighbour count (8-connectivity) for each catalogue pixel
    kernel_sum = np.ones((3, 3), dtype=np.float64)
    from scipy.signal import convolve2d
    nb = convolve2d(labels.astype(np.float64), kernel_sum, mode="same", boundary="fill", fillvalue=0.0)
    nb = np.where(labels, nb - 1.0, 0.0)  # exclude self
    endpoints = labels & (nb == 1.0)
    junctions = labels & (nb >= 3.0)
    print(f"[structure] endpoints={int(endpoints.sum()):,} junctions={int(junctions.sum()):,}")

    # Stepover/relay proxy: endpoint density in a 7 px window (ends that face each other).
    ep_dense = binary_dilation(endpoints, structure=DISK7).astype(np.float64)
    j_dense = binary_dilation(junctions, structure=DISK3).astype(np.float64)

    dt = distance_transform_edt(~labels)  # distance to nearest catalogue trace (px)
    corridor = foot & ~labels & (dt >= 2.0) & (dt <= 6.0)  # 200-600 m off mapped trace
    print(f"[corridor] off-catalogue blind-strand pixels 2-6px off trace: {int(corridor.sum()):,}")

    surface = np.zeros(foot.shape, dtype=np.float64)
    surface[corridor] = ep_dense[corridor] + 0.5 * j_dense[corridor]
    # distance weighting: strongest near the 2-4 px blind-strand band
    dist_w = np.clip(1.0 - (dt - 2.0) / 4.0, 0.0, 1.0)
    surface = surface * dist_w
    surface[~foot] = 0.0
    surface[labels] = 0.0  # pixel-exact catalogue mask
    finite_s = surface[foot & (surface > 0)]
    print(f"[surface] positive pixels={int(finite_s.size):,} max={float(surface.max()):.4f}")

    # Normalize to [0,1] (percentile clip to resist outliers).
    lo, hi = np.percentile(finite_s, 5), np.percentile(finite_s, 99.5)
    if hi <= lo:
        hi = lo + 1.0
    surf_n = np.clip((surface - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)
    surf_n[~foot] = np.nan

    # ---- Dot placement with uniqueness vs all nine focus sites ----
    focus_paths = [
        "GEMSDOE24-gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
        "GEMSDOE25-gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
        "GEMSDOE27-gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif",
        "GEMSDOE28-gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif",
        "GEMSDOE30-gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif",
        "GEMSDOE31-gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif",
        "GEMSDOE32-gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
        "GEMSDOE33-GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
        "GEMSDOE36-gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
    ]
    exclusion = np.zeros(foot.shape, dtype=bool)
    for name in focus_paths:
        p = DOWNLOADS / name
        with rasterio.open(p) as ds:
            a = ds.read(1)
        focus_dots = (a > 0.5) & np.isfinite(a) & foot
        dt_focus = distance_transform_edt(~focus_dots)
        exclusion |= (dt_focus <= 3.0)
        print(f"[uniqueness] {name}: {int(focus_dots.sum())} dots")
    print(f"[uniqueness] pixels within 3 px of any focus dot: {int(exclusion.sum()):,}")

    eligible = corridor & ~exclusion & foot & ~labels
    print(f"[emit] eligible pixels after catalogue + focus exclusion: {int(eligible.sum()):,}")

    cap = 10000
    dots = nonmax_suppress(surf_n, eligible, min_sep_px=4, cap=cap)
    # Final uniqueness audit vs focus sites.
    ov = {name: within3_frac(dots, (rasterio.open(DOWNLOADS / name).read(1) > 0.5) & np.isfinite(
        rasterio.open(DOWNLOADS / name).read(1)) & foot) for name in focus_paths}
    print(f"[emit] selected {int(dots.sum())} dots; max within-3px vs any focus site = {max(ov.values()):.6f}")
    assert max(ov.values()) <= 0.70, "uniqueness vs focus sites failed"

    # ---- Write validated submission pair ----
    slug = "h-blindstepover-conduit"
    note = ("Unique blind stepover/relay conduit detector: endpoints 200-600m off catalogue traces, "
            "10k dots, >3px from all nine focus-site dots")
    if len(note) > 140:
        note = note[:137] + "..."
    meta = {
        "candidate_id": f"karage3-{slug}-{ts}",
        "description": "H-blind-stepover-conduit off-catalogue blind-fault detector (novel, not a copy of any focus-site file)",
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
        mask=dots,
        foot=foot,
        labels=labels,
        template_tif=TEMPLATE,
        out_dir=DOWNLOADS,
        slug=slug,
        timestamp_tag=ts,
        candidate_meta=meta,
    )

    # ---- Holdout diagnostic (catalogue hide-and-recover) ----
    mask_bool = dots & foot
    hr = holdout.evaluate_hide_and_recover(mask_bool, ctx, name=f"karage3-{slug}-{ts}")
    try:
        sg = holdout.evaluate_sgmc_with_ci(mask_bool, ctx, name=f"karage3-{slug}-{ts}")
    except Exception as exc:  # placeholder SGMC grid offline
        sg = {"error": str(exc), "note": "organizer SGMC grid unavailable offline; all-zeros placeholder -> 0"}

    # ---- Surface saved for audit ----
    surf_npy = DOWNLOADS / f"karage3-{slug}-{ts}-surface.npy"
    np.save(surf_npy, np.where(foot, surf_n, np.nan).astype(np.float32))

    run_card = {
        "schema": "GEMSDOEkarage3-RUN-CARD-v1",
        "generated_utc": ts,
        "hypothesis": TOP,
        "mechanism": ("Endpoint/stepover density in the 200-600 m off-trace corridor. Blind geothermal conduits "
                      "most plausibly connect mapped fault strands at stepovers and relays, which leave no mapped "
                      "surface trace; dots there target hidden faults missing from the catalogue."),
        "named_non_fault_mimic": TOP["non_fault_mimic"],
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": hr["evaluator_version"],
            "pooled_dti": hr["pooled_dti"],
            "ci95": hr["ci95_cluster_bootstrap"],
            "n_withheld_positives": hr["n_withheld_positives"],
            "n_spatial_clusters": hr["n_spatial_clusters"],
            "label": "catalogue hide-and-recover diagnostic; NOT a leaderboard estimate, NOT organizer-confirmed",
        },
        "sgmc_off_catalogue": sg,
        "registry_correlation_and_overlap": {
            "vs_nine_focus_sites_max_within3px": max(ov.values()),
            "vs_nine_focus_sites": ov,
            "unique_vs_focus_sites": bool(max(ov.values()) <= 0.70),
            "full_registry_spearman": "NOT RUNNABLE OFFLINE — registry rasters are not cached locally "
                                      "(DrivenData login required) and literal_registry_complete=false",
            "full_registry_within3px": "NOT RUNNABLE OFFLINE — same reason",
        },
        "raster_sha256": bundle["zeros_tif"]["sha256"],
        "raster_sha256_nan": bundle["nan_tif"]["sha256"],
        "validator_zeros": bundle["zeros_tif"],
        "validator_nan": bundle["nan_tif"],
        "submission_name": f"karage3-{slug}-{ts}",
        "submission_note": note,
        "note_length_chars": len(note),
        "emitted_pixels": int(dots.sum()),
        "files": {
            "zeros_tif": bundle["zeros_tif"]["filename"],
            "nan_tif": bundle["nan_tif"]["filename"],
            "surface_npy": surf_npy.name,
            "audit_json": f"karage3-{slug}-{ts}-audit.json",
        },
        "offline_limitations": [
            "Organizer training features / SGMC grid not available offline (DrivenData login required); "
            "SGMC off-catalogue holdout computed against an all-zeros local placeholder (reported 0 / not measurable).",
            "Full-registry uniqueness (G4/G5/G6) not runnable offline: registry rasters are not cached and "
            "literal_registry_complete=false; the registered lattice covers 99.87% of the footprint within "
            "3 px, so the literal full-registry dot rule is unsatisfiable as written for any footprint-internal "
            "dot set — owner decision required.",
            "No organizer receipt exists for any file; local holdout does not track leaderboard scores.",
        ],
        "verdict": "negative",
        "ok_to_submit": False,
        "ok_to_submit_reason": ("Format-valid and unique against the nine focus sites, but NOT cleared: the "
                                "project's full-registry literal rule cannot be verified offline (registry rasters "
                                "not cached; completeness flag false) and is unsatisfiable as written vs the "
                                "registered lattice; no organizer receipt. Download for inspection/reproduction only."),
    }
    card_path = DOWNLOADS / f"karage3-{slug}-{ts}-run-card.json"
    card_path.write_text(json.dumps(run_card, indent=2, default=str))
    print(f"\n[run card] {card_path}")
    print(f"[verdict] {run_card['verdict']}  ok_to_submit={run_card['ok_to_submit']}")
    print(f"[zeros] {bundle['zeros_tif']['filename']} sha256={bundle['zeros_tif']['sha256']}")
    print(f"[nan]   {bundle['nan_tif']['filename']} sha256={bundle['nan_tif']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
