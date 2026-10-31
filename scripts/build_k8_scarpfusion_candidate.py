#!/usr/bin/env python3
"""K8 candidate generator: SCARPFUSION (scarp-first concealed-fault fusion).

LANE (protocol rule 1, one paragraph): Place a sparse binary dot set on the local
maxima of a weighted fusion of five percentile-ranked, per-pixel evidence fields —
(1) LiDAR scarp evidence (max of step_max, ex_max, lapneg_max, lappos_max,
cross_max, relief from the pinned 3DEP-derived stack), (2) isostatic-gravity
horizontal gradient (band iso_grav_anom_hg), (3) TMI horizontal gradient
(band tmi_hg), (4) earthquake density (band deq_n100a15), (5) geodetic second
invariant of strain rate (band geod_2ndinv) — weights 0.40/0.15/0.15/0.15/0.15,
thinned by a 5 px-disc non-maximum suppression and capped at N highest-fusion dots,
excluding pixels within CATALOGUE_BUFFER_PX of the USGS/INGENIOUS catalogue.
No model is fitted, so no fold-local feature leakage can enter the surface.

HYPOTHESIS: expert-labeled new faults (the hidden test set) preferentially follow
fresh, geomorphically expressed scarps and their geophysically corroborated
concealed continuations, so scarp-first placement with corroboration beats both
catalogue-proximal and pure-topographic-ridge placement.

NAMED NON-FAULT MIMICKER (protocol rule 5): lithologic/stratigraphic density and
magnetic contrasts, and anthropogenic cuts (roads, gravel pits), can produce
step/curvature/gradient responses without fault slip; the seismicity and strain
fields can cluster on geothermal swarms rather than faults.

Determinism: fixed seed, fixed band names, tie-broken by (value, row, col) order.
Output: .npy emission mask + generator receipt JSON. Gates (holdout, format,
uniqueness, release) run downstream in the canonical scripts; nothing here
clears a submission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, maximum_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32.paths import data_dir  # noqa: E402

SENTINEL = -1e30
EXPECTED_FOOTPRINT = 5_167_373
NMS_SIZE_PX = 5            # ~500 m non-maximum suppression disc (size = 2*r+1)
CATALOGUE_BUFFER_PX = 2    # keep dots strictly off the catalogue (writer zeroes label pixels)
SEED = 20261031
WEIGHTS = {
    "scarp": 0.40,
    "iso_grav_anom_hg": 0.15,
    "tmi_hg": 0.15,
    "deq_n100a15": 0.15,
    "geod_2ndinv": 0.15,
}
SCARP_BANDS = ("step_max", "ex_max", "lapneg_max", "lappos_max", "cross_max", "relief")


def tie_aware_rank(x: np.ndarray) -> np.ndarray:
    """Average ranks in [0, 1] over the flattened vector (ties share the average rank)."""
    u, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    cum = np.cumsum(counts, dtype=np.int64)
    avg = (cum - counts + 1 + cum) / 2.0
    r = avg[inv].astype(np.float64)
    r /= max(int(x.size), 1)
    return r


def read_band_by_name(ds, name: str) -> np.ndarray:
    idx = [i for i, d in enumerate(ds.descriptions) if d and d.split(" - ")[0].strip() == name]
    if len(idx) != 1:
        raise ValueError(f"band {name!r} not uniquely found in {list(ds.descriptions)}")
    return ds.read(idx[0] + 1)


def compute_surface(ddir: Path) -> dict:
    """Shared K8 evidence surface: 5-layer weighted percentile fusion + canary context."""
    with rasterio.open(ddir / "sample_submission.tif") as t:
        foot = np.isfinite(t.read(1)) & (t.read_masks(1) > 0)
    if int(foot.sum()) != EXPECTED_FOOTPRINT:
        raise ValueError(f"unexpected footprint {int(foot.sum())}")

    with rasterio.open(ddir / "training_features.tif") as ds:
        grav = read_band_by_name(ds, "iso_grav_anom_hg").astype(np.float64)
        tmi = read_band_by_name(ds, "tmi_hg").astype(np.float64)
        deq = read_band_by_name(ds, "deq_n100a15").astype(np.float64)
        strain = read_band_by_name(ds, "geod_2ndinv").astype(np.float64)
    with rasterio.open(ddir / "external" / "lidar_scarp_features_u8.tif") as ds:
        names = list(ds.descriptions)
        scarp = np.max(np.stack([ds.read(names.index(b) + 1) for b in SCARP_BANDS]), axis=0).astype(np.float64)
        scarp_valid = ds.read(names.index("valid") + 1) > 0
    with rasterio.open(ddir / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot

    def band_ok(a: np.ndarray) -> np.ndarray:
        return foot & np.isfinite(a) & (a > SENTINEL)

    eligible = foot.copy()
    for a in (grav, tmi, deq, strain):
        eligible &= band_ok(a)
    # Scarp-first: restrict placement to lidar-covered cells so the scarp rank is
    # meaningful everywhere a dot may land. Cells with zero scarp evidence remain
    # eligible (covered bedrock/basins with no scarp) but rank lowest on that layer.
    eligible &= scarp_valid
    # Catalogue buffer: never place within CATALOGUE_BUFFER_PX px of a catalogue pixel.
    eligible &= distance_transform_edt(~labels) > float(CATALOGUE_BUFFER_PX)

    layers = {
        "scarp": tie_aware_rank(scarp[eligible]),
        "iso_grav_anom_hg": tie_aware_rank(grav[eligible]),
        "tmi_hg": tie_aware_rank(tmi[eligible]),
        "deq_n100a15": tie_aware_rank(deq[eligible]),
        "geod_2ndinv": tie_aware_rank(strain[eligible]),
    }
    S = np.zeros(int(eligible.sum()), dtype=np.float64)
    for k, w in WEIGHTS.items():
        S += w * layers[k]

    # Leakage canary (protocol rule 4): each layer alone vs SGMC off-catalogue truth.
    with rasterio.open(ddir / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = (ds.read(1) > 0) & foot
    off = foot & ~labels & (distance_transform_edt(~labels) > 3.0)
    from sklearn.metrics import roc_auc_score

    canary = {}
    for k in layers:
        x = layers[k][off[eligible]]
        y = sgmc[eligible][off[eligible]]
        canary[k] = float(roc_auc_score(y, x)) if np.std(x) > 0 else None

    full = np.full(foot.shape, -np.inf, dtype=np.float64)
    full[eligible] = S
    return {
        "foot": foot,
        "labels": labels,
        "eligible": eligible,
        "S": S,
        "full": full,
        "canary": canary,
        "sgmc": sgmc,
    }


def build(n_dots: int, ddir: Path, out_dir: Path, slug: str) -> dict:
    ctx = compute_surface(ddir)
    foot, labels, eligible = ctx["foot"], ctx["labels"], ctx["eligible"]
    S, full, canary = ctx["S"], ctx["full"], ctx["canary"]

    # NMS on a full-grid surface (eligible cells only get S; others -inf).
    mx = maximum_filter(full, size=NMS_SIZE_PX, mode="constant", cval=-np.inf)
    nms_mask = eligible & (full >= mx) & np.isfinite(mx)
    idx = np.flatnonzero(nms_mask)
    if idx.size < n_dots:
        raise ValueError(f"only {idx.size} NMS survivors for {n_dots} dots")

    vals = full[nms_mask]
    # Deterministic order: by S desc, then (row, col); tiny seeded jitter breaks quantised ties.
    rng = np.random.default_rng(SEED)
    jitter = rng.uniform(0.0, 1e-9, size=vals.shape)
    order = np.lexsort((idx % foot.shape[1], idx // foot.shape[1], -(vals + jitter)))
    chosen = idx[order[:n_dots]]

    mask = np.zeros(foot.shape, dtype=bool)
    mask.ravel()[chosen] = True
    if not (mask & ~eligible).sum() == 0:
        raise ValueError("dot placed on ineligible pixel")
    if int((mask & labels).sum()) != 0:
        raise ValueError("dot placed on catalogue pixel")

    out_dir.mkdir(parents=True, exist_ok=True)
    npy_path = out_dir / f"{slug}_mask.npy"
    np.save(npy_path, mask)

    receipt = {
        "candidate": slug,
        "lane": "K8 scarp-first concealed-fault fusion (see module docstring)",
        "hypothesis": "expert new faults follow fresh scarps + corroborated concealed continuations",
        "mimicker": "lithologic/stratigraphic contrasts and anthropogenic cuts; geothermal seismicity swarms",
        "n_dots": int(mask.sum()),
        "n_eligible": int(eligible.sum()),
        "n_nms_survivors": int(idx.size),
        "weights": WEIGHTS,
        "scarp_bands": list(SCARP_BANDS),
        "nms_size_px": NMS_SIZE_PX,
        "catalogue_buffer_px": CATALOGUE_BUFFER_PX,
        "seed": SEED,
        "share_dots_within_3px_of_catalogue": float(
            (mask & (distance_transform_edt(~labels) <= 3.0)).sum() / mask.sum()
        ),
        "leakage_canary_single_layer_auc_vs_sgmc_offcat": canary,
        "max_canary_auc": max(v for v in canary.values() if v is not None),
        "mask_sha256": hashlib.sha256(np.packbits(mask).tobytes()).hexdigest(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "cleared": False,
        "note": "candidate only; gates run downstream (evaluate_holdout.py, validate_submission.py, uniqueness screens)",
    }
    (out_dir / f"{slug}_generator_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-dots", type=int, default=34_000)
    ap.add_argument("--slug", default="karage3-k8-scarpfusion-v1")
    ap.add_argument("--out-dir", type=Path, default=ROOT / ".cache" / "k8")
    ap.add_argument("--data-dir", type=Path, default=None)
    args = ap.parse_args()
    receipt = build(args.n_dots, args.data_dir or data_dir(), args.out_dir, args.slug)
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
