"""ARENA48-H1-TMSPI — Thurston–Smith local-wavenumber + Wijns theta-map contact skeleton.

Lane (single method): unsupervised dual-field Source-Parameter Imaging (SPI) contact
skeleton. Miller–Singh TDR is computed only as the parent field of the local wavenumber;
TDR *zero-crossings* (H36-1) and Steger NMS (H36-1C) are not used.

Physical references (public, verified):
- Miller & Singh (1994) tilt angle TDR = arctan(VDR / HG).
- Wijns, Perez & Kowalczyk (2005) theta map θ = arccos(HG / AS).
  https://doi.org/10.1190/1.1883351
- Thurston & Smith (1997) local wavenumber / Source Parameter Imaging.
  k = |∇TDR|; contact depth z ≈ 1/k (Euler structural index N ≈ 0).
- Cooper & Cowan (2006) TDX is *not* the ranking field here (it was an H36 channel).

Catalogue rasters (labels.tif, existing_faults.tif, SGMC, Qfaults, dist_known_fault_px)
are never read by feature construction.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter

# Official 1-based band numbers in training_features.tif (prepared_manifest.json).
BAND_TMI_HG = 3
BAND_ISO_GRAV_SLOPE = 5
BAND_TMI_VG = 9
BAND_ISO_GRAV_VG = 11

# Basement-contact depth window (Great Basin range-front / buried intrabasin faults).
# 100 m pixels: 0.4 km = 4 px, 6.0 km = 60 px. Local wavenumber k = 1/z_px.
DEPTH_PX_LO = 4.0
DEPTH_PX_HI = 60.0
K_LO = 1.0 / DEPTH_PX_HI  # ~0.0167 /px
K_HI = 1.0 / DEPTH_PX_LO  # ~0.250 /px
EPS = 1e-8


def sanitize_band(raw: np.ndarray, footprint: np.ndarray, nodata: float = -3.4e38) -> np.ndarray:
    """Replace sentinel/non-finite cells with nearest valid neighbour inside the footprint."""
    from .features import _fill_nearest

    valid = np.isfinite(raw) & (raw > nodata * 0.5) & footprint
    filled, _ = _fill_nearest(raw, valid)
    return np.where(footprint, filled, np.float32(0.0)).astype(np.float32)


def analytic_signal(hg: np.ndarray, vg: np.ndarray) -> np.ndarray:
    return np.hypot(np.asarray(hg, np.float64), np.asarray(vg, np.float64))


def miller_singh_tdr(hg: np.ndarray, vg: np.ndarray) -> np.ndarray:
    """TDR ∈ (−π/2, π/2). Used only as the parent field of local wavenumber."""
    return np.arctan2(np.asarray(vg, np.float64), np.asarray(hg, np.float64) + EPS)


def wijns_theta_map(hg: np.ndarray, vg: np.ndarray) -> np.ndarray:
    """Wijns et al. (2005) θ = arccos(HG / AS) ∈ [0, π/2]. θ → 0 over contacts."""
    hg64 = np.asarray(hg, np.float64)
    asv = analytic_signal(hg, vg)
    ratio = np.clip(hg64 / (asv + EPS), 0.0, 1.0)
    return np.arccos(ratio)


def theta_edge_strength(hg: np.ndarray, vg: np.ndarray) -> np.ndarray:
    """Amplitude-independent contact strength = π/2 − θ ∈ [0, π/2]. Peaks on edges."""
    return (0.5 * np.pi) - wijns_theta_map(hg, vg)


def local_wavenumber(tdr: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Thurston–Smith local wavenumber k = |∇TDR| after light Gaussian pre-smooth."""
    t = gaussian_filter(np.asarray(tdr, np.float64), sigma=sigma, mode="nearest")
    gy, gx = np.gradient(t)
    return np.hypot(gx, gy)


def spi_contact_weight(k: np.ndarray) -> np.ndarray:
    """Soft window around Euler-N≈0 contacts in the 0.4–6 km depth band.

    Weight is 1 inside [k_lo, k_hi] and Gaussian-tapers outside so the transform
    stays continuous (needed for Spearman uniqueness on the pre-placement surface).
    """
    k = np.asarray(k, np.float64)
    logk = np.log(np.maximum(k, EPS))
    log_lo, log_hi = np.log(K_LO), np.log(K_HI)
    mid = 0.5 * (log_lo + log_hi)
    half = 0.5 * (log_hi - log_lo)
    # Raised-cosine window on log-k: 1 in-band, 0 far outside.
    t = (logk - mid) / (half + EPS)
    w = np.where(np.abs(t) <= 1.0, 0.5 * (1.0 + np.cos(np.pi * t)), 0.0)
    return w


def contact_field(hg: np.ndarray, vg: np.ndarray, footprint: np.ndarray, sigma: float = 1.0) -> dict[str, np.ndarray]:
    """Return named TM-SPI channels for one potential-field pair (HG, VG)."""
    tdr = miller_singh_tdr(hg, vg)
    k = local_wavenumber(tdr, sigma=sigma)
    theta_e = theta_edge_strength(hg, vg)
    spi_w = spi_contact_weight(k)
    belief = theta_e * spi_w
    belief = np.where(footprint, belief, 0.0)
    return {
        "tdr": tdr,
        "k": k,
        "theta_edge": theta_e,
        "spi_weight": spi_w,
        "belief": belief,
    }


def unit_stretch(field: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Stretch positive in-footprint values to [0, 1] using the 1st–99th percentile."""
    a = np.maximum(np.asarray(field, np.float64), 0.0)
    v = a[footprint & (a > 0)]
    if v.size == 0:
        return np.zeros_like(a)
    lo, hi = np.percentile(v, [1.0, 99.0])
    if hi <= lo:
        out = np.where(a > 0, 1.0, 0.0)
    else:
        out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    return np.where(footprint, out, 0.0)


def geometric_mean_concordance(mag_belief: np.ndarray, grav_belief: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Dual-field concordance: contacts that exist in BOTH magnetics and gravity.

    Each field is percentile-stretched to [0, 1], then a floored geometric mean
    ``sqrt((0.05+0.95 u_m)(0.05+0.95 u_g))`` is taken so a single-domain peak cannot
    outrank a dual-domain peak (ratio ~4.5×) while support is not annihilated when
    the two contact maps fail to overlap pixel-exactly. Unfaulted pluton walls
    (magnetic-only) and unfaulted basin-fill density contrasts (gravity-only) are
    therefore down-weighted, not hard-masked.
    """
    um = unit_stretch(mag_belief, footprint)
    ug = unit_stretch(grav_belief, footprint)
    out = np.sqrt((0.05 + 0.95 * um) * (0.05 + 0.95 * ug))
    # Floor is a ranking bias, not a dense prior: keep support = union of the two contacts.
    out = np.where((um > 0.0) | (ug > 0.0), out, 0.0)
    return np.where(footprint, out, 0.0)


def morphological_nms(field: np.ndarray, footprint: np.ndarray, size: int = 3) -> np.ndarray:
    """3×3 morphological non-maximum suppression. Not Steger (1998) eigenvector NMS."""
    f = np.asarray(field, np.float64)
    mx = maximum_filter(f, size=size, mode="nearest")
    keep = (f >= mx) & (f > 0.0) & footprint
    return np.where(keep, f, 0.0)


def percentile_support(field: np.ndarray, footprint: np.ndarray, q: float = 97.0) -> np.ndarray:
    """Zero below the in-footprint percentile so CELF support stays line-like."""
    f = np.asarray(field, np.float64)
    vals = f[footprint & (f > 0)]
    if vals.size == 0:
        return np.zeros_like(f)
    thr = float(np.percentile(vals, q))
    return np.where(footprint & (f >= thr), f, 0.0)


def build_experiment_fields(
    tmi_hg: np.ndarray,
    tmi_vg: np.ndarray,
    grav_hg: np.ndarray,
    grav_vg: np.ndarray,
    footprint: np.ndarray,
    nms_size: int = 3,
    support_percentile: float = 20.0,
) -> dict[str, np.ndarray]:
    """Build the three pre-registered experiment surfaces and CELF support fields.

    Morphological NMS is retained as a *diagnostic* 1-px crest, but CELF emission
    uses the percentile-thresholded continuous belief so the 37,654-dot budget is
    feasible (hard 3×3 NMS on the 96th percentile left < 2,100 pixels).
    """
    mag = contact_field(tmi_hg, tmi_vg, footprint)
    grav = contact_field(grav_hg, grav_vg, footprint)
    conc = geometric_mean_concordance(mag["belief"], grav["belief"], footprint)

    def _prep(belief: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        surface = np.where(footprint, belief, 0.0)
        support = percentile_support(surface, footprint, support_percentile)
        return surface, support

    mag_s, mag_n = _prep(mag["belief"])
    grav_s = np.where(footprint, grav["belief"], 0.0)
    # Gravity TDR is smoother, so the 0.4–6 km SPI window is ~1 Mpx. Keep the top
    # 8% so CELF support stays comparable to the magnetic arm (~90 kpx).
    grav_n = percentile_support(grav_s, footprint, 92.0)
    conc_s, conc_n = _prep(conc)
    # EXP3 keeps magnetic contact support (line-like SPI window) and re-ranks it by
    # dual-field concordance so gravity cannot inflate a basin-fill blob.
    conc_n = np.where(mag["belief"] > 0.0, conc_n, 0.0)
    return {
        "mag_surface": mag_s,
        "mag_support": mag_n,
        "grav_surface": grav_s,
        "grav_support": grav_n,
        "concordance_surface": conc_s,
        "concordance_support": conc_n,
        "mag_theta_edge": mag["theta_edge"],
        "mag_k": mag["k"],
        "mag_spi_weight": mag["spi_weight"],
        "grav_theta_edge": grav["theta_edge"],
        "grav_k": grav["k"],
        "grav_spi_weight": grav["spi_weight"],
        "mag_belief": mag["belief"],
        "grav_belief": grav["belief"],
        "concordance": conc,
    }


CHANNEL_CANARY_KEYS = (
    "mag_theta_edge",
    "mag_k",
    "mag_spi_weight",
    "mag_belief",
    "grav_theta_edge",
    "grav_k",
    "grav_spi_weight",
    "grav_belief",
    "concordance",
)


def leakage_canary_aucs(
    channels: dict[str, np.ndarray],
    positives: np.ndarray,
    footprint: np.ndarray,
    max_neg: int = 200_000,
    seed: int = 50,
) -> dict[str, float]:
    """Single-feature ROC-AUC of each TM-SPI channel vs a binary truth mask.

    Negatives are a seeded subsample of footprint \\ positives. AUC > 0.90 is the
    protocol leakage canary (Rule 4). Sampling negatives does not touch the uniqueness
    Spearman test (which remains full-footprint).
    """
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
        arr = np.asarray(channels[name], np.float64)
        x = np.concatenate([arr[py, px], arr[ny, nx]])
        if not np.isfinite(x).all():
            raise ValueError(f"non-finite canary channel {name}")
        if np.ptp(x) <= 0:
            out[name] = 0.5
            continue
        auc = float(roc_auc_score(y, x))
        out[name] = max(auc, 1.0 - auc)  # two-polarity
    return out
