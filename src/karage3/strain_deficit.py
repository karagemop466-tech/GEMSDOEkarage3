"""Lane H-K3C-1 — Kostrov strain-deficit regional prior (holdout-legal).

Mechanism (Kostrov 1974 moment balance): the geodetic strain-rate tensor integrated over a volume must be
accommodated by slip on faults inside it.  Where the measured strain-rate second invariant is high but the
*visible* catalogue carries little fault length, unmapped structures must take up the deficit.  The prior is a
smooth, bounded multiplier on an existing detector surface; it re-allocates dot budget regionally and never
creates crests on its own.

Every catalogue-derived quantity is computed from the fold-visible catalogue passed in, never from hidden faults.
Official layer used: ``training_features.tif`` Band 04 ``geod_2ndinv`` (base feature-stack channel index 3,
verified in ``data/prepared_manifest.json``).
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.stats import rankdata

BAND04_GEOD_2NDINV_COL = 3      # zero-based channel of Band 04 in .cache/gems_work/feature_stack.npy
SIGMA_PX = 100                  # 10 km Gaussian window for visible catalogue density
GAMMA = 0.5                     # prior exponent (preregistered)
CLIP = (0.5, 2.0)               # bounded multiplier (preregistered)
DENSITY_FLOOR = 0.25            # c in S / (D + c); avoids division blow-up in catalogue-empty basins

__all__ = ["strain_deficit_prior", "BAND04_GEOD_2NDINV_COL", "SIGMA_PX", "GAMMA", "CLIP", "DENSITY_FLOOR"]


def _rank01(values: np.ndarray) -> np.ndarray:
    r = rankdata(values, method="average").astype(np.float64)
    n = float(values.size)
    return ((r - 1.0) / max(n - 1.0, 1.0)).astype(np.float32)


def strain_deficit_prior(
    base_stack: np.ndarray,
    visible_mask: np.ndarray,
    foot: np.ndarray,
    sigma_px: float = SIGMA_PX,
    gamma: float = GAMMA,
    clip: tuple[float, float] = CLIP,
    density_floor: float = DENSITY_FLOOR,
    return_parts: bool = False,
):
    """Return a float32 multiplier in ``[clip[0], clip[1]]`` (1.0 outside the footprint).

    ``S`` = footprint rank of Band 04 ``geod_2ndinv`` in [0, 1];
    ``D`` = 10-km Gaussian density of the *visible* catalogue, normalised to footprint mean 1;
    ``ratio = S / (D + c)``; ``prior = clip((ratio / median_footprint(ratio)) ** gamma, clip)``.
    """
    foot = np.asarray(foot, bool)
    vis = np.asarray(visible_mask, bool) & foot
    strain = np.asarray(base_stack[:, :, BAND04_GEOD_2NDINV_COL], dtype=np.float32)

    s01 = np.zeros(foot.shape, dtype=np.float32)
    s01[foot] = _rank01(strain[foot])

    dens = gaussian_filter(vis.astype(np.float32), sigma=float(sigma_px), mode="constant", cval=0.0)
    # Normalise by the footprint mean density so the floor `c` is dimensionless.
    mean_d = float(dens[foot].mean())
    d_norm = dens / max(mean_d, 1e-12)
    del dens

    ratio = np.zeros(foot.shape, dtype=np.float32)
    ratio[foot] = s01[foot] / (d_norm[foot] + np.float32(density_floor))
    med = float(np.median(ratio[foot]))
    prior = np.ones(foot.shape, dtype=np.float32)
    prior[foot] = np.clip(np.power(ratio[foot] / max(med, 1e-12), np.float32(gamma)), clip[0], clip[1])
    if return_parts:
        return prior, {"strain_rank01": s01, "visible_density_norm": d_norm.astype(np.float32), "ratio": ratio, "median_ratio": med}
    return prior
