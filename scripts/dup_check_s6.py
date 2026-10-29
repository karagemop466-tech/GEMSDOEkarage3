#!/usr/bin/env python3
"""Duplicate check for Session-6 candidates against every restored scored raster.

Protocol: log DUPLICATE and stop if the literal 3-px overlap with any registry
raster exceeds 70% of dots, or if the rank correlation exceeds 0.90. Binary dot
maps make Spearman degenerate, so the overlap test is the operative one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from focus_site_audit import dots_of, literal_overlap  # noqa: E402
from gems32.paths import data_dir  # noqa: E402

CANDIDATES = {
    "S6-E1": ROOT / "evidence/experiments/s6-e1/gemsdoekarage3-s6-offcons-tmihg-ridge-37654-20261029.tif",
    "S6-E2": ROOT / "evidence/experiments/s6-e2/gemsdoekarage3-s6-lidar-step-coh-37654-20261029.tif",
}
OUT = ROOT / "evidence" / "dup-check-s6.json"


def main() -> int:
    raster_paths = sorted((data_dir() / "scored").glob("*.tif"))
    result = {"protocol": {"overlap_stop": 0.70, "rank_stop": 0.90, "rule": "literal 3-px overlap, dots of candidate within 3 px of any dot of the reference raster"},
              "n_reference_rasters": len(raster_paths), "candidates": {}}
    refs = {}
    for rp in raster_paths:
        with rasterio.open(rp) as s:
            refs[rp.name] = s.read(1).astype(np.float32)
    for name, cpath in CANDIDATES.items():
        with rasterio.open(cpath) as s:
            cand = s.read(1).astype(np.float32)
        cdots = dots_of(cand)
        rows = []
        for rn, arr in refs.items():
            rdots = dots_of(arr)
            ov = literal_overlap(cdots, rdots) if rdots.any() else 0.0
            # rank correlation on the union of valid pixels (binary, so degenerate; reported for completeness)
            fin = np.isfinite(arr) & np.isfinite(cand)
            samp = np.flatnonzero(fin.ravel())
            rng = np.random.default_rng(7)
            samp = rng.choice(samp, size=min(200_000, samp.size), replace=False)
            rho = float(spearmanr(cand.ravel()[samp], arr.ravel()[samp]).correlation) if np.std(arr.ravel()[samp]) > 0 else None
            rows.append({"reference": rn, "reference_dots": int(rdots.sum()), "literal_overlap_3px": round(float(ov), 6),
                         "spearman_sampled": None if rho is None else round(rho, 6)})
        worst = max(rows, key=lambda r: r["literal_overlap_3px"])
        dup = worst["literal_overlap_3px"] > 0.70 or any((r["spearman_sampled"] or 0) > 0.90 for r in rows)
        result["candidates"][name] = {"file": str(cpath.relative_to(ROOT)), "dots": int(cdots.sum()),
                                      "worst_reference": worst, "verdict": "DUPLICATE_STOP" if dup else "not_duplicate_by_protocol",
                                      "references": rows}
        print(name, "dots", int(cdots.sum()), "worst", worst["reference"], worst["literal_overlap_3px"],
              "verdict", result["candidates"][name]["verdict"], flush=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
