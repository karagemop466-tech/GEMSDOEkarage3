"""A48-H1 JXSTEP — fault-juxtaposition step-concordance channels (label-free).

Frozen lane: ``docs/research/arena48-preregistration-and-hypotheses.md`` §2.

Geology in one line: a fault juxtaposes two different crustal/surface blocks, so
*across* its trace several independent fields step at the same orientation even when
the elevation scarp itself is buried or degraded (the population a surface-scarp
catalogue structurally misses).

For every field ``f`` and every strike-normal orientation ``n`` this module fits the
concentrated step-vs-ramp cross-profile used by R6-1 for elevation, generalised to
non-elevation fields:

    din  = f(+2.5 px along n) - f(-2.5 px along n)
    dout = f(+6.5 px along n) - f(-6.5 px along n)
    r    = |dout| / (|din| + eps)          (~1 pure step, ~2.6 pure ramp)
    c    = clip((2.6 - r) / 1.6, 0, 1),  zero unless sign(din) == sign(dout)
    step = |din| * c

Fields (official 19-band stack indices, see ``features.CHANNELS``):
``depth_to_base_surf`` (15), ``iso_grav_anom`` (13), ``cond_surf`` (17), ``tc`` (6;
radiometric total count), and a *second-moment* field — the 5x5 local standard
deviation (roughness) of ``det_elev`` (12) — whose step records a surface-age/texture
juxtaposition rather than an elevation offset.

Outputs (7 float32 channels, zero outside the 8-px-eroded footprint so footprint-rim
cliffs can never masquerade as steps):

    jx_step_depth, jx_step_grav, jx_step_cond, jx_step_tc, jx_step_rough
        per-field step magnitude maximised over the 4 orientations (field units);
    jx_concordant
        same-orientation geometric mean of the robust-normalised (p99) per-field
        step scores, maximised over orientation;
    jx_quiescent
        jx_concordant * exp(-elev_step / p99(elev_step)): the blind variant that
        keeps juxtapositions *without* an elevation step.

No catalogue-derived quantity enters any channel: the only masks are the sample
footprint.  Leakage is additionally screened by the runner's single-feature canary.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import ndimage

JX_CHANNELS = [
    "jx_step_depth",
    "jx_step_grav",
    "jx_step_cond",
    "jx_step_tc",
    "jx_step_rough",
    "jx_concordant",
    "jx_quiescent",
]

# features.CHANNELS order: band01..band19 occupy indices 0..18.
_FIELD_INDEX = {
    "jx_step_depth": 14,   # band15 depth_to_base_surf
    "jx_step_grav": 12,    # band13 iso_grav_anom
    "jx_step_cond": 16,    # band17 cond_surf
    "jx_step_tc": 5,       # band06 tc (radiometric total count)
}
_DEM_INDEX = 11            # band12 det_elev

_NORMALS = (
    (0.0, 1.0),
    (1.0, 0.0),
    (float(np.sqrt(0.5)), float(np.sqrt(0.5))),
    (float(np.sqrt(0.5)), -float(np.sqrt(0.5))),
)
_INNER_PX = 2.5
_OUTER_PX = 6.5
_RAMP_RATIO = _OUTER_PX / _INNER_PX  # 2.6 for a pure linear ramp


def _sample(f: np.ndarray, dy: float, dx: float) -> np.ndarray:
    """``f`` sampled at ``(y+dy, x+dx)`` (bilinear, nearest edge extension)."""
    return ndimage.shift(f, shift=(-dy, -dx), order=1, mode="nearest")


def step_score_orientation(f_smooth: np.ndarray, dy: float, dx: float) -> np.ndarray:
    """Concentrated-step magnitude of a (pre-smoothed) field across normal ``(dy, dx)``."""
    ip = _sample(f_smooth, _INNER_PX * dy, _INNER_PX * dx)
    im = _sample(f_smooth, -_INNER_PX * dy, -_INNER_PX * dx)
    op = _sample(f_smooth, _OUTER_PX * dy, _OUTER_PX * dx)
    om = _sample(f_smooth, -_OUTER_PX * dy, -_OUTER_PX * dx)
    din = ip - im
    dout = op - om
    eps = np.float32(1e-12)
    r = np.abs(dout) / (np.abs(din) + eps)
    np.minimum(r, np.float32(10.0), out=r)
    c = np.clip((_RAMP_RATIO - r) / (_RAMP_RATIO - 1.0), 0.0, 1.0)
    c = np.where(din * dout > 0, c, np.float32(0.0)).astype(np.float32)
    return (np.abs(din).astype(np.float32) * c).astype(np.float32)


def step_score(f: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    """Max-over-orientation step score plus the per-orientation scores of field ``f``."""
    f_smooth = ndimage.gaussian_filter(np.asarray(f, dtype=np.float32), sigma=1.2, mode="nearest")
    per_o = [step_score_orientation(f_smooth, dy, dx) for dy, dx in _NORMALS]
    best = per_o[0].copy()
    for s in per_o[1:]:
        np.maximum(best, s, out=best)
    best = np.where(valid, best, np.float32(0.0)).astype(np.float32)
    per_o = [np.where(valid, s, np.float32(0.0)).astype(np.float32) for s in per_o]
    return best, per_o


def _roughness(dem: np.ndarray) -> np.ndarray:
    """5x5 local standard deviation (second-moment / texture field) of the DEM."""
    dem = np.asarray(dem, dtype=np.float32)
    mean = ndimage.uniform_filter(dem, size=5, mode="nearest")
    mean_sq = ndimage.uniform_filter(dem * dem, size=5, mode="nearest")
    var = np.maximum(mean_sq - mean * mean, np.float32(0.0))
    return np.sqrt(var).astype(np.float32)


def _p99(a: np.ndarray, valid: np.ndarray) -> float:
    v = a[valid]
    return float(np.percentile(v, 99.0)) if v.size else 1.0


def build_jx_stack(stack: np.ndarray, foot: np.ndarray, out_path: str | Path,
                   log=print) -> np.ndarray:
    """Build (or reuse) the (H, W, 7) float32 JXSTEP stack as a disk memmap."""
    out_path = Path(out_path)
    h, w = foot.shape
    if out_path.exists():
        mm = np.lib.format.open_memmap(out_path, mode="r")
        if mm.shape == (h, w, len(JX_CHANNELS)) and mm.dtype == np.float32:
            log(f"[jx] reusing cached {out_path} {mm.shape}")
            return mm
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out = np.lib.format.open_memmap(out_path, mode="w+", dtype=np.float32,
                                     shape=(h, w, len(JX_CHANNELS)))
    valid = ndimage.binary_erosion(np.asarray(foot, bool), iterations=8)

    fields = {}
    for name, idx in _FIELD_INDEX.items():
        fields[name] = np.asarray(stack[:, :, idx], dtype=np.float32)
    dem = np.asarray(stack[:, :, _DEM_INDEX], dtype=np.float32)
    fields["jx_step_rough"] = _roughness(dem)

    # log-sum of (normalised score + 0.01) per orientation for the concordance mean
    logsum = [np.zeros((h, w), dtype=np.float32) for _ in _NORMALS]
    for ci, name in enumerate(JX_CHANNELS[:5]):
        best, per_o = step_score(fields[name], valid)
        out[:, :, ci] = best
        log(f"[jx] {name}: p99(valid)={_p99(best, valid):.4g}")
        for o, s in enumerate(per_o):
            p = _p99(s, valid) or 1.0
            logsum[o] += np.log(s / np.float32(p) + np.float32(0.01)).astype(np.float32)
        del best, per_o
    del fields

    concordant = np.zeros((h, w), dtype=np.float32)
    for ls in logsum:
        g = np.exp(ls / np.float32(5.0)).astype(np.float32) - np.float32(0.01)
        np.maximum(concordant, g, out=concordant)
    del logsum
    concordant = np.where(valid, np.clip(concordant, 0.0, None), np.float32(0.0)).astype(np.float32)
    out[:, :, 5] = concordant

    elev_best, _ = step_score(dem, valid)
    del dem
    p_elev = _p99(elev_best, valid) or 1.0
    quiescent = concordant * np.exp(-elev_best / np.float32(p_elev)).astype(np.float32)
    out[:, :, 6] = np.where(valid, quiescent, np.float32(0.0)).astype(np.float32)
    log(f"[jx] jx_concordant p99={_p99(concordant, valid):.4g}; "
        f"jx_quiescent p99={_p99(out[:, :, 6], valid):.4g}")
    out.flush()
    return np.lib.format.open_memmap(out_path, mode="r")
