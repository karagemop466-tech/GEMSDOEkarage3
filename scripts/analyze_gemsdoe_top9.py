#!/usr/bin/env python3
"""Structural analysis of the nine GEMSDOE top-site TIFFs (no score is computed here).

For every fetched file it measures, from the saved bytes and the restored catalogue raster:
  * dot count (value > 0), footprint coverage, and whether dots sit inside the footprint;
  * how many dots lie within 3 px (300 m) of a catalogue fault in labels.tif (value == 1)
    versus off-catalogue (> 3 px away); off-catalogue dots are the only ones that can add
    holdout credit that is not already known;
  * the directional literal overlap used by the repo's uniqueness rule: the fraction of
    file A's dots within 3 px of any dot in file B (9 x 9 matrix, symmetric check);
  * Pearson correlation of the two binary dot rasters (a rank-correlation proxy only).

Output: docs/data/gemsdoe-top9-analysis.json. Everything here is measured, not projected.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_gemsdoe_top9 import SITES, CACHE  # noqa: E402

LABELS = ROOT / ".cache" / "gems_data" / "labels.tif"
OUT = ROOT / "docs" / "data" / "gemsdoe-top9-analysis.json"
RADIUS_PX = 3.0


def dot_coords(a: np.ndarray) -> np.ndarray:
    """(row, col) of every cell with a finite positive value (the 'dots')."""
    return np.argwhere(np.isfinite(a) & (a > 0))


def main() -> int:
    with rasterio.open(LABELS) as ds:
        lab = ds.read(1)
    footprint = lab != -1  # labels.tif uses -1 as nodata/outside; 0/1 inside
    cat = np.argwhere(lab == 1)
    from scipy.ndimage import distance_transform_edt as _edt
    DIST_CAT = _edt(~(lab == 1))  # distance (px) from each cell to the nearest catalogue fault pixel
    cat_tree = cat if cat.size else np.zeros((0, 2))
    tree = cKDTree(cat_tree) if cat.size else None

    rows, dots_by_site = [], {}
    for site, repo, sha, path, reported in SITES:
        p = CACHE / site / Path(path).name
        with rasterio.open(p) as ds:
            a = ds.read(1).astype(np.float64)
        d = dot_coords(a)
        dots_by_site[site] = d
        inside = footprint[d[:, 0], d[:, 1]] if d.size else np.zeros(0, bool)
        if tree is not None and d.size:
            dist_cat, _ = tree.query(d, k=1)
        else:
            dist_cat = np.full(d.shape[0], np.inf)
        near = dist_cat <= RADIUS_PX
        vals = a[d[:, 0], d[:, 1]] if d.size else np.zeros(0)
        # Nearest-neighbour spacing among a file's own dots (measures placement density).
        if d.size > 2:
            t = cKDTree(d)
            nn, _ = t.query(d, k=2)
            nn = nn[:, 1]
            spacing = dict(median_px=float(np.median(nn)), p10_px=float(np.percentile(nn, 10)))
        else:
            spacing = dict(median_px=None, p10_px=None)
        from scipy.ndimage import distance_transform_edt
        dd_cat = DIST_CAT[d[:, 0], d[:, 1]] if d.size else np.zeros(0)
        rows.append(dict(
            site=site, file_name=Path(path).name,
            dots_on_catalogue_pixel=int((dd_cat == 0).sum()),
            dots_1_to_3px_from_catalogue=int(((dd_cat > 0) & (dd_cat <= RADIUS_PX)).sum()),
            dots_gt_3px_from_catalogue=int((dd_cat > RADIUS_PX).sum()),
            n_dots=int(d.shape[0]),
            dot_values_unique=[float(v) for v in np.unique(vals)[:6]],
            dots_inside_footprint=int(inside.sum()),
            dots_outside_footprint=int((~inside).sum()),
            dots_within_3px_of_catalogue=int(near.sum()),
            dots_off_catalogue_gt_3px=int((~near).sum()),
            off_catalogue_fraction=float((~near).mean()) if d.size else None,
            catalogue_positive_pixels=int(cat.shape[0]),
            own_nn_spacing=spacing,
        ))
        print(site, rows[-1]["n_dots"], rows[-1]["off_catalogue_fraction"], flush=True)

    sites = [s[0] for s in SITES]
    n = len(sites)
    overlap = np.full((n, n), np.nan)
    pearson = np.full((n, n), np.nan)
    rasters = {}
    for i, si in enumerate(sites):
        rasters[si] = None
    for i, si in enumerate(sites):
        di = dots_by_site[si]
        for j, sj in enumerate(sites):
            if i == j:
                overlap[i, j] = 1.0
                pearson[i, j] = 1.0
                continue
            dj = dots_by_site[sj]
            if di.size == 0 or dj.size == 0:
                continue
            tj = cKDTree(dj)
            dist, _ = tj.query(di, k=1)
            overlap[i, j] = float((dist <= RADIUS_PX).mean())  # share of A's dots within 3 px of B
    # Pearson on binary dot indicators, computed from sparse coordinates (cell-level overlap).
    shape = (3730, 3292)
    masks = {}
    for si in sites:
        m = np.zeros(shape, np.float32)
        d = dots_by_site[si]
        m[d[:, 0], d[:, 1]] = 1.0
        masks[si] = m
    for i, si in enumerate(sites):
        for j, sj in enumerate(sites):
            if j < i:
                pearson[i, j] = pearson[j, i]
                continue
            if i == j:
                continue
            x, y = masks[si].ravel(), masks[sj].ravel()
            sx, sy = x.std(), y.std()
            pearson[i, j] = float(((x - x.mean()) * (y - y.mean())).mean() / (sx * sy)) if sx and sy else np.nan
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(
        schema_version=1,
        note=("Measured from saved bytes and labels.tif (catalogue). Off-catalogue = > 3 px from a "
              "catalogue fault pixel. Overlap[i][j] = fraction of site i dots within 3 px of any site j dot. "
              "Pearson is on binary dot masks (proxy; the repo rank rule still needs the full registry)."),
        sites=sites,
        per_file=rows,
        overlap_within_3px_directional=[[None if np.isnan(v) else round(float(v), 6) for v in r] for r in overlap],
        pearson_binary_dots=[[None if np.isnan(v) else round(float(v), 6) for v in r] for r in pearson],
    ), indent=2, allow_nan=False) + "\n")
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
