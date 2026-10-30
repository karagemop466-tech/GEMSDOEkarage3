#!/usr/bin/env python3
"""Build a UNIQUE, format-valid GeoTIFF submission candidate for the DOE GEMS prize.

Hypothesis H-OFFCAT-CORRIDOR (geometric prior; NOT a validated detector):
  The DrivenData GEMS target label set is faults NOT in the USGS/INGENIOUS
  catalogue (problem page 967). A candidate that only re-dots catalogue traces
  cannot earn credit for hidden off-catalogue faults. So this file places dots
  (a) off the catalogue (labels.tif + collar excluded), (b) outside the 3-px
  neighbourhood of every previously published submission dot (literal uniqueness
  vs the known dot registry), and (c) in a novel non-lattice, non-dotted-ridge
  spatial pattern (stratified jitter with a blind-fault distance prior), not the
  shared h19-5 dotted-ridge family.

  Layers available in this checkout (no organizer training_features.tif):
    * footprint + grid from data/bridge/sample_submission.tif  (EPSG:32611,
      3730 x 3292, 100 m, transform [100,0,243350,0,-100,4508550])
    * catalogue faults from data/bridge/labels.tif
  MISSING: training_features.tif (potential-field / DEM gradient layers) is required
  for a real edge-based blind-fault detector and is not available without a
  DrivenData login. Consequently this file is a geometric prior, not a scored
  geological model.

OUTPUTS (written to docs/downloads/):
  * <slug>-<ts>-<sha8>-zeros.tif   format-valid single-band float32 GeoTIFF
                                    (0 outside footprint, {0,1} inside, no NaN)
  * <slug>-<ts>-<sha8>-zeros.zip    single-TIF zip for portal upload
  * <slug>-<ts>-<sha8>-audit.json   submission_writer audit sidecar
  * docs/data/unique-submission-run-card.json   protocol run card

VERDICT: NOT OK TO SUBMIT.
  - No organizer labels → no holdout truth for off-catalogue faults → score not
    estimable; no claim is made that it beats 0.2778 or any leaderboard value.
  - Holdout, leakage-canary and full-registry uniqueness gates cannot run without
    training_features.tif / labels provenance and the organizer template.
  - This file is format-valid and demonstrably unique vs known prior dots, but it
    has not passed the promotion gates. Do not spend a weekly submission slot.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from submission_writer import write_validated_submission  # noqa: E402

SLUG = "karage3-offcat-corridor-prior-v1"
NOTE = "Off-catalogue blind-fault corridor prior: stratified dots off mapped catalogue faults and away from all prior submission dots."
assert len(NOTE) <= 140, len(NOTE)

DDIR = ROOT / "data" / "bridge"
SAMPLE = DDIR / "sample_submission.tif"
LABELS = DDIR / "labels.tif"
N_DOTS = 15_000          # emission budget (dots)
CAT_COLLAR_PX = 3        # mask catalogue traces pixel-exactly (300 m collar)
EXISTING_DOT_COLLAR_PX = 3  # avoid prior submission dots for literal uniqueness
MIN_DOT_SEP_PX = 6       # minimum separation between new dots (non-lattice, non-ridge)
RNG_SEED = 20261030


def read_footprint_grid(path: Path):
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        foot = np.isfinite(arr) & (ds.read_masks(1) > 0)
        grid = (ds.crs, ds.shape, ds.transform)
    return foot, grid


def read_labels(path: Path, foot: np.ndarray):
    with rasterio.open(path) as ds:
        raw = ds.read(1).astype(np.float32)
    lab = (raw > 0) & foot
    return lab


def collect_existing_dots(foot: np.ndarray) -> np.ndarray:
    """Boolean mask of pixels within EXISTING_DOT_COLLAR_PX of any prior submission dot."""
    exclude = np.zeros(foot.shape, dtype=bool)
    n_files = 0
    n_dots = 0
    for tif in sorted(ROOT.glob("docs/**/*.tif")):
        # skip the outputs we are about to write (none exist yet) and any non-grid tif
        try:
            with rasterio.open(tif) as ds:
                if (ds.shape, str(ds.crs)) != (foot.shape, "EPSG:32611"):
                    continue
                a = ds.read(1)
        except Exception:
            continue
        dots = np.isfinite(a) & (a > 0.5) & foot
        if not dots.any():
            continue
        n_files += 1
        n_dots += int(dots.sum())
        # Mark every pixel within the collar of each existing dot.
        buf = ndimage.binary_dilation(dots, iterations=EXISTING_DOT_COLLAR_PX)
        exclude |= buf
    print(f"existing dot files scanned: {n_files}, prior dots: {n_dots:,}, "
          f"exclude-collar pixels: {int(exclude.sum()):,}")
    return exclude


def poisson_disc_sample(candidate: np.ndarray, n_dots: int, min_sep_px: int,
                        weight: np.ndarray | None, rng: np.random.Generator,
                        max_tries: int = 200) -> np.ndarray:
    """Greedy Poisson-disc-like sampling weighted by ``weight`` (None = uniform).

    Returns boolean mask of placed dots. Novel non-lattice pattern.
    """
    H, W = candidate.shape
    flat_idx = np.flatnonzero(candidate.ravel())
    if flat_idx.size == 0:
        return np.zeros((H, W), dtype=bool)
    if weight is not None:
        w = weight.ravel()[flat_idx].astype(np.float64)
        w = np.maximum(w, 0.0)
        if w.sum() <= 0:
            w = np.ones_like(w)
        p = w / w.sum()
    else:
        p = None
    placed = np.zeros((H, W), dtype=bool)
    placed_list = []
    order = rng.choice(flat_idx, size=flat_idx.size, replace=True, p=p)
    tries = 0
    for idx in order:
        if tries > max_tries * max(1, n_dots):
            break
        tries += 1
        y, x = divmod(int(idx), W)
        if not candidate[y, x]:
            continue
        if placed_list:
            yy = np.array([p0 for p0, _ in placed_list])
            xx = np.array([p1 for _, p1 in placed_list])
            dist2 = (yy - y) ** 2 + (xx - x) ** 2
            if dist2.min() < min_sep_px ** 2:
                continue
        placed[y, x] = True
        placed_list.append((y, x))
        if len(placed_list) >= n_dots:
            break
    return placed


def main() -> int:
    t0 = datetime.now(timezone.utc)
    foot, grid = read_footprint_grid(SAMPLE)
    crs, shape, transform = grid
    labels = read_labels(LABELS, foot)
    catalogue_exclude = ndimage.binary_dilation(labels, iterations=CAT_COLLAR_PX) & foot

    existing_exclude = collect_existing_dots(foot)

    # Candidate zone: on the footprint, off the catalogue, away from prior dots.
    candidate = foot & ~catalogue_exclude & ~existing_exclude
    print(f"footprint: {int(foot.sum()):,}  catalogue+collar excl: {int(catalogue_exclude.sum()):,}  "
          f"candidate zone: {int(candidate.sum()):,}")

    # Blind-fault distance prior: moderate distance from catalogue faults (near a
    # faulted terrane but not on a mapped trace). Weight ramps from the collar out
    # to ~2 km then gently decays, favouring covered/off-catalogue terrain.
    d_cat = ndimage.distance_transform_edt(~catalogue_exclude).astype(np.float32)
    d_cat = np.where(foot, d_cat, 0.0)
    prior = np.clip((d_cat - CAT_COLLAR_PX) / 20.0, 0.0, 1.0)  # 0 at collar, ~1 at 2 km
    prior = np.where(candidate, prior, 0.0)

    rng = np.random.default_rng(RNG_SEED)
    mask = poisson_disc_sample(candidate, N_DOTS, MIN_DOT_SEP_PX, prior, rng)
    n_dots = int(mask.sum())
    print(f"placed dots: {n_dots:,}")

    if n_dots == 0:
        raise SystemExit("No dots placed: candidate zone empty (lower N_DOTS or collars).")

    ts = t0.strftime("%Y%m%dT%H%M%SZ")
    digest8 = hashlib.sha256(np.packbits(mask)).hexdigest()[:8]

    meta = {
        "candidate_id": SLUG,
        "description": "Geometric off-catalogue corridor prior (stratified jitter, catalogue- and prior-dot excluded).",
        "submission_note_zeros": NOTE,
        "submission_note_nan": NOTE,
        "catalogue_hidden_mean": None,
        "catalogue_hidden_per_quadrant": {},
        "sgmc_prevalence_calibrated_dti": None,
        "drift_corrected_holdout_mean": None,
        "drift_corrected_per_quadrant": {},
        "predicted_leaderboard_dti": None,
        "ei_drift_corrected": None,
        "slot_decision": "HOLD-DO-NOT-SUBMIT",
    }
    bundle = write_validated_submission(
        mask, slug=SLUG, candidate_meta=meta, ddir=DDIR,
        out_dir=ROOT / "docs" / "downloads", timestamp_tag=ts,
    )

    zeros_name = bundle["zeros_tif"]["filename"]
    zeros_sha = bundle["zeros_tif"]["sha256"]

    # Run card (protocol rule 5).
    card = {
        "schema": "GEMSDOEkarage3-RUN-CARD-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis": "H-OFFCAT-CORRIDOR: hidden (off-catalogue) geothermal faults are more likely in covered faulted terrain away from mapped USGS/INGENIOUS traces; dots placed off-catalogue in a novel non-lattice pattern should encounter blind faults that the dotted-ridge family (clustered on/near catalogue traces) misses.",
        "mechanism": "Exclude catalogue faults + 300 m collar; exclude 3 px around every prior submission dot; weight the surviving off-catalogue zone by distance-from-catalogue prior; place dots by weighted Poisson-disc sampling (min 6 px separation) for a novel spatial pattern.",
        "named_non_fault_mimic": "Lithologic contacts, dikes/intrusive margins, landslide scarps, road cuts, fence lines and acquisition striping can all produce edge/lineament-like geometry without being faults.",
        "layers": ["footprint (sample_submission.tif)", "catalogue faults (labels.tif)", "prior submission dot registry (docs/downloads)"],
        "physical_signature": "off-catalogue spatial exclusion + distance-from-catalogue prior (geometric proxy; no potential-field/DEM gradient layers available)",
        "differs_from_existing": "Avoids all prior submission dots (literal uniqueness) and off-catalogue (excludes labels); the dotted-ridge family clusters on/near catalogue traces and reuses the same dot array across GEMSDOE24/25/27/28/30/31/32/33/36.",
        "leakage_canary": {"status": "NOT RUN", "note": "training_features.tif unavailable; no feature-only AUC vs catalogue can be computed."},
        "holdout_dti": {"label": "NOT ESTIMABLE", "value": None, "ci95": None,
                        "n_withheld_positives": None, "evaluator": "none (no organizer labels/training features)"},
        "registry_correlation_and_overlap": {
            "unique_vs_prior_dots_by_construction": True,
            "max_overlap3px_vs_known_prior_dots": 0.0,
            "note": "3-px collar around every prior dot excluded before placement; full-registry literal scan not run (registry incomplete in this checkout).",
        },
        "raster": f"docs/downloads/{zeros_name}",
        "raster_sha256": zeros_sha,
        "validator_output": bundle["zeros_tif"],
        "submission_name": SLUG,
        "submission_note": NOTE,
        "submission_note_chars": len(NOTE),
        "n_dots": n_dots,
        "budget_exhausted": False,
        "verdict": "negative",
        "ok_to_submit": False,
        "reason": "Format-valid and unique vs prior dots, but NOT validated: no organizer labels/training_features.tif, so holdout DTI, leakage canary, and leaderboard-score estimate cannot be computed. Do not submit.",
    }
    card_path = ROOT / "docs" / "data" / "unique-submission-run-card.json"
    card_path.parent.mkdir(parents=True, exist_ok=True)
    card_path.write_text(json.dumps(card, indent=2, default=str) + "\n")

    print(json.dumps({
        "slug": SLUG, "dots": n_dots, "zeros_tif": zeros_name,
        "zeros_sha256": zeros_sha, "run_card": str(card_path),
        "ok_to_submit": False, "verdict": "negative",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
