"""H-K3-1 (CRSB-GUB): Conjugate Riedel-Stepover Stress-Shadow & Geothermometer-Disequilibrium
Upflow Bridge for Blind Geothermal Fault Discovery in the DOE GEMS Competition.

Preregistered prior to implementation in:
  - `docs/research/hypotheses-preregistration-karage3.md`
  - `registry/preregistration.json`

Core scientific & mathematical mechanisms:
  1. Exact 2-D Fourier harmonic upward continuation & vertical differentiation (Blakely 1995
     Eqs. 12.8 & 12.14) -> Miller-Singh (1994) Tilt Angle theta_T(z) -> Verduzco et al. (2004)
     Total Horizontal Derivative of Tilt (THDR = |grad_h theta_T|), equalizing buried low-throw
     intra-basin / accommodation fault walls against high-throw master range-front scarps.
  2. Multi-scale structure-tensor Conjugate Riedel / Horsetail / Relay-Breach Angular Dispersion
     Omega_conj = sin^2(phi_local_200m - phi_master_1800m) * THDR_joint gated by geodetic
     transtensional shear-dilation, isolating 15-75 deg oblique transfer & stepover splays.
  3. DOE GDR #1391 Chemical-Thermal Geothermometer Disequilibrium
     Delta_T_diseq = max(T_quartz, T_chalc, T_cation) - max(T_measured, 14 C) across 27,092
     wells/springs (with `dist_known_fault_px` strictly dropped and asserted absent), fused with
     2,782 INGENIOUS 2-m shallow temperature probes (`F2mDAB`) and 281 paleo-sinter/travertine
     vents, advected *anisotropically* along local THDR fault strikes.
  4. Uniform-negative, inverse-observability-weighted Dual-Cover OOF HistGradientBoostingClassifier
     (51-ch M_Full inside 1 m LiDAR + quantile-calibrated 48-ch strictly LiDAR-free M_NoLiDAR in
     the 24.63% LiDAR gap) + Propensity-Compensated Far-Field Max-Envelope + 300 m (`min_sep_px=3.0`)
     triangular-kernel submodular CELF emission (`gems32.emitter.emit`).
"""
from __future__ import annotations

import gc
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyproj
import rasterio
from numpy.lib.format import open_memmap
from rasterio.transform import rowcol
from scipy.fft import fftfreq, irfft2, rfft2, rfftfreq
from scipy.ndimage import convolve, distance_transform_edt, gaussian_filter, sobel
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from . import emitter, paths

TARGET_BUDGET: int = 37_654
B_COLLAR_PX: float = 2.0
AXIAL_MIN_SEP_PX: float = 3.0  # Exact 300 m triangular kernel zero-point

CRSB_EXTRA_CHANNELS: tuple[str, ...] = (
    "grav_thdr_depth_inv",            # 0: Verduzco THDR on gravity (z=0 & z=400 m Fourier harmonic)
    "mag_thdr_multialt",              # 1: Multi-altitude (0, 150, 600, 1500 m) RTP/TMI THDR persistence
    "thdr_dip_migration_vec",         # 2: Tilt zero-contour downdip migration x Band 15 graben deepening
    "riedel_conjugate_obliquity",     # 3: sin^2(phi_200m - phi_1800m) conjugate Riedel/relay splay index
    "stress_shadow_transfer_saddle",  # 4: Hessian saddle (-lambda1*lambda2) inter-basin relay bridge
    "geotherm_diseq_upflow",          # 5: GDR #1391 max(Quartz,Chalc,NaKCa) - T_meas blind upflow plume
    "aniso_vent_conduit_bridge",      # 6: Fault-strike-advected 2m F2mDAB + sinter + geotherm bridge
    "mag_destruction_cond_trough",    # 7: RTP magnetite-leaching trough x playa-decoupled cond_surf cap
    "geodawn_blk_alteration_crest",   # 8: 4-block normalized GeoDAWN 214Bi radon + K/Th alteration crest
    "kostrov_seismic_dilation_bridge",# 9: Geodetic shear*dilation + diffuse seismicity on THDR strikes
    "lidar_valid_indicator",          # 10: 1 m 3DEP LiDAR coverage indicator (touches 1 m LiDAR)
    "lidar_deconfounded_scarp_crest", # 11: TIGER-road & Lahontan-shoreline cleaned 1 m LiDAR crest
    "lidar_profile_asymmetry",        # 12: Cross-scarp downface/upface polarity asymmetry (1 m LiDAR)
    "mapping_observability_prior",    # 13: Label-free terrain/cover mapping propensity O_map in [0.15, 1]
    "subsurf_multimodal_corrob_chain",# 14: LiDAR-free 5-domain corroboration along 1.2 km strike kernel
    "crsb_gub_unsup_ridge",           # 15: Unified LiDAR-free 4-azimuth NMS CRSB-GUB physical crest
)

# Global indices in concatenated [35 base + 16 CRSB = 51 channels]:
# Extra channels 10, 11, 12 -> global indices 45, 46, 47 touch 1 m LiDAR.
# All remaining 48 channels (0..44, 48, 49, 50) are strictly 1 m LiDAR-free!
LIDAR_GLOBAL_COLS: frozenset[int] = frozenset({45, 46, 47})
MNOLIDAR_COL_INDICES: tuple[int, ...] = tuple(i for i in range(35 + len(CRSB_EXTRA_CHANNELS)) if i not in LIDAR_GLOBAL_COLS)
assert len(MNOLIDAR_COL_INDICES) == 48


def robust_unit_f32(arr: np.ndarray, valid: np.ndarray, lo_pct: float = 2.0, hi_pct: float = 99.2) -> np.ndarray:
    """Map `arr` monotonically into `[0, 1]` using robust footprint percentiles on a subsampled stride."""
    out = np.zeros(arr.shape, dtype=np.float32)
    m = valid & np.isfinite(arr)
    if not m.any():
        return out
    sub = arr[m][::5]
    if sub.size < 32:
        sub = arr[m]
    p_lo, p_hi = np.percentile(sub, [lo_pct, hi_pct])
    span = float(max(p_hi - p_lo, 1e-6))
    out[m] = np.clip((arr[m] - np.float32(p_lo)) / np.float32(span), 0.0, 1.0)
    return out


def _grad_xy(a: np.ndarray, sigma: float = 0.9) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s = gaussian_filter(a.astype(np.float32, copy=False), sigma, mode="nearest") if sigma > 0 else a.astype(np.float32, copy=False)
    gy = sobel(s, axis=0).astype(np.float32) * np.float32(0.125)
    gx = sobel(s, axis=1).astype(np.float32) * np.float32(0.125)
    mag = np.hypot(gx, gy).astype(np.float32)
    return mag, gy, gx


def fourier_tilt_and_thdr(
    field: np.ndarray,
    foot: np.ndarray,
    heights_m: tuple[float, ...],
    dx_m: float = 100.0,
    pad_px: int = 48,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Compute exact Fourier upward-continued Tilt Angle theta_T(z) and Verduzco THDR(z) at `heights_m`."""
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
    del ky, kx, k_rad

    tilts: list[np.ndarray] = []
    thdrs: list[np.ndarray] = []
    for z in heights_m:
        atten = np.exp(-np.float32(z) * two_pi_k)
        u_z = irfft2(spec * atten, s=(ph, pw), workers=2)[pad_px : pad_px + h, pad_px : pad_px + w].astype(np.float32)
        vz = irfft2(spec * two_pi_k * atten, s=(ph, pw), workers=2)[pad_px : pad_px + h, pad_px : pad_px + w].astype(np.float32)
        del atten
        hgrad, _, _ = _grad_xy(u_z, sigma=0.8)
        del u_z
        eps = np.float32(max(float(np.percentile(hgrad[foot][::8], 15)) * 0.25, 1e-5))
        tilt = np.arctan2(vz, hgrad + eps).astype(np.float32)
        del vz, hgrad
        thdr, _, _ = _grad_xy(tilt, sigma=0.85)
        tilts.append(tilt)
        thdrs.append(thdr)

    del spec, two_pi_k
    return tilts, thdrs


def _structure_orientation(field: np.ndarray, sigma_grad: float, sigma_int: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return `(coherence, cos_2phi, sin_2phi)` of ridge strike `phi` (perpendicular to gradient)."""
    _, gy, gx = _grad_xy(field, sigma=sigma_grad)
    jxx = gaussian_filter(gx * gx, sigma=sigma_int, mode="nearest")
    jyy = gaussian_filter(gy * gy, sigma=sigma_int, mode="nearest")
    jxy = gaussian_filter(gx * gy, sigma=sigma_int, mode="nearest")
    del gy, gx
    tr = jxx + jyy + np.float32(1e-10)
    dx = jxx - jyy
    dy = np.float32(2.0) * jxy
    del jxx, jyy, jxy
    norm = np.hypot(dx, dy) + np.float32(1e-10)
    coh = (norm / tr).astype(np.float32)
    # Gradient double-angle is (dx/norm, dy/norm); ridge strike phi = theta_grad + pi/2 flips sign of cos(2*theta) & sin(2*theta)
    c2_strike = (-dx / norm).astype(np.float32)
    s2_strike = (-dy / norm).astype(np.float32)
    return coh, c2_strike, s2_strike


def _block_zscore_f32(a: np.ndarray, block_id: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.zeros(a.shape, dtype=np.float32)
    for bid in (1, 2, 3, 4):
        m = valid & (block_id == bid) & np.isfinite(a)
        if not m.any():
            continue
        sub = a[m][::5]
        med = np.float32(np.median(sub))
        mad = np.float32(max(float(np.median(np.abs(sub - med))) * 1.4826, 1e-4))
        out[m] = np.clip((a[m] - med) / mad, -7.0, 7.0)
    return out


def _safe_float(val: object) -> float:
    try:
        s = str(val).strip()
        return float(s) if s else float("nan")
    except Exception:
        return float("nan")


def read_point_shapefile_zip(zip_path: Path) -> tuple[np.ndarray, np.ndarray, list[dict[str, str]]]:
    """Pure stdlib reader for EPSG:4269 Point `.shp` + `.dbf` inside INGENIOUS zip archives."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        shp_name = next(n for n in zf.namelist() if n.lower().endswith(".shp"))
        dbf_name = next(n for n in zf.namelist() if n.lower().endswith(".dbf"))
        prj_name = next(n for n in zf.namelist() if n.lower().endswith(".prj"))
        shp_bytes = zf.read(shp_name)
        dbf_bytes = zf.read(dbf_name)
        prj_text = zf.read(prj_name).decode("utf-8", errors="strict")

    epsg = pyproj.CRS.from_wkt(prj_text).to_epsg()
    if epsg != 4269:
        raise ValueError(f"Expected EPSG:4269 in {zip_path}, got {epsg}")

    nrec, hlen, rlen = struct.unpack("<IHH", dbf_bytes[4:12])
    fields: list[tuple[str, int]] = []
    pos = 32
    while pos + 32 <= hlen and dbf_bytes[pos] != 0x0D:
        fname = dbf_bytes[pos : pos + 11].split(b"\x00", 1)[0].decode("latin1").strip()
        flen = int(dbf_bytes[pos + 16])
        fields.append((fname, flen))
        pos += 32

    attrs: list[dict[str, str]] = []
    deleted: list[bool] = []
    p = hlen
    for _ in range(nrec):
        if p + rlen > len(dbf_bytes):
            break
        rec = dbf_bytes[p : p + rlen]
        p += rlen
        deleted.append(rec[0] == 0x2A)
        off = 1
        row: dict[str, str] = {}
        for fname, flen in fields:
            row[fname] = rec[off : off + flen].decode("latin1", errors="replace").strip()
            off += flen
        attrs.append(row)

    xs: list[float] = []
    ys: list[float] = []
    sp = 100
    while sp + 8 <= len(shp_bytes):
        _, clen_words = struct.unpack(">II", shp_bytes[sp : sp + 8])
        cbytes = clen_words * 2
        content = shp_bytes[sp + 8 : sp + 8 + cbytes]
        sp += 8 + cbytes
        if len(content) >= 20 and struct.unpack("<i", content[:4])[0] == 1:
            x, y = struct.unpack("<dd", content[4:20])
            xs.append(float(x))
            ys.append(float(y))
        else:
            xs.append(float("nan"))
            ys.append(float("nan"))

    n = min(len(xs), len(attrs))
    keep_lon, keep_lat, keep_attr = [], [], []
    for i in range(n):
        if not deleted[i] and np.isfinite(xs[i]) and np.isfinite(ys[i]):
            keep_lon.append(xs[i])
            keep_lat.append(ys[i])
            keep_attr.append(attrs[i])
    return np.asarray(keep_lon, np.float64), np.asarray(keep_lat, np.float64), keep_attr


def _anisotropic_strike_advect(
    seed_grid: np.ndarray,
    c2_strike: np.ndarray,
    s2_strike: np.ndarray,
    foot: np.ndarray,
) -> np.ndarray:
    """Advect hydrothermal point/plume anomalies anisotropically along 4 quantized fault-strike sectors."""
    # First smooth mildly (sigma=2.5 px = 250 m) for well location uncertainty, then elongate 1.4 km along local strike
    base_sm = gaussian_filter(seed_grid, sigma=2.5, mode="constant")
    phi = np.float32(0.5) * np.arctan2(s2_strike, c2_strike)  # [-pi/2, pi/2]
    # 4 oriented 15x15 line kernels at 0, 45, 90, 135 deg (sigma_along=6.0 px, sigma_across=1.4 px)
    r = 7
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1].astype(np.float32)
    out = np.zeros(seed_grid.shape, dtype=np.float32)
    angles = (0.0, np.pi * 0.25, np.pi * 0.5, np.pi * 0.75)
    for ang in angles:
        # Note: row=y (down), col=x (right); strike angle `phi` from (gx, gy) normal:
        # Since c2_strike = -cos(2*theta_grad), phi is angle in (x, y) plane!
        ca, sa = np.float32(np.cos(ang)), np.float32(np.sin(ang))
        along = xx * ca + yy * sa
        across = -xx * sa + yy * ca
        kern = np.exp(-0.5 * ((along / 5.5) ** 2 + (across / 1.35) ** 2)).astype(np.float32)
        kern /= kern.sum()
        resp = convolve(base_sm, kern, mode="nearest")
        # Soft cos^2 angular weight between local strike `phi` and sector `ang`
        w_ang = np.square(np.cos(phi - np.float32(ang))).astype(np.float32)
        out += w_ang * resp
        del resp, w_ang
    # Sum of cos^2(phi - k*pi/4) over k=0..3 equals 2.0 identically!
    out *= np.float32(0.5)
    out[~foot] = 0.0
    del base_sm, phi
    return out


def sharpen_4azimuth_nms(surface: np.ndarray, valid: np.ndarray, boost: float = 0.50) -> np.ndarray:
    """Contrast-preserving 4-azimuth directional non-maximum suppression ridge sharpener."""
    s = np.where(valid & np.isfinite(surface), np.maximum(surface, np.float32(0.0)), np.float32(0.0)).astype(np.float32)
    sm = gaussian_filter(s, sigma=0.70, mode="nearest")
    _, gy, gx = _grad_xy(sm, sigma=0.0)
    jxx = gaussian_filter(gx * gx, sigma=1.6, mode="nearest")
    jyy = gaussian_filter(gy * gy, sigma=1.6, mode="nearest")
    jxy = gaussian_filter(gx * gy, sigma=1.6, mode="nearest")
    theta_n = np.float32(0.5) * np.arctan2(np.float32(2.0) * jxy, jxx - jyy + np.float32(1e-12))
    del gy, gx, jxx, jyy, jxy

    # Quantize ridge normal into 4 sectors: 0 (E-W normal), 1 (NW-SE), 2 (N-S), 3 (NE-SW)
    ang = np.mod(theta_n + np.float32(np.pi), np.float32(np.pi))
    sec = (np.floor((ang + np.float32(np.pi / 8.0)) / np.float32(np.pi / 4.0)).astype(np.int8)) % 4
    del theta_n, ang

    # Shifted neighbors at +-1 and +-2 px along each normal direction
    shifts = ((0, 1), (1, 1), (1, 0), (1, -1))
    nms = np.zeros_like(s)
    h, w = s.shape
    pad = np.pad(sm, 2, mode="edge")
    for k, (dr, dc) in enumerate(shifts):
        m = sec == k
        if not m.any():
            continue
        p1 = pad[2 + dr : 2 + dr + h, 2 + dc : 2 + dc + w]
        m1 = pad[2 - dr : 2 - dr + h, 2 - dc : 2 - dc + w]
        p2 = pad[2 + 2 * dr : 2 + 2 * dr + h, 2 + 2 * dc : 2 + 2 * dc + w]
        m2 = pad[2 - 2 * dr : 2 - 2 * dr + h, 2 - 2 * dc : 2 - 2 * dc + w]
        neigh_max = np.maximum(np.maximum(p1, m1), np.float32(0.85) * np.maximum(p2, m2))
        is_crest = sm >= neigh_max * np.float32(0.985)
        prom = np.clip((sm - np.float32(0.5) * (p1 + m1)) / (sm + np.float32(1e-5)), 0.0, 1.0)
        nms[m] = np.where(is_crest[m], np.float32(0.65) + np.float32(0.35) * prom[m], np.float32(0.18) * (sm[m] / (neigh_max[m] + np.float32(1e-5))))
    del pad, sm, sec

    b = np.float32(boost)
    out = s * ((np.float32(1.0) - b) + b * nms)
    out[~valid] = 0.0
    return out.astype(np.float32)


def visible_tip_stepover_cone(visible_mask: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Fold-local visible-only structural tip & stepover continuation cone (strictly zero hidden-fault access)."""
    vis = (np.asarray(visible_mask, bool) & foot).astype(np.float32)
    if not vis.any():
        return np.zeros(foot.shape, dtype=np.float32)
    # Count visible fault pixels in 3x3 neighborhood: endpoints have 1 neighbor (sum == 2 including self)
    nb = convolve(vis, np.ones((3, 3), dtype=np.float32), mode="constant")
    tips = ((vis > 0.5) & (nb <= 2.5)).astype(np.float32)
    del nb
    # Estimate local visible fault strike from smoothed visible skeleton
    vis_sm = gaussian_filter(vis, sigma=2.2, mode="constant")
    _, c2, s2 = _structure_orientation(vis_sm, sigma_grad=1.0, sigma_int=3.5)
    del vis_sm
    # Propagate tip stress shadow anisotropically along visible strike (1.5 km) + mild regional stepover halo
    tip_cone = _anisotropic_strike_advect(tips, c2, s2, foot)
    step_halo = gaussian_filter(tips, sigma=9.0, mode="constant")
    d_vis = distance_transform_edt(~(vis > 0.5)).astype(np.float32)
    # Zero inside 2 px of visible fault; peak at 3..16 px ahead of tips / across relay ramps
    collar_taper = np.clip((d_vis - 2.0) / 3.0, 0.0, 1.0) * np.exp(-np.maximum(d_vis - 4.0, 0.0) / 18.0)
    cone = robust_unit_f32((np.float32(0.70) * tip_cone + np.float32(0.30) * step_halo) * collar_taper, foot, lo_pct=50.0, hi_pct=99.6)
    del vis, tips, c2, s2, tip_cone, step_halo, d_vis, collar_taper
    return cone


def build_crsb_extra_stack(
    ddir: Path,
    base_stack_path: Path,
    out_path: Path,
    verbose: bool = True,
) -> dict[str, Any]:
    """Build and persist the 16 strictly label-free CRSB-GUB physical channels (`< 850 MB` RSS)."""
    def log(msg: str) -> None:
        if verbose:
            print(f"[CRSB-GUB] {msg}", flush=True)

    with rasterio.open(ddir / "sample_submission.tif") as ds:
        ref = ds.read(1)
        transform = ds.transform
    ext_dir = (ddir / "external") if (ddir / "external").exists() else (ddir.parent / "external")
    foot = np.isfinite(ref)
    h, w = foot.shape
    del ref

    base = np.load(base_stack_path, mmap_mode="r")
    assert base.shape == (h, w, 35), f"Unexpected base stack shape {base.shape}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    crsb = open_memmap(out_path, mode="w+", dtype=np.float32, shape=(h, w, len(CRSB_EXTRA_CHANNELS)))

    # 1. Potential-Field Verduzco Tilt-Derivatives (THDR) & Dip Migration (Channels 0, 1, 2)
    log("Computing exact Fourier upward-continued Gravity & Magnetic Verduzco THDR...")
    iso_grav = np.asarray(base[:, :, 12], dtype=np.float32)
    g_tilts, g_thdrs = fourier_tilt_and_thdr(iso_grav, foot, heights_m=(0.0, 450.0))
    del iso_grav
    grav_slope_b5 = np.asarray(base[:, :, 4], dtype=np.float32)
    grav_vg_b11 = np.asarray(base[:, :, 10], dtype=np.float32)
    g_tilt_b = np.arctan2(grav_vg_b11, grav_slope_b5 * np.float32(10.0) + np.float32(0.08)).astype(np.float32)
    g_thdr_b, _, _ = _grad_xy(g_tilt_b, sigma=0.9)
    del grav_slope_b5, grav_vg_b11, g_tilt_b

    grav_thdr = robust_unit_f32(
        np.float32(0.40) * g_thdr_b + np.float32(0.35) * g_thdrs[0] + np.float32(0.25) * g_thdrs[1],
        foot,
    )
    crsb[:, :, 0] = grav_thdr
    del g_thdr_b, g_thdrs

    rtp = np.asarray(base[:, :, 1], dtype=np.float32)
    m_tilts, m_thdrs = fourier_tilt_and_thdr(rtp, foot, heights_m=(0.0, 600.0, 1500.0))
    with rasterio.open(ext_dir / "geodawn_extensions_u8.tif") as ds:
        ext_up150 = ds.read(4).astype(np.float32)
    up150_g, _, _ = _grad_xy(ext_up150, sigma=1.1)
    del ext_up150

    mag_thdr = robust_unit_f32(
        np.sqrt(np.maximum(m_thdrs[0], 0.0) * np.maximum(m_thdrs[1], 0.0)) * np.float32(0.60)
        + np.sqrt(np.maximum(m_thdrs[1], 0.0) * np.maximum(m_thdrs[2], 0.0)) * np.float32(0.25)
        + robust_unit_f32(up150_g, foot) * np.float32(0.15),
        foot,
    )
    crsb[:, :, 1] = mag_thdr
    del up150_g, m_thdrs

    # Channel 2: Tilt zero-contour downdip migration aligned with Band 15 basement deepening
    depth_base = np.asarray(base[:, :, 14], dtype=np.float32)
    _, dby, dbx = _grad_xy(depth_base, sigma=2.0)
    _, gt0y, gt0x = _grad_xy(g_tilts[0], sigma=1.2)
    # Where tilt transitions z=0 -> z=450m/1500m in the direction of deepening basement:
    dtilt_g = g_tilts[0] - g_tilts[1]
    dtilt_m = m_tilts[0] - m_tilts[2]
    dip_align = np.maximum(-(gt0x * dbx + gt0y * dby), 0.0)
    dip_mig = robust_unit_f32(
        (np.abs(dtilt_g) * np.float32(0.55) + np.abs(dtilt_m) * np.float32(0.45))
        * (np.float32(0.35) + np.float32(0.65) * robust_unit_f32(dip_align, foot)),
        foot,
    )
    crsb[:, :, 2] = dip_mig
    del g_tilts, m_tilts, dby, dbx, gt0y, gt0x, dtilt_g, dtilt_m, dip_align, dip_mig
    gc.collect()

    # 2. Conjugate Riedel / Stepover Angular Dispersion & Relay Saddle (Channels 3, 4)
    log("Computing Conjugate Riedel-Stepover Angular Dispersion & Relay Saddle...")
    joint_thdr = np.float32(0.52) * grav_thdr + np.float32(0.48) * mag_thdr
    coh_loc, c2_loc, s2_loc = _structure_orientation(joint_thdr, sigma_grad=0.8, sigma_int=2.0)
    _, c2_reg, s2_reg = _structure_orientation(joint_thdr, sigma_grad=2.5, sigma_int=18.0)
    # Exact identity: sin^2(phi_loc - phi_reg) = 0.5 * (1 - cos(2*(phi_loc - phi_reg)))
    cos_2diff = np.clip(c2_loc * c2_reg + s2_loc * s2_reg, -1.0, 1.0)
    sin2_obliq = np.float32(0.5) * (np.float32(1.0) - cos_2diff)
    del c2_reg, s2_reg, cos_2diff

    shear_b7 = robust_unit_f32(np.asarray(base[:, :, 6], dtype=np.float32), foot)
    dilat_b8 = robust_unit_f32(np.maximum(np.asarray(base[:, :, 7], dtype=np.float32), 0.0), foot)
    riedel_idx = robust_unit_f32(
        joint_thdr * coh_loc * sin2_obliq * (np.float32(0.40) + np.float32(0.60) * np.sqrt(shear_b7 * (dilat_b8 + np.float32(0.15)))),
        foot,
    )
    crsb[:, :, 3] = riedel_idx
    del coh_loc, sin2_obliq

    # Channel 4: Potential-field / basement relay-ramp Hessian saddle (-lambda1 * lambda2 > 0)
    db_sm = gaussian_filter(depth_base, sigma=3.5, mode="nearest")
    dxx = gaussian_filter(db_sm, sigma=1.5, order=(0, 2), mode="nearest")
    dyy = gaussian_filter(db_sm, sigma=1.5, order=(2, 0), mode="nearest")
    dxy = gaussian_filter(db_sm, sigma=1.5, order=(1, 1), mode="nearest")
    det_h = dxx * dyy - dxy * dxy
    saddle = robust_unit_f32(np.maximum(-det_h, 0.0) * (np.float32(0.35) + np.float32(0.65) * joint_thdr), foot)
    crsb[:, :, 4] = saddle
    del db_sm, dxx, dyy, dxy, det_h, saddle
    gc.collect()

    # 3. Geothermometer Disequilibrium & Strike-Advected Vent Bridges (Channels 5, 6)
    log("Computing GDR #1391 Geothermometer Disequilibrium & Strike-Advected Vent Bridges...")
    ws_df = pd.read_csv(ext_dir / "gdr_wellspring_in_footprint.csv", low_memory=False)
    if "dist_known_fault_px" in ws_df.columns:
        ws_df = ws_df.drop(columns=["dist_known_fault_px"])
    assert "dist_known_fault_px" not in ws_df.columns

    vv_df = pd.read_csv(ext_dir / "gdr_volcanic_vents_in_footprint.csv", low_memory=False)
    if "dist_known_fault_px" in vv_df.columns:
        vv_df = vv_df.drop(columns=["dist_known_fault_px"])
    assert "dist_known_fault_px" not in vv_df.columns

    t_meas = pd.to_numeric(ws_df["temp_c"], errors="coerce").fillna(0.0).to_numpy(np.float32)
    t_qtz = pd.to_numeric(ws_df["geothermquartz_c"], errors="coerce").fillna(0.0).to_numpy(np.float32)
    t_cha = pd.to_numeric(ws_df["geothermchalc_c"], errors="coerce").fillna(0.0).to_numpy(np.float32)
    t_cat = pd.to_numeric(ws_df["geothermcat_c"], errors="coerce").fillna(0.0).to_numpy(np.float32)
    t_chem = np.maximum(np.maximum(np.where(t_qtz < 320, t_qtz, 0.0), np.where(t_cha < 320, t_cha, 0.0)), np.where(t_cat < 320, t_cat, 0.0))
    t_obs_clean = np.where((t_meas > 0.0) & (t_meas < 150.0), t_meas, 15.0)
    # Blind upflow chemical disequilibrium + direct hot-spring anomaly
    diseq = np.clip((t_chem - np.maximum(t_obs_clean, 15.0) - 20.0) / 110.0, 0.0, 2.0)
    direct_hot = np.clip((np.where(t_meas < 150.0, t_meas, 0.0) - 26.0) / 55.0, 0.0, 2.0)
    ws_score = np.float32(0.68) * diseq + np.float32(0.32) * direct_hot

    ws_r = np.clip(pd.to_numeric(ws_df["row"], errors="coerce").fillna(-1).to_numpy(np.int32), 0, h - 1)
    ws_c = np.clip(pd.to_numeric(ws_df["col"], errors="coerce").fillna(-1).to_numpy(np.int32), 0, w - 1)
    keep_ws = (ws_score > 0.02) & foot[ws_r, ws_c]

    diseq_seed = np.zeros((h, w), dtype=np.float32)
    np.maximum.at(diseq_seed, (ws_r[keep_ws], ws_c[keep_ws]), ws_score[keep_ws].astype(np.float32))
    # Density-normalized plume + strike advection
    ws_cnt = np.zeros((h, w), dtype=np.float32)
    valid_ws = foot[ws_r, ws_c]
    np.add.at(ws_cnt, (ws_r[valid_ws], ws_c[valid_ws]), np.float32(1.0))
    diseq_plume = gaussian_filter(diseq_seed, sigma=5.5, mode="constant") / (gaussian_filter(ws_cnt, sigma=5.5, mode="constant") + np.float32(0.03))
    geotherm_diseq = robust_unit_f32(diseq_plume, foot, lo_pct=5.0, hi_pct=99.4)
    crsb[:, :, 5] = geotherm_diseq
    del ws_df, t_meas, t_qtz, t_cha, t_cat, t_chem, t_obs_clean, diseq, direct_hot, ws_score, ws_cnt, diseq_plume

    # Read 2m INGENIOUS temperature probes + Paleo-Geothermal sinter/travertine vents
    transformer = pyproj.Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)
    vent_seed = diseq_seed.copy()
    del diseq_seed

    p_lon, p_lat, p_attr = read_point_shapefile_zip(ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip")
    pe, pn = transformer.transform(p_lon, p_lat)
    pr, pc = rowcol(transform, pe, pn)
    pr_a, pc_a = np.asarray(pr, np.int64), np.asarray(pc, np.int64)
    in_b = (pr_a >= 0) & (pr_a < h) & (pc_a >= 0) & (pc_a < w)
    for idx_p in np.flatnonzero(in_b):
        rr_i, cc_i = int(pr_a[idx_p]), int(pc_a[idx_p])
        if not foot[rr_i, cc_i]:
            continue
        dab = _safe_float(p_attr[idx_p].get("F2mDAB", ""))
        if np.isfinite(dab) and dab > 1.0:
            vent_seed[rr_i, cc_i] = max(vent_seed[rr_i, cc_i], float(np.clip(dab / 8.0, 0.0, 2.2)))

    s_lon, s_lat, s_attr = read_point_shapefile_zip(ext_dir / "paleo_geothermal_regional.zip")
    se, sn = transformer.transform(s_lon, s_lat)
    sr, sc = rowcol(transform, se, sn)
    sr_a, sc_a = np.asarray(sr, np.int64), np.asarray(sc, np.int64)
    in_s = (sr_a >= 0) & (sr_a < h) & (sc_a >= 0) & (sc_a < w)
    for idx_s in np.flatnonzero(in_s):
        rr_i, cc_i = int(sr_a[idx_s]), int(sc_a[idx_s])
        if not foot[rr_i, cc_i]:
            continue
        dtype_str = str(
            s_attr[idx_s].get(
                "Deposit_ty",
                s_attr[idx_s].get("Deposit_type", s_attr[idx_s].get("Type", s_attr[idx_s].get("TYPE", ""))),
            )
        ).strip().lower()
        # IR-K3-27: Paleo_geothermal_final.dbf stores deposit type under 10-char DBF field 'Deposit_ty'.
        # Cold-water pluvial Lake Lahontan shoreline 'Tufa' mounds are vetoed (0.0); >=175 C siliceous sinter
        # and silica-cemented conduits receive 1.0; CO2-rich hydrothermal travertine receives 0.65.
        w_dep = 0.0 if "tufa" in dtype_str else (1.0 if ("sinter" in dtype_str or "silic" in dtype_str) else 0.65)
        if w_dep > 0.0:
            vent_seed[rr_i, cc_i] = max(vent_seed[rr_i, cc_i], float(1.6 * w_dep))

    # Volcanic vents in footprint
    vr = np.clip(pd.to_numeric(vv_df["row"], errors="coerce").fillna(-1).to_numpy(np.int32), 0, h - 1)
    vc = np.clip(pd.to_numeric(vv_df["col"], errors="coerce").fillna(-1).to_numpy(np.int32), 0, w - 1)
    in_vv = foot[vr, vc]
    np.maximum.at(vent_seed, (vr[in_vv], vc[in_vv]), np.float32(1.1))
    del vv_df, p_lon, p_lat, p_attr, s_lon, s_lat, s_attr

    adv_vent = _anisotropic_strike_advect(vent_seed, c2_loc, s2_loc, foot)
    del vent_seed
    vent_bridge = robust_unit_f32(adv_vent * (np.float32(0.30) + np.float32(0.70) * joint_thdr), foot, lo_pct=10.0, hi_pct=99.5)
    crsb[:, :, 6] = vent_bridge
    del adv_vent
    gc.collect()

    # 4. Magnetite-Destruction Trough, Block-Normalized Radiometrics & Kostrov Strain (Channels 7, 8, 9)
    log("Computing Magnetite-Destruction Trough, Block-Normalized Radiometrics & Strain Coupling...")
    det_elev = np.asarray(base[:, :, 11], dtype=np.float32)
    elev_slope = np.asarray(base[:, :, 18], dtype=np.float32)
    cond_surf = np.asarray(base[:, :, 16], dtype=np.float32)
    # Flat-playa indicator (low detrended elevation AND near-zero slope) to decouple evaporite playas
    playa_flat = np.clip((-det_elev - 35.0) / 140.0, 0.0, 1.0) * np.clip((1.6 - elev_slope) / 1.6, 0.0, 1.0)
    playa_clean = np.float32(1.0) - np.float32(0.80) * playa_flat

    # Magnetite leaching trough: positive Laplacian (+d2/dx2 + d2/dy2) of RTP inside magnetic terrain
    rtp_sm = gaussian_filter(rtp, sigma=1.6, mode="nearest")
    rtp_reg = gaussian_filter(rtp, sigma=8.0, mode="nearest")
    demag_trough = np.maximum(rtp_reg - rtp_sm, 0.0)
    del rtp, rtp_sm, rtp_reg
    cond_edge, _, _ = _grad_xy(cond_surf, sigma=1.4)
    cond_resid = robust_unit_f32(cond_surf * playa_clean, foot)
    mag_destr = robust_unit_f32(
        robust_unit_f32(demag_trough, foot) * (np.float32(0.45) * cond_resid + np.float32(0.55) * robust_unit_f32(cond_edge, foot)) * playa_clean,
        foot,
    )
    crsb[:, :, 7] = mag_destr
    del demag_trough, cond_surf, cond_edge, cond_resid

    with rasterio.open(ext_dir / "acquisition_block_id_100m.tif") as ds:
        blk_id = ds.read(1)
    with rasterio.open(ext_dir / "geodawn_rad_u8.tif") as ds:
        rad_k = ds.read(1).astype(np.float32)
        rad_th = ds.read(2).astype(np.float32)
        rad_u = ds.read(3).astype(np.float32)
    rad_valid = foot & (rad_th > 0) & (rad_k > 0)
    zk = _block_zscore_f32(rad_k, blk_id, rad_valid)
    zth = _block_zscore_f32(rad_th, blk_id, rad_valid)
    zu = _block_zscore_f32(rad_u, blk_id, rad_valid)
    del rad_k, rad_th, rad_u, blk_id
    # 214Bi radon excess (zu - 0.65*zth) + potassic/silica zoning gradient, playa-vetoed
    radon_ex = np.maximum(zu - np.float32(0.65) * zth, 0.0) * playa_clean
    kth_diff = zk - np.float32(0.75) * zth
    kth_grad, _, _ = _grad_xy(kth_diff, sigma=1.5)
    rad_crest = robust_unit_f32(
        (np.float32(0.55) * robust_unit_f32(radon_ex, foot) + np.float32(0.45) * robust_unit_f32(kth_grad * playa_clean, foot))
        * (np.float32(0.35) + np.float32(0.65) * joint_thdr),
        foot,
    )
    crsb[:, :, 8] = rad_crest
    del zk, zth, zu, radon_ex, kth_diff, kth_grad

    # Channel 9: Kostrov strain x seismicity on THDR fault strikes
    inv2_b4 = robust_unit_f32(np.asarray(base[:, :, 3], dtype=np.float32), foot)
    deq_b10 = robust_unit_f32(np.log1p(np.maximum(np.asarray(base[:, :, 9], dtype=np.float32), 0.0)), foot)
    ieq_b16 = robust_unit_f32(-np.asarray(base[:, :, 15], dtype=np.float32), foot)  # lower distance/interval = higher seismic proximity
    strain_seis = robust_unit_f32(
        joint_thdr * (np.float32(0.40) * shear_b7 + np.float32(0.30) * dilat_b8 + np.float32(0.15) * inv2_b4 + np.float32(0.15) * np.maximum(deq_b10, ieq_b16)),
        foot,
    )
    crsb[:, :, 9] = strain_seis
    del inv2_b4, deq_b10, ieq_b16, shear_b7, dilat_b8
    gc.collect()

    # 5. 1 m LiDAR De-Confounded Scarp & Profile Asymmetry + TIGER Road Gate (Channels 10, 11, 12)
    log("Computing TIGER-Road & Lahontan-Shoreline De-Confounded 1 m LiDAR Features...")
    with rasterio.open(ext_dir / "tiger_road_distance_m.tif") as ds:
        d_road = ds.read(1).astype(np.float32)
    tiger_gate = np.where(foot & np.isfinite(d_road), np.float32(1.0) - np.exp(-np.square(np.maximum(d_road, 0.0) / np.float32(175.0))), np.float32(1.0)).astype(np.float32)
    del d_road

    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as ds:
        li_ex = ds.read(1).astype(np.float32)
        li_step = ds.read(3).astype(np.float32)
        li_lapn = ds.read(4).astype(np.float32)
        li_down = ds.read(6).astype(np.float32)
        li_up = ds.read(7).astype(np.float32)
        li_coh = ds.read(10).astype(np.float32)
        li_strike_u8 = ds.read(11).astype(np.float32)
        li_valid = (ds.read(12) > 0) & foot

    crsb[:, :, 10] = li_valid.astype(np.float32)

    # Lahontan contour-parallelism veto: compare LiDAR scarp strike against regional elevation contour strike
    _, ey_reg, ex_reg = _grad_xy(det_elev, sigma=5.0)
    contour_phi = np.arctan2(-ex_reg, ey_reg + np.float32(1e-9))
    li_phi = (li_strike_u8 / np.float32(255.0)) * np.float32(np.pi)
    sin_orth = np.abs(np.sin(li_phi - contour_phi)).astype(np.float32)
    # Only damp contour-parallel benches in low-relief piedmont/basin zones without THDR support
    lahontan_zone = np.clip((120.0 - np.abs(det_elev + 65.0)) / 120.0, 0.0, 1.0) * np.clip((5.0 - elev_slope) / 5.0, 0.0, 1.0)
    shoreline_keep = np.float32(1.0) - np.float32(0.65) * lahontan_zone * (np.float32(1.0) - sin_orth) * (np.float32(1.0) - joint_thdr)
    del ey_reg, ex_reg, contour_phi, li_phi, sin_orth, lahontan_zone

    raw_li_crest = (
        np.float32(0.38) * (li_step / np.float32(255.0))
        + np.float32(0.28) * (li_ex / np.float32(255.0))
        + np.float32(0.20) * (li_lapn / np.float32(255.0))
        + np.float32(0.14) * (li_coh / np.float32(255.0))
    ) * tiger_gate * shoreline_keep
    raw_li_crest[~li_valid] = 0.0
    crsb[:, :, 11] = robust_unit_f32(raw_li_crest, li_valid)

    asym = (np.abs(li_down - li_up) / (li_down + li_up + np.float32(6.0))) * (li_step / np.float32(255.0)) * tiger_gate * shoreline_keep
    asym[~li_valid] = 0.0
    crsb[:, :, 12] = robust_unit_f32(asym, li_valid)
    del li_ex, li_step, li_lapn, li_down, li_up, li_coh, li_strike_u8, raw_li_crest, asym, shoreline_keep
    gc.collect()

    # 6. Label-Free Mapping Observability Prior, Multi-Physics Chain & Unified Unsup Ridge (Channels 13, 14, 15)
    log("Computing Mapping Observability Prior, Multi-Physics Chain & Unified CRSB-GUB Ridge...")
    relief5 = robust_unit_f32(np.asarray(base[:, :, 24], dtype=np.float32), foot)
    slope_u = robust_unit_f32(elev_slope, foot)
    burial_u = robust_unit_f32(depth_base, foot)
    # High O_map on steep LiDAR-covered bedrock/piedmont scarps; low O_map in deep basins & LiDAR gaps
    o_map = np.clip(
        np.float32(0.18)
        + np.float32(0.32) * li_valid.astype(np.float32)
        + np.float32(0.28) * np.maximum(slope_u, relief5)
        + np.float32(0.22) * (np.float32(1.0) - burial_u),
        0.15,
        1.0,
    ).astype(np.float32)
    o_map[~foot] = 0.0
    crsb[:, :, 13] = o_map
    del relief5, slope_u, burial_u, depth_base, det_elev, elev_slope, li_valid

    # Channel 14: 5-domain independent subsurface corroboration smoothed along 1.2 km local fault strike
    dom_count = (
        (grav_thdr > 0.42).astype(np.float32)
        + (mag_thdr > 0.42).astype(np.float32)
        + (riedel_idx > 0.38).astype(np.float32)
        + (np.maximum(vent_bridge, np.maximum(mag_destr, rad_crest)) > 0.40).astype(np.float32)
        + (strain_seis > 0.40).astype(np.float32)
    ) / np.float32(5.0)
    chain_corrob = robust_unit_f32(_anisotropic_strike_advect(dom_count * joint_thdr, c2_loc, s2_loc, foot), foot)
    crsb[:, :, 14] = chain_corrob
    del dom_count, c2_loc, s2_loc

    # Channel 15: Strictly LiDAR-free 4-azimuth NMS physical CRSB-GUB fault-conduit ridge
    topo_ridge_b22 = robust_unit_f32(np.asarray(base[:, :, 21], dtype=np.float32), foot)  # 100 m DEM ridge_s1 (100% coverage, non-1m-LiDAR)
    raw_unsup = (
        np.float32(0.24) * grav_thdr
        + np.float32(0.22) * mag_thdr
        + np.float32(0.16) * riedel_idx
        + np.float32(0.14) * np.maximum(vent_bridge, geotherm_diseq * joint_thdr)
        + np.float32(0.10) * np.maximum(mag_destr, rad_crest)
        + np.float32(0.08) * chain_corrob
        + np.float32(0.06) * topo_ridge_b22
    ) * (np.float32(0.45) + np.float32(0.55) * tiger_gate) * playa_clean
    unsup_nms = sharpen_4azimuth_nms(raw_unsup, foot, boost=0.55)
    crsb[:, :, 15] = robust_unit_f32(unsup_nms, foot, lo_pct=1.0, hi_pct=99.6)
    crsb.flush()

    del grav_thdr, mag_thdr, joint_thdr, riedel_idx, geotherm_diseq, vent_bridge, mag_destr, rad_crest, strain_seis, chain_corrob, topo_ridge_b22, raw_unsup, unsup_nms, tiger_gate, playa_clean, playa_flat, o_map
    gc.collect()

    nonfinite = sum(int((~np.isfinite(crsb[:, :, i][foot])).sum()) for i in range(len(CRSB_EXTRA_CHANNELS)))
    assert nonfinite == 0, f"CRSB stack contains {nonfinite} nonfinite footprint values"
    return {
        "n_extra_channels": len(CRSB_EXTRA_CHANNELS),
        "channels": list(CRSB_EXTRA_CHANNELS),
        "shape": [h, w, len(CRSB_EXTRA_CHANNELS)],
        "nonfinite_in_footprint": nonfinite,
        "path": str(out_path),
    }


def gather_51ch(
    base_stack: np.ndarray,
    crsb_stack: np.ndarray,
    ys: np.ndarray,
    xs: np.ndarray,
    col_indices: tuple[int, ...] | None = None,
) -> np.ndarray:
    xb = np.asarray(base_stack[ys, xs, :], dtype=np.float32)
    xc = np.asarray(crsb_stack[ys, xs, :], dtype=np.float32)
    full = np.hstack([xb, xc])
    return full[:, col_indices] if col_indices is not None else full


def run_leakage_canary_51ch(
    base_stack: np.ndarray,
    crsb_stack: np.ndarray,
    base_names: list[str],
    ctx,
    max_auc: float = 0.90,
    stride: int = 4,
) -> dict[str, Any]:
    """Protocol Rule 4 single-feature two-polarity leakage canary across all 51 channels."""
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

    all_names = list(base_names) + list(CRSB_EXTRA_CHANNELS)
    rows = []
    for i, name in enumerate(all_names):
        plane = base_stack[:, :, i] if i < 35 else crsb_stack[:, :, i - 35]
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
                "in_mnolidar": i in MNOLIDAR_COL_INDICES,
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


def fit_debiased_crsb_classifier(
    base_stack: np.ndarray,
    crsb_stack: np.ndarray,
    train_region: np.ndarray,
    visible_train: np.ndarray,
    foot: np.ndarray,
    col_indices: tuple[int, ...] | None = None,
    seed: int = 303,
    max_pos: int = 42_000,
    n_neg_unif: int = 150_000,
) -> HistGradientBoostingClassifier:
    """Fit a fold-local SAR-PU observability-debiased HistGradientBoostingClassifier.

    Unlike prior near-fault hard-negative designs (which suppressed posteriors >1.5 km from visible
    faults), unlabeled negatives are sampled *uniformly* across `train_region` outside a 4-px
    ambiguous halo around `visible_train`, and weighted by mapping observability `O_map` so
    low-observability blind basins/uplands are not over-penalized as confident negatives.
    """
    rng = np.random.default_rng(seed)
    tr_pos = train_region & visible_train & foot
    d_tr = distance_transform_edt(~tr_pos)

    pos_y, pos_x = np.nonzero(tr_pos)
    if pos_y.size > max_pos:
        pp = rng.choice(pos_y.size, size=max_pos, replace=False)
        pos_y, pos_x = pos_y[pp], pos_x[pp]

    neg_pool_y, neg_pool_x = np.nonzero(train_region & foot & (~visible_train) & (d_tr > 4.0))
    del d_tr
    nu = min(n_neg_unif, neg_pool_y.size)
    pu = rng.choice(neg_pool_y.size, size=nu, replace=False)
    neg_y, neg_x = neg_pool_y[pu], neg_pool_x[pu]
    del neg_pool_y, neg_pool_x, pu

    o_map_plane = crsb_stack[:, :, 13]
    # Positives in low-observability blind settings receive inverse-propensity boost; unlabeled in blind settings get softer negative weight
    w_pos = np.clip(np.float32(1.0) / np.maximum(o_map_plane[pos_y, pos_x], np.float32(0.30)), 1.0, 2.6).astype(np.float32)
    w_neg = (np.float32(0.38) + np.float32(0.62) * o_map_plane[neg_y, neg_x]).astype(np.float32)

    ys = np.concatenate([pos_y, neg_y])
    xs = np.concatenate([pos_x, neg_x])
    y = np.concatenate([np.ones(pos_y.size, dtype=np.int8), np.zeros(neg_y.size, dtype=np.int8)])
    sw = np.concatenate([w_pos, w_neg])
    del pos_y, pos_x, neg_y, neg_x, w_pos, w_neg

    order = np.argsort(ys * foot.shape[1] + xs)
    ys, xs, y, sw = ys[order], xs[order], y[order], sw[order]

    X = gather_51ch(base_stack, crsb_stack, ys, xs, col_indices=col_indices)
    clf = HistGradientBoostingClassifier(
        max_iter=165,
        learning_rate=0.055,
        max_leaf_nodes=45,
        min_samples_leaf=80,
        l2_regularization=2.5,
        early_stopping=False,
        random_state=seed,
    )
    clf.fit(X, y, sample_weight=sw)
    del X, y, sw, ys, xs
    return clf


def predict_chunked_51ch(
    clf: HistGradientBoostingClassifier,
    base_stack: np.ndarray,
    crsb_stack: np.ndarray,
    mask: np.ndarray,
    col_indices: tuple[int, ...] | None = None,
    chunk_size: int = 200_000,
) -> np.ndarray:
    out = np.zeros(mask.shape, dtype=np.float32)
    ys, xs = np.nonzero(mask)
    for start in range(0, ys.size, chunk_size):
        sl = slice(start, min(start + chunk_size, ys.size))
        X = gather_51ch(base_stack, crsb_stack, ys[sl], xs[sl], col_indices=col_indices)
        out[ys[sl], xs[sl]] = clf.predict_proba(X)[:, 1].astype(np.float32)
        del X
    return out


def calibrate_gap_quantiles(
    p_full: np.ndarray,
    p_nolidar: np.ndarray,
    calib_lidar_valid: np.ndarray,
    calib_lidar_gap: np.ndarray,
    target_gap_mask: np.ndarray,
    blend_raw: float = 0.25,
) -> np.ndarray:
    """Fold-local monotone 257-knot quantile calibration of `M_NoLiDAR` onto `M_Full` scale."""
    out = p_full.copy()
    if not target_gap_mask.any():
        return out
    ref_v = p_full[calib_lidar_valid][::4]
    src_v = p_nolidar[calib_lidar_gap][::4]
    if ref_v.size < 64 or src_v.size < 64:
        out[target_gap_mask] = p_nolidar[target_gap_mask]
        return out
    qs = np.linspace(0.0, 100.0, 257)
    sk = np.percentile(src_v, qs).astype(np.float32)
    rk = np.percentile(ref_v, qs).astype(np.float32)
    uk, idx = np.unique(sk, return_index=True)
    if uk.size < 4:
        out[target_gap_mask] = p_nolidar[target_gap_mask]
        return out
    mapped = np.interp(p_nolidar[target_gap_mask], uk, rk[idx]).astype(np.float32)
    w_r = np.float32(blend_raw)
    out[target_gap_mask] = np.clip((np.float32(1.0) - w_r) * mapped + w_r * p_nolidar[target_gap_mask], 0.0, 1.0)
    return out


def build_crsb_surface(
    p_dual: np.ndarray | None,
    crsb_stack: np.ndarray,
    visible_mask: np.ndarray,
    foot: np.ndarray,
    region_mask: np.ndarray | None = None,
    mode: str = "exp3_maxenv",
) -> np.ndarray:
    """Construct the pre-placement continuous belief surface for EXP-1, EXP-2, or EXP-3.

    Identical stationary formula on OOF holdout folds and full-map emission.
    """
    mask = foot if region_mask is None else (region_mask & foot)
    unsup_ridge = np.asarray(crsb_stack[:, :, 15], dtype=np.float32)
    lidar_valid = np.asarray(crsb_stack[:, :, 10], dtype=np.float32) > 0.5
    lidar_crest = np.asarray(crsb_stack[:, :, 11], dtype=np.float32)
    o_map = np.asarray(crsb_stack[:, :, 13], dtype=np.float32)
    corrob = np.asarray(crsb_stack[:, :, 14], dtype=np.float32)

    surf = np.zeros(foot.shape, dtype=np.float32)
    if mode == "exp1_unsup":
        # Purely unsupervised physical CRSB-GUB + deconfounded LiDAR crest
        phys = np.where(lidar_valid, np.float32(0.62) * unsup_ridge + np.float32(0.38) * lidar_crest, unsup_ridge)
        surf[mask] = phys[mask] * (np.float32(0.75) + np.float32(0.25) * corrob[mask])
        surf = sharpen_4azimuth_nms(surf, mask, boost=0.45)
        return np.clip(surf, 0.0, 1.0).astype(np.float32)

    assert p_dual is not None
    if mode == "exp2_oof_only":
        surf[mask] = p_dual[mask]
        surf = sharpen_4azimuth_nms(surf, mask, boost=0.45)
        return np.clip(surf, 0.0, 1.0).astype(np.float32)

    if mode == "exp3_maxenv":
        # Preregistered Propensity-Compensated Max-Envelope + Visible Tip/Stepover Cone:
        # Calibrate physical ridge floor to the 99.1th percentile of `p_dual[mask]` so blind
        # hydrothermal/THDR ridges lift low-observability zones without displacing high-confidence
        # mapped-corridor OOF fault segments.
        p_ref = float(np.percentile(p_dual[mask][::5], 99.1)) if mask.any() else 0.35
        phys_comb = np.where(
            lidar_valid,
            np.float32(0.72) * unsup_ridge + np.float32(0.28) * lidar_crest,
            unsup_ridge,
        ) * (np.float32(0.65) + np.float32(0.35) * corrob)
        blind_gain = np.float32(p_ref * 0.88) * (np.float32(1.18) - np.float32(0.48) * o_map)
        env_floor = blind_gain * np.power(np.maximum(phys_comb, 0.0), np.float32(1.25))
        fused = np.maximum(p_dual * (np.float32(0.86) + np.float32(0.14) * phys_comb), env_floor)
        tip_cone = visible_tip_stepover_cone(visible_mask, foot)
        surf[mask] = fused[mask] * (np.float32(1.0) + np.float32(0.38) * tip_cone[mask])
        del phys_comb, blind_gain, env_floor, fused, tip_cone
        surf = sharpen_4azimuth_nms(surf, mask, boost=0.48)
        return np.clip(surf, 0.0, 1.0).astype(np.float32)

    raise ValueError(f"Unknown CRSB surface mode: {mode}")


def emit_crsb_submodular(
    surface: np.ndarray,
    visible_mask: np.ndarray,
    eligible_mask: np.ndarray,
    foot: np.ndarray,
    budget: int = TARGET_BUDGET,
    min_sep_px: float = AXIAL_MIN_SEP_PX,
    b_collar_px: float = B_COLLAR_PX,
    support_mult: int = 10,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Emit `budget` off-catalogue dots via canonical `gems32.emitter.emit` (`min_sep_px = 3.0`)."""
    if budget <= 0 or not (eligible_mask & foot).any():
        return np.zeros(surface.shape, dtype=bool), {"n_emitted": 0, "stopped_by": "zero_budget"}

    vis = np.asarray(visible_mask, bool) & foot
    d_vis = distance_transform_edt(~vis).astype(np.float32)
    elig = eligible_mask & foot & (d_vis > float(b_collar_px)) & (surface > 0.0)
    del d_vis

    n_elig = int(elig.sum())
    if n_elig == 0:
        return np.zeros(surface.shape, dtype=bool), {"n_emitted": 0, "stopped_by": "empty_eligible"}

    max_sup = max(int(budget) * int(support_mult), min(n_elig, 50_000))
    if n_elig > max_sup:
        vals = surface[elig]
        thr = float(np.partition(vals, n_elig - max_sup)[n_elig - max_sup])
        sup = elig & (surface >= thr)
        del vals
    else:
        sup = elig

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
