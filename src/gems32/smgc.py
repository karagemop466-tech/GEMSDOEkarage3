"""H-K3-1 (SMGC-CT): Stationary Max-Envelope Geothermal-Conduit & Crustal-Tensor Crest Allocation.

Pre-registered in ``docs/research/smgc-preregistration-20261027.md`` before implementation.

Implements the four priority geological transforms from ``docs/research.md`` on top of the
shared 83-channel multi-physics stack (35 template + 20 SPCP + 8 TRHV + 8 LDGI + 12 FBGR = 83,
plus 4 new SMGC channels = 87 strictly label-free channels):
  1. ``mag_edge_migration_dip`` (Priority 1): Normal displacement of horizontal-gradient maxima
     between z = 0, 500 m, and 2,000 m upward-continued TMI/RTP fields, rejecting broad contacts
     to isolate concealed dipping fault planes.
  2. ``rad_comp_discontinuity_kth_uth`` (Priority 2): Oriented change-point gradients in
     4-block-standardized log(K/Th) and log(U/Th) corroborated by magnetic edges while rejecting
     total-count-only lithologic shifts.
  3. ``cross_field_grav_rtp_offset`` (Priority 3): Persistent parallel signed gradients in
     isostatic gravity and RTP magnetics with 100-300 m cross-strike offset across dipping
     basin-bounding fault contacts.
  4. ``asymm_piedmont_curv_scarp`` (Priority 4): Signed cross-edge profile curvature asymmetry
     across linear topographic/magnetic edges with drainage-concavity and Lake Lahontan
     shoreline rejection.

And resolves ``H48-1-FBGR``'s ``SGMC-cal`` shortfall (``0.056798 < 0.064121`` Champion) without
any non-stationary ``eta(V)`` holdout-vs-live switch by replacing purely multiplicative
``p_dual * mod`` with a 100% stationary Max-Envelope PU Debiasing Floor:
  Phi_SMGC(x) = Sharpen_4theta( max( S_exposed(x), tau_far * W_far(d_vis(x)) * C_SMGC(x) ) )
packed via ``gems32.emitter.emit(..., budget=37654, min_sep_px=2.8)``.
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
    maximum_filter,
    minimum_filter,
    sobel,
)
from sklearn.metrics import roc_auc_score

from . import emitter, fbgr, ldgi, mdrc, paths, spcp, trhv

TARGET_BUDGET: int = 37_654
B_COLLAR_PX: float = 2.0
AXIAL_MIN_SEP_PX: float = 2.8

SMGC_EXTRA_CHANNELS: tuple[str, ...] = (
    "mag_edge_migration_dip",          # 0 (global 83): Upward-continued RTP/TMI normal gradient migration (Priority 1)
    "rad_comp_discontinuity_kth_uth",  # 1 (global 84): Oriented K/Th & U/Th change-point discontinuity (Priority 2)
    "cross_field_grav_rtp_offset",     # 2 (global 85): Parallel spatially-offset gravity & RTP signed edges (Priority 3)
    "asymm_piedmont_curv_scarp",       # 3 (global 86): Cross-edge profile curvature asymmetry w/ drainage veto (Priority 4)
)


def build_smgc_extra_stack(
    ddir: Path | None = None,
    base_stack_path: Path | None = None,
    spcp_path: Path | None = None,
    trhv_path: Path | None = None,
    ldgi_path: Path | None = None,
    fbgr_path: Path | None = None,
    out_path: Path | None = None,
    force: bool = False,
    log=print,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build or open the 4-channel strictly label-free `SMGC` disk-backed float32 stack."""
    ddir = ddir or paths.data_dir()
    wdir = paths.work_dir()
    wdir.mkdir(parents=True, exist_ok=True)

    base_stack_path = base_stack_path or (wdir / "feature_stack.npy")
    spcp_path = spcp_path or (wdir / "spcp_extra_20ch.npy")
    trhv_path = trhv_path or (wdir / "trhv_extra_8ch.npy")
    ldgi_path = ldgi_path or (wdir / "ldgi_extra_8ch.npy")
    fbgr_path = fbgr_path or (wdir / "fbgr_extra_12ch.npy")
    out_path = out_path or (wdir / "smgc_extra_4ch.npy")
    receipt_path = out_path.with_suffix(".json")

    if out_path.exists() and receipt_path.exists() and not force:
        mm = open_memmap(out_path, mode="r")
        if mm.shape[2] == len(SMGC_EXTRA_CHANNELS):
            return mm, json.loads(receipt_path.read_text())

    with rasterio.open(ddir / "sample_submission.tif") as src:
        sample = src.read(1)
        foot = np.isfinite(sample)
        h, w = sample.shape
    del sample

    base_mm = open_memmap(base_stack_path, mode="r")
    spcp_mm = open_memmap(spcp_path, mode="r")
    trhv_mm = open_memmap(trhv_path, mode="r")
    fbgr_mm = open_memmap(fbgr_path, mode="r")

    def _clean_base(idx0: int) -> np.ndarray:
        plane = np.asarray(base_mm[:, :, idx0], dtype=np.float32).copy()
        valid = foot & np.isfinite(plane) & (np.abs(plane) < 1e12)
        med = np.float32(np.median(plane[valid][::4])) if valid.any() else np.float32(0.0)
        plane[~valid] = med
        return plane

    mm = open_memmap(out_path, mode="w+", dtype=np.float32, shape=(h, w, len(SMGC_EXTRA_CHANNELS)))

    tiger_clean = np.asarray(trhv_mm[:, :, 4], dtype=np.float32)

    # --- Ch 0 (Priority 1): Magnetic-edge normal migration under upward continuation (RTP + TMI) ---
    rtp = _clean_base(1)      # Band 02: rtp
    tmi_hg = _clean_base(2)   # Band 03: tmi_hg
    tmi_vg = _clean_base(8)   # Band 09: tmi_vg
    rtp_uc500, rtp_uc2k = fbgr.harmonic_upward_continue_pair_f32(rtp, foot, heights_m=(500.0, 2000.0))
    mh0, gy_m0, gx_m0 = fbgr._hgrad_mag_and_vec(rtp, sigma=1.0)
    mh500, gy_m500, gx_m500 = fbgr._hgrad_mag_and_vec(rtp_uc500, sigma=1.0)
    mh2k, gy_m2k, gx_m2k = fbgr._hgrad_mag_and_vec(rtp_uc2k, sigma=1.2)
    del rtp, rtp_uc500, rtp_uc2k

    # Normal unit vector to the z=0 magnetic gradient ridge
    g_m0_mag = np.hypot(gx_m0, gy_m0) + np.float32(1e-5)
    nx_m, ny_m = gx_m0 / g_m0_mag, gy_m0 / g_m0_mag
    del gx_m0, gy_m0, g_m0_mag

    u_m0 = spcp.robust_unit_f32(mh0, foot, pct=99.4)
    u_m500 = spcp.robust_unit_f32(mh500, foot, pct=99.4)
    u_m2k = spcp.robust_unit_f32(mh2k, foot, pct=99.4)
    del mh0, mh500, mh2k

    # Normal displacement of gradient maxima between z=0 -> z=500m -> z=2000m, rejecting broad regional blobs
    broad_m = gaussian_filter(u_m2k, sigma=8.0, mode="nearest")
    narrow_m = np.maximum(u_m500 - np.float32(0.70) * broad_m, np.float32(0.0))
    align_500_2k = np.maximum(
        (gx_m500 * gx_m2k + gy_m500 * gy_m2k)
        / ((np.hypot(gx_m500, gy_m500) + np.float32(1e-5)) * (np.hypot(gx_m2k, gy_m2k) + np.float32(1e-5))),
        np.float32(0.0),
    )
    del gx_m500, gy_m500, gx_m2k, gy_m2k, broad_m
    tilt_sharp = spcp.robust_unit_f32(
        np.hypot(tmi_hg, np.float32(100.0) * tmi_vg) / (np.abs(tmi_vg) * np.float32(100.0) + np.abs(tmi_hg) + np.float32(1.0)),
        foot,
        pct=99.4,
    )
    del tmi_hg, tmi_vg
    mag_mig = spcp.robust_unit_f32(
        mdrc.directional_chain_max(
            np.sqrt(np.maximum(u_m0 * narrow_m, np.float32(0.0)))
            * (np.float32(0.45) + np.float32(0.55) * align_500_2k)
            * (np.float32(0.60) + np.float32(0.40) * tilt_sharp)
            * (np.float32(0.35) + np.float32(0.65) * tiger_clean),
            foot,
            halflen=2,
        ),
        foot,
        pct=99.5,
    )
    mm[:, :, 0] = mag_mig
    del u_m500, u_m2k, narrow_m, align_500_2k, tilt_sharp
    gc.collect()
    log("  [SMGC] ch 0 (Priority 1: magnetic-edge migration under upward continuation) built")

    # --- Ch 1 (Priority 2): Radiometric compositional discontinuity in log(K/Th) & log(U/Th) ---
    with rasterio.open(ddir / "external" / "acquisition_block_id_100m.tif") as ds:
        block_id = ds.read(1)
    with rasterio.open(ddir / "external" / "geodawn_rad_u8.tif") as ds:
        rad_k = ds.read(1).astype(np.float32)
        rad_th = ds.read(2).astype(np.float32)
        rad_u = ds.read(3).astype(np.float32)
        rad_tc = ds.read(4).astype(np.float32)

    rad_valid = foot & (rad_tc > 0) & (rad_th > 0) & (rad_k > 0) & (rad_u > 0)
    log_k_th = fbgr._block_zscore_f32(np.log((rad_k + np.float32(1.0)) / (rad_th + np.float32(1.0))), block_id, rad_valid)
    log_u_th = fbgr._block_zscore_f32(np.log((rad_u + np.float32(1.0)) / (rad_th + np.float32(1.0))), block_id, rad_valid)
    z_tc = fbgr._block_zscore_f32(rad_tc, block_id, rad_valid)
    del block_id, rad_k, rad_th, rad_u, rad_tc, rad_valid

    gk_mag, _, _ = fbgr._hgrad_mag_and_vec(log_k_th, sigma=1.2)
    gu_mag, _, _ = fbgr._hgrad_mag_and_vec(log_u_th, sigma=1.2)
    gtc_mag, _, _ = fbgr._hgrad_mag_and_vec(z_tc, sigma=1.2)
    del log_k_th, log_u_th, z_tc

    u_gk = spcp.robust_unit_f32(gk_mag, foot, pct=99.4)
    u_gu = spcp.robust_unit_f32(gu_mag, foot, pct=99.4)
    u_gtc = spcp.robust_unit_f32(gtc_mag, foot, pct=99.4)
    del gk_mag, gu_mag, gtc_mag

    # Compositional ratio change point minus total-count-only shift, corroborated by magnetic edge u_m0
    comp_step = np.maximum(np.float32(0.55) * u_gk + np.float32(0.45) * u_gu - np.float32(0.35) * u_gtc, np.float32(0.0))
    del u_gk, u_gu, u_gtc
    rad_disc = spcp.robust_unit_f32(
        mdrc.directional_chain_max(
            comp_step * (np.float32(0.35) + np.float32(0.65) * np.sqrt(np.maximum(u_m0, np.float32(0.02))))
            * (np.float32(0.35) + np.float32(0.65) * tiger_clean),
            foot,
            halflen=2,
        ),
        foot,
        pct=99.5,
    )
    mm[:, :, 1] = rad_disc
    del comp_step
    gc.collect()
    log("  [SMGC] ch 1 (Priority 2: radiometric compositional discontinuity K/Th & U/Th) built")

    # --- Ch 2 (Priority 3): Cross-field edge offset between Gravity and RTP ---
    iso_grav = _clean_base(12)  # Band 13: iso_grav_anom
    gg_mag, gy_g, gx_g = fbgr._hgrad_mag_and_vec(iso_grav, sigma=1.1)
    del iso_grav
    g_norm = np.hypot(gx_g, gy_g) + np.float32(1e-5)
    nx_g, ny_g = gx_g / g_norm, gy_g / g_norm
    del gx_g, gy_g, g_norm

    u_gg = spcp.robust_unit_f32(gg_mag, foot, pct=99.4)
    del gg_mag

    # Parallel alignment of gravity and magnetic gradient normals: cos^2(theta_g - theta_m)
    cos2_gm = ((nx_g * nx_m + ny_g * ny_m) ** 2).astype(np.float32)
    del nx_g, ny_g

    # Offset ring (100-300 m) of RTP edge around gravity edge & vice versa
    ring_m = maximum_filter(u_m0, size=5) - minimum_filter(u_m0, size=3)
    ring_g = maximum_filter(u_gg, size=5) - minimum_filter(u_gg, size=3)
    cross_offset = spcp.robust_unit_f32(
        mdrc.directional_chain_max(
            (np.float32(0.50) * np.sqrt(np.maximum(u_gg * ring_m, np.float32(0.0)))
             + np.float32(0.50) * np.sqrt(np.maximum(u_m0 * ring_g, np.float32(0.0))))
            * (np.float32(0.30) + np.float32(0.70) * cos2_gm),
            foot,
            halflen=2,
        ),
        foot,
        pct=99.5,
    )
    mm[:, :, 2] = cross_offset
    del u_gg, ring_m, ring_g, cos2_gm
    gc.collect()
    log("  [SMGC] ch 2 (Priority 3: cross-field gravity & RTP parallel offset edge) built")

    # --- Ch 3 (Priority 4): Asymmetric piedmont curvature (elevation + magnetic edge, drainage veto) ---
    det_elev = _clean_base(11)    # Band 12: det_elev
    elev_slope = _clean_base(18)  # Band 19: det_elev_slope
    es = gaussian_filter(det_elev, sigma=1.2, mode="nearest")
    del det_elev
    ey = sobel(es, axis=0).astype(np.float32) * np.float32(0.125)
    ex = sobel(es, axis=1).astype(np.float32) * np.float32(0.125)
    eyy = sobel(ey, axis=0).astype(np.float32) * np.float32(0.125)
    exx = sobel(ex, axis=1).astype(np.float32) * np.float32(0.125)
    exy = sobel(ex, axis=0).astype(np.float32) * np.float32(0.125)
    del es

    e_norm2 = ex * ex + ey * ey + np.float32(1e-5)
    # Profile curvature along slope line
    prof_curv = -(ex * ex * exx + np.float32(2.0) * ex * ey * exy + ey * ey * eyy) / e_norm2
    # Planform / Laplacian concavity (positive in drainage thalwegs -> veto)
    lap_elev = exx + eyy
    drainage_veto = spcp._sigmoid_f32(-lap_elev / (np.std(lap_elev[foot][::8]) + np.float32(1e-4)))
    del ex, ey, exx, eyy, exy, e_norm2, lap_elev

    # Cross-edge curvature dipole (difference between max convex scarp brow and concave scarp toe within 200 m)
    c_pos = maximum_filter(np.maximum(prof_curv, np.float32(0.0)), size=3)
    c_neg = maximum_filter(np.maximum(-prof_curv, np.float32(0.0)), size=3)
    del prof_curv
    lahontan_orth = np.asarray(spcp_mm[:, :, 14], dtype=np.float32)
    pied_asymm = spcp.robust_unit_f32(
        mdrc.directional_chain_max(
            np.sqrt(np.maximum(c_pos * c_neg, np.float32(0.0)))
            * drainage_veto
            * (np.float32(0.40) + np.float32(0.60) * lahontan_orth)
            * (np.float32(0.45) + np.float32(0.55) * np.maximum(u_m0, mag_mig))
            * spcp._sigmoid_f32((elev_slope - np.float32(1.2)) / np.float32(0.8))
            * (np.float32(0.35) + np.float32(0.65) * tiger_clean),
            foot,
            halflen=2,
        ),
        foot,
        pct=99.5,
    )
    mm[:, :, 3] = pied_asymm
    del c_pos, c_neg, drainage_veto, lahontan_orth, u_m0, nx_m, ny_m, elev_slope, tiger_clean

    if hasattr(mm, "flush"):
        mm.flush()
    gc.collect()

    meta: dict[str, Any] = {
        "channels": list(SMGC_EXTRA_CHANNELS),
        "shape": [h, w, len(SMGC_EXTRA_CHANNELS)],
        "dtype": "float32",
        "label_free": True,
        "preregistered_priorities_implemented": [
            "Priority 1: Magnetic-edge migration under upward continuation (TMI & RTP)",
            "Priority 2: Radiometric compositional discontinuity (K/Th & U/Th)",
            "Priority 3: Cross-field edge offset (gravity & RTP)",
            "Priority 4: Asymmetric piedmont curvature with drainage & Lahontan rejection",
        ],
    }
    receipt_path.write_text(json.dumps(meta, indent=2) + "\n")
    log("  [SMGC] ch 3 (Priority 4: asymmetric piedmont curvature w/ drainage rejection) built")
    return open_memmap(out_path, mode="r"), meta


def run_leakage_canary_87ch(
    base_stack: np.ndarray,
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    fbgr_stack: np.ndarray,
    smgc_stack: np.ndarray,
    base_names: list[str],
    ctx,
    max_auc: float = 0.90,
    stride: int = 4,
) -> dict[str, Any]:
    """Protocol Rule 4 single-feature two-polarity leakage canary across all 87 channels."""
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

    stacks = (base_stack, spcp_stack, trhv_stack, ldgi_stack, fbgr_stack, smgc_stack)
    offsets = np.cumsum([0] + [s.shape[2] for s in stacks])
    all_names = (
        list(base_names)
        + list(spcp.SPCP_EXTRA_CHANNELS)
        + list(trhv.TRHV_EXTRA_CHANNELS)
        + list(ldgi.LDGI_EXTRA_CHANNELS)
        + list(fbgr.FBGR_EXTRA_CHANNELS)
        + list(SMGC_EXTRA_CHANNELS)
    )
    assert len(all_names) == int(offsets[-1]) == 87

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


def build_smgc_unsup_crest_field(
    base_stack: np.ndarray,
    spcp_stack: np.ndarray,
    trhv_stack: np.ndarray,
    ldgi_stack: np.ndarray,
    fbgr_stack: np.ndarray,
    smgc_stack: np.ndarray,
    foot: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Build the unified label-free 87-channel `SMGC-CT` physical fault & hydrothermal conduit crest fields.

    Returns ``(far_crest, p4_sharp)``, both strictly label-free float32 arrays in ``[0, 1]``:
      - ``far_crest``: Combines ``spcp_stack[:, :, 19]`` (`multipillar_composite`),
        ``spcp_stack[:, :, 16]`` (`topo_scarp_composite`), and our 4 new `SMGC` priority
        channels (`smgc_stack[:, :, 0..3]`), gated by TIGER road rejection and flat deep
        playa suppression (`slope < 2 deg & depth > 300 m`).
      - ``p4_sharp``: Oriented 4-azimuth sharpened crest of the 4 new `SMGC` channels
        (magnetic-edge migration, K/Th & U/Th compositional discontinuity, cross-field
        gravity-RTP offset, and asymmetric piedmont curvature).
    """
    spcp_scarp = np.asarray(spcp_stack[:, :, 16], dtype=np.float32)  # topo_scarp_composite
    spcp_full = np.asarray(spcp_stack[:, :, 19], dtype=np.float32)   # multipillar_composite
    tiger_cl = np.asarray(trhv_stack[:, :, 4], dtype=np.float32)     # tiger_road_clean_gate

    smgc_mig = np.asarray(smgc_stack[:, :, 0], dtype=np.float32)     # Priority 1: mag_edge_migration_dip
    smgc_rad = np.asarray(smgc_stack[:, :, 1], dtype=np.float32)     # Priority 2: rad_comp_discontinuity_kth_uth
    smgc_off = np.asarray(smgc_stack[:, :, 2], dtype=np.float32)     # Priority 3: cross_field_grav_rtp_offset
    smgc_pie = np.asarray(smgc_stack[:, :, 3], dtype=np.float32)     # Priority 4: asymm_piedmont_curv_scarp

    # Strict flat deep basin veto so flat_basin_dot_frac stays < 2.5%
    depth_base = np.asarray(base_stack[:, :, 14], dtype=np.float32)
    elev_slope = np.asarray(base_stack[:, :, 18], dtype=np.float32)
    flat_deep = (elev_slope < 2.0) & (depth_base > 300.0) & foot
    del depth_base, elev_slope

    p4_new = (
        np.float32(0.28) * smgc_mig
        + np.float32(0.20) * smgc_rad
        + np.float32(0.22) * smgc_off
        + np.float32(0.30) * smgc_pie
    )
    del smgc_mig, smgc_rad, smgc_off, smgc_pie

    far_raw = (
        np.float32(0.62) * spcp_full
        + np.float32(0.18) * spcp_scarp
        + np.float32(0.20) * p4_new
    ) * (np.float32(0.35) + np.float32(0.65) * tiger_cl)
    far_raw[flat_deep] *= np.float32(0.08)
    far_raw[~foot] = 0.0
    del spcp_scarp, spcp_full, tiger_cl, flat_deep

    far_crest = spcp.robust_unit_f32(
        fbgr.sharpen_probability_crest(far_raw, foot, crest_boost=0.50), foot, pct=99.99
    )
    del far_raw
    p4_sharp = spcp.robust_unit_f32(
        fbgr.sharpen_probability_crest(p4_new, foot, crest_boost=0.50), foot, pct=99.98
    )
    del p4_new
    return far_crest, p4_sharp


def compose_smgc_max_envelope_surface(
    s_exp: np.ndarray,
    p_dual: np.ndarray,
    far_crest: np.ndarray,
    p4_sharp: np.ndarray,
    vis_relay: np.ndarray,
    visible_mask: np.ndarray,
    region_mask: np.ndarray,
    tau_corridor: float = 0.555,
    d_in_px: float = 11.0,
    d_out_px: float = 40.0,
    w_out_floor: float = 0.52,
) -> np.ndarray:
    """Compose the stationary Max-Envelope `SMGC-CT` surface on `region_mask`.

    Identical stationary formula in every holdout fold/draw (`visible_mask = V_vis`)
    and in full-catalogue live emission (`visible_mask = labels.tif > 0`):
      1. Exposed/relay branch boosted by the 4 `SMGC` priority channels (`p4_sharp`) and
         conduit-aligned relay continuation (`vis_relay * far_crest`):
         S_exp_mod(x) = S_exp(x) * (1 + 0.12 * P4_sharp(x) + 0.25 * R_vis(x) * C_far(x))
      2. Mesoscale Structural Corridor PU-Debiased Envelope (`W_corridor(d_vis)`):
         W_in(x)  = sigmoid((d(x, V_vis) - d_in_px) / 2.5)
         W_out(x) = w_out_floor + (1 - w_out_floor) * sigmoid((d_out_px - d(x, V_vis)) / 7.0)
         S_far(x) = tau_corridor * W_in(x) * W_out(x) * C_far(x)
                    * (0.68 + 0.32 * sqrt(max(P_dual(x), 0.01))) * (1 + 0.45 * R_vis(x))
      3. Stationary Max-Envelope:
         Phi_SMGC(x) = max(S_exp_mod(x), S_far(x))
    """
    d_vis = distance_transform_edt(~visible_mask).astype(np.float32)
    w_in = spcp._sigmoid_f32((d_vis - np.float32(d_in_px)) / np.float32(2.5))
    w_out = np.float32(w_out_floor) + np.float32(1.0 - w_out_floor) * spcp._sigmoid_f32(
        (np.float32(d_out_px) - d_vis) / np.float32(7.0)
    )
    w_cor = w_in * w_out
    del d_vis, w_in, w_out

    s_exp_m = s_exp * (
        np.float32(1.0)
        + np.float32(0.12) * p4_sharp
        + np.float32(0.25) * vis_relay * far_crest
    )
    if tau_corridor > 0.0:
        s_far = (
            np.float32(tau_corridor)
            * w_cor
            * far_crest
            * (np.float32(0.68) + np.float32(0.32) * np.sqrt(np.maximum(p_dual, np.float32(0.01))))
            * (np.float32(1.0) + np.float32(0.45) * vis_relay)
        )
        out = np.where(region_mask, np.maximum(s_exp_m, s_far), np.float32(0.0))
    else:
        out = np.where(region_mask, s_exp_m, np.float32(0.0))
    return np.clip(out, 0.0, 1.0).astype(np.float32)

