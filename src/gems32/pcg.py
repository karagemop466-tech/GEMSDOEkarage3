"""ARENA49-H1-PCG — Kovesi log-Gabor phase-congruency (PC) step/line skeleton.

Lane (single method): amplitude-invariant phase-congruency edge detection on
Band 12 ``det_elev`` and Band 13 ``iso_grav_anom``, dual-field concordance.

Physical references (public, verified in the pre-registration):
- Kovesi, P. (1999). Image Features From Phase Congruency. Videre 1(3).
  https://www.peterkovesi.com/papers/Kovesi_Videre_v1n3001.pdf
  Step edges, lines and Mach bands occur where Fourier components are maximally
  in phase.  PC is dimensionless and invariant to overall amplitude/contrast,
  unlike gradient, Hessian, tilt or local-wavenumber magnitudes, all of which
  scale with the (unknown) throw/density contrast of the fault.
- Monogenic/PC lineament mapping of magnetic data, GeoConvention 2016:
  https://geoconvention.com/wp-content/uploads/abstracts/2016/147_GC2016_Monogenic_Phase_Congruency.pdf

Declared simplifications relative to Kovesi's full algorithm (frozen in
``docs/research/arena49-pc-preregistration-20261026.md`` before fitting):
- frequency-spread weighting W_o uses the amplitude-spread statistic
  s = (sumAn / maxAn - 1) / (nscale - 1) in [0, 1] with a sigmoid
  (cutoff 0.5, gain 10), instead of Kovesi's exact spread estimator.  Without
  this weighting a point where a single scale dominates (e.g. far from an
  edge, where only the largest wavelength responds) spuriously scores PC ~ 1;
  the synthetic step test in ``tests/test_pcg.py`` pins this behaviour;
- noise floor T_o = 2 * median(|EO| at the smallest scale) per orientation,
  in place of the full Rayleigh-distribution estimate;
- PC is computed on the nearest-neighbour-filled full grid and masked to the
  footprint afterwards, so the irregular footprint boundary is not a step edge.

Catalogue rasters are never read by feature construction.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_erosion, maximum_filter

# Official 1-based band numbers in training_features.tif (prepared_manifest.json).
BAND_DET_ELEV = 12
BAND_ISO_GRAV_ANOM = 13

NSCALE = 4
NORIENT = 6
MIN_WAVELENGTH = 3.0
MULT = 2.0
SIGMA_ONF = 0.55
NOISE_K = 2.0
EPS = 1e-12

CHANNEL_CANARY_KEYS = (
    "pc_dem",
    "pc_grav",
    "concordance",
    "pc_dem_max_orient",
    "pc_grav_max_orient",
)


def phase_congruency(
    field: np.ndarray,
    footprint: np.ndarray,
    nscale: int = NSCALE,
    norient: int = NORIENT,
    min_wavelength: float = MIN_WAVELENGTH,
    mult: float = MULT,
    sigma_onf: float = SIGMA_ONF,
    noise_k: float = NOISE_K,
) -> dict[str, np.ndarray]:
    """Kovesi-style log-Gabor phase congruency of one scalar field.

    Returns ``pc`` in [0, 1] (masked to ``footprint``), the strongest single
    orientation ``pc_max_orient`` in [0, 1], and the summed log-Gabor amplitude
    ``amplitude_sum`` (>= 0).  A constant field returns PC == 0 everywhere.
    """
    f = np.asarray(field, dtype=np.float64)
    foot = np.asarray(footprint, bool)
    if f.shape != foot.shape:
        raise ValueError(f"field shape {f.shape} != footprint shape {foot.shape}")
    out_pc = np.zeros(f.shape, dtype=np.float64)
    out_max = np.zeros(f.shape, dtype=np.float64)
    out_amp = np.zeros(f.shape, dtype=np.float64)
    if not foot.any() or float(np.ptp(f[foot])) == 0.0:
        return {"pc": out_pc, "pc_max_orient": out_max, "amplitude_sum": out_amp}

    work = f.copy()
    work[foot] -= float(work[foot].mean())

    h, w = f.shape
    spectrum = np.fft.fft2(work)
    del work

    # Frequency grids (cycles/px).
    fy = np.fft.fftfreq(h).astype(np.float64)[:, None]
    fx = np.fft.fftfreq(w).astype(np.float64)[None, :]
    radius = np.sqrt(fy * fy + fx * fx)  # broadcast (h, w)
    theta = np.arctan2(fy * np.ones_like(radius), fx * np.ones_like(radius))

    # Butterworth low-pass (order 15, cutoff 0.45) as in Kovesi's implementation,
    # suppressing the very highest frequencies / ringing.
    lowpass = 1.0 / (1.0 + (radius / 0.45) ** (2 * 15))
    lowpass[0, 0] = 0.0

    log_sigma = np.log(sigma_onf)
    theta_sigma = np.pi / norient / 1.2

    total_num = np.zeros(f.shape, dtype=np.float64)
    total_den = np.zeros(f.shape, dtype=np.float64)

    for o in range(norient):
        orient = o * np.pi / norient
        # Angular Gaussian spread (one-sided wedge -> quadrature response).
        dtheta = np.abs(np.mod(theta - orient + np.pi, 2.0 * np.pi) - np.pi)
        # sin/cos form keeps the spread smooth across the -pi/pi seam.
        spread = np.exp(-(dtheta ** 2) / (2.0 * theta_sigma ** 2))
        del dtheta

        sum_e = np.zeros(f.shape, dtype=np.float64)
        sum_o = np.zeros(f.shape, dtype=np.float64)
        sum_an = np.zeros(f.shape, dtype=np.float64)
        max_an = np.zeros(f.shape, dtype=np.float64)
        noise_floor = 0.0
        for n in range(nscale):
            wavelength = min_wavelength * (mult ** n)
            fo = 1.0 / wavelength
            with np.errstate(divide="ignore", invalid="ignore"):
                log_gabor = np.exp(
                    -((np.log(radius / fo)) ** 2) / (2.0 * log_sigma ** 2)
                )
            log_gabor[0, 0] = 0.0
            filt = log_gabor * spread * lowpass
            del log_gabor
            eo = np.fft.ifft2(spectrum * filt)
            del filt
            an = np.abs(eo)
            if n == 0:
                noise_floor = noise_k * float(np.median(an[foot])) if foot.any() else 0.0
            sum_e += eo.real
            sum_o += eo.imag
            sum_an += an
            max_an = np.maximum(max_an, an)
            del eo, an

        energy = np.sqrt(sum_e * sum_e + sum_o * sum_o)
        del sum_e, sum_o
        # Frequency-spread weighting: s ~ 1 when all scales respond comparably
        # (a true feature), s ~ 0 when one scale dominates (non-feature).
        if nscale > 1:
            spread_s = (sum_an / (max_an + EPS) - 1.0) / (nscale - 1)
        else:
            spread_s = np.ones_like(sum_an)
        del max_an
        weight = 1.0 / (1.0 + np.exp((0.5 - np.clip(spread_s, 0.0, 1.0)) * 10.0))
        del spread_s
        pc_o = weight * np.maximum(energy - noise_floor, 0.0) / (sum_an + EPS)
        total_num += weight * np.maximum(energy - noise_floor, 0.0)
        total_den += sum_an
        del weight
        out_max = np.maximum(out_max, pc_o)
        out_amp += sum_an
        del energy, pc_o, sum_an, spread

    del spectrum, radius, theta, lowpass
    pc = total_num / (total_den + EPS)
    pc = np.clip(pc, 0.0, 1.0)
    out_pc = np.where(foot, pc, 0.0)
    out_max = np.clip(np.where(foot, out_max, 0.0), 0.0, 1.0)
    out_amp = np.where(foot, out_amp, 0.0)
    return {"pc": out_pc, "pc_max_orient": out_max, "amplitude_sum": out_amp}


def unit_stretch(field: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Percentile-stretch positive in-footprint values to [0, 1] (as tmspi)."""
    a = np.maximum(np.asarray(field, dtype=np.float64), 0.0)
    v = a[footprint & (a > 0)]
    if v.size == 0:
        return np.zeros_like(a)
    lo, hi = np.percentile(v, [1.0, 99.0])
    if hi <= lo:
        out = np.where(a > 0, 1.0, 0.0)
    else:
        out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    return np.where(footprint, out, 0.0)


def geometric_mean_concordance(
    dem_pc: np.ndarray, grav_pc: np.ndarray, footprint: np.ndarray
) -> np.ndarray:
    """Floored geometric mean of the two stretched PC fields.

    A single-domain peak (DEM-only shoreline bench, gravity-only basin-fill
    contact) cannot outrank a dual-domain peak (ratio ~4.5x), while support is
    the union of the two fields so a contact visible in only one field at PC
    level is down-weighted, not hard-masked.
    """
    ud = unit_stretch(dem_pc, footprint)
    ug = unit_stretch(grav_pc, footprint)
    out = np.sqrt((0.05 + 0.95 * ud) * (0.05 + 0.95 * ug))
    out = np.where((ud > 0.0) | (ug > 0.0), out, 0.0)
    return np.where(footprint, out, 0.0)


def percentile_support(
    field: np.ndarray, support_domain: np.ndarray, q: float = 90.0
) -> np.ndarray:
    """Zero below the q-th percentile of positive values in the support domain."""
    f = np.asarray(field, dtype=np.float64)
    vals = f[support_domain & (f > 0)]
    if vals.size == 0:
        return np.zeros_like(f)
    thr = float(np.percentile(vals, q))
    return np.where(support_domain & (f >= thr), f, 0.0)


def eroded_domain(footprint: np.ndarray, px: int = 3) -> np.ndarray:
    """Footprint eroded by ``px`` so footprint-boundary steps cannot emit."""
    if px <= 0:
        return np.asarray(footprint, bool)
    return binary_erosion(np.asarray(footprint, bool), iterations=px)


def morphological_nms(field: np.ndarray, footprint: np.ndarray, size: int = 3) -> np.ndarray:
    f = np.asarray(field, dtype=np.float64)
    mx = maximum_filter(f, size=size, mode="nearest")
    keep = (f >= mx) & (f > 0.0) & footprint
    return np.where(keep, f, 0.0)


def build_experiment_fields(
    det_elev: np.ndarray,
    iso_grav_anom: np.ndarray,
    footprint: np.ndarray,
    support_percentile: float = 90.0,
) -> dict[str, np.ndarray]:
    """Build the three pre-registered ARENA49 experiment surfaces/supports."""
    domain = eroded_domain(footprint, 3)
    dem = phase_congruency(det_elev, footprint)
    grav = phase_congruency(iso_grav_anom, footprint)
    conc = geometric_mean_concordance(dem["pc"], grav["pc"], footprint)

    dem_support = percentile_support(dem["pc"], domain, support_percentile)
    grav_support = percentile_support(grav["pc"], domain, support_percentile)
    # EXP3 keeps the DEM-PC (line-like step) support and re-ranks it by the
    # dual-field concordance, so gravity cannot inflate a basin-fill blob.
    conc_support = np.where(dem_support > 0.0, conc, 0.0)
    conc_support = np.where(domain, conc_support, 0.0)

    return {
        "dem_surface": np.where(footprint, dem["pc"], 0.0),
        "dem_support": dem_support,
        "grav_surface": np.where(footprint, grav["pc"], 0.0),
        "grav_support": grav_support,
        "concordance_surface": np.where(footprint, conc, 0.0),
        "concordance_support": conc_support,
        "pc_dem": dem["pc"],
        "pc_grav": grav["pc"],
        "concordance": conc,
        "pc_dem_max_orient": dem["pc_max_orient"],
        "pc_grav_max_orient": grav["pc_max_orient"],
        "support_domain": domain,
    }


def leakage_canary_aucs(
    channels: dict[str, np.ndarray],
    positives: np.ndarray,
    footprint: np.ndarray,
    max_neg: int = 200_000,
    seed: int = 49,
) -> dict[str, float]:
    """Single-feature two-polarity ROC-AUC per PC channel (Protocol Rule 4)."""
    from sklearn.metrics import roc_auc_score

    pos = np.asarray(positives, bool) & footprint
    rng = np.random.default_rng(seed)
    py, px = np.nonzero(pos)
    ny, nx = np.nonzero(footprint & ~pos)
    if py.size == 0 or ny.size == 0:
        raise ValueError("canary requires both positives and negatives inside the footprint")
    if ny.size > max_neg:
        pick = rng.choice(ny.size, size=max_neg, replace=False)
        ny, nx = ny[pick], nx[pick]
    y = np.concatenate([np.ones(py.size, np.int8), np.zeros(ny.size, np.int8)])
    out: dict[str, float] = {}
    for name in CHANNEL_CANARY_KEYS:
        arr = np.asarray(channels[name], dtype=np.float64)
        x = np.concatenate([arr[py, px], arr[ny, nx]])
        if not np.isfinite(x).all():
            raise ValueError(f"non-finite canary channel {name}")
        if np.ptp(x) <= 0:
            out[name] = 0.5
            continue
        auc = float(roc_auc_score(y, x))
        out[name] = max(auc, 1.0 - auc)  # two-polarity
    return out
