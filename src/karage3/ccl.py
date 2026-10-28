"""Catalogue-Completion Learner (CCL) — lane K3-CCL, GEMSDOEkarage3, 2026-10-28.

Hypothesis
----------
Uncatalogued faults are not independent of catalogued ones: they are the *missing pieces of
the same fault systems* — along-strike continuations beyond mapped tips, en-echelon / parallel
splays at a characteristic spacing, and linkage zones between overlapping tips.  A learner that
is shown the physics stack *together with the geometry of the visible catalogue* and is trained
on simulated incompleteness (whole catalogue components hidden, then asked to recover them)
learns that completion grammar directly, instead of learning "what a catalogued fault looks
like" (which pulls predictions back onto already-known faults, the one place the hidden test
set provably is not).

Everything catalogue-derived is computed from the *visible* catalogue of the scenario only.
Positives are whole hidden components outside the test quadrant's 15-px collar, so the
holdout's own withheld components are never seen in training (leak-free by construction).

This module reuses the shared stack (`gems32.features`, 35 channels) and the shared evaluator
(`gems32.holdout.evaluate_hide_and_recover`).  It contains no copy of any registry raster.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

STACK_CHANNELS = 34  # channels 0..33 of the shared stack; 34 = footprint (constant inside)
LIDAR_BANDS = {"ex_max": 1, "step_max": 3, "downface_max": 6, "coh100": 10, "lidar_valid": 12}
GEOM_NAMES = ["vis_logd", "vis_along_strike", "vis_strike_align", "vis_density_r20",
              "vis_tip_logd", "vis_dist_band"]


def catalogue_geometry(visible: np.ndarray, strike_cos2: np.ndarray, strike_sin2: np.ndarray) -> np.ndarray:
    """Per-pixel geometry of the *visible* catalogue, (H, W, 6) float32.

    vis_logd          log1p(distance to nearest visible fault pixel, px)
    vis_along_strike  cos 2(phi - strike_V): +1 when the pixel lies along strike of the nearest
                      visible fault (tip continuation), -1 when offset perpendicular (parallel splay)
    vis_strike_align  cos 2(theta_pix - theta_V): +1 when the local DEM fabric is parallel to the
                      nearest visible fault
    vis_density_r20   fraction of a 41x41 window that is visible catalogue (fault-system density)
    vis_tip_logd      log1p(distance to nearest visible-fault tip = skeleton endpoint)
    vis_dist_band     distance clipped to [0, 40] px (lets trees learn characteristic spacing)
    """
    v = np.asarray(visible, bool)
    h, w = v.shape
    out = np.zeros((h, w, len(GEOM_NAMES)), np.float32)
    if not v.any():
        out[..., 0] = np.log1p(999.0)
        out[..., 4] = np.log1p(999.0)
        out[..., 5] = 40.0
        return out
    d, (iy, ix) = ndimage.distance_transform_edt(~v, return_indices=True)
    out[..., 0] = np.log1p(d)
    # Orientation of visible traces from the structure tensor of the smoothed binary map;
    # same convention as gems32.features (theta = gradient orientation, doubled-angle encoding).
    vf = ndimage.gaussian_filter(v.astype(np.float32), 1.5)
    gx = ndimage.gaussian_filter(vf, 1.0, order=(0, 1))
    gy = ndimage.gaussian_filter(vf, 1.0, order=(1, 0))
    jxx = ndimage.gaussian_filter(gx * gx, 2.0)
    jyy = ndimage.gaussian_filter(gy * gy, 2.0)
    jxy = ndimage.gaussian_filter(gx * gy, 2.0)
    theta_g = 0.5 * np.arctan2(2 * jxy, (jxx - jyy) + 1e-12)
    th_v = theta_g[iy, ix]                      # gradient orientation at the nearest visible pixel
    yy, xx = np.indices((h, w), dtype=np.float32)
    phi = np.arctan2(iy - yy, ix - xx)          # direction to nearest visible pixel
    # strike = theta_g + pi/2  =>  cos 2(phi - strike) = -cos 2(phi - theta_g)
    along = -np.cos(2.0 * (phi - th_v))
    out[..., 1] = np.where(d > 0, along, 1.0)
    c2v, s2v = np.cos(2 * th_v), np.sin(2 * th_v)
    out[..., 2] = strike_cos2 * c2v + strike_sin2 * s2v
    out[..., 3] = ndimage.uniform_filter(v.astype(np.float32), size=41, mode="constant")
    # tips: catalogue pixels with exactly one 8-neighbour (catalogue rasters are ~1-px traces)
    nb = ndimage.convolve(v.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - v
    tips = v & (nb <= 1)
    if tips.any():
        out[..., 4] = np.log1p(ndimage.distance_transform_edt(~tips))
    else:
        out[..., 4] = np.log1p(999.0)
    out[..., 5] = np.minimum(d, 40.0)
    del d, iy, ix, yy, xx, phi, along
    return out


def gather(stack, lidar: np.ndarray, geom: np.ndarray | None, ys: np.ndarray, xs: np.ndarray) -> np.ndarray:
    """Feature rows for pixel coordinates (stack may be a memmap)."""
    parts = [np.asarray(stack[ys, xs, :STACK_CHANNELS], np.float32),
             lidar[:, ys, xs].T.astype(np.float32)]
    if geom is not None:
        parts.append(geom[ys, xs, :])
    return np.concatenate(parts, axis=1)


def feature_names(with_geom: bool, stack_names: list[str]) -> list[str]:
    names = list(stack_names[:STACK_CHANNELS]) + ["lidar_" + k for k in LIDAR_BANDS]
    return names + (GEOM_NAMES if with_geom else [])


def sample_training(rng, positives: np.ndarray, negatives_pool: np.ndarray, neg_ratio: int = 12,
                    max_pos: int = 40000):
    py, px = np.nonzero(positives)
    if py.size > max_pos:
        sel = rng.choice(py.size, max_pos, replace=False)
        py, px = py[sel], px[sel]
    ny, nx = np.nonzero(negatives_pool)
    k = min(ny.size, neg_ratio * py.size)
    sel = rng.choice(ny.size, k, replace=False)
    ys = np.concatenate([py, ny[sel]])
    xs = np.concatenate([px, nx[sel]])
    y = np.concatenate([np.ones(py.size, np.int8), np.zeros(k, np.int8)])
    return ys, xs, y


def fit(X: np.ndarray, y: np.ndarray, seed: int = 20261028):
    from sklearn.ensemble import HistGradientBoostingClassifier
    pos_w = float((y == 0).sum()) / max(float((y == 1).sum()), 1.0)
    sw = np.where(y == 1, pos_w, 1.0)
    m = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                       min_samples_leaf=80, l2_regularization=1.0,
                                       early_stopping=False, random_state=seed)
    m.fit(X, y, sample_weight=sw)
    return m


def predict_region(model, stack, lidar, geom, region: np.ndarray, chunk: int = 600_000) -> np.ndarray:
    out = np.zeros(region.shape, np.float32)
    ys, xs = np.nonzero(region)
    for i in range(0, ys.size, chunk):
        y, x = ys[i:i + chunk], xs[i:i + chunk]
        out[y, x] = model.predict_proba(gather(stack, lidar, geom, y, x))[:, 1].astype(np.float32)
    return out


def crest_mask(score: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Pixels that are local maxima of the smoothed score across the local ridge normal."""
    s = ndimage.gaussian_filter(score, sigma)
    sxx = ndimage.gaussian_filter(s, 1.0, order=(0, 2))
    syy = ndimage.gaussian_filter(s, 1.0, order=(2, 0))
    sxy = ndimage.gaussian_filter(s, 1.0, order=(1, 1))
    # eigenvector of the most negative Hessian eigenvalue = ridge normal
    ang = 0.5 * np.arctan2(2 * sxy, sxx - syy)
    l_a = sxx * np.cos(ang) ** 2 + 2 * sxy * np.sin(ang) * np.cos(ang) + syy * np.sin(ang) ** 2
    l_b = sxx * np.sin(ang) ** 2 - 2 * sxy * np.sin(ang) * np.cos(ang) + syy * np.cos(ang) ** 2
    nrm = np.where(l_a < l_b, ang, ang + np.pi / 2)
    dy = np.rint(np.sin(nrm)).astype(int)
    dx = np.rint(np.cos(nrm)).astype(int)
    h, w = s.shape
    yy, xx = np.indices((h, w))
    y1, x1 = np.clip(yy + dy, 0, h - 1), np.clip(xx + dx, 0, w - 1)
    y2, x2 = np.clip(yy - dy, 0, h - 1), np.clip(xx - dx, 0, w - 1)
    return (s >= s[y1, x1]) & (s >= s[y2, x2])


def _disk_offsets(r: float):
    k = int(np.ceil(r))
    oy, ox = np.mgrid[-k:k + 1, -k:k + 1]
    m = (oy ** 2 + ox ** 2) < r * r
    return oy[m], ox[m]


def greedy_dots(score: np.ndarray, allowed: np.ndarray, budget: int, min_sep: float = 2.8,
                crest: np.ndarray | None = None, quota: list[tuple[np.ndarray, int]] | None = None) -> np.ndarray:
    """Deterministic Poisson-disk greedy: highest score first, no two dots closer than min_sep px.

    If ``crest`` is given, crest pixels are offered first, then the rest (fill).  ``quota`` is an
    optional list of (zone_mask, max_dots) constraints (used only to stay out of another lane).
    """
    h, w = score.shape
    out = np.zeros((h, w), bool)
    blocked = ~allowed.copy()
    oy, ox = _disk_offsets(min_sep)
    passes = [allowed & crest, allowed & ~crest] if crest is not None else [allowed]
    used = [0] * (len(quota) if quota else 0)
    n = 0
    for region in passes:
        ys, xs = np.nonzero(region & (score > 0))
        order = np.argsort(-score[ys, xs], kind="stable")
        for i in order:
            y, x = int(ys[i]), int(xs[i])
            if blocked[y, x]:
                continue
            if quota:
                hit = [j for j, (zm, cap) in enumerate(quota) if zm[y, x]]
                if any(used[j] >= quota[j][1] for j in hit):
                    continue
                for j in hit:
                    used[j] += 1
            out[y, x] = True
            n += 1
            yy, xx = oy + y, ox + x
            ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
            blocked[yy[ok], xx[ok]] = True
            if n >= budget:
                return out
    return out
