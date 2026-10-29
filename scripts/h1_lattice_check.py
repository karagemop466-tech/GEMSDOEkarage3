"""Measure main's H1 candidate against the registered r13 lattice witness.

Literal rule (repo protocol, not an organizer rule): a file is a duplicate when
>70% of its dots lie within 3 px (300 m) of the dots of a registry raster.
Writes evidence/h1-lattice-check-20261029.json. Read-only on the candidates.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
LATTICE = ROOT / ".cache/gems_data/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
CARD = ROOT / "evidence/unique-submission-h1-20261029T182309Z.json"
OUT = ROOT / "evidence/h1-lattice-check-20261029.json"
STEM = "docs/downloads/gemsdoe32-karage3-h1-seismic-gravity-basin-20261029T182309Z-91540319-"


def dots(path):
    with rasterio.open(path) as s:
        a = s.read(1).astype("float64")
        return (np.isfinite(a) & (a > 0)), s.transform, s.crs
        
def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    lat, lt, _ = dots(LATTICE)
    dist = ndimage.distance_transform_edt(~lat)
    card = json.loads(CARD.read_text())
    out = {"schema_version": 1, "rule": "duplicate if >70% of dots within 3 px of a registry raster's dots",
           "lattice": {"file": str(LATTICE.relative_to(ROOT)), "sha256": sha256(LATTICE), "dots": int(lat.sum())},
           "candidate_card": str(CARD.relative_to(ROOT)), "candidates": {},
           "holdout_metrics_in_card": card["bundle"]["holdout_metrics"],
           "registry_check": "14 of 113 registry repositories restored locally; full registry not checked"}
    for mode in ("nan", "zeros"):
        p = ROOT / (STEM + mode + ".tif")
        d, tf, _ = dots(p)
        if tf != lt:
            raise SystemExit(f"grid mismatch: {p}")
        dd = dist[d]
        out["candidates"][mode] = {
            "file": str(p.relative_to(ROOT)), "sha256": sha256(p), "dots": int(d.sum()),
            "within_3px_of_lattice_fraction": round(float((dd <= 3).mean()), 6),
            "min_distance_px": round(float(dd.min()), 4), "median_distance_px": round(float(np.median(dd)), 4),
            "max_distance_px": round(float(dd.max()), 4),
        }
    out["literal_lattice_duplicate"] = any(c["within_3px_of_lattice_fraction"] > 0.70 for c in out["candidates"].values())
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
