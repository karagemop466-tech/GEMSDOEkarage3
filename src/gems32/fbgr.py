"""H48-1-FBGR: Fourier-Continued Basement-Graben Relay, GeoDAWN Block-Normalized 214Bi Radon /
Silica-Potassic Zonation & Stationary Dual-Cover Axial-Crest Submodular Cover.

Pre-registered in ``docs/research/h48-fbgr-preregistration-20261027.md`` before implementation.

Key scientific & engineering properties:
  1. Fixes ``IR-48-BAND14-01`` with exact 2-D Fourier harmonic upward continuation
     (Blakely 1995 Eq. 12.8: U_hat(k; z) = U_hat(k; 0) * exp(-2*pi*z*|k|)) applied to both
     Band 13 ``iso_grav_anom`` and Band 02 ``rtp`` at z = {500 m, 2,000 m}, extracting
     crustal-root gradient persistence and listric/normal hanging-wall dip-migration asymmetry.
  2. Fixes ``IR-A48-JX-01`` using the SHA-256-pinned GeoDAWN 4-block contractor flight polygon
     raster (``acquisition_block_id_100m.tif``, DOI 10.5066/P93LGLVQ) to z-standardize K, eTh,
     eU, TC, U/Th, U/K within each block before extracting playa-vetoed 214Bi (eU - beta*eTh)
     radon-degassing fault-conduit crests and concentric DoG silica-core / potassic-halo zones
     corroborated by BLM historic hydrothermal/geothermal claims (``blm_closed_claim_distance_m.tif``).
  3. Fixes ``IR-48-CCAA-01`` by eliminating ``H47-1``'s non-stationary ``eta`` holdout-vs-live
     regime switch and ``s63`` blend, replacing them with a 100% stationary Dual-Cover OOF
     architecture (83-ch ``M_Full`` inside 1 m LiDAR + quantile-calibrated 71-ch strictly
     LiDAR-free ``M_Sub`` inside the 24.63% 1 m LiDAR gap) + oriented Axial-Crest NMS +
     ``min_sep_px = 2.8`` submodular ``gems32.emitter.emit``.
  4. Memory-engineered (< 750 MB peak RSS on 3.8 GiB zero-swap hosts) using disk-backed float32
     memmaps and ``scipy.fft.rfft2``/``irfft2`` real-to-complex transforms.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from numpy.lib.format import open_memmap
from scipy.fft import fftfreq, irfft2, rfft2, rfftfreq
from scipy.ndimage import convolve, distance_transform_edt, gaussian_filter, maximum_filter, minimum_filter, sobel
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from . import emitter, ldgi, mdrc, paths, spcp, trhv

TARGET_BUDGET: int = 37_654
B_COLLAR_PX: float = 2.0
AXIAL_MIN_SEP_PX: float = 2.8

FBGR_EXTRA_CHANNELS: tuple[str, ...] = (
    "grav_uc500_2k_persist",         # 0: Fourier UC (0, 500 m, 2 km) isostatic gravity h-grad crest persistence
    "rtp_uc500_2k_persist",          # 1: Fourier UC (0, 500 m, 2 km) RTP magnetic tilt/h-grad crest persistence
    "basement_dip_shift_asymm",      # 2: Hanging-wall z=0->2km crest migration x Band 15 graben deepening
    "geodawn_blk_radon_crest",       # 3: Block-normalized 214Bi (eU - beta*eTh) radon conduit ridge (playa-vetoed)
    "geodawn_blk_silica_potassic_dog",  # 4: Block-normalized concentric DoG low-TC silica core / high-K/Th halo
    "blm_epithermal_conduit_corrob", # 5: BLM hydrothermal/geothermal claim density x PF root & GDR vent plumes
    "morris_slip_dilation_obliq",    # 6: Azimuthal GPS transtensional slip-dilation + seismic coupling on PF strike
    "ctx_subsurf_aniso_500_1500m",   # 7: LiDAR-free 0.5/1.5 km along-strike vs cross-strike corridor continuity
    "ctx_subsurf_prominence_3km",    # 8: LiDAR-free 3 km local-to-regional prominence of crustal/MT crests
    "ctx_multimodal_corrob_2km",     # 9: LiDAR-free 2 km multi-physics independent domain corroboration count
    "ctx_lidar_aniso_chain_1km",     # 10: 1 m LiDAR de-confounded scarp 1 km directional chain (inside lidar_valid)
    "fbgr_unsup_conduit_crest",      # 11: LiDAR-free unified 100 m basement + geothermal + radon conduit crest
)

# Verified channel indices in the 83-channel concatenated stack:
#   0..34  (35): base_stack       -> 35/35 strictly 1 m LiDAR-free
#   35..54 (20): spcp_stack       -> 12..15, 19 (global 47,48,49,50,54) touch 1 m LiDAR; rest (15) LiDAR-free
#   55..62 ( 8): trhv_stack       -> 5 (global 60) touches 1 m LiDAR; rest (7) LiDAR-free
#   63..70 ( 8): ldgi_stack       -> 0..3, 7 (global 63,64,65,66,70) touch 1 m LiDAR; 4,5,6 (global 67,68,69) LiDAR-free
#   71..82 (12): fbgr_stack       -> 10 (global 81) touches 1 m LiDAR; 0..9, 11 (11) LiDAR-free
LIDAR_DEPENDENT_GLOBAL_COLS: frozenset[int] = frozenset({47, 48, 49, 50, 54, 60, 63, 64, 65, 66, 70, 81})
MSUB_COL_INDICES: tuple[int, ...] = tuple(i for i in range(83) if i not in LIDAR_DEPENDENT_GLOBAL_COLS)
assert len(MSUB_COL_INDICES) == 71, f"Expected 71 pure non-LiDAR columns, got {len(MSUB_COL_INDICES)}"


def harmonic_upward_continue_pair_f32(
    field: np.ndarray,
    foot: np.ndarray,
    heights_m: tuple[float, float] = (500.0, 2000.0),
    dx_m: float = 100.0,
    pad_px: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """Exact 2-D Fourier harmonic upward continuation (Blakely 1995 Eq. 12.8) at two altitudes in one FFT."""
    h, w = field.shape
    med = np.float32(np.median(field[foot][::4])) if foot.any() else np.float32(0.0)
    work = np.where(foot & np.isfinite(field), field - med, np.float32(0.0)).astype(np.float32)
    padded = np.pad(work, ((pad_px, pad_px), (pad_px, pad_px)), mode="reflect")
    del work

    ph, pw = padded.shape
    spec = rfft2(padded, workers=2)
    del padded

    ky = fftfreq(ph, d=dx_m).astype(np.float32)[:, None]
    kx = rfftfreq(pw, d=dx_m).astype(np.float32)[None, :]
    k_rad = np.hypot(ky, kx).astype(np.float32)
    del ky, kx

    z1, z2 = float(heights_m[0]), float(heights_m[1])
    u1 = irfft2(spec * np.exp(-np.float32(2.0 * np.pi * z1) * k_rad), s=(ph, pw), workers=2)[
        pad_px : pad_px + h, pad_px : pad_px + w
    ].astype(np.float32)
    u2 = irfft2(spec * np.exp(-np.float32(2.0 * np.pi * z2) * k_rad), s=(ph, pw), workers=2)[
        pad_px : pad_px + h, pad_px : pad_px + w
    ].astype(np.float32)
    del spec, k_rad
    return u1, u2


def _hgrad_mag_and_vec(a: np.ndarray, sigma: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s = gaussian_filter(a.astype(np.float32, copy=False), sigma, mode="nearest") if sigma > 0 else a
    gy = sobel(s, axis=0).astype(np.float32) * np.float32(0.125)
    gx = sobel(s, axis=1).astype(np.float32) * np.float32(0.125)
    return np.hypot(gx, gy).astype(np.float32), gy, gx


def _block_zscore_f32(a: np.ndarray, block_id: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Standardize `a` (median / MAD) independently within each GeoDAWN contractor block 1..4."""
    out = np.zeros(a.shape, dtype=np.float32)
    for bid in (1, 2, 3, 4):
        m = valid & (block_id == bid)
        if not m.any():
            continue
        sub = a[m][::4]
        if sub.size < 16:
            sub = a[m]
        med = np.float32(np.median(sub))
        mad = np.float32(max(float(np.median(np.abs(sub - med))) * 1.4826, 1e-4))
        out[m] = np.clip((a[m] - med) / mad, -8.0, 8.0)
    return out


def sharpen_probability_crest(
    prob: np.ndarray,
    foot: np.ndarray,
    crest_boost: float = 0.45,
) -> np.ndarray:
    """Probability-contrast-preserving 4-azimuth non-maximum suppression crest sharpener.

    Preserves amplitude heterogeneity (`0.55 * p + 0.45 * p * nms_ratio`) so high-confidence
    ridges strongly outrank low-confidence background while localizing 2D probability ribbons
    onto their 1-px axial crest before `min_sep_px = 2.8` CELF packing.
    """
    p = np.where(foot & np.isfinite(prob), np.maximum(prob, np.float32(0.0)), np.float32(0.0)).astype(np.float32)
    ps = gaussian_filter(p, sigma=0.75, mode="nearest")
    gy = sobel(ps, axis=0)
    gx = sobel(ps, axis=1)
    # Normal direction to ridge is gradient of smoothed probability (or structure tensor)
    jxx = gaussian_filter(gx * gx, sigma=1.8, mode="nearest")
    jyy = gaussian_filter(gy * gy, sigma=1.8, mode="nearest")
    jxy = gaussian_filter(gx * gy, sigma=1.8, mode="nearest")
    # Principal normal direction (across-ridge curvature axis)
    theta_n = np.float32(0.5) * np.arctan2(np.float32(2.0) * jxy, jxx - jyy + np.float32(1e-12))
    del gy, gx, jxx, jyy, jxy

    # Quantize normal into 4 canonical 45-deg sectors: 0 (E-W), 1 (NW-SE), 2 (N-S), 3 (NE-SW)
    ang = np.mod(theta_n, np.float32(np.pi))
    sec = (np.floor((ang + np.float32(np.pi / 8.0)) / np.float32(np.pi / 4.0)).astype(np.int8)) % 4
    del theta_n, ang

    # Shifted neighbors at 1 px and 2 px along the 4 normal axes
    pad = np.pad(ps, 2, mode="edge")
    h, w = p.shape
    offsets = (
        ((0, 1), (0, -1), (0, 2), (0, -2)),     # sector 0: normal along x
        ((1, 1), (-1, -1), (2, 2), (-2, -2)),   # sector 1: normal along diag
        ((1, 0), (-1, 0), (2, 0), (-2, 0)),     # sector 2: normal along y
        ((1, -1), (-1, 1), (2, -2), (-2, 2)),   # sector 3: normal along anti-diag
    )
    nms_soft = np.zeros_like(p)
    for s_idx, ((dy1, dx1), (dy2, dx2), (dy3, dx3), (dy4, dx4)) in enumerate(offsets):
        m = foot & (sec == s_idx)
        if not m.any():
            continue
        n1 = pad[2 + dy1 : 2 + dy1 + h, 2 + dx1 : 2 + dx1 + w][m]
        n2 = pad[2 + dy2 : 2 + dy2 + h, 2 + dx2 : 2 + dx2 + w][m]
        n3 = pad[2 + dy3 : 2 + dy3 + h, 2 + dx3 : 2 + dx3 + w][m]
        n4 = pad[2 + dy4 : 2 + dy4 + h, 2 + dx4 : 2 + dx4 + w][m]
        c_val = ps[m]
        nbr_max1 = np.maximum(n1, n2)
        nbr_mean2 = np.float32(0.25) * (n1 + n2 + n3 + n4)
        is_peak = (c_val >= nbr_max1 - np.float32(1e-6)).astype(np.float32)
        prom = np.clip((c_val - nbr_mean2) / (c_val + np.float32(1e-5)), 0.0, 1.0)
        nms_soft[m] = np.float32(0.65) * is_peak + np.float32(0.35) * prom
    del pad, ps, sec

    w0 = np.float32(1.0 - float(crest_boost))
    w1 = np.float32(crest_boost)
    out = p * (w0 + w1 * nms_soft)
    out[~foot] = 0.0
    return out.astype(np.float32)


def build_fbgr_extra_stack(
    ddir: Path | None = None,
    base_stack_path: Path | None = None,
    spcp_path: Path | None = None,
    trhv_path: Path | None = None,
    ldgi_path: Path | None = None,
    out_path: Path | None = None,
    force: bool = False,
    log=print,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build or open the 12-channel strictly label-free `FBGR` disk-backed float32 stack."""
    ddir = ddir or paths.data_dir()
    wdir = paths.work_dir()
    wdir.mkdir(parents=True, exist_ok=True)

    base_stack_path = base_stack_path or (wdir / "feature_stack.npy")
    spcp_path = spcp_path or (wdir / "spcp_extra_20ch.npy")
    trhv_path = trhv_path or (wdir / "trhv_extra_8ch.npy")
    ldgi_path = ldgi_path or (wdir / "ldgi_extra_8ch.npy")
    out_path = out_path or (wdir / "fbgr_extra_12ch.npy")
    receipt_path = out_path.with_suffix(".json")

    if out_path.exists() and receipt_path.exists() and not force:
        mm = open_memmap(out_path, mode="r")
        if mm.shape[2] == len(FBGR_EXTRA_CHANNELS):
            return mm, json.loads(receipt_path.read_text())

    with rasterio.open(ddir / "sample_submission.tif") as src:
        sample = src.read(1)
        foot = np.isfinite(sample)
        h, w = sample.shape
    del sample

    base_mm = open_memmap(base_stack_path, mode="r")
    spcp_mm = open_memmap(spcp_path, mode="r")
    trhv_mm = open_memmap(trhv_path, mode="r")
    ldgi_mm = open_memmap(ldgi_path, mode="r")

    def _clean_base(idx0: int) -> np.ndarray:
        plane = np.asarray(base_mm[:, :, idx0], dtype=np.float32).copy()
        valid = foot & np.isfinite(plane) & (np.abs(plane) < 1e12)
        med = np.float32(np.median(plane[valid][::4])) if valid.any() else np.float32(0.0)
        plane[~valid] = med
        return plane

    mm = open_memmap(out_path, mode="w+", dtype=np.float32, shape=(h, w, len(FBGR_EXTRA_CHANNELS)))

    # --- Ch 0..2: Exact 2-D Fourier Harmonic Upward Continuation (z = 500 m, 2,000 m) ---
    iso_grav = _clean_base(12)  # Band 13: iso_grav_anom
    grav_uc500, grav_uc2k = harmonic_upward_continue_pair_f32(iso_grav, foot, heights_m=(500.0, 2000.0))
    gh0, gy_g0, gx_g0 = _hgrad_mag_and_vec(iso_grav, sigma=1.0)
    del iso_grav
    gh500, _, _ = _hgrad_mag_and_vec(grav_uc500, sigma=0.8)
    gh2k, gy_g2k, gx_g2k = _hgrad_mag_and_vec(grav_uc2k, sigma=0.8)
    del grav_uc2k

    kneg_g0, strike_pf = spcp.principal_negative_curvature_and_strike(gh500, sigma=1.4)
    del grav_uc500
    u_g0 = spcp.robust_unit_f32(gh0, foot, pct=99.4)
    u_g500 = spcp.robust_unit_f32(gh500, foot, pct=99.4)
    u_g2k = spcp.robust_unit_f32(gh2k, foot, pct=99.4)
    u_gkneg = spcp.robust_unit_f32(kneg_g0, foot, pct=99.4)
    del gh0, gh500, gh2k, kneg_g0

    grav_persist = spcp.robust_unit_f32(
        np.cbrt(np.maximum(u_g0 * u_g500 * u_g2k, np.float32(0.0))) * (np.float32(0.45) + np.float32(0.55) * u_gkneg),
        foot,
        pct=99.5,
    )
    mm[:, :, 0] = grav_persist
    del u_gkneg
    gc.collect()

    rtp = _clean_base(1)  # Band 02: rtp
    rtp_uc500, rtp_uc2k = harmonic_upward_continue_pair_f32(rtp, foot, heights_m=(500.0, 2000.0))
    mh0, _, _ = _hgrad_mag_and_vec(rtp, sigma=1.0)
    del rtp
    mh500, _, _ = _hgrad_mag_and_vec(rtp_uc500, sigma=0.8)
    mh2k, _, _ = _hgrad_mag_and_vec(rtp_uc2k, sigma=0.8)
    # Approximate vertical derivative at 500 m via upward-continuation difference (rtp_uc500 - rtp_uc2k)/1500
    dz_rtp = np.abs(rtp_uc500 - rtp_uc2k) / np.float32(15.0)
    tilt_wall = np.exp(-np.abs(np.arctan2(dz_rtp, mh500 + np.float32(1e-3))) / np.float32(0.45)).astype(np.float32)
    del rtp_uc500, rtp_uc2k, dz_rtp

    kneg_m, _ = spcp.principal_negative_curvature_and_strike(mh500, sigma=1.4)
    u_m0 = spcp.robust_unit_f32(mh0, foot, pct=99.4)
    u_m500 = spcp.robust_unit_f32(mh500, foot, pct=99.4)
    u_m2k = spcp.robust_unit_f32(mh2k, foot, pct=99.4)
    u_mkneg = spcp.robust_unit_f32(kneg_m, foot, pct=99.4)
    del mh0, mh500, mh2k, kneg_m

    rtp_persist = spcp.robust_unit_f32(
        np.cbrt(np.maximum(u_m0 * u_m500 * u_m2k, np.float32(0.0)))
        * (np.float32(0.45) + np.float32(0.30) * u_mkneg + np.float32(0.25) * tilt_wall),
        foot,
        pct=99.5,
    )
    mm[:, :, 1] = rtp_persist
    del u_m0, u_m500, u_m2k, u_mkneg, tilt_wall

    # Ch 2: Hanging-wall normal-fault dip-migration asymmetry concordant with Band 15 basement deepening
    depth_base = _clean_base(14)  # Band 15: depth_to_base_surf
    _, dy_db, dx_db = _hgrad_mag_and_vec(depth_base, sigma=2.0)
    # Down-dip unit vector points toward deeper basin fill (+grad depth_to_base_surf)
    db_norm = np.hypot(dx_db, dy_db) + np.float32(1e-5)
    ux_dip, uy_dip = dx_db / db_norm, dy_db / db_norm
    del dx_db, dy_db, db_norm
    # Lateral migration of gravity gradient crest from z=0 to z=2km projected onto hanging-wall dip vector
    shift_proj = np.maximum(
        (u_g2k - np.float32(0.75) * u_g0), np.float32(0.0)
    ) + np.float32(0.5) * np.maximum(-(gx_g2k * ux_dip + gy_g2k * uy_dip) / (np.hypot(gx_g2k, gy_g2k) + np.float32(1e-5)), 0.0) * u_g500
    del gy_g0, gx_g0, gy_g2k, gx_g2k, ux_dip, uy_dip, u_g0, u_g500, u_g2k
    dip_asymm = spcp.robust_unit_f32(
        shift_proj * spcp._sigmoid_f32((depth_base - np.float32(120.0)) / np.float32(180.0)),
        foot,
        pct=99.5,
    )
    mm[:, :, 2] = dip_asymm
    del shift_proj
    log("  [FBGR] ch 0..2 (Fourier harmonic upward continuation 500m/2km + dip asymmetry) built")

    # --- Ch 3..5: GeoDAWN 4-Block Standardized 214Bi Radon Crest, Silica/Potassic DoG & BLM Claims ---
    det_elev = _clean_base(11)    # Band 12
    cond_surf = _clean_base(16)   # Band 17
    elev_slope = _clean_base(18)  # Band 19
    tiger_clean = np.asarray(trhv_mm[:, :, 4], dtype=np.float32)

    # Playa flat-sink veto: suppresses closed-basin evaporative uranium/saline sinks (slope < 0.8 deg & local elev min)
    local_relief_1km = maximum_filter(det_elev, size=15) - minimum_filter(det_elev, size=15)
    playa_sink = (
        spcp._sigmoid_f32((np.float32(1.0) - elev_slope) / np.float32(0.35))
        * spcp._sigmoid_f32((np.float32(12.0) - local_relief_1km) / np.float32(4.0))
        * spcp._sigmoid_f32((cond_surf - np.float32(3.35)) / np.float32(0.35))
    )
    non_playa_gate = np.clip(np.float32(1.0) - np.float32(0.90) * playa_sink, np.float32(0.10), np.float32(1.0)).astype(np.float32)
    del det_elev, cond_surf, local_relief_1km, playa_sink

    with rasterio.open(ddir / "external" / "acquisition_block_id_100m.tif") as ds:
        block_id = ds.read(1)
    with rasterio.open(ddir / "external" / "geodawn_rad_u8.tif") as ds:
        rad_k = ds.read(1).astype(np.float32)
        rad_th = ds.read(2).astype(np.float32)
        rad_u = ds.read(3).astype(np.float32)
        rad_tc = ds.read(4).astype(np.float32)
    with rasterio.open(ddir / "external" / "geodawn_extensions_u8.tif") as ds:
        ext_uk = ds.read(2).astype(np.float32)
        ext_uth = ds.read(3).astype(np.float32)

    rad_valid = foot & (rad_tc > 0) & (rad_th > 0) & (rad_u > 0)
    z_k = _block_zscore_f32(rad_k, block_id, rad_valid)
    z_th = _block_zscore_f32(rad_th, block_id, rad_valid)
    z_u = _block_zscore_f32(rad_u, block_id, rad_valid)
    z_tc = _block_zscore_f32(rad_tc, block_id, rad_valid)
    z_uth = _block_zscore_f32(ext_uth, block_id, rad_valid & (ext_uth > 0))
    z_uk = _block_zscore_f32(ext_uk, block_id, rad_valid & (ext_uk > 0))
    del block_id, rad_k, rad_th, rad_u, rad_tc, ext_uk, ext_uth, rad_valid

    # Ch 3: 214Bi Radon-Radium conduit excess = block-standardized eU residualized on immobile eTh
    radon_excess = np.maximum(
        np.float32(0.50) * (z_u - np.float32(0.72) * z_th)
        + np.float32(0.30) * z_uth
        + np.float32(0.20) * z_uk,
        np.float32(0.0),
    )
    del z_u, z_uth, z_uk
    rn_kneg1, _ = spcp.principal_negative_curvature_and_strike(radon_excess, sigma=1.3)
    rn_kneg2, _ = spcp.principal_negative_curvature_and_strike(radon_excess, sigma=2.4)
    radon_crest = spcp.robust_unit_f32(
        mdrc.directional_chain_max(
            (np.float32(0.45) * gaussian_filter(radon_excess, sigma=1.1, mode="nearest")
             + np.float32(0.35) * spcp.robust_unit_f32(rn_kneg1, foot, pct=99.4)
             + np.float32(0.20) * spcp.robust_unit_f32(rn_kneg2, foot, pct=99.4))
            * non_playa_gate
            * (np.float32(0.30) + np.float32(0.70) * tiger_clean),
            foot,
            halflen=2,
        ),
        foot,
        pct=99.5,
    )
    mm[:, :, 3] = radon_crest
    del radon_excess, rn_kneg1, rn_kneg2

    # Ch 4: Concentric DoG Silica-Leached Core (-z_tc, sigma=1.5) / Potassic Adularia Halo (+z_k - 0.65*z_th, sigma=5.0)
    potassic_blk = np.maximum(z_k - np.float32(0.65) * z_th, np.float32(0.0))
    silica_core = np.maximum(
        gaussian_filter(-z_tc, sigma=1.5, mode="nearest") - gaussian_filter(-z_tc, sigma=5.5, mode="nearest"),
        np.float32(0.0),
    )
    potassic_halo = gaussian_filter(potassic_blk, sigma=4.8, mode="nearest")
    del z_k, z_th, z_tc, potassic_blk
    dog_sil_pot = spcp.robust_unit_f32(
        np.sqrt(np.maximum(silica_core * np.maximum(potassic_halo, np.float32(0.05)), np.float32(0.0)))
        * non_playa_gate
        * (np.float32(0.35) + np.float32(0.65) * tiger_clean),
        foot,
        pct=99.5,
    )
    mm[:, :, 4] = dog_sil_pot
    del silica_core, potassic_halo

    # Ch 5: BLM Historic Hydrothermal Lode & Geothermal Claim Proximity x PF/GDR Vent Corroboration
    with rasterio.open(ddir / "external" / "blm_closed_claim_distance_m.tif") as ds:
        blm_dist_m = ds.read(1).astype(np.float32)
    blm_valid = foot & np.isfinite(blm_dist_m) & (blm_dist_m >= 0.0)
    blm_prox = np.where(blm_valid, np.exp(-np.clip(blm_dist_m, 0.0, 15000.0) / np.float32(1200.0)), np.float32(0.0))
    del blm_dist_m, blm_valid
    gdr_vent = np.maximum(
        np.asarray(trhv_mm[:, :, 0], dtype=np.float32),
        np.asarray(trhv_mm[:, :, 2], dtype=np.float32),
    )
    blm_conduit = spcp.robust_unit_f32(
        blm_prox
        * (np.float32(0.45) * grav_persist + np.float32(0.35) * rtp_persist + np.float32(0.20) * np.maximum(gdr_vent, radon_crest))
        * non_playa_gate
        * (np.float32(0.35) + np.float32(0.65) * tiger_clean),
        foot,
        pct=99.5,
    )
    mm[:, :, 5] = blm_conduit
    del blm_prox, gdr_vent, non_playa_gate
    gc.collect()
    log("  [FBGR] ch 3..5 (GeoDAWN 4-block 214Bi radon + silica/potassic DoG + BLM claims) built")

    # --- Ch 6: Azimuthal Transtensional Slip-Dilation & Seismic Coupling on Basement PF Strike ---
    geod_i2 = _clean_base(3)      # Band 04: geod_2ndinv
    geod_sh = _clean_base(6)      # Band 07: geod_shearrate
    geod_dl = _clean_base(7)      # Band 08: geod_dilaterate
    deq = _clean_base(9)          # Band 10: deq_n100a15
    ieq = _clean_base(15)         # Band 16: ieq_n100a15

    _, gy_sh, gx_sh = _hgrad_mag_and_vec(geod_sh + np.float32(0.6) * np.maximum(geod_dl, np.float32(-5.0)), sigma=3.0)
    theta_eps = np.arctan2(gy_sh, gx_sh + np.float32(1e-12)).astype(np.float32)
    del gy_sh, gx_sh
    # Morris et al. (1996) slip-dilation obliquity sin^2(2 * (theta_PF - theta_strain))
    obliq_sin2 = (np.sin(np.float32(2.0) * (strike_pf - theta_eps)) ** 2).astype(np.float32)
    del theta_eps
    seis_act = spcp.robust_unit_f32(
        np.log1p(np.maximum(deq, np.float32(0.0))) * np.sqrt(np.maximum(ieq, np.float32(0.0))),
        foot,
        pct=99.2,
    )
    strain_mag = spcp.robust_unit_f32(
        np.maximum(geod_sh, np.float32(0.0)) * np.maximum(geod_dl + np.float32(3.0), np.float32(0.0))
        / (geod_i2 + np.float32(8.0)),
        foot,
        pct=99.2,
    )
    del geod_i2, geod_sh, geod_dl, deq, ieq
    morris_obliq = spcp.robust_unit_f32(
        (np.float32(0.55) * grav_persist + np.float32(0.45) * rtp_persist)
        * (np.float32(0.35) + np.float32(0.65) * obliq_sin2)
        * (np.float32(0.50) * strain_mag + np.float32(0.50) * seis_act),
        foot,
        pct=99.5,
    )
    mm[:, :, 6] = morris_obliq
    del obliq_sin2, seis_act, strain_mag, strike_pf

    # --- Ch 7..9: Strictly LiDAR-Free Multi-Scale Corridor Context (500 m, 1.5 km, 2 km, 3 km) ---
    pf_concord = np.asarray(spcp_mm[:, :, 4], dtype=np.float32)
    cond_edge = np.asarray(spcp_mm[:, :, 9], dtype=np.float32)
    hydro_breach = np.asarray(spcp_mm[:, :, 11], dtype=np.float32)
    dem_r1 = np.maximum(np.asarray(base_mm[:, :, 21], dtype=np.float32), np.float32(0.0))
    dem_r2 = np.maximum(np.asarray(base_mm[:, :, 22], dtype=np.float32), np.float32(0.0))
    dem100_crest = spcp.robust_unit_f32(np.float32(0.6) * dem_r1 + np.float32(0.4) * dem_r2, foot, pct=99.4)
    del dem_r1, dem_r2

    subsurf_seed = (
        np.float32(0.30) * grav_persist
        + np.float32(0.24) * rtp_persist
        + np.float32(0.22) * pf_concord
        + np.float32(0.14) * dem100_crest
        + np.float32(0.10) * np.maximum(radon_crest, hydro_breach)
    ).astype(np.float32)

    chain_500m = mdrc.directional_chain_max(subsurf_seed, foot, halflen=3)
    blur_500m = gaussian_filter(subsurf_seed, sigma=5.0, mode="nearest")
    blur_1500m = gaussian_filter(subsurf_seed, sigma=15.0, mode="nearest")
    ctx_aniso = spcp.robust_unit_f32(
        chain_500m * (np.float32(0.55) + np.float32(0.45) * blur_1500m)
        + np.float32(0.35) * np.maximum(chain_500m - blur_500m, np.float32(0.0)),
        foot,
        pct=99.5,
    )
    mm[:, :, 7] = ctx_aniso
    del chain_500m, blur_500m, blur_1500m

    reg_3km = gaussian_filter(subsurf_seed, sigma=30.0, mode="nearest")
    loc_prom = np.maximum(subsurf_seed - np.float32(0.65) * reg_3km, np.float32(0.0)) + np.float32(0.25) * spcp.robust_unit_f32(
        cond_edge, foot, pct=99.4
    )
    mm[:, :, 8] = spcp.robust_unit_f32(loc_prom, foot, pct=99.5)
    del reg_3km, loc_prom, subsurf_seed, cond_edge

    # Ch 9: Multi-physics independent domain corroboration soft-count (6 domains, strictly LiDAR-free)
    dom_topo100 = spcp._sigmoid_f32((dem100_crest - np.float32(0.28)) / np.float32(0.10))
    dom_grav = spcp._sigmoid_f32((grav_persist - np.float32(0.26)) / np.float32(0.10))
    dom_mag = spcp._sigmoid_f32((rtp_persist - np.float32(0.26)) / np.float32(0.10))
    dom_rad = spcp._sigmoid_f32((np.maximum(radon_crest, dog_sil_pot) - np.float32(0.26)) / np.float32(0.10))
    dom_therm = spcp._sigmoid_f32((np.maximum(hydro_breach, blm_conduit) - np.float32(0.24)) / np.float32(0.10))
    dom_strain = spcp._sigmoid_f32((morris_obliq - np.float32(0.24)) / np.float32(0.10))
    soft_count = (dom_topo100 + dom_grav + dom_mag + dom_rad + dom_therm + dom_strain) / np.float32(6.0)
    del dom_topo100, dom_grav, dom_mag, dom_rad, dom_therm, dom_strain, pf_concord, hydro_breach
    mm[:, :, 9] = spcp.robust_unit_f32(
        np.float32(0.55) * soft_count + np.float32(0.45) * gaussian_filter(soft_count, sigma=12.0, mode="nearest"),
        foot,
        pct=99.5,
    )
    del soft_count, dem100_crest, elev_slope, depth_base

    # --- Ch 10: 1 m LiDAR De-Confounded Scarp 1 km Directional Chain (inside lidar_valid) ---
    lidar_clean = np.asarray(trhv_mm[:, :, 5], dtype=np.float32)
    lidar_valid = np.asarray(spcp_mm[:, :, 12], dtype=np.float32) > 0.5
    lidar_chain1k = mdrc.directional_chain_max(lidar_clean, foot, halflen=4)
    mm[:, :, 10] = np.where(
        lidar_valid & foot,
        spcp.robust_unit_f32(
            np.float32(0.60) * lidar_chain1k + np.float32(0.40) * gaussian_filter(lidar_clean, sigma=6.0, mode="nearest"),
            lidar_valid & foot,
            pct=99.5,
        ),
        np.float32(0.0),
    ).astype(np.float32)
    del lidar_clean, lidar_valid, lidar_chain1k

    # --- Ch 11: Unified Strictly LiDAR-Free 100 m Basement + Geothermal + Radon Conduit Crest ---
    svd_wall = np.asarray(ldgi_mm[:, :, 5], dtype=np.float32)
    unsup_sub = (
        np.float32(0.26) * grav_persist
        + np.float32(0.22) * rtp_persist
        + np.float32(0.14) * dip_asymm
        + np.float32(0.12) * radon_crest
        + np.float32(0.08) * dog_sil_pot
        + np.float32(0.08) * blm_conduit
        + np.float32(0.10) * np.maximum(morris_obliq, svd_wall)
    ) * (np.float32(0.45) + np.float32(0.55) * ctx_aniso) * (np.float32(0.30) + np.float32(0.70) * tiger_clean)
    mm[:, :, 11] = spcp.robust_unit_f32(unsup_sub, foot, pct=99.5)
    del grav_persist, rtp_persist, dip_asymm, radon_crest, dog_sil_pot, blm_conduit, morris_obliq, ctx_aniso, svd_wall, tiger_clean, unsup_sub

    if hasattr(mm, "flush"):
        mm.flush()
    gc.collect()

    meta: dict[str, Any] = {
        "channels": list(FBGR_EXTRA_CHANNELS),
        "shape": [h, w, len(FBGR_EXTRA_CHANNELS)],
        "dtype": "float32",
        "label_free": True,
        "fourier_upward_continuation_heights_m": [500.0, 2000.0],
        "geodawn_block_normalization": "4 contractor blocks (Winnemucca, Fallon, Hawthorne, Tonopah)",
        "msub_pure_non_lidar_col_count": len(MSUB_COL_INDICES),
    }
    receipt_path.write_text(json.dumps(meta, indent=2) + "\n")
    log("  [FBGR] ch 6..11 (Morris obliquity + multi-scale corridor context + conduit crest) built")
    return open_memmap(out_path, mode="r"), meta


def gather_83ch(
    base_stack: np.ndarray,
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    fbgr_stack: np.ndarray,
    ys: np.ndarray,
    xs: np.ndarray,
    col_indices: tuple[int, ...] | None = None,
) -> np.ndarray:
    xb = np.asarray(base_stack[ys, xs, :], dtype=np.float32)
    xs_arr = np.asarray(spcp_stack[ys, xs, :], dtype=np.float32)
    xt = np.asarray(trhv_stack[ys, xs, :], dtype=np.float32)
    xl = np.asarray(ldgi_stack[ys, xs, :], dtype=np.float32)
    xf = np.asarray(fbgr_stack[ys, xs, :], dtype=np.float32)
    full = np.hstack([xb, xs_arr, xt, xl, xf])
    if col_indices is not None:
        return full[:, col_indices]
    return full


def run_leakage_canary_83ch(
    base_stack: np.ndarray,
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    fbgr_stack: np.ndarray,
    base_names: list[str],
    ctx,
    max_auc: float = 0.90,
    stride: int = 4,
) -> dict[str, Any]:
    """Protocol Rule 4 single-feature two-polarity leakage canary across all 83 channels."""
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

    stacks = (base_stack, spcp_stack, trhv_stack, ldgi_stack, fbgr_stack)
    offsets = np.cumsum([0] + [s.shape[2] for s in stacks])
    all_names = (
        list(base_names)
        + list(spcp.SPCP_EXTRA_CHANNELS)
        + list(trhv.TRHV_EXTRA_CHANNELS)
        + list(ldgi.LDGI_EXTRA_CHANNELS)
        + list(FBGR_EXTRA_CHANNELS)
    )
    assert len(all_names) == int(offsets[-1]) == 83

    rows = []
    for i, name in enumerate(all_names):
        s_idx = int(np.searchsorted(offsets[1:], i, side="right"))
        plane = stacks[s_idx][:, :, i - int(offsets[s_idx])]
        vals = np.concatenate([plane[py, px], plane[ny, nx]]).astype(np.float64)
        vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
        if np.ptp(vals) <= 1e-12:
            raw_auc, auc_dir = 0.5, 0.5
        else:
            raw_auc = float(roc_auc_score(y_true, vals))
            auc_dir = max(raw_auc, 1.0 - raw_auc)
        rows.append(
            {
                "index": i,
                "channel": name,
                "in_msub_pure_non_lidar": i in MSUB_COL_INDICES,
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


def fit_fbgr_classifier(
    base_stack: np.ndarray,
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    fbgr_stack: np.ndarray,
    train_region: np.ndarray,
    visible_train: np.ndarray,
    foot: np.ndarray,
    col_indices: tuple[int, ...] | None = None,
    seed: int = 48,
    max_pos: int = 44_000,
    n_neg_hard: int = 88_000,
    n_neg_unif: int = 88_000,
) -> HistGradientBoostingClassifier:
    """Fit a fold-local hard+uniform-negative `HistGradientBoostingClassifier` on `83` or `71` columns."""
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

    X = gather_83ch(base_stack, spcp_stack, trhv_stack, ldgi_stack, fbgr_stack, ys, xs, col_indices=col_indices)
    clf = HistGradientBoostingClassifier(
        max_iter=175,
        learning_rate=0.052,
        max_leaf_nodes=47,
        min_samples_leaf=85,
        l2_regularization=3.0,
        early_stopping=False,
        random_state=seed,
    )
    clf.fit(X, y)
    del X, y, ys, xs
    return clf


def predict_chunked_fbgr(
    clf: HistGradientBoostingClassifier,
    base_stack: np.ndarray,
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    fbgr_stack: np.ndarray,
    mask: np.ndarray,
    col_indices: tuple[int, ...] | None = None,
    chunk_size: int = 180_000,
) -> np.ndarray:
    out = np.zeros(mask.shape, dtype=np.float32)
    ys, xs = np.nonzero(mask)
    for start in range(0, ys.size, chunk_size):
        sl = slice(start, min(start + chunk_size, ys.size))
        X = gather_83ch(
            base_stack, spcp_stack, trhv_stack, ldgi_stack, fbgr_stack, ys[sl], xs[sl], col_indices=col_indices
        )
        out[ys[sl], xs[sl]] = clf.predict_proba(X)[:, 1].astype(np.float32)
        del X
    return out


def calibrate_msub_to_mfull_quantiles(
    p_full: np.ndarray,
    p_sub: np.ndarray,
    calib_lidar_valid: np.ndarray,
    calib_lidar_gap: np.ndarray,
    target_gap_mask: np.ndarray,
    blend_raw: float = 0.25,
) -> np.ndarray:
    """Fold-local monotone quantile calibration mapping `M_Sub` (`~lidar_valid`) onto `M_Full`'s scale.

    Uses ONLY `calib_*` (`train_region`) pixels to fit the 257-knot quantile transfer curve so zero
    test-quadrant distribution information leaks. Preserves `blend_raw` raw probability contrast
    while eliminating systematic gap under-confidence.
    """
    out = p_full.copy()
    if not target_gap_mask.any():
        return out
    ref_vals = p_full[calib_lidar_valid][::3]
    src_vals = p_sub[calib_lidar_gap][::3]
    if ref_vals.size < 64 or src_vals.size < 64:
        out[target_gap_mask] = p_sub[target_gap_mask]
        return out

    qs = np.linspace(0.0, 100.0, 257)
    src_knots = np.percentile(src_vals, qs).astype(np.float32)
    ref_knots = np.percentile(ref_vals, qs).astype(np.float32)
    uk, idx = np.unique(src_knots, return_index=True)
    if uk.size < 4:
        out[target_gap_mask] = p_sub[target_gap_mask]
        return out

    mapped = np.interp(p_sub[target_gap_mask], uk, ref_knots[idx]).astype(np.float32)
    w_raw = np.float32(blend_raw)
    out[target_gap_mask] = np.clip((np.float32(1.0) - w_raw) * mapped + w_raw * p_sub[target_gap_mask], 0.0, 1.0)
    return out


def build_stationary_fbgr_surface(
    p_dual: np.ndarray,
    fbgr_stack: np.ndarray,
    trhv_stack: np.ndarray,
    visible_mask: np.ndarray,
    foot: np.ndarray,
    region_mask: np.ndarray | None = None,
    w_unsup_conduit: float = 0.14,
    w_tip_relay: float = 0.48,
    sharpen_crest: bool = True,
    crest_boost: float = 0.45,
) -> np.ndarray:
    """Stationary unified pre-placement belief surface (identical formula on OOF folds and full map).

    Crucially uses ZERO `eta` holdout-vs-live censorship switch (`IR-48-CCAA-01`) and ZERO `s63`
    blend, combining:
      - Dual-Cover OOF posterior `p_dual` (`M_Full` on `lidar_valid` + calibrated `M_Sub` on `~lidar_valid`),
      - Strictly LiDAR-free physical basement/radon/geothermal conduit crest (`fbgr_stack[:, :, 11]`),
      - Bounded fold-local anisotropic tip/relay continuation (`ldgi.anisotropic_tip_relay_cone`),
      - Anthropogenic TIGER road prism damping (`trhv_stack[:, :, 4]`), and
      - Optional probability-contrast-preserving 4-azimuth NMS crest sharpening (`sharpen_probability_crest`).
    """
    if region_mask is None:
        region_mask = foot
    mask = region_mask & foot
    relay = ldgi.anisotropic_tip_relay_cone(visible_mask, foot)
    conduit_crest = np.asarray(fbgr_stack[:, :, 11], dtype=np.float32)
    tiger_clean = np.asarray(trhv_stack[:, :, 4], dtype=np.float32)

    surf = np.zeros(foot.shape, dtype=np.float32)
    pd = p_dual[mask]
    cc = conduit_crest[mask]
    rl = relay[mask]
    tg = tiger_clean[mask]

    w_c = np.float32(w_unsup_conduit)
    w_r = np.float32(w_tip_relay)
    base_p = (np.float32(1.0) - w_c) * pd + w_c * (cc * np.sqrt(np.maximum(pd, np.float32(0.02))))
    surf[mask] = base_p * (np.float32(1.0) + w_r * rl) * (np.float32(0.35) + np.float32(0.65) * tg)
    del relay, pd, cc, rl, tg, base_p

    if sharpen_crest:
        surf = sharpen_probability_crest(surf, mask, crest_boost=crest_boost)
    return np.clip(surf, 0.0, 1.0).astype(np.float32)


def emit_fbgr_submodular(
    surface: np.ndarray,
    visible_mask: np.ndarray,
    eligible_mask: np.ndarray,
    foot: np.ndarray,
    budget: int = TARGET_BUDGET,
    min_sep_px: float = AXIAL_MIN_SEP_PX,
    b_collar_px: float = B_COLLAR_PX,
    support_mult: int = 9,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Emit `budget` off-catalogue dots via shared `gems32.emitter.emit` with `min_sep_px` guard.

    Uses `support_mult = 9` (`~338,886` candidate crest pixels on the full map) so `min_sep_px = 2.8`
    (`~24.6` blocked pixels per accepted dot if dense, ~6 along 1-px crests) never exhausts candidate
    pool headroom short of `37,654` dots (`IR-2026-10-26-04` guard).
    """
    if budget <= 0 or not (eligible_mask & foot).any():
        return np.zeros(surface.shape, dtype=bool), {"n_emitted": 0, "stopped_by": "zero_budget"}

    vis = np.asarray(visible_mask, bool) & foot
    d_vis = distance_transform_edt(~vis).astype(np.float32)
    elig = eligible_mask & foot & (d_vis > float(b_collar_px)) & (surface > 0.0)
    del d_vis

    n_elig = int(elig.sum())
    if n_elig == 0:
        return np.zeros(surface.shape, dtype=bool), {"n_emitted": 0, "stopped_by": "empty_eligible"}

    max_sup = max(int(budget) * int(support_mult), min(n_elig, 45_000))
    if n_elig > max_sup:
        vals = surface[elig]
        thr = float(np.partition(vals, n_elig - max_sup)[n_elig - max_sup])
        sup = elig & (surface >= thr)
        del vals
    else:
        sup = elig

    # Contrast power p^1.35 sharpens submodular marginal ordering without flattening ranks
    field = np.where(sup, np.power(np.maximum(surface, 0.0), 1.35), 0.0).astype(np.float64)
    del elig, sup
    dots, elog = emitter.emit(
        field,
        budget=int(budget),
        prior_dti=0.0,
        gain_floor=0.0,
        min_sep_px=float(min_sep_px),
    )
    del field
    return dots, elog.as_dict()
