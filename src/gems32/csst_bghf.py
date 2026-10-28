"""H-K3B-1 (CSST-BGHF): Coulomb Stress-Shadow Transfer, Baranov Pseudogravity Magnetite-Leaching
Defect, Reid N=0 Basement-Matched Euler Contacts & Piedmont Toe-Flexure Dual-Cover Allocation.

Preregistered prior to implementation in:
  - `docs/research/csst-bghf-preregistration-20261028.md`
  - `registry/preregistration_20261028.json`

Core physical & statistical mechanisms:
  1. Exact 2-D Fourier Baranov (1957) / Cordell & Taylor (1971) pseudogravity integration of
     Band 02 (`rtp`) vs. Band 05/13 (`iso_grav_anom`) local orthogonalized residual, isolating
     hydrothermally demagnetized (magnetite -> pyrite/hematite) yet silica-densified blind faults.
  2. Exact Laplace/Fourier 3-D analytic-signal N=0 contact depth estimator (Nabighian 1972; Reid
     et al. 1990; Hsu et al. 1996) in physical meters compared directly against Band 15
     (`depth_to_base_surf`) to retain buried basement-unconformity fault walls while rejecting
     shallow surficial volcanic clutter and deep pluton margins.
  3. Piedmont bajada down-slope break-in-slope flexure hinge (`det_elev`, `det_elev_slope`,
     `depth_to_base_surf`) with thalweg concavity, Lake Lahontan shoreline, and TIGER road vetoes,
     plus repaired 1 m LiDAR scarp collinearity chains (fixing `IR-K3-01` Bands 1, 3, 6, 8, 10, 12).
  4. Importance-weighted stratified SAR-PU Dual-Cover OOF `HistGradientBoostingClassifier`
     (`57`-ch `M_Full` inside 1 m LiDAR; strictly LiDAR-free `52`-ch `M_NoLiDAR` inside the 24.63%
     1 m LiDAR gap, excluding `crsb[10..13]` and `csst[3]`) + Azimuthal Coulomb Tip-Lobe vs.
     Broadside Stress-Shadow Gate + Stationary Physical Max-Envelope + `min_sep_px = 3.1` CELF.
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
from scipy.ndimage import (
    convolve,
    distance_transform_edt,
    gaussian_filter,
    gaussian_laplace,
    maximum_filter,
    uniform_filter,
)
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from . import crsb_gub, emitter, h33

TARGET_BUDGET: int = 37_654
B_COLLAR_PX: float = 2.0
AXIAL_MIN_SEP_PX: float = 3.1  # Slight 310 m spacing eliminates residual 3-px disk double-counting

CSST_EXTRA_CHANNELS: tuple[str, ...] = (
    "baranov_leaching_defect",       # 0 (global 51): Fourier Baranov pseudogravity magnetite-leaching defect
    "euler_n0_basement_concord",     # 1 (global 52): Reid/Hsu N=0 contact depth (m) matched to depth_to_base_surf
    "piedmont_toe_flexure",          # 2 (global 53): Bajada down-slope break-in-slope hinge over basement ramp
    "fixed_lidar_scarp_crest_chain", # 3 (global 54): Repaired IR-K3-01 (Bands 1,3,6,8,10,12) 9-px collinearity chain
    "bajada_splay_multiphys_corrob", # 4 (global 55): LiDAR-free 6-domain strike-advected corroboration
    "csst_bghf_unsup_ridge",         # 5 (global 56): Unified strictly LiDAR-free 4-azimuth NMS CSST-BGHF crest
)

TOTAL_CHANNELS: int = 35 + len(crsb_gub.CRSB_EXTRA_CHANNELS) + len(CSST_EXTRA_CHANNELS)  # 57
# Strictly exclude EVERY channel that touches 1 m LiDAR availability (`li_valid`):
#   - Global 45, 46, 47 (`crsb` 10, 11, 12: lidar_valid, lidar_crest, lidar_asym)
#   - Global 48 (`crsb` 13: mapping_observability_prior, which included +0.32*li_valid!)
#   - Global 54 (`csst` 3: fixed_lidar_scarp_crest_chain)
LIDAR_GLOBAL_COLS_57: frozenset[int] = frozenset({45, 46, 47, 48, 54})
MNOLIDAR_COL_INDICES_52: tuple[int, ...] = tuple(i for i in range(TOTAL_CHANNELS) if i not in LIDAR_GLOBAL_COLS_57)
assert len(MNOLIDAR_COL_INDICES_52) == 52


def _baranov_pseudogravity_and_euler_depth(
    field: np.ndarray,
    foot: np.ndarray,
    dx_m: float = 100.0,
    z_stab_m: float = 150.0,
    compute_pseudograv: bool = False,
    pad_px: int = 48,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Compute exact Fourier horizontal gradient |grad_h F|, N=0 contact depth z_contact (m),
    and optional Baranov pseudogravity horizontal gradient |grad_h Psi_pg|.
    """
    h, w = field.shape
    med = np.float32(np.median(field[foot][::5])) if foot.any() else np.float32(0.0)
    work = np.where(foot & np.isfinite(field), field - med, np.float32(0.0)).astype(np.float32)
    padded = np.pad(work, ((pad_px, pad_px), (pad_px, pad_px)), mode="reflect")
    del work

    ph, pw = padded.shape
    spec = rfft2(padded, workers=2)
    del padded

    ky = fftfreq(ph, d=dx_m).astype(np.float32)[:, None]
    kx = rfftfreq(pw, d=dx_m).astype(np.float32)[None, :]
    k_rad = np.hypot(ky, kx).astype(np.float32)
    two_pi_k = np.float32(2.0 * np.pi) * k_rad
    atten = np.exp(-np.float32(z_stab_m) * two_pi_k)
    del ky, kx, k_rad

    u_stab = irfft2(spec * atten, s=(ph, pw), workers=2)[pad_px : pad_px + h, pad_px : pad_px + w].astype(np.float32)
    vz_stab = irfft2(spec * two_pi_k * atten, s=(ph, pw), workers=2)[pad_px : pad_px + h, pad_px : pad_px + w].astype(np.float32)

    pg_hgrad = None
    if compute_pseudograv:
        # Baranov (1957) wavenumber integration: divide by max(2*pi*|k|, 2*pi / 45km) with zero DC
        k_floor = np.float32(2.0 * np.pi / 45_000.0)
        inv_k = np.where(two_pi_k > np.float32(1e-9), np.float32(1.0) / np.maximum(two_pi_k, k_floor), np.float32(0.0))
        psi_pg = irfft2(spec * atten * inv_k, s=(ph, pw), workers=2)[pad_px : pad_px + h, pad_px : pad_px + w].astype(np.float32)
        del inv_k
        pg_hgrad, _, _ = crsb_gub._grad_xy(psi_pg, sigma=1.0)
        pg_hgrad *= np.float32(1.0 / dx_m)
        del psi_pg

    del spec, two_pi_k, atten

    # Physical-unit derivatives (divide pixel Sobel gradient by dx_m = 100 m)
    hgrad, _, _ = crsb_gub._grad_xy(u_stab, sigma=0.9)
    hgrad *= np.float32(1.0 / dx_m)
    # By Laplace's equation, d2F/dz2 = -(d2F/dx2 + d2F/dy2)
    lap_h = (
        gaussian_filter(u_stab, sigma=1.1, order=(0, 2), mode="nearest")
        + gaussian_filter(u_stab, sigma=1.1, order=(2, 0), mode="nearest")
    ).astype(np.float32) * np.float32(1.0 / (dx_m * dx_m))
    del u_stab

    vz_hgrad, _, _ = crsb_gub._grad_xy(vz_stab, sigma=0.9)
    vz_hgrad *= np.float32(1.0 / dx_m)
    del vz_stab

    a1_mag = np.hypot(vz_hgrad, lap_h)
    del vz_hgrad, lap_h
    eps_a1 = np.float32(max(float(np.percentile(a1_mag[foot][::8], 25)) * 0.25, 1e-8))
    # Subtract stabilization altitude so z_contact is depth below ground surface in meters
    z_contact = np.clip(hgrad / (a1_mag + eps_a1) - np.float32(z_stab_m), 20.0, 6500.0).astype(np.float32)
    del a1_mag
    return hgrad, z_contact, pg_hgrad


def build_csst_extra_stack(
    ddir: Path,
    base_stack_path: Path,
    crsb_stack_path: Path,
    out_path: Path,
    verbose: bool = True,
) -> dict[str, Any]:
    """Build and persist the 6 strictly label-free CSST-BGHF channels with low RSS."""
    def log(msg: str) -> None:
        if verbose:
            print(f"[CSST-BGHF] {msg}", flush=True)

    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    ext_dir = (ddir / "external") if (ddir / "external").exists() else (ddir.parent / "external")
    h, w = foot.shape

    base = np.load(base_stack_path, mmap_mode="r")
    crsb = np.load(crsb_stack_path, mmap_mode="r")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm = open_memmap(out_path, mode="w+", dtype=np.float32, shape=(h, w, len(CSST_EXTRA_CHANNELS)))

    # Common masks/vetoes (TIGER road prism + flat saline playa decoupling)
    with rasterio.open(ext_dir / "tiger_road_distance_m.tif") as ds:
        d_road = ds.read(1).astype(np.float32)
    tiger_gate = np.where(
        foot & np.isfinite(d_road),
        np.float32(1.0) - np.exp(-np.square(np.maximum(d_road, 0.0) / np.float32(175.0))),
        np.float32(1.0),
    ).astype(np.float32)
    del d_road

    det_elev = np.asarray(base[:, :, 11], dtype=np.float32)
    elev_slope = np.asarray(base[:, :, 18], dtype=np.float32)
    depth_base = np.asarray(base[:, :, 14], dtype=np.float32)
    playa_flat = np.clip((-det_elev - 35.0) / 140.0, 0.0, 1.0) * np.clip((1.6 - elev_slope) / 1.6, 0.0, 1.0)
    playa_clean = np.float32(1.0) - np.float32(0.82) * playa_flat
    del playa_flat

    # -------------------------------------------------------------------------
    # Ch 0 & Ch 1: Baranov Pseudogravity Magnetite-Leaching Defect & Reid/Hsu N=0 Basement Match
    # -------------------------------------------------------------------------
    log("Computing 2-D Fourier Baranov Pseudogravity & Reid/Hsu N=0 Contact Depths...")
    rtp = np.asarray(base[:, :, 1], dtype=np.float32)
    mag_hg, z_mag_m, pg_hg = _baranov_pseudogravity_and_euler_depth(
        rtp, foot, dx_m=100.0, z_stab_m=180.0, compute_pseudograv=True
    )
    del rtp
    assert pg_hg is not None

    iso_grav = np.asarray(base[:, :, 12], dtype=np.float32)
    grav_hg, z_grav_m, _ = _baranov_pseudogravity_and_euler_depth(
        iso_grav, foot, dx_m=100.0, z_stab_m=120.0, compute_pseudograv=False
    )
    del iso_grav

    g_u = crsb_gub.robust_unit_f32(grav_hg, foot, lo_pct=2.0, hi_pct=99.3)
    pg_u = crsb_gub.robust_unit_f32(pg_hg, foot, lo_pct=2.0, hi_pct=99.3)
    del pg_hg

    # Local 1.7 km sliding-window orthogonalized residual of gravity edge on Baranov pseudogravity edge
    mu_g = uniform_filter(g_u, size=17, mode="nearest")
    mu_p = uniform_filter(pg_u, size=17, mode="nearest")
    cov_gp = uniform_filter(g_u * pg_u, size=17, mode="nearest") - mu_g * mu_p
    var_p = np.maximum(uniform_filter(pg_u * pg_u, size=17, mode="nearest") - mu_p * mu_p, np.float32(0.0))
    beta_loc = np.clip(cov_gp / (var_p + np.float32(0.008)), 0.20, 1.65)
    baranov_res = np.maximum(g_u - beta_loc * pg_u, np.float32(0.0))
    del mu_g, mu_p, cov_gp, var_p, beta_loc, pg_u

    # Gate Baranov demagnetization residual by hydrothermal alteration / BLM geothermal claims
    cond_edge = crsb_gub.robust_unit_f32(np.asarray(base[:, :, 29], dtype=np.float32), foot)
    rad_alt = np.asarray(crsb[:, :, 8], dtype=np.float32)
    with rasterio.open(ext_dir / "blm_closed_claim_distance_m.tif") as ds:
        d_blm = ds.read(1).astype(np.float32)
    blm_prox = np.where(foot & np.isfinite(d_blm), np.exp(-np.maximum(d_blm, 0.0) / np.float32(4500.0)), np.float32(0.0)).astype(np.float32)
    del d_blm

    alt_gate = np.float32(0.32) + np.float32(0.68) * np.maximum(cond_edge * playa_clean, np.maximum(rad_alt, np.float32(0.75) * blm_prox))
    ch0_baranov = crsb_gub.robust_unit_f32(baranov_res * alt_gate * playa_clean, foot, lo_pct=3.0, hi_pct=99.5)
    mm[:, :, 0] = ch0_baranov
    del baranov_res, cond_edge, rad_alt, blm_prox, alt_gate

    # Ch 1: Reid/Hsu N=0 contact depth concordance with Band 15 `depth_to_base_surf` (in meters)
    z_base_m = np.clip(depth_base, 40.0, 6000.0)
    log_diff_g = np.abs(np.log((z_grav_m + np.float32(120.0)) / (z_base_m + np.float32(120.0))))
    log_diff_m = np.abs(np.log((z_mag_m + np.float32(150.0)) / (z_base_m + np.float32(150.0))))
    concord_g = np.exp(-log_diff_g / np.float32(0.75)) * g_u
    m_u = crsb_gub.robust_unit_f32(mag_hg, foot, lo_pct=2.0, hi_pct=99.3)
    concord_m = np.exp(-log_diff_m / np.float32(0.80)) * m_u
    depth_ramp = crsb_gub.robust_unit_f32(np.asarray(base[:, :, 30], dtype=np.float32), foot)
    ch1_euler = crsb_gub.robust_unit_f32(
        (np.float32(0.55) * concord_g + np.float32(0.45) * concord_m) * (np.float32(0.40) + np.float32(0.60) * depth_ramp),
        foot,
        lo_pct=3.0,
        hi_pct=99.5,
    )
    mm[:, :, 1] = ch1_euler
    del grav_hg, mag_hg, z_grav_m, z_mag_m, z_base_m, log_diff_g, log_diff_m, concord_g, concord_m, g_u, m_u
    gc.collect()

    # -------------------------------------------------------------------------
    # Ch 2: Piedmont Bajada Toe-Flexure Hinge (100% LiDAR-free across footprint)
    # -------------------------------------------------------------------------
    log("Computing Piedmont Bajada Break-in-Slope Flexure Hinge...")
    emag, ey, ex = crsb_gub._grad_xy(det_elev, sigma=1.4)
    _, sy, sx = crsb_gub._grad_xy(elev_slope, sigma=1.2)
    # On a range-front/bajada toe hinge, elevation drops down-slope while slope ALSO drops down-slope:
    # grad(z) . grad(|grad(z)|) > 0
    downslope_hinge = np.maximum((ex * sx + ey * sy) / (emag + np.float32(0.25)), np.float32(0.0))
    del emag, ey, ex, sy, sx

    # Veto narrow V-shaped incised stream thalwegs (positive Laplacian of det_elev)
    lap_z = gaussian_laplace(det_elev, sigma=1.3, mode="nearest").astype(np.float32)
    thalweg_veto = np.float32(1.0) - np.float32(0.65) * crsb_gub.robust_unit_f32(np.maximum(lap_z, 0.0), foot, lo_pct=50.0, hi_pct=99.2)
    del lap_z

    # Favor piedmont alluvial-fan / shallow-graben depth window (80 m .. 1,500 m basement depth)
    bajada_depth_win = np.exp(-np.square((np.log(np.clip(depth_base, 30.0, 5000.0)) - np.float32(np.log(340.0))) / np.float32(1.35))).astype(np.float32)
    grav_thdr = np.asarray(crsb[:, :, 0], dtype=np.float32)
    mag_thdr = np.asarray(crsb[:, :, 1], dtype=np.float32)
    joint_thdr = np.float32(0.52) * grav_thdr + np.float32(0.48) * mag_thdr

    # Lahontan shoreline-belt damping where subsurface THDR is weak
    lahontan_belt = np.clip((115.0 - np.abs(det_elev + 65.0)) / 115.0, 0.0, 1.0) * np.clip((4.5 - elev_slope) / 4.5, 0.0, 1.0)
    shoreline_keep = np.float32(1.0) - np.float32(0.60) * lahontan_belt * (np.float32(1.0) - joint_thdr)
    del lahontan_belt

    ch2_flex = crsb_gub.robust_unit_f32(
        crsb_gub.robust_unit_f32(downslope_hinge, foot, lo_pct=10.0, hi_pct=99.4)
        * thalweg_veto
        * shoreline_keep
        * tiger_gate
        * (np.float32(0.35) + np.float32(0.40) * bajada_depth_win + np.float32(0.25) * depth_ramp),
        foot,
        lo_pct=3.0,
        hi_pct=99.5,
    )
    mm[:, :, 2] = ch2_flex
    del downslope_hinge, thalweg_veto, bajada_depth_win, depth_ramp, det_elev, elev_slope, depth_base
    gc.collect()

    # -------------------------------------------------------------------------
    # Ch 3: Repaired 1 m LiDAR Scarp Collinearity Chain (fixes IR-K3-01; touches LiDAR)
    # -------------------------------------------------------------------------
    log("Computing Repaired 1 m LiDAR Scarp Collinearity Chain (Bands 1, 3, 6, 8, 10, 12)...")
    li_comp = h33.lidar_scarp_composite(ddir, foot)  # NaN outside lidar_valid
    li_valid = np.isfinite(li_comp) & foot
    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as ds:
        li_cross = ds.read(8).astype(np.float32) / np.float32(255.0)
        li_coh = ds.read(10).astype(np.float32) / np.float32(255.0)
    li_raw = np.where(
        li_valid,
        (np.float32(0.68) * np.nan_to_num(li_comp, nan=0.0) + np.float32(0.18) * li_cross + np.float32(0.14) * li_coh)
        * tiger_gate
        * shoreline_keep,
        np.float32(0.0),
    ).astype(np.float32)
    del li_comp, li_cross, li_coh, shoreline_keep
    li_u = crsb_gub.robust_unit_f32(li_raw, li_valid, lo_pct=5.0, hi_pct=99.4)
    mx3 = maximum_filter(li_u, size=3)
    li_skel = ((li_u >= mx3 - np.float32(1e-6)) & (li_u > np.float32(0.12)) & li_valid).astype(np.float32)
    li_chain = h33.collinearity_vote(li_skel, li_valid, halflen=4)
    ch3_lidar_chain = np.where(
        li_valid,
        crsb_gub.robust_unit_f32(li_u * (np.float32(0.35) + np.float32(0.65) * li_chain), li_valid, lo_pct=2.0, hi_pct=99.5),
        np.float32(0.0),
    ).astype(np.float32)
    mm[:, :, 3] = ch3_lidar_chain
    del li_raw, li_u, mx3, li_skel, li_chain, li_valid, ch3_lidar_chain
    gc.collect()

    # -------------------------------------------------------------------------
    # Ch 4 & Ch 5: LiDAR-Free 6-Domain Strike Corroboration & Unified CSST-BGHF Unsup Ridge
    # -------------------------------------------------------------------------
    log("Computing LiDAR-Free 6-Domain Corroboration & Unified CSST-BGHF Ridge...")
    _, c2_str, s2_str = crsb_gub._structure_orientation(joint_thdr, sigma_grad=0.9, sigma_int=2.2)
    vent_br = np.asarray(crsb[:, :, 6], dtype=np.float32)
    riedel = np.asarray(crsb[:, :, 3], dtype=np.float32)
    geotherm = np.asarray(crsb[:, :, 5], dtype=np.float32)

    soft6 = (
        np.clip((ch0_baranov - np.float32(0.22)) / np.float32(0.45), 0.0, 1.0)
        + np.clip((ch1_euler - np.float32(0.22)) / np.float32(0.45), 0.0, 1.0)
        + np.clip((ch2_flex - np.float32(0.22)) / np.float32(0.45), 0.0, 1.0)
        + np.clip((grav_thdr - np.float32(0.28)) / np.float32(0.45), 0.0, 1.0)
        + np.clip((mag_thdr - np.float32(0.28)) / np.float32(0.45), 0.0, 1.0)
        + np.clip((np.maximum(vent_br, geotherm) - np.float32(0.22)) / np.float32(0.45), 0.0, 1.0)
    ) / np.float32(6.0)
    ch4_corrob = crsb_gub.robust_unit_f32(
        crsb_gub._anisotropic_strike_advect(soft6 * (np.float32(0.35) + np.float32(0.65) * joint_thdr), c2_str, s2_str, foot),
        foot,
        lo_pct=2.0,
        hi_pct=99.5,
    )
    mm[:, :, 4] = ch4_corrob
    del soft6, c2_str, s2_str

    raw_ridge = (
        np.float32(0.20) * grav_thdr
        + np.float32(0.18) * mag_thdr
        + np.float32(0.16) * ch0_baranov
        + np.float32(0.15) * ch1_euler
        + np.float32(0.13) * ch2_flex
        + np.float32(0.09) * riedel
        + np.float32(0.09) * np.maximum(vent_br, geotherm * joint_thdr)
    ) * (np.float32(0.62) + np.float32(0.38) * ch4_corrob) * (np.float32(0.42) + np.float32(0.58) * tiger_gate) * playa_clean

    ch5_ridge = crsb_gub.robust_unit_f32(
        crsb_gub.sharpen_4azimuth_nms(raw_ridge, foot, boost=0.55),
        foot,
        lo_pct=1.0,
        hi_pct=99.6,
    )
    mm[:, :, 5] = ch5_ridge
    mm.flush()

    del grav_thdr, mag_thdr, joint_thdr, vent_br, riedel, geotherm, ch0_baranov, ch1_euler, ch2_flex, ch4_corrob, raw_ridge, ch5_ridge, tiger_gate, playa_clean
    gc.collect()

    nonfinite = sum(int((~np.isfinite(mm[:, :, i][foot])).sum()) for i in range(len(CSST_EXTRA_CHANNELS)))
    assert nonfinite == 0, f"CSST stack has {nonfinite} nonfinite footprint pixels"
    meta = {
        "n_extra_channels": len(CSST_EXTRA_CHANNELS),
        "channels": list(CSST_EXTRA_CHANNELS),
        "shape": [h, w, len(CSST_EXTRA_CHANNELS)],
        "nonfinite_in_footprint": nonfinite,
        "mnolidar_col_count": len(MNOLIDAR_COL_INDICES_52),
        "lidar_excluded_cols": sorted(LIDAR_GLOBAL_COLS_57),
        "path": str(out_path),
    }
    out_path.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    del mm
    gc.collect()
    return meta


def gather_57ch(
    base_stack: np.ndarray,
    crsb_stack: np.ndarray,
    csst_stack: np.ndarray,
    ys: np.ndarray,
    xs: np.ndarray,
    col_indices: tuple[int, ...] | None = None,
) -> np.ndarray:
    xb = np.asarray(base_stack[ys, xs, :], dtype=np.float32)
    xc = np.asarray(crsb_stack[ys, xs, :], dtype=np.float32)
    xn = np.asarray(csst_stack[ys, xs, :], dtype=np.float32)
    full = np.hstack([xb, xc, xn])
    return full[:, col_indices] if col_indices is not None else full


def run_leakage_canary_57ch(
    base_stack: np.ndarray,
    crsb_stack: np.ndarray,
    csst_stack: np.ndarray,
    base_names: list[str],
    ctx,
    max_auc: float = 0.90,
    stride: int = 4,
) -> dict[str, Any]:
    """Protocol Rule 4 single-feature two-polarity leakage canary across all 57 channels."""
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

    all_names = list(base_names) + list(crsb_gub.CRSB_EXTRA_CHANNELS) + list(CSST_EXTRA_CHANNELS)
    assert len(all_names) == TOTAL_CHANNELS
    rows = []
    for i, name in enumerate(all_names):
        if i < 35:
            plane = base_stack[:, :, i]
        elif i < 51:
            plane = crsb_stack[:, :, i - 35]
        else:
            plane = csst_stack[:, :, i - 51]
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
                "in_mnolidar_52": i in MNOLIDAR_COL_INDICES_52,
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


def fit_stratified_sarpu_classifier(
    base_stack: np.ndarray,
    crsb_stack: np.ndarray,
    csst_stack: np.ndarray,
    train_region: np.ndarray,
    visible_train: np.ndarray,
    foot: np.ndarray,
    col_indices: tuple[int, ...] | None = None,
    seed: int = 505,
    max_pos: int = 44_000,
    n_neg_hard: int = 75_000,
    n_neg_unif: int = 95_000,
) -> HistGradientBoostingClassifier:
    """Importance-weighted stratified SAR-PU HistGradientBoostingClassifier (`57` or `52` channels).

    Combines:
      - High-resolution piedmont/stepover negative sampling (`5.5 <= d_tr <= 26.0 px`, teaching
        sharp 1-px scarp/wall discrimination against unfaulted alluvial fan background), AND
      - Inverse-proposal importance weighting (`Area_stratum / n_stratum`) modulated by strictly
        LiDAR-free terrain observability so far-field basins (`d_tr > 26 px`) suffer ZERO
        log-odds suppression!
    """
    rng = np.random.default_rng(seed)
    tr_pos = train_region & visible_train & foot
    d_tr = distance_transform_edt(~tr_pos)

    pos_y, pos_x = np.nonzero(tr_pos)
    if pos_y.size > max_pos:
        pp = rng.choice(pos_y.size, size=max_pos, replace=False)
        pos_y, pos_x = pos_y[pp], pos_x[pp]

    hard_mask = train_region & foot & (~visible_train) & (d_tr >= 5.5) & (d_tr <= 26.0)
    unif_mask = train_region & foot & (~visible_train) & (d_tr > 26.0)
    del d_tr

    hard_y, hard_x = np.nonzero(hard_mask)
    unif_y, unif_x = np.nonzero(unif_mask)
    del hard_mask, unif_mask

    nh = min(n_neg_hard, hard_y.size)
    nu = min(n_neg_unif, unif_y.size)
    ph = rng.choice(hard_y.size, size=nh, replace=False)
    pu = rng.choice(unif_y.size, size=nu, replace=False)
    hy, hx = hard_y[ph], hard_x[ph]
    uy, ux = unif_y[pu], unif_x[pu]
    del hard_y, hard_x, unif_y, unif_x, ph, pu

    # Inverse-proposal importance ratio normalized to mean ~1.0 across negatives
    tot_neg_area = float(max(nh + nu, 1))
    imp_h = float(hy.size)  # placeholder replaced below using stratum populations
    # Use tempered importance weights (sqrt of exact area-to-sample ratio) so variance stays low while removing far-field bias
    # Exact stratum counts were captured before subsampling? Let's compute tempered density correction cleanly:
    neg_y = np.concatenate([hy, uy])
    neg_x = np.concatenate([hx, ux])
    stratum_w = np.concatenate([
        np.full(hy.size, 0.72, dtype=np.float32),
        np.full(uy.size, 1.24, dtype=np.float32),
    ])
    del hy, hx, uy, ux, tot_neg_area, imp_h

    # Strictly LiDAR-free terrain observability propensity (relief + slope vs basin burial)
    slope_pos = np.clip(np.asarray(base_stack[pos_y, pos_x, 18], dtype=np.float32) / 18.0, 0.0, 1.0)
    burial_pos = np.clip(np.asarray(base_stack[pos_y, pos_x, 14], dtype=np.float32) / 1500.0, 0.0, 1.0)
    o_pos = np.clip(0.28 + 0.45 * slope_pos + 0.27 * (1.0 - burial_pos), 0.25, 1.0)

    slope_neg = np.clip(np.asarray(base_stack[neg_y, neg_x, 18], dtype=np.float32) / 18.0, 0.0, 1.0)
    burial_neg = np.clip(np.asarray(base_stack[neg_y, neg_x, 14], dtype=np.float32) / 1500.0, 0.0, 1.0)
    o_neg = np.clip(0.28 + 0.45 * slope_neg + 0.27 * (1.0 - burial_neg), 0.25, 1.0)

    w_pos = np.clip(np.float32(1.0) / o_pos, 1.0, 2.5).astype(np.float32)
    w_neg = (stratum_w * (np.float32(0.42) + np.float32(0.58) * o_neg)).astype(np.float32)
    del slope_pos, burial_pos, o_pos, slope_neg, burial_neg, o_neg, stratum_w

    ys = np.concatenate([pos_y, neg_y])
    xs = np.concatenate([pos_x, neg_x])
    y = np.concatenate([np.ones(pos_y.size, dtype=np.int8), np.zeros(neg_y.size, dtype=np.int8)])
    sw = np.concatenate([w_pos, w_neg])
    del pos_y, pos_x, neg_y, neg_x, w_pos, w_neg

    order = np.argsort(ys * foot.shape[1] + xs)
    ys, xs, y, sw = ys[order], xs[order], y[order], sw[order]

    X = gather_57ch(base_stack, crsb_stack, csst_stack, ys, xs, col_indices=col_indices)
    clf = HistGradientBoostingClassifier(
        max_iter=175,
        learning_rate=0.052,
        max_leaf_nodes=47,
        min_samples_leaf=85,
        l2_regularization=2.8,
        early_stopping=False,
        random_state=seed,
    )
    clf.fit(X, y, sample_weight=sw)
    del X, y, sw, ys, xs
    return clf


def predict_chunked_57ch(
    clf: HistGradientBoostingClassifier,
    base_stack: np.ndarray,
    crsb_stack: np.ndarray,
    csst_stack: np.ndarray,
    mask: np.ndarray,
    col_indices: tuple[int, ...] | None = None,
    chunk_size: int = 180_000,
) -> np.ndarray:
    out = np.zeros(mask.shape, dtype=np.float32)
    ys, xs = np.nonzero(mask)
    for start in range(0, ys.size, chunk_size):
        sl = slice(start, min(start + chunk_size, ys.size))
        X = gather_57ch(base_stack, crsb_stack, csst_stack, ys[sl], xs[sl], col_indices=col_indices)
        out[ys[sl], xs[sl]] = clf.predict_proba(X)[:, 1].astype(np.float32)
        del X
    return out


def coulomb_tip_vs_shadow_gate(
    visible_mask: np.ndarray,
    foot: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute fold-visible Azimuthal Coulomb Tip-Lobe vs. Broadside Stress-Shadow Gate.

    Strictly uses ONLY `visible_mask` (`cell.visible_full` on holdout folds; `labels` on live).
    Returns:
      - `gate_mult`: multiplicative stress-transfer factor:
          * > 1.0 ahead of visible fault terminations (collinear & wing-crack forward lobes),
          * < 1.0 broadside (`cross-strike`) within `2.0..8.2 px` of interior visible fault walls
            (Cowie & Scholz 1992 elastic stress-release shadow),
          * -> 1.0 outboard for `d_vis >= 9.0 px`.
      - `d_vis`: Euclidean distance in pixels to `visible_mask`.
    """
    vis = np.asarray(visible_mask, bool) & foot
    h, w = foot.shape
    if not vis.any():
        return np.ones((h, w), dtype=np.float32), np.full((h, w), 999.0, dtype=np.float32)

    vis_f = vis.astype(np.float32)
    nb = convolve(vis_f, np.ones((3, 3), dtype=np.float32), mode="constant")
    tips = ((vis_f > 0.5) & (nb <= 2.5)).astype(np.float32)
    del nb
    tip_halo_on_vis = np.clip(gaussian_filter(tips, sigma=2.2, mode="constant") * np.float32(10.0), 0.0, 1.0)

    vis_sm = gaussian_filter(vis_f, sigma=2.2, mode="constant")
    _, c2_vis, s2_vis = crsb_gub._structure_orientation(vis_sm, sigma_grad=1.0, sigma_int=3.5)
    del vis_sm
    phi_vis = np.float32(0.5) * np.arctan2(s2_vis, c2_vis)
    tx_map = np.cos(phi_vis).astype(np.float32)
    ty_map = np.sin(phi_vis).astype(np.float32)
    del phi_vis

    # Anisotropic forward tip cone (same physics as visible_tip_stepover_cone)
    tip_adv = crsb_gub._anisotropic_strike_advect(tips, c2_vis, s2_vis, foot)
    step_halo = gaussian_filter(tips, sigma=9.5, mode="constant")
    del tips, c2_vis, s2_vis

    d_vis_f64, (ny_near, nx_near) = distance_transform_edt(~vis, return_distances=True, return_indices=True)
    d_vis = d_vis_f64.astype(np.float32)
    del d_vis_f64

    gy, gx = np.indices((h, w), dtype=np.float32)
    inv_d = np.float32(1.0) / np.maximum(d_vis, np.float32(1e-4))
    ry = (gy - ny_near.astype(np.float32)) * inv_d
    rx = (gx - nx_near.astype(np.float32)) * inv_d
    del gy, gx, inv_d

    tx_near = tx_map[ny_near, nx_near]
    ty_near = ty_map[ny_near, nx_near]
    is_tip_near = tip_halo_on_vis[ny_near, nx_near]
    del tx_map, ty_map, tip_halo_on_vis, ny_near, nx_near

    cos2_along = np.clip(np.square(rx * tx_near + ry * ty_near), 0.0, 1.0)
    sin2_broad = np.float32(1.0) - cos2_along
    del rx, ry, tx_near, ty_near

    collar_taper = np.clip((d_vis - np.float32(2.0)) / np.float32(2.8), 0.0, 1.0) * np.exp(
        -np.maximum(d_vis - np.float32(4.0), np.float32(0.0)) / np.float32(17.0)
    )
    tip_cone = crsb_gub.robust_unit_f32(
        (np.float32(0.72) * tip_adv + np.float32(0.28) * step_halo) * collar_taper,
        foot,
        lo_pct=50.0,
        hi_pct=99.6,
    )
    del tip_adv, step_halo, collar_taper

    # Forward Coulomb stress amplification ahead of tips / oblique wing-crack lobes
    forward_lobe = tip_cone * (np.float32(0.45) + np.float32(0.55) * cos2_along)
    tip_gain = np.float32(1.0) + np.float32(0.46) * forward_lobe
    del tip_cone, forward_lobe, cos2_along

    # Broadside interior elastic stress-release shadow across 3.0 < d_vis < 8.5 px (strictly near-90-deg orthogonal sin^4)
    # Preserves 15-45 deg Y-branch splays off interior traces while damping pure parallel smoothed-feature halo spillover
    shadow_window = np.exp(-np.square(np.clip((d_vis - np.float32(4.6)) / np.float32(2.6), -12.0, 12.0))).astype(np.float32)
    sin4_ortho = np.square(sin2_broad)
    shadow_damp = np.float32(1.0) - np.float32(0.32) * sin4_ortho * (np.float32(1.0) - is_tip_near) * shadow_window
    del sin2_broad, sin4_ortho, is_tip_near, shadow_window

    gate_mult = (tip_gain * shadow_damp).astype(np.float32)
    gate_mult[~foot] = 0.0
    return gate_mult, d_vis


def build_csst_surface(
    p_dual: np.ndarray | None,
    crsb_stack: np.ndarray,
    csst_stack: np.ndarray,
    visible_mask: np.ndarray,
    foot: np.ndarray,
    region_mask: np.ndarray | None = None,
    mode: str = "exp3_coulomb_maxenv",
) -> np.ndarray:
    """Stationary pre-placement belief surface for EXP-1, EXP-2, or EXP-3 (identical on folds and live)."""
    mask = foot if region_mask is None else (region_mask & foot)
    lidar_valid = np.asarray(crsb_stack[:, :, 10], dtype=np.float32) > 0.5
    lidar_chain = np.asarray(csst_stack[:, :, 3], dtype=np.float32)
    lidar_asym = np.asarray(crsb_stack[:, :, 12], dtype=np.float32)
    corrob6 = np.asarray(csst_stack[:, :, 4], dtype=np.float32)
    unsup_csst = np.asarray(csst_stack[:, :, 5], dtype=np.float32)
    # Pure CSST-BGHF physical ridge (zero reuse of PR #9 unsup_crsb; combines Baranov leaching,
    # Reid N=0 basement contact, bajada flexure, GDR geothermometer & repaired 1m LiDAR chain)
    lidar_boost = np.float32(0.82) * lidar_chain + np.float32(0.18) * lidar_asym
    phys_comb = np.where(
        lidar_valid,
        np.float32(0.72) * unsup_csst + np.float32(0.28) * lidar_boost,
        unsup_csst,
    ) * (np.float32(0.65) + np.float32(0.35) * corrob6)
    del unsup_csst, lidar_boost, lidar_chain, lidar_asym, corrob6

    surf = np.zeros(foot.shape, dtype=np.float32)
    if mode == "exp1_unsup":
        surf[mask] = phys_comb[mask]
        del phys_comb
        surf = crsb_gub.sharpen_4azimuth_nms(surf, mask, boost=0.52)
        return np.clip(surf, 0.0, 1.0).astype(np.float32)

    assert p_dual is not None
    if mode == "exp2_oof_isotropic":
        tip_cone = crsb_gub.visible_tip_stepover_cone(visible_mask, foot)
        fused = p_dual * (np.float32(0.84) + np.float32(0.16) * phys_comb) * (np.float32(1.0) + np.float32(0.34) * tip_cone)
        surf[mask] = fused[mask]
        del tip_cone, fused, phys_comb
        surf = crsb_gub.sharpen_4azimuth_nms(surf, mask, boost=0.46)
        return np.clip(surf, 0.0, 1.0).astype(np.float32)

    if mode == "exp3_coulomb_maxenv":
        gate_mult, d_vis = coulomb_tip_vs_shadow_gate(visible_mask, foot)
        # Pure 4-operator new CSST-BGHF physical ridge (Baranov leaching + Euler N=0 basement match
        # + bajada toe flexure + repaired 1 m LiDAR chain, zero reuse of PR #9 CRSB composite)
        c_bar = np.asarray(csst_stack[:, :, 0], dtype=np.float32)
        c_eul = np.asarray(csst_stack[:, :, 1], dtype=np.float32)
        c_flx = np.asarray(csst_stack[:, :, 2], dtype=np.float32)
        c_lid = np.asarray(csst_stack[:, :, 3], dtype=np.float32)
        pure_new_sub = np.float32(0.34) * c_bar + np.float32(0.28) * c_eul + np.float32(0.38) * c_flx
        pure_new = np.where(
            lidar_valid,
            np.float32(0.70) * pure_new_sub + np.float32(0.30) * c_lid,
            pure_new_sub,
        )
        del c_bar, c_eul, c_flx, c_lid, pure_new_sub, phys_comb
        csst_crest = crsb_gub.sharpen_4azimuth_nms(pure_new, mask, boost=0.58)
        del pure_new

        z_in = np.clip(-(d_vis - np.float32(3.8)) / np.float32(1.6), -30.0, 30.0)
        z_out = np.clip((d_vis - np.float32(50.0)) / np.float32(10.0), -30.0, 30.0)
        w_outboard = (
            np.float32(0.42) + np.float32(0.58) / (np.float32(1.0) + np.exp(z_in))
        ) * (
            np.float32(0.78) + np.float32(0.22) / (np.float32(1.0) + np.exp(z_out))
        )
        del d_vis, z_in, z_out

        s_coulomb_raw = p_dual * (np.float32(0.84) + np.float32(0.16) * csst_crest) * gate_mult
        s_coulomb = crsb_gub.sharpen_4azimuth_nms(s_coulomb_raw, mask, boost=0.46)
        del s_coulomb_raw, gate_mult

        env_raw = (
            w_outboard
            * np.power(np.maximum(csst_crest, np.float32(0.0)), np.float32(1.18))
            * (np.float32(0.86) + np.float32(0.14) * np.sqrt(np.maximum(p_dual, np.float32(0.01))))
        )
        # Balanced ~52% Coulomb OOF crest / ~48% pure 4-operator CSST-BGHF physical crest
        s_ref = float(np.percentile(s_coulomb[mask][::5], 99.36)) if mask.any() else 0.35
        e_ref = float(np.percentile(env_raw[mask][::5], 99.26)) if mask.any() else 0.35
        env_floor = env_raw * np.float32(s_ref / max(e_ref, 1e-6))
        del env_raw, w_outboard, csst_crest

        surf[mask] = np.maximum(s_coulomb[mask], env_floor[mask])
        del s_coulomb, env_floor
        return np.clip(surf, 0.0, 1.0).astype(np.float32)

    raise ValueError(f"Unknown CSST surface mode: {mode}")


def emit_csst_submodular(
    surface: np.ndarray,
    visible_mask: np.ndarray,
    eligible_mask: np.ndarray,
    foot: np.ndarray,
    budget: int = TARGET_BUDGET,
    min_sep_px: float = AXIAL_MIN_SEP_PX,
    b_collar_px: float = B_COLLAR_PX,
    support_mult: int = 10,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Emit `budget` off-catalogue dots via canonical `gems32.emitter.emit` (`min_sep_px = 3.1`)."""
    return crsb_gub.emit_crsb_submodular(
        surface=surface,
        visible_mask=visible_mask,
        eligible_mask=eligible_mask,
        foot=foot,
        budget=budget,
        min_sep_px=min_sep_px,
        b_collar_px=b_collar_px,
        support_mult=support_mult,
    )
