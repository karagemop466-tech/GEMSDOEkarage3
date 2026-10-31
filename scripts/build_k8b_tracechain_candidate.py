#!/usr/bin/env python3
"""K8-B candidate: SCARPFUSION surface with TRACE-CHAIN placement (experiment E3).

Same evidence surface as `build_k8_scarpfusion_candidate.py` (imported, no fork):
weighted fusion of scarp / gravity-edge / magnetic-edge / seismicity / strain ranks.
Only the placement changes, to test the geometry hypothesis:

  v1 (E2): 5 px-disc non-maximum-suppression peaks, capped at N dots.
  v2 (E3): threshold surface at its top-`QTHR` fraction within eligible cells,
           3x3 binary opening to drop specks, morphological skeleton to 1-px
           trace chains, then greedy pearl-chain sampling in descending surface
           order with `MIN_SPACING_PX` minimum spacing and a hard dot cap.

RATIONALE: expert-labeled faults are drawn as thin curvilinear traces; the highest
user-reported focus files are all sparse pearl-chains along curvilinear structure
(37.6k-44k dots). Chain placement concentrates the same evidence into trace-like
geometry instead of scattered peaks.

Determinism: fixed seed, descending (S + seeded jitter), row/col tie-break.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import binary_opening, skeletonize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_k8_scarpfusion_candidate import (  # noqa: E402
    CATALOGUE_BUFFER_PX,
    SEED,
    WEIGHTS,
    compute_surface,
)

QTHR = 0.045          # keep the top 4.5 % of smoothed eligible cells as trace cores
SMOOTH_SIGMA_PX = 1.5 # Gaussian pre-smoothing (~150 m) to connect responses into chains
MIN_SPACING_PX = 2    # pearl-chain minimum dot spacing (Chebyshev window px)
DOT_CAP = 38_000      # hard cap on emitted dots


def place_trace_chains(ctx: dict, rng: np.random.Generator) -> tuple[np.ndarray, dict]:
    foot, eligible, full = ctx["foot"], ctx["eligible"], ctx["full"]
    # Smooth the surface over eligible cells only (normalising by a smoothing of the
    # eligibility mask keeps covered/uncovered edges from biasing the level set).
    Sm = np.zeros(foot.shape, dtype=np.float64)
    Sm[eligible] = full[eligible]
    num = ndi.gaussian_filter(Sm, sigma=SMOOTH_SIGMA_PX, mode="constant", cval=0.0)
    den = ndi.gaussian_filter(eligible.astype(np.float64), sigma=SMOOTH_SIGMA_PX, mode="constant", cval=0.0)
    smooth = np.divide(num, den, out=np.full_like(num, -np.inf), where=den > 1e-6)
    thr = np.quantile(smooth[eligible], 1.0 - QTHR)
    core = np.zeros(foot.shape, dtype=bool)
    core[eligible] = smooth[eligible] >= thr
    core_open = ndi.binary_opening(core, np.ones((3, 3), bool))
    skel = skeletonize(core_open) & eligible

    cand = np.flatnonzero(skel)
    vals = full.ravel()[cand]
    jitter = rng.uniform(0.0, 1e-9, size=vals.shape)
    order = np.lexsort((cand % foot.shape[1], cand // foot.shape[1], -(vals + jitter)))

    mask = np.zeros(foot.shape, dtype=bool)
    occ = np.zeros(foot.shape, dtype=bool)
    n_rejected = 0
    r = MIN_SPACING_PX  # Chebyshev window == Euclidean radius r (conservative)
    for i in order:
        if int(mask.sum()) >= DOT_CAP:
            break
        y, x = divmod(int(cand[i]), foot.shape[1])
        y0, y1 = max(0, y - r), min(foot.shape[0], y + r + 1)
        x0, x1 = max(0, x - r), min(foot.shape[1], x + r + 1)
        if occ[y0:y1, x0:x1].any():
            n_rejected += 1
            continue
        mask[y, x] = True
        occ[y, x] = True

    info = {
        "threshold": float(thr),
        "core_pixels": int(core.sum()),
        "core_after_opening": int(core_open.sum()),
        "skeleton_pixels": int(skel.sum()),
        "dots": int(mask.sum()),
        "rejected_by_spacing": int(n_rejected),
        "smooth_sigma_px": SMOOTH_SIGMA_PX,
    }
    return mask, info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", default="karage3-k8b-tracechain-v2")
    ap.add_argument("--out-dir", type=Path, default=ROOT / ".cache" / "k8")
    ap.add_argument("--data-dir", type=Path, default=None)
    args = ap.parse_args()
    from gems32.paths import data_dir

    ddir = args.data_dir or data_dir()
    ctx = compute_surface(ddir)
    rng = np.random.default_rng(SEED + 1)
    mask, info = place_trace_chains(ctx, rng)

    labels = ctx["labels"]
    from scipy.ndimage import distance_transform_edt

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / f"{args.slug}_mask.npy", mask)
    receipt = {
        "candidate": args.slug,
        "lane": "K8 scarp-first concealed-fault fusion; trace-chain placement (E3)",
        "hypothesis": "same evidence as K8 v1; trace-like chain geometry matches how experts draw faults",
        "mimicker": "lithologic/stratigraphic contrasts and anthropogenic cuts; geothermal seismicity swarms",
        "placement": {"qthr": QTHR, "min_spacing_px": MIN_SPACING_PX, "dot_cap": DOT_CAP, **info},
        "weights": WEIGHTS,
        "catalogue_buffer_px": CATALOGUE_BUFFER_PX,
        "seed": SEED + 1,
        "share_dots_within_3px_of_catalogue": float(
            (mask & (distance_transform_edt(~labels) <= 3.0)).sum() / mask.sum()
        ),
        "leakage_canary_single_layer_auc_vs_sgmc_offcat": ctx["canary"],
        "max_canary_auc": max(v for v in ctx["canary"].values() if v is not None),
        "mask_sha256": hashlib.sha256(np.packbits(mask).tobytes()).hexdigest(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "cleared": False,
    }
    (out_dir / f"{args.slug}_generator_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
