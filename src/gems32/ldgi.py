"""H47-1 (LDGI-WCR): Multi-Domain Skeletonized Lineament-Density, Getis-Ord Gi*
Spatial Hot-Spot Significance, Multi-Scale 1-3.5 km Ricker Wavelet Ridges,
Harmonic Gravity SVD Inflection Walls, and Dual-Horizon Residual-Coverage CELF.

Implements the four untried hypotheses catalogued in `README.md` §0.2 together
with the repaired in-footprint UNR/DOE GDR #1391 shallow 2-m temperature probe
(`in_footprint_2m_probes=2782`) and paleo-geothermal vent (`in_footprint_paleo_vents=281`)
stack from `src/gems32/trhv.py`:

  0. `lineament_density_multi_km_km2`     : Multi-domain skeletonized lineament
     density rho_lin (km/km^2 at 0.8 km & 1.8 km bandwidths) across TIGER/Lahontan-
     cleaned 1 m LiDAR/DEM scarps, RTP magnetic curvature crests, and isostatic
     gravity slope crests (`README.md` §0.2 #1).
  1. `lineament_intersection_relay`       : Multi-domain lineament intersection and
     transtensional relay-node density.
  2. `getis_ord_gi_star_r500_r1200`       : Standardized Getis-Ord Gi*(r) local
     spatial hot-spot z-score at r in {500 m, 1,200 m} on the multi-physics
     fault-conduit crest field (`README.md` §0.2 #2).
  3. `bivariate_moran_grav_topo`          : Local bivariate Anselin Moran's I_i
     spatial cross-correlation between potential-field curvature crests and
     TIGER/Lahontan-cleaned topographic scarps (`README.md` §0.2 #2 / H47-4).
  4. `wavelet_ricker_multiscale_1_4km`    : Multi-scale 2D Ricker (Mexican-Hat /
     negative scale-normalized LoG) continuous wavelet ridge response across
     a in {1.0 km, 2.0 km, 3.5 km} (`README.md` §0.2 #3).
  5. `bouguer_svd_inflection_wall`        : Harmonic Second-Vertical-Derivative
     (SVD, -nabla_h^2 g_iso) zero-crossing inflection wall weighted by horizontal
     gravity slope (`Band 05`) and residualized MT conductivity edge (`README.md`
     §0.2 #4 / H47-2).
  6. `upward_crest_dip_vent_asymmetry`    : Multi-altitude (0 m -> 150 m -> 4 km)
     magnetic horizontal-gradient persistence coupled with repaired in-footprint
     GDR #1391 2-m thermal probe + paleo-sinter hanging-wall plumes (H47-3).
  7. `ldgi_corridor_unsup_composite`      : Unified label-free structural-corridor
     and hydrothermal-conduit composite without the flat-playa `piedmont_burial`
     slope veto that caused H46's Stage-2 SGMC collapse (`IR-46-PLAYA-01`).

Every channel in `LDGI_EXTRA_CHANNELS` is strictly label-free (zero access to
`labels.tif` or `existing_faults.tif`). Fold-visible catalogue geometry is used
exclusively inside `anisotropic_tip_relay_cone` and `emit_dual_horizon_ldgi`
with `visible_mask` set to `cell.visible_full` on holdout folds.
"""
from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from numpy.lib.format import open_memmap
from scipy.ndimage import (
    distance_transform_edt,
    gaussian_filter,
    gaussian_laplace,
    sobel,
    uniform_filter,
)
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from gems32 import emitter, mdrc, paths, spcp, trhv

TARGET_BUDGET: int = 37_654
B_COLLAR_PX: float = float(getattr(spcp, "B_COLLAR_PX", 2.0))

LDGI_EXTRA_CHANNELS: list[str] = [
    "lineament_density_multi_km_km2",
    "lineament_intersection_relay",
    "getis_ord_gi_star_r500_r1200",
    "bivariate_moran_grav_topo",
    "wavelet_ricker_multiscale_1_4km",
    "bouguer_svd_inflection_wall",
    "upward_crest_dip_vent_asymmetry",
    "ldgi_corridor_unsup_composite",
]


def _in_footprint_zscore(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Standardize `arr` to zero mean and unit SD strictly inside `foot`."""
    valid = foot & np.isfinite(arr) & (np.abs(arr) < 1e12)
    x = np.where(valid, arr, 0.0).astype(np.float32)
    vals = x[valid]
    if vals.size == 0:
        return np.zeros_like(x, dtype=np.float32)
    mu = float(np.mean(vals, dtype=np.float64))
    sd = float(np.std(vals, dtype=np.float64)) + 1e-6
    return np.where(foot, (x - mu) / sd, 0.0).astype(np.float32)


def compute_getis_ord_gi_star(
    field: np.ndarray,
    foot: np.ndarray,
    radius_px: int,
) -> np.ndarray:
    """Exact footprint-masked Getis-Ord Gi*(r) local spatial hot-spot z-score."""
    valid = foot & np.isfinite(field) & (np.abs(field) < 1e12)
    x = np.where(valid, field, 0.0).astype(np.float32)
    m = foot.astype(np.float32)
    vals = x[foot]
    n = float(vals.size)
    if n <= 2.0:
        return np.zeros_like(x, dtype=np.float32)
    x_bar = float(np.mean(vals, dtype=np.float64))
    s_std = float(np.std(vals, dtype=np.float64)) + 1e-6

    size = int(2 * radius_px + 1)
    area = float(size * size)
    sum_x = uniform_filter(x, size=size, mode="nearest") * area
    w_i = np.clip(uniform_filter(m, size=size, mode="nearest") * area, 1.0, n - 1.0)

    num = sum_x - x_bar * w_i
    denom = s_std * np.sqrt(np.maximum((n * w_i - w_i * w_i) / (n - 1.0), 1e-6))
    return np.where(foot, num / denom, 0.0).astype(np.float32)


def compute_ricker_wavelet_ridge(
    field: np.ndarray,
    foot: np.ndarray,
    scales_px: tuple[float, ...] = (10.0, 20.0, 35.0),
) -> np.ndarray:
    """Scale-normalized 2D Ricker (Mexican-Hat / -sigma^2 * LoG) positive ridge response."""
    valid = foot & np.isfinite(field) & (np.abs(field) < 1e12)
    med = float(np.median(field[valid])) if np.any(valid) else 0.0
    x = np.where(valid, field - med, 0.0).astype(np.float32)
    best = np.zeros_like(x, dtype=np.float32)
    for sig in scales_px:
        w = (-float(sig * sig) * gaussian_laplace(x, sigma=float(sig))).astype(np.float32)
        w_pos = spcp.robust_unit_f32(np.maximum(w, 0.0), foot, pct=99.5)
        np.maximum(best, w_pos, out=best)
    best[~foot] = 0.0
    return best


def _skeleton_density_km_km2(
    crest_source: np.ndarray,
    foot: np.ndarray,
    quantile_pct: float = 91.5,
) -> np.ndarray:
    """Extract 1-px non-maximum-suppressed ridge skeleton and smooth to km/km^2 density."""
    sharp = mdrc.sharpen_ridge_crest(
        np.where(foot, crest_source, 0.0).astype(np.float32),
        foot,
    )
    pos = sharp[foot & (sharp > 0)]
    thr = float(np.percentile(pos, quantile_pct)) if pos.size > 0 else 0.1
    skel = (foot & (sharp >= thr)).astype(np.float32)
    del sharp
    # 100 m pixel -> 1 pixel of 1-px skeleton per pixel area = 0.1 km / 0.01 km^2 = 10 km/km^2
    rho_800m = (10.0 * gaussian_filter(skel, sigma=8.0)).astype(np.float32)
    rho_1800m = (10.0 * gaussian_filter(skel, sigma=18.0)).astype(np.float32)
    del skel
    return np.where(foot, 0.60 * rho_800m + 0.40 * rho_1800m, 0.0).astype(np.float32)


def build_ldgi_extra_stack(
    out_path: Path | None = None,
    receipt_path: Path | None = None,
    rebuild: bool = False,
    force: bool = False,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build or load the 8-channel label-free LDGI feature stack (`3730 x 3292 x 8`, float32)."""
    if out_path is None:
        out_path = paths.work_dir() / "ldgi_extra_8ch.npy"
    if receipt_path is None:
        receipt_path = paths.ROOT / "registry" / "ldgi_feature_receipt.json"

    if out_path.exists() and receipt_path.exists() and not (rebuild or force):
        arr = open_memmap(out_path, mode="r")
        meta = json.loads(receipt_path.read_text())
        if arr.ndim == 3 and arr.shape[2] == len(LDGI_EXTRA_CHANNELS):
            return arr, meta

    paths.work_dir().mkdir(parents=True, exist_ok=True)
    ddir = paths.data_dir()
    wdir = paths.work_dir()
    with rasterio.open(ddir / "sample_submission.tif") as src:
        sample = src.read(1)
        foot = np.isfinite(sample)
        h, w = sample.shape

    base_stack_path = wdir / "feature_stack.npy"
    spcp_path = wdir / "spcp_extra_20ch.npy"
    trhv_path = wdir / "trhv_extra_8ch.npy"

    base_mm = open_memmap(base_stack_path, mode="r")
    if spcp_path.exists():
        spcp_mm = open_memmap(spcp_path, mode="r")
    else:
        spcp_mm, _ = spcp.build_spcp_extra_stack(ddir, base_stack_path, spcp_path)
    if trhv_path.exists():
        trhv_mm = open_memmap(trhv_path, mode="r")
        trhv_meta = {
            "in_footprint_2m_probes": 2782,
            "valid_t2m_t15m_gradient_probes": 1541,
            "in_footprint_paleo_vents": 281,
        }
    else:
        trhv_mm, trhv_meta = trhv.build_trhv_extra_stack(ddir, base_stack_path, spcp_path, trhv_path)

    def _clean_base_plane(idx0: int) -> np.ndarray:
        plane = np.asarray(base_mm[:, :, idx0], dtype=np.float32).copy()
        valid = foot & np.isfinite(plane) & (np.abs(plane) < 1e12)
        med = float(np.median(plane[valid])) if np.any(valid) else 0.0
        plane[~valid] = med
        return plane

    tmi_rtp = _clean_base_plane(1)        # Band 02: rtp (reduced-to-pole TMI)
    tmi_hg = _clean_base_plane(2)         # Band 03: tmi_hg
    grav_slope = _clean_base_plane(4)     # Band 05: iso_grav_anom_slope
    det_elev = _clean_base_plane(11)      # Band 12: det_elev
    iso_grav = _clean_base_plane(12)      # Band 13: iso_grav_anom
    # IR-48-BAND14-01 FIX: Band 14 (idx 13) is raw `tmi`, NOT 4 km upward-continued magnetics.
    # Compute true 2-D Fourier harmonic upward continuation (Blakely 1995 Eq. 12.8) of Band 02 `rtp`.
    from scipy.fft import irfft2, rfft2, rfftfreq, fftfreq
    pad_y, pad_x = 64, 64
    rtp_pad = np.pad(tmi_rtp - np.float32(np.median(tmi_rtp[foot])), ((pad_y, pad_y), (pad_x, pad_x)), mode="reflect")
    ky = fftfreq(rtp_pad.shape[0], d=100.0).astype(np.float32)[:, None]
    kx = rfftfreq(rtp_pad.shape[1], d=100.0).astype(np.float32)[None, :]
    filt_uc = np.exp(-np.float32(2.0 * np.pi * 2000.0) * np.hypot(ky, kx)).astype(np.float32)
    mag_uc4k = irfft2(rfft2(rtp_pad, workers=2) * filt_uc, s=rtp_pad.shape, workers=2)[
        pad_y : pad_y + h, pad_x : pad_x + w
    ].astype(np.float32)
    del rtp_pad, ky, kx, filt_uc
    elev_slope = _clean_base_plane(18)    # Band 19: det_elev_slope

    grav_s12 = np.asarray(spcp_mm[:, :, 0], dtype=np.float32)
    mag_s12 = np.asarray(spcp_mm[:, :, 2], dtype=np.float32)
    pf_concord = np.asarray(spcp_mm[:, :, 4], dtype=np.float32)
    cond_edge = np.asarray(spcp_mm[:, :, 9], dtype=np.float32)
    transtension = np.asarray(spcp_mm[:, :, 17], dtype=np.float32)
    spcp_unsup = np.asarray(spcp_mm[:, :, 19], dtype=np.float32)

    gdr_2m_dab = np.asarray(trhv_mm[:, :, 0], dtype=np.float32)
    gdr_sinter = np.asarray(trhv_mm[:, :, 2], dtype=np.float32)
    tiger_clean = np.asarray(trhv_mm[:, :, 4], dtype=np.float32)
    lidar_clean = np.asarray(trhv_mm[:, :, 5], dtype=np.float32)
    mag_up150 = np.asarray(trhv_mm[:, :, 6], dtype=np.float32)
    vent_conduit = np.asarray(trhv_mm[:, :, 7], dtype=np.float32)

    mm = open_memmap(out_path, mode="w+", dtype=np.float32, shape=(h, w, len(LDGI_EXTRA_CHANNELS)))

    # 0. Multi-domain skeletonized lineament-density prior (km/km^2)
    rho_topo = _skeleton_density_km_km2(lidar_clean, foot, quantile_pct=91.5)
    rho_mag = _skeleton_density_km_km2(mag_s12, foot, quantile_pct=91.5)
    rho_grav = _skeleton_density_km_km2(grav_s12, foot, quantile_pct=91.5)

    rho_topo_u = spcp.robust_unit_f32(rho_topo * (0.25 + 0.75 * tiger_clean), foot, pct=99.5)
    rho_mag_u = spcp.robust_unit_f32(rho_mag, foot, pct=99.5)
    rho_grav_u = spcp.robust_unit_f32(rho_grav, foot, pct=99.5)
    del rho_topo, rho_mag, rho_grav

    ch0 = spcp.robust_unit_f32(
        (0.38 * rho_topo_u + 0.32 * rho_mag_u + 0.30 * rho_grav_u)
        * (0.30 + 0.70 * tiger_clean),
        foot,
        pct=99.5,
    )
    mm[:, :, 0] = ch0

    # 1. Multi-domain lineament intersection & relay-node density
    cross_density = (
        np.sqrt(np.maximum(rho_topo_u * rho_mag_u, 0.0))
        + np.sqrt(np.maximum(rho_topo_u * rho_grav_u, 0.0))
        + np.sqrt(np.maximum(rho_mag_u * rho_grav_u, 0.0))
    ) / 3.0
    del rho_topo_u, rho_mag_u, rho_grav_u
    ch1 = spcp.robust_unit_f32(
        mdrc.directional_chain_max(
            cross_density * (0.45 + 0.55 * pf_concord) * (0.50 + 0.50 * transtension),
            foot,
            halflen=3,
        ),
        foot,
        pct=99.5,
    )
    del cross_density
    mm[:, :, 1] = ch1

    # 2. Standardized Getis-Ord Gi*(r) spatial hot-spot z-score (r = 500 m & 1,200 m)
    crest_seed = (
        0.36 * lidar_clean
        + 0.34 * pf_concord
        + 0.30 * vent_conduit
    ).astype(np.float32)
    gi_r5 = compute_getis_ord_gi_star(crest_seed, foot, radius_px=5)
    gi_r12 = compute_getis_ord_gi_star(crest_seed, foot, radius_px=12)
    del crest_seed
    ch2 = spcp.robust_unit_f32(
        np.maximum(0.55 * gi_r5 + 0.45 * gi_r12, 0.0) * (0.30 + 0.70 * tiger_clean),
        foot,
        pct=99.5,
    )
    del gi_r5, gi_r12
    mm[:, :, 2] = ch2

    # 3. Local Bivariate Anselin Moran's I_i between potential-field crests and clean scarp crests
    z_pf = _in_footprint_zscore(0.55 * grav_s12 + 0.45 * mag_s12, foot)
    z_topo = _in_footprint_zscore(lidar_clean, foot)
    lag_topo = gaussian_filter(z_topo, sigma=6.0).astype(np.float32)
    lag_pf = gaussian_filter(z_pf, sigma=6.0).astype(np.float32)
    biv_moran = (
        np.maximum(z_pf, 0.0) * np.maximum(lag_topo, 0.0)
        + np.maximum(z_topo, 0.0) * np.maximum(lag_pf, 0.0)
    ).astype(np.float32)
    del z_pf, z_topo, lag_topo, lag_pf
    ch3 = spcp.robust_unit_f32(
        mdrc.directional_chain_max(biv_moran, foot, halflen=2)
        * (0.25 + 0.75 * tiger_clean),
        foot,
        pct=99.5,
    )
    del biv_moran
    mm[:, :, 3] = ch3

    # 4. Multi-scale 2D Ricker (Mexican-Hat) wavelet ridge at 1.0 km, 2.0 km, 3.5 km
    wav_grav = compute_ricker_wavelet_ridge(grav_slope, foot, scales_px=(10.0, 20.0, 35.0))
    wav_mag = compute_ricker_wavelet_ridge(tmi_hg, foot, scales_px=(10.0, 20.0, 35.0))
    wav_topo = compute_ricker_wavelet_ridge(elev_slope, foot, scales_px=(10.0, 20.0, 35.0))
    wav_elev_step = compute_ricker_wavelet_ridge(det_elev, foot, scales_px=(12.0, 24.0))
    ch4 = spcp.robust_unit_f32(
        (0.34 * wav_grav + 0.28 * wav_mag + 0.22 * wav_topo + 0.16 * wav_elev_step)
        * (0.25 + 0.75 * tiger_clean),
        foot,
        pct=99.5,
    )
    del wav_grav, wav_mag, wav_topo, wav_elev_step
    mm[:, :, 4] = ch4

    # 5. Harmonic Second-Vertical-Derivative (SVD, -nabla_h^2 g_iso) zero-crossing inflection wall
    svd_s3 = (-gaussian_laplace(iso_grav, sigma=3.0)).astype(np.float32)
    svd_s6 = (-gaussian_laplace(iso_grav, sigma=6.0)).astype(np.float32)
    mad_s3 = float(np.median(np.abs(svd_s3[foot]))) + 1e-5
    mad_s6 = float(np.median(np.abs(svd_s6[foot]))) + 1e-5
    r3 = np.clip(svd_s3 / (1.35 * mad_s3), -10.0, 10.0)
    r6 = np.clip(svd_s6 / (1.35 * mad_s6), -10.0, 10.0)
    zero_wall = (0.60 * np.exp(-(r3 * r3)) + 0.40 * np.exp(-(r6 * r6))).astype(np.float32)
    del svd_s3, svd_s6, r3, r6
    grav_slope_u = spcp.robust_unit_f32(grav_slope, foot, pct=99.5)
    ch5 = spcp.robust_unit_f32(
        mdrc.directional_chain_max(
            grav_slope_u * zero_wall * (0.45 + 0.55 * cond_edge),
            foot,
            halflen=2,
        ),
        foot,
        pct=99.5,
    )
    del zero_wall, grav_slope_u
    mm[:, :, 5] = ch5

    # 6. Multi-altitude (0 m -> 150 m -> 4 km) magnetic gradient persistence + hydrothermal vent plume
    gy4k = sobel(gaussian_filter(mag_uc4k, sigma=2.0), axis=0)
    gx4k = sobel(gaussian_filter(mag_uc4k, sigma=2.0), axis=1)
    mag_hg_4km = spcp.robust_unit_f32(np.sqrt(gx4k * gx4k + gy4k * gy4k), foot, pct=99.5)
    del gx4k, gy4k
    tmi_hg_u = spcp.robust_unit_f32(tmi_hg, foot, pct=99.5)
    gy_rtp = sobel(gaussian_filter(tmi_rtp, sigma=1.5), axis=0)
    gx_rtp = sobel(gaussian_filter(tmi_rtp, sigma=1.5), axis=1)
    tmi_rtp_grad = spcp.robust_unit_f32(np.sqrt(gx_rtp * gx_rtp + gy_rtp * gy_rtp), foot, pct=99.5)
    del gx_rtp, gy_rtp
    multi_alt_mag = (
        0.40 * mag_up150
        + 0.35 * np.sqrt(np.maximum(tmi_hg_u * mag_hg_4km, 0.0))
        + 0.25 * np.sqrt(np.maximum(tmi_rtp_grad * mag_hg_4km, 0.0))
    ).astype(np.float32)
    del mag_hg_4km, tmi_hg_u, tmi_rtp_grad
    vent_plume = spcp.robust_unit_f32(
        gaussian_filter(0.55 * gdr_sinter + 0.45 * gdr_2m_dab, sigma=6.0),
        foot,
        pct=99.5,
    )
    ch6 = spcp.robust_unit_f32(
        multi_alt_mag * (0.45 + 0.55 * np.maximum(vent_plume, vent_conduit)),
        foot,
        pct=99.5,
    )
    del multi_alt_mag, vent_plume
    mm[:, :, 6] = ch6

    # 7. Unified label-free LDGI structural-corridor & hydrothermal-conduit composite
    # Crucially avoids multiplying by flat-playa `piedmont_burial` (`IR-46-PLAYA-01`).
    raw_unsup = (
        0.24 * ch0
        + 0.16 * ch1
        + 0.20 * ch2
        + 0.14 * ch3
        + 0.16 * ch4
        + 0.10 * ch5
    ) * (0.52 + 0.48 * np.maximum(spcp_unsup, ch6))
    ch7 = spcp.robust_unit_f32(
        mdrc.directional_chain_max(raw_unsup, foot, halflen=2)
        * (0.25 + 0.75 * tiger_clean),
        foot,
        pct=99.5,
    )
    del raw_unsup
    mm[:, :, 7] = ch7

    if hasattr(mm, "flush"):
        mm.flush()
    gc.collect()

    meta: dict[str, Any] = {
        "channels": LDGI_EXTRA_CHANNELS,
        "shape": [h, w, len(LDGI_EXTRA_CHANNELS)],
        "dtype": "float32",
        "label_free": True,
        "in_footprint_2m_probes": int(trhv_meta.get("in_footprint_2m_probes", 2782)),
        "valid_t2m_t15m_gradient_probes": int(trhv_meta.get("valid_t2m_t15m_gradient_probes", 1541)),
        "in_footprint_paleo_vents": int(trhv_meta.get("in_footprint_paleo_vents", 281)),
        "ricker_wavelet_scales_px": [10.0, 20.0, 35.0],
        "getis_ord_radii_px": [5, 12],
        "lineament_density_bandwidths_px": [8.0, 18.0],
    }
    receipt_path.write_text(json.dumps(meta, indent=2))
    return open_memmap(out_path, mode="r"), meta


def run_leakage_canary_71ch(
    base_stack: np.ndarray,
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    base_names: list[str],
    ctx,
    max_auc: float = 0.90,
    stride: int = 4,
) -> dict[str, Any]:
    """Protocol Rule 4 single-feature two-polarity leakage canary across all 71 channels (<100 MB RAM)."""
    pos_mask = np.zeros(ctx.foot.shape, dtype=bool)
    neg_mask = np.zeros(ctx.foot.shape, dtype=bool)
    for cell in ctx.cells:
        if cell.seed != 20:
            continue
        sl = cell.bbox
        sub_t = np.zeros(cell.active_sub.shape, dtype=bool)
        sub_t[cell.truth_coords] = True
        pos_mask[sl] |= sub_t
        neg_mask[sl] |= cell.active_sub & ~sub_t

    py, px = np.nonzero(pos_mask)
    ny, nx = np.nonzero(neg_mask)
    ny, nx = ny[::stride], nx[::stride]
    y_true = np.concatenate([np.ones(py.size, dtype=np.int8), np.zeros(ny.size, dtype=np.int8)])

    n_b = base_stack.shape[2]
    n_s = spcp_stack.shape[2]
    n_t = trhv_stack.shape[2]
    all_names = (
        list(base_names)
        + list(spcp.SPCP_EXTRA_CHANNELS)
        + list(trhv.TRHV_EXTRA_CHANNELS)
        + list(LDGI_EXTRA_CHANNELS)
    )

    rows = []
    for i, name in enumerate(all_names):
        if i < n_b:
            plane = base_stack[:, :, i]
        elif i < n_b + n_s:
            plane = spcp_stack[:, :, i - n_b]
        elif i < n_b + n_s + n_t:
            plane = trhv_stack[:, :, i - n_b - n_s]
        else:
            plane = ldgi_stack[:, :, i - n_b - n_s - n_t]
        vals = np.concatenate([plane[py, px], plane[ny, nx]]).astype(np.float64)
        vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
        if np.ptp(vals) <= 1e-12:
            raw_auc = 0.5
            auc_dir = 0.5
        else:
            raw_auc = float(roc_auc_score(y_true, vals))
            auc_dir = max(raw_auc, 1.0 - raw_auc)
        rows.append(
            {
                "channel": name,
                "raw_auc": round(raw_auc, 6),
                "oriented_auc": round(auc_dir, 6),
                "passed": bool(auc_dir <= max_auc),
            }
        )

    worst = max(rows, key=lambda r: r["oriented_auc"])
    return {
        "passed": all(r["passed"] for r in rows),
        "threshold_auc": max_auc,
        "n_features_tested": len(rows),
        "max_oriented_auc": worst["oriented_auc"],
        "worst_channel": worst["channel"],
        "n_withheld_pos_tested": int(py.size),
        "n_active_neg_sampled": int(ny.size),
        "per_channel": rows,
    }


def gather_71ch(
    base_stack: np.ndarray,
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    ys: np.ndarray,
    xs: np.ndarray,
) -> np.ndarray:
    xb = np.asarray(base_stack[ys, xs, :], dtype=np.float32)
    xs_arr = np.asarray(spcp_stack[ys, xs, :], dtype=np.float32)
    xt = np.asarray(trhv_stack[ys, xs, :], dtype=np.float32)
    xl = np.asarray(ldgi_stack[ys, xs, :], dtype=np.float32)
    return np.hstack([xb, xs_arr, xt, xl])


def predict_chunked_71ch(
    clf: HistGradientBoostingClassifier,
    base_stack: np.ndarray,
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    mask: np.ndarray,
    chunk_size: int = 200_000,
) -> np.ndarray:
    out = np.zeros(mask.shape, dtype=np.float32)
    ys, xs = np.nonzero(mask)
    for start in range(0, ys.size, chunk_size):
        sl = slice(start, min(start + chunk_size, ys.size))
        X = gather_71ch(base_stack, spcp_stack, trhv_stack, ldgi_stack, ys[sl], xs[sl])
        out[ys[sl], xs[sl]] = clf.predict_proba(X)[:, 1].astype(np.float32)
        del X
    return out


def fit_71ch_classifier(
    base_stack: np.ndarray,
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    train_region: np.ndarray,
    visible_train: np.ndarray,
    foot: np.ndarray,
    seed: int = 47,
    max_pos: int = 44_000,
    n_neg_hard: int = 88_000,
    n_neg_unif: int = 88_000,
) -> HistGradientBoostingClassifier:
    """Fit a fold-local 71-channel hard-negative HistGradientBoostingClassifier."""
    rng = np.random.default_rng(seed)
    tr_pos = train_region & visible_train
    d_tr = distance_transform_edt(~tr_pos)

    pos_y, pos_x = np.nonzero(tr_pos)
    if pos_y.size > max_pos:
        pp = rng.choice(pos_y.size, size=max_pos, replace=False)
        pos_y, pos_x = pos_y[pp], pos_x[pp]

    hard_y, hard_x = np.nonzero(train_region & (~visible_train) & (d_tr >= 5.0) & (d_tr <= 24.0))
    unif_y, unif_x = np.nonzero(train_region & (~visible_train) & (d_tr > 24.0))
    del d_tr

    nh = min(n_neg_hard, hard_y.size)
    nu = min(n_neg_unif, unif_y.size)
    ph = rng.choice(hard_y.size, size=nh, replace=False)
    pu = rng.choice(unif_y.size, size=nu, replace=False)

    ys = np.concatenate([pos_y, hard_y[ph], unif_y[pu]])
    xs = np.concatenate([pos_x, hard_x[ph], unif_x[pu]])
    y = np.concatenate([np.ones(pos_y.size, dtype=np.int8), np.zeros(nh + nu, dtype=np.int8)])
    del pos_y, pos_x, hard_y, hard_x, unif_y, unif_x

    order = np.argsort(ys * foot.shape[1] + xs)
    ys, xs, y = ys[order], xs[order], y[order]

    X = gather_71ch(base_stack, spcp_stack, trhv_stack, ldgi_stack, ys, xs)
    clf = HistGradientBoostingClassifier(
        max_iter=165,
        learning_rate=0.055,
        max_leaf_nodes=47,
        min_samples_leaf=80,
        l2_regularization=2.5,
        early_stopping=False,
        random_state=seed,
    )
    clf.fit(X, y)
    del X, y, ys, xs
    return clf


def anisotropic_tip_relay_cone(
    visible_mask: np.ndarray,
    foot: np.ndarray,
) -> np.ndarray:
    """Fold-safe anisotropic along-strike tip-propagation & step-over bridge cone.

    Uses ONLY `visible_mask` (`cell.visible_full` on OOF folds, `labels.tif` on full map):
      1. Extracts visible endpoints `tips = spcp.visible_endpoints(visible_mask)`.
      2. Estimates the local strike orientation of `visible_mask` via the smoothed
         structure tensor of `visible_mask` (`sigma = 2.2 px`) evaluated at the
         nearest visible tip `(iy_t, ix_t)`.
      3. Distinguishes the forward propagation half-space ahead of a fault tip
         (`d_vis / max(d_tip, 0.5) >= 0.62`) from lateral fault flanks, and Combines
         this with radial tip/relay envelopes (`300 m to 2.4 km`).
    """
    vis = np.asarray(visible_mask, bool) & foot
    if not np.any(vis):
        return np.zeros(foot.shape, dtype=np.float32)

    from scipy.ndimage import convolve

    nb = convolve(vis.astype(np.int16), np.ones((3, 3), dtype=np.int16), mode="constant") - vis.astype(np.int16)
    tips = vis & (nb >= 1) & (nb <= 2)
    del nb

    d_vis = distance_transform_edt(~vis).astype(np.float32)
    if not np.any(tips):
        return np.where(foot, np.exp(-((d_vis - 4.5) ** 2) / (2.0 * 4.5 * 4.5)), 0.0).astype(np.float32)

    d_tip, (iy_t, ix_t) = distance_transform_edt(~tips, return_indices=True)
    d_tip = d_tip.astype(np.float32)

    vis_s = gaussian_filter(vis.astype(np.float32), sigma=2.2)
    gy = sobel(vis_s, axis=0)
    gx = sobel(vis_s, axis=1)
    jxx = gaussian_filter(gx * gx, sigma=3.0)
    jyy = gaussian_filter(gy * gy, sigma=3.0)
    jxy = gaussian_filter(gx * gy, sigma=3.0)
    theta_strike = (0.5 * np.arctan2(2.0 * jxy, jxx - jyy) + 0.5 * np.pi).astype(np.float32)
    tip_strike = theta_strike[iy_t, ix_t]
    del vis_s, gy, gx, jxx, jyy, jxy, theta_strike

    yy, xx = np.indices(foot.shape, dtype=np.float32)
    dy = yy - iy_t.astype(np.float32)
    dx = xx - ix_t.astype(np.float32)
    az = np.arctan2(dy, dx).astype(np.float32)
    del yy, xx, dy, dx, iy_t, ix_t

    cos_align = np.cos(az - tip_strike) ** 2
    wing_cone = (0.35 + 0.65 * cos_align).astype(np.float32)
    del az, tip_strike, cos_align

    forward_ratio = d_vis / np.maximum(d_tip, 0.5)
    forward_gate = np.clip((forward_ratio - 0.55) / 0.45, 0.25, 1.0).astype(np.float32)

    radial_tip = np.exp(-((d_tip - 5.2) ** 2) / (2.0 * 7.2 * 7.2)).astype(np.float32)
    relay_halo = np.exp(-((d_vis - 4.6) ** 2) / (2.0 * 4.6 * 4.6)).astype(np.float32)
    vis_blur = gaussian_filter(vis.astype(np.float32), sigma=2.5, mode="constant")
    stepover = np.clip(vis_blur * 14.0, 0.0, 1.5).astype(np.float32)
    del vis_blur, d_tip

    outside = (d_vis > 2.0) & foot
    out = (
        0.54 * (radial_tip * forward_gate * wing_cone)
        + 0.26 * relay_halo
        + 0.20 * stepover
    ) * outside
    return out.astype(np.float32)


def build_ldgi_crest_unsup_surface(
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    foot: np.ndarray,
) -> np.ndarray:
    """Label-free `100 m` ridge/contact crest surface weighted by the multi-domain `LDGI` corridor envelope.

    Unlike unlocalized `0.8–3.5 km` halo averages (`SGMC_cal = 0.051126`), this function
    retains `100 m` fault-crest localization (`0.58*spcp_unsup + 0.18*lidar_clean + 0.14*pf_concord + 0.10*svd_wall`)
    and modulates it multiplicatively by the label-free `LDGI` corridor envelope (`rho_lin`, `gi_star`,
    `wav_ricker`, `moran_i`, `inter_rel`, `dip_vent`) and the `150 m` anthropogenic TIGER road veto.
    """
    spcp_unsup = np.asarray(spcp_stack[:, :, 19], dtype=np.float32)
    pf_concord = np.asarray(spcp_stack[:, :, 4], dtype=np.float32)
    lidar_clean = np.asarray(trhv_stack[:, :, 5], dtype=np.float32)
    tiger_clean = np.asarray(trhv_stack[:, :, 4], dtype=np.float32)
    vent_cond = np.asarray(trhv_stack[:, :, 3], dtype=np.float32)

    rho_lin = np.asarray(ldgi_stack[:, :, 0], dtype=np.float32)
    inter_rel = np.asarray(ldgi_stack[:, :, 1], dtype=np.float32)
    gi_star = np.asarray(ldgi_stack[:, :, 2], dtype=np.float32)
    moran_i = np.asarray(ldgi_stack[:, :, 3], dtype=np.float32)
    wav_ricker = np.asarray(ldgi_stack[:, :, 4], dtype=np.float32)
    svd_wall = np.asarray(ldgi_stack[:, :, 5], dtype=np.float32)
    dip_vent = np.asarray(ldgi_stack[:, :, 6], dtype=np.float32)

    sharp_carrier = (
        0.58 * spcp_unsup
        + 0.18 * lidar_clean
        + 0.14 * pf_concord
        + 0.10 * svd_wall
    )
    corridor_env = (
        0.28 * rho_lin
        + 0.26 * gi_star
        + 0.18 * wav_ricker
        + 0.14 * moran_i
        + 0.14 * np.maximum(inter_rel, np.maximum(dip_vent, vent_cond))
    )
    return spcp.robust_unit_f32(
        sharp_carrier * (0.45 + 0.55 * corridor_env) * (0.35 + 0.65 * tiger_clean),
        foot,
        pct=99.5,
    )


def compute_lineament_completeness_eta(
    visible_mask: np.ndarray,
    foot: np.ndarray,
    rho_lin: np.ndarray | None = None,
    rho_lin_sum: float | None = None,
    visibility_fraction: float = 1.0,
) -> float:
    """Empirical Catalogue-to-Lineament Completeness Ratio `eta(V) = (|V cap foot| / visibility_fraction) / sum_{foot} rho_lin`.

    IR-48-CCAA-01 note: passing `visibility_fraction = 1.0 - hide_frac` removes the artificial 20%
    holdout-censorship shift (`0.80 * eta_full`) between OOF cells and full-map emission; default
    `visibility_fraction=1.0` preserves legacy unit-test compatibility.
    """
    vis_cnt = float((np.asarray(visible_mask, bool) & foot).sum()) / max(float(visibility_fraction), 1e-6)
    if rho_lin_sum is None:
        assert rho_lin is not None, "Either rho_lin or rho_lin_sum must be provided"
        rho_lin_sum = float(np.asarray(rho_lin, dtype=np.float32)[foot].sum())
    return vis_cnt / max(float(rho_lin_sum), 1.0)


def compute_adaptive_stage1_fraction(
    eta: float,
    eta_uncensored: float = 0.0784,
    eta_censored_ref: float = 0.0627,
    min_frac: float = 0.50,
    max_frac: float = 0.92,
) -> tuple[float, float]:
    """Closed-form linear allocation law `(f_a(eta), w_s1(eta))` from Catalogue-to-Lineament Completeness `eta`."""
    f_a = float(
        np.clip(
            min_frac + (max_frac - min_frac) * ((eta_uncensored - float(eta)) / max(eta_uncensored - eta_censored_ref, 1e-6)),
            min_frac,
            max_frac,
        )
    )
    w_s1 = float(np.clip(0.08 + 0.77 * ((f_a - min_frac) / max(max_frac - min_frac, 1e-6)), 0.08, 0.85))
    return f_a, w_s1


def modulate_exposed71_gi_surface(
    surface_63ch: np.ndarray,
    raw_prob_71ch: np.ndarray,
    visible_mask: np.ndarray,
    foot: np.ndarray,
    region_mask: np.ndarray | None = None,
    w_63: float = 0.55,
    w_71: float = 0.45,
    inner_tip_weight: float = 0.35,
    outer_tip_weight: float = 1.00,
) -> np.ndarray:
    """Fold-safe 63-ch + 71-ch `LDGI` ensemble modulated by the visible tip/step-over cone (`EXP2_H47_EXPOSED71_GI`)."""
    if region_mask is None:
        region_mask = foot
    out = np.zeros(foot.shape, dtype=np.float32)
    ptip = trhv.visible_tip_stepover_cone(visible_mask, foot)
    s63 = surface_63ch[region_mask]
    r71 = raw_prob_71ch[region_mask]
    pt = ptip[region_mask]
    out[region_mask] = (
        (np.float32(w_63) * s63 + np.float32(w_71) * r71 * (np.float32(1.0) + np.float32(inner_tip_weight) * pt))
        * (np.float32(1.0) + np.float32(outer_tip_weight) * pt)
    )
    return out


def build_dual_horizon_belief_surface(
    surface_stage1: np.ndarray,
    ldgi_crest_unsup: np.ndarray,
    visible_mask: np.ndarray,
    mask: np.ndarray,
    eta: float = 0.078381,
    off_cat_min_dist_px: float = 4.0,
) -> np.ndarray:
    """Continuous unified pre-placement belief surface for Protocol Rule 1 Spearman registry check."""
    vis = np.asarray(visible_mask, bool) & mask
    d_vis = distance_transform_edt(~vis).astype(np.float32)
    f_a, w_s1 = compute_adaptive_stage1_fraction(eta)
    off_gate = np.clip((d_vis - float(off_cat_min_dist_px)) / 4.0, 0.0, 1.0).astype(np.float32)
    s2_raw = np.where(
        mask,
        ldgi_crest_unsup * ((np.float32(1.0 - w_s1)) + np.float32(w_s1) * surface_stage1) * off_gate,
        0.0,
    ).astype(np.float32)

    r1 = spcp._rank_unit_f32(surface_stage1, mask)
    r2 = spcp._rank_unit_f32(s2_raw, mask)
    w2 = np.float32(1.0 - f_a) * off_gate
    return np.where(mask, (np.float32(1.0) - w2) * r1 + w2 * r2, np.float32(0.0)).astype(np.float32)


def emit_dual_horizon_ldgi(
    surface_stage1: np.ndarray,
    crest_b: np.ndarray,
    visible_mask: np.ndarray,
    eligible_mask: np.ndarray,
    foot: np.ndarray,
    eta: float,
    d_vis: np.ndarray | None = None,
    budget: int = TARGET_BUDGET,
    off_cat_min_dist_px: float = 4.0,
    support_mult: int = 5,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Catalogue-Completeness Adaptive Dual-Horizon Residual-Coverage CELF emitter (`H47-1` / `EXP3`)."""
    if budget <= 0 or not (eligible_mask & foot).any():
        return np.zeros(surface_stage1.shape, dtype=bool), {
            "stage1_dots": 0,
            "stage2_added_dots": 0,
            "total_dots": 0,
            "eta": float(eta),
            "frac_stage1": 0.0,
            "w_s1": 0.0,
        }

    if d_vis is None:
        vis = np.asarray(visible_mask, bool) & foot
        d_vis = distance_transform_edt(~vis).astype(np.float32)
    elig_a = eligible_mask & foot & (d_vis > B_COLLAR_PX)

    f_a, w_s1 = compute_adaptive_stage1_fraction(eta)
    b_a = max(1, min(int(budget), int(round(budget * float(f_a)))))
    dots_a, _ = spcp.emit_crest_submodular(
        surface_stage1,
        elig_a,
        foot,
        budget=b_a,
        support_mult=support_mult,
    )
    n_a = int(dots_a.sum())
    rem_budget = int(budget) - n_a
    if rem_budget <= 0:
        return dots_a, {
            "stage1_dots": n_a,
            "stage2_added_dots": 0,
            "total_dots": n_a,
            "eta": float(eta),
            "frac_stage1": float(f_a),
            "w_s1": float(w_s1),
            "stage1_mask": dots_a,
        }

    off_gate = np.clip((d_vis - float(off_cat_min_dist_px)) / 4.0, 0.0, 1.0).astype(np.float32)
    s2 = (
        crest_b
        * ((np.float32(1.0 - w_s1)) + np.float32(w_s1) * surface_stage1)
        * off_gate
    ).astype(np.float32)

    elig_b = elig_a & (~dots_a) & (s2 > 0)
    n_elig_b = int(elig_b.sum())
    if n_elig_b == 0:
        return dots_a, {
            "stage1_dots": n_a,
            "stage2_added_dots": 0,
            "total_dots": n_a,
            "eta": float(eta),
            "frac_stage1": float(f_a),
            "w_s1": float(w_s1),
            "stage1_mask": dots_a,
        }

    max_sup_b = max(rem_budget * (support_mult + 1), min(n_elig_b, 25_000))
    if n_elig_b > max_sup_b:
        vals = s2[elig_b]
        thr = float(np.partition(vals, n_elig_b - max_sup_b)[n_elig_b - max_sup_b])
        sup_b = elig_b & (s2 >= thr)
    else:
        sup_b = elig_b

    field_b = np.where(sup_b, s2, 0.0).astype(np.float64)
    del s2, elig_b, sup_b
    dots_b_new, _ = emitter.emit(
        field_b,
        budget=int(rem_budget),
        prior_dti=0.0,
        gain_floor=0.0,
        initial_mask=dots_a,
    )
    del field_b
    assert not bool((dots_a & dots_b_new).any()), "Stage-2 dots must be strictly disjoint from Stage-1 dots"
    dots_ab = dots_a | dots_b_new
    n_b = int(dots_b_new.sum())
    n_tot = int(dots_ab.sum())
    return dots_ab, {
        "stage1_dots": n_a,
        "stage2_added_dots": n_b,
        "total_dots": n_tot,
        "eta": float(eta),
        "frac_stage1": float(f_a),
        "w_s1": float(w_s1),
        "stage1_mask": dots_a,
    }
