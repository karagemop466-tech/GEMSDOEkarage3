#!/usr/bin/env python3
"""Build a novel, unique geological surface for the GEMSDOE submission.

Hypothesis (distinct from dotted-h19-5 multiline-corroboration):
    Along known fault strands, geothermal upflow localises where several
    *independent* physical fields co-vary: subsurface conductive/basement
    boundary (cond_surf & depth_to_base_surf gradient), active dilation
    (geod_dilaterate), 1 m LiDAR scarp expression, and radiometric alteration
    (total count).  Dots are placed on the top-N co-located high-signal pixels
    within the fault zone, with non-maximum separation, so dots cluster at the
    most conductive/dilated/scapped spots rather than uniformly along the strand.

    This differs from dotted-h19-5 (topography/multiline corroboration of
    catalogue strands) in BOTH the physical basis (conductivity/dilation/
    basement instead of topography lineaments) and the placement rule
    (co-located multi-physics hot spots within the fault zone).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32.paths import data_dir  # noqa: E402


def robust_unit(a: np.ndarray, foot: np.ndarray, pct: float = 99.5) -> np.ndarray:
    out = np.zeros(a.shape, dtype=np.float32)
    v = foot & np.isfinite(a)
    if not v.any():
        return out
    vals = a[v]
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25.0, 75.0])
    scale = max(float(q75 - q25) / 1.349, 1e-9)
    z = (a - med) / scale
    hi = float(np.percentile(z[v], pct))
    hi = max(hi, 1e-6)
    out[v] = np.clip(z[v] / hi, 0.0, 6.0) / 6.0
    return out


def straightness(gx: np.ndarray, gy: np.ndarray) -> np.ndarray:
    mag = np.hypot(gx, gy) + 1e-9
    nx, ny = gx / mag, gy / mag
    c = np.zeros_like(nx)
    s = np.zeros_like(nx)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            c += np.roll(np.roll(nx, dy, 0), dx, 1) * nx + np.roll(np.roll(ny, dy, 0), dx, 1) * ny
            s += 1.0
    return np.clip((c / s - 0.5) / 0.5, 0.0, 1.0)


def main() -> None:
    ddir = data_dir()
    with rasterio.open(ddir / "sample_submission.tif") as tpl:
        foot = np.isfinite(tpl.read(1)).astype(bool)
        template_grid = (tpl.crs, tpl.shape, tpl.transform)
    with rasterio.open(ddir / "training_features.tif") as ds:
        bands = ds.read().astype(np.float64)

    def band(i: int) -> np.ndarray:
        a = bands[i - 1]
        return np.where(foot & np.isfinite(a) & (a > -1e30), a, np.nan)

    with rasterio.open(ddir / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot
    with rasterio.open(ddir / "external/lidar_scarp_features_u8.tif") as ds:
        lidar1 = ds.read(1).astype(np.float64) / 255.0
    with rasterio.open(ddir / "external/geodawn_rad_u8.tif") as ds:
        tc = ds.read(1).astype(np.float64) / 255.0  # band 1 = K

    cond = band(17)
    dep = band(15)
    dil = band(8)
    tc6 = band(6)

    # Subsurface boundary strength: gradient of conductivity & basement depth.
    gc = np.hypot(*np.gradient(gaussian_filter(np.where(foot, cond, np.nan), 1.5)))
    gd = np.hypot(*np.gradient(gaussian_filter(np.where(foot, dep, np.nan), 1.5)))
    cond_g = robust_unit(gc, foot)
    dep_g = robust_unit(gd, foot)

    # Long-straight boundary: orientation coherence of conductivity gradient.
    gyc, gxc = np.gradient(gaussian_filter(np.where(foot, cond, np.nan), 1.5))
    straight_c = straightness(gxc, gyc)

    dil_n = robust_unit(dil, foot)
    tc_n = robust_unit(tc6, foot)
    lidar_n = robust_unit(lidar1, foot)

    # Novel multi-physics co-location score (no off-catalogue distance emphasis:
    # dots stay fault-proximal so withheld segments can be recovered).
    surf = cond_g * dep_g * straight_c * (0.3 + 0.7 * dil_n) * (0.3 + 0.7 * tc_n) * (0.3 + 0.7 * lidar_n)
    surf = np.where(foot, surf, 0.0)
    surf = np.nan_to_num(surf, nan=0.0, posinf=0.0, neginf=0.0)
    mx = float(surf.max())
    surf = (surf / (mx + 1e-12)).astype(np.float32)
    surf[~foot] = 0.0

    np.save(".cache/novel_surface.npy", surf)
    meta = {
        "hypothesis": "conductive-basement thermal-structural co-location within fault zone",
        "layers": ["cond_surf(17)", "depth_to_base_surf(15)", "geod_dilaterate(8)", "tc(6)", "lidar_scarp_ex_max"],
        "footprint_pixels": int(foot.sum()),
        "surface_max": float(surf.max()),
        "surface_mean": float(surf[foot].mean()),
        "template_grid": {"crs": str(template_grid[0]), "shape": template_grid[1], "transform": list(template_grid[2])},
    }
    Path(".cache/novel_surface_meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
