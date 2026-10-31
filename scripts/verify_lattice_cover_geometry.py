"""Independent geometric check of the lattice-covering claim (no raster needed).

Question: what share of the plane lies within 3 px of a regular dot lattice of
spacing s px? If this is near 100% for s around 4-5 px, then any dense
candidate placed on that footprint is within 3 px of the lattice, which is the
mechanism behind the literal 70% rule being unsatisfiable (see
evidence/k8d-lattice-covering-proof.json). This script does NOT reproduce the
repo's 99.87% figure, which depends on the real r13-lattice-s5 dot layout.

Run: python scripts/verify_lattice_cover_geometry.py [--out evidence/lattice-cover-geometry-20261031.json]
"""
from __future__ import annotations

import argparse
import json

import numpy as np
from scipy.spatial import cKDTree


def square_lattice_share(spacing: float, radius: float = 3.0, n: int = 400) -> float:
    k = int(np.ceil(n / spacing)) + 3
    pts = np.array([(i * spacing, j * spacing) for i in range(-3, k) for j in range(-3, k)], float)
    ys, xs = np.meshgrid(np.arange(n) + 0.5, np.arange(n) + 0.5, indexing="ij")
    grid = np.stack([xs.ravel(), ys.ravel()], axis=1)
    dist, _ = cKDTree(pts).query(grid)
    return float((dist <= radius).mean())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    rows = [{"spacing_px": s, "share_within_3px": round(square_lattice_share(s), 4)} for s in (4, 5, 6, 8)]
    result = {
        "schema": "lattice-cover-geometry-v1",
        "model": "ideal square lattice, Euclidean distance <= 3 px, sampled on a 400x400 pixel-centre grid",
        "rows": rows,
        "caveat": "Ideal lattice only. Not the repo's r13-lattice-s5 raster; the 99.87% figure is not reproduced here.",
    }
    text = json.dumps(result, indent=1)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")


if __name__ == "__main__":
    main()
