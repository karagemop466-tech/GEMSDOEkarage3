"""K3 label-free surfaces (see knowledge/preregistration_k3.md, frozen 2026-10-27).

Primitives ``robust_unit`` / ``line_response`` / ``collinearity_vote`` implement the same maths
as GEMSDOE32 ``src/gems32/h33.py`` (vendored-template repo, commit in PROVENANCE.md) and are
re-used under the brief's reuse rule; the K3 builders themselves are new. No builder reads
labels, existing faults, any scored raster, or any catalogue-derived column, so every surface
is safe under the visible-only hide-and-recover evaluator.

IR-K3-01 fix: external-raster bands are selected **by raster description name**, never by
assumed index (the template's LiDAR composite reads bands 1/2/5 while claiming
ex_max/step_max/downface_max; descriptions prove 2=ex_mean, 5=lappos_max).
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, maximum_filter

NODATA_SENTINEL = -3.4028234663852886e38


# --------------------------------------------------------------------------------------------
# shared primitives (same maths as template h33.py)
# --------------------------------------------------------------------------------------------

def robust_unit(a: np.ndarray, foot: np.ndarray, pct: float = 99.5, clip: float = 6.0) -> np.ndarray:
    """Robust footprint-normalised non-negative score in [0, 1] (median/IQR z scaled at pct)."""
    out = np.zeros(a.shape, dtype=np.float32)
    v = foot & np.isfinite(a)
    if not v.any():
        return out
    vals = a[v]
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25.0, 75.0])
    scale = max(float(q75 - q25) / 1.349, 1e-9)
    z = (a - med) / scale
    hi = max(float(np.percentile(z[v], pct)), 1e-6)
    out[v] = np.clip(z[v] / hi, 0.0, clip) / clip
    return out


def fill_smooth(a: np.ndarray, foot: np.ndarray, sigma: float | None) -> np.ndarray:
    """Median-fill non-valid pixels then optional Gaussian smoothing (template _fill)."""
    v = foot & np.isfinite(a)
    med = float(np.median(a[v])) if v.any() else 0.0
    f = np.where(v, a, med).astype(np.float32)
    return gaussian_filter(f, sigma, mode="nearest") if sigma else f


def line_response(a: np.ndarray, sigma: float) -> np.ndarray:
    """Frangi/Sato curvilinear response: -(Hessian eigenvalue of least |.|), both polarities."""
    axx = gaussian_filter(a, sigma, order=(0, 2), mode="nearest")
    ayy = gaussian_filter(a, sigma, order=(2, 0), mode="nearest")
    axy = gaussian_filter(a, sigma, order=(1, 1), mode="nearest")
    tmp = np.sqrt(np.maximum(((axx - ayy) * 0.5) ** 2 + axy ** 2, 0.0))
    l1 = (axx + ayy) * 0.5 + tmp
    l2 = (axx + ayy) * 0.5 - tmp
    small = np.where(np.abs(l1) >= np.abs(l2), l2, l1)
    return -small


def collinearity_vote(skel: np.ndarray, foot: np.ndarray, halflen: int = 4) -> np.ndarray:
    """Max mean skeleton occupancy over 8 straight lines of half-length ``halflen`` (template)."""
    s = np.where(foot, skel, 0.0).astype(np.float32)
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    best = np.zeros_like(s)
    for dy, dx in dirs:
        acc = np.zeros_like(s)
        for k in range(-halflen, halflen + 1):
            acc += np.roll(np.roll(s, k * dy, axis=0), k * dx, axis=1)
        np.maximum(best, acc / (2 * halflen + 1), out=best)
    return best


def band_npy(bands_dir: Path, idx: int, name: str, foot: np.ndarray) -> np.ndarray:
    a = np.load(bands_dir / f"{idx:02d}_{name}.npy").astype(np.float32)
    return np.where(foot & np.isfinite(a), a, np.nan)


def external_by_name(ddir: Path, rel: str, description: str, foot: np.ndarray) -> np.ndarray:
    """Read one band of an external raster selected by its embedded description (IR-K3-01)."""
    with rasterio.open(ddir / "external" / rel) as ds:
        names = list(ds.descriptions)
        if description not in names:
            raise KeyError(f"{rel}: band {description!r} not in descriptions {names}")
        a = ds.read(names.index(description) + 1).astype(np.float32)
    return np.where(foot, a, np.nan)


def rank_surface(surface: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Rank in [0,1] inside the footprint (memory-light: ranks footprint values only)."""
    out = np.zeros(surface.shape, dtype=np.float32)
    vals = np.asarray(surface, dtype=np.float32)[foot]
    order = np.argsort(np.argsort(vals, kind="stable"), kind="stable")
    out[foot] = order.astype(np.float32) / max(float(vals.size - 1), 1.0)
    return out


# --------------------------------------------------------------------------------------------
# K3-H3 — corrected-LiDAR crest-base scarp-pair (dipole)
# --------------------------------------------------------------------------------------------

def build_h3_scarppair(bands_dir: Path, ddir: Path, foot: np.ndarray) -> np.ndarray:
    """Crest-base dipole on the *correctly identified* 3DEP LiDAR bands.

    Bands (by description): step_max (10 m minus 50 m slope), lapneg_max (crest convexity),
    lappos_max (base concavity), downface_max / upface_max (step facing), coh100 (100 m
    orientation coherence), valid (lidar coverage). Quantisation is uint8 sqrt (template
    receipt), used as given. A pixel scores only where a convex crest and a concave base
    co-occur within a 3x3 neighbourhood (scarp profile), weighted by step amplitude, facing
    strength and orientation coherence. Mimics: paleo-shorelines, terrace risers, road cuts.
    """
    rel = "lidar_scarp_features_u8.tif"

    def u8(name: str) -> np.ndarray:
        return external_by_name(ddir, rel, name, foot) / 255.0

    valid = u8("valid")
    have = foot & np.isfinite(valid) & (valid > 0)
    step = robust_unit(fill_smooth(u8("step_max"), foot, 0.6), foot)
    crest = robust_unit(fill_smooth(u8("lapneg_max"), foot, 0.6), foot)
    base = robust_unit(fill_smooth(u8("lappos_max"), foot, 0.6), foot)
    face = robust_unit(
        np.maximum(fill_smooth(u8("downface_max"), foot, 0.6),
                   fill_smooth(u8("upface_max"), foot, 0.6)), foot)
    coh = np.clip(np.where(np.isfinite(u8("coh100")), u8("coh100"), 0.0), 0.0, 1.0)
    pair = np.minimum(maximum_filter(crest, size=3), maximum_filter(base, size=3))
    score = pair * (0.35 + 0.65 * step) * (0.35 + 0.65 * face) * (0.45 + 0.55 * coh)
    score = np.where(have, score, 0.0).astype(np.float32)
    out = robust_unit(score, foot)
    out[~have] = 0.0
    return out.astype(np.float32)


# --------------------------------------------------------------------------------------------
# K3-H1 — depth-persistent potential-field worms
# --------------------------------------------------------------------------------------------

def _worm_persistence(field: np.ndarray, foot: np.ndarray,
                      sigmas: tuple[float, ...] = (1.0, 2.0, 4.0)) -> np.ndarray:
    """Fraction of smoothing scales at which the pixel lies on (within 1 px of) an HG ridge,
    times scale-1 HG strength. Gaussian scale increase is the cheap proxy for upward
    continuation: deep/basement edges persist, shallow noise decays."""
    f = fill_smooth(field, foot, None)
    persist = np.zeros(foot.shape, dtype=np.float32)
    strength = None
    for s in sigmas:
        g = gaussian_filter(f, s, mode="nearest")
        gy, gx = np.gradient(g)
        hg = np.hypot(gy, gx).astype(np.float32)
        if strength is None:
            strength = robust_unit(hg, foot)
        ridge = (hg >= maximum_filter(hg, size=3) - 1e-12) & (hg > 0)
        persist += maximum_filter(ridge.astype(np.float32), size=3)
    persist /= float(len(sigmas))
    return (persist * (0.30 + 0.70 * strength)).astype(np.float32)


def build_h1_worms(bands_dir: Path, ddir: Path, foot: np.ndarray) -> np.ndarray:
    """OR-fusion of magnetic (rtp) and gravity (iso_grav_anom) worm persistence, with the
    contractor TMI upward-continued-150 m grid as a third voter. Mimics: lithologic contacts."""
    mag = _worm_persistence(band_npy(bands_dir, 2, "rtp", foot), foot)
    grav = _worm_persistence(band_npy(bands_dir, 13, "iso_grav_anom", foot), foot)
    up150 = external_by_name(ddir, "geodawn_extensions_u8.tif", "TMI_up150", foot)
    up = _worm_persistence(up150, foot, sigmas=(1.0, 2.0))
    a, b, c = (np.clip(robust_unit(x, foot), 0, 1) for x in (mag, grav, up))
    fusion = 1.0 - (1.0 - a) * (1.0 - b) * (1.0 - 0.6 * c)
    out = robust_unit(fusion.astype(np.float32), foot)
    out[~foot] = 0.0
    return out.astype(np.float32)


# --------------------------------------------------------------------------------------------
# K3-H4 — geodetic strain-localisation ridges (screen only)
# --------------------------------------------------------------------------------------------

def build_h4_strain(bands_dir: Path, ddir: Path, foot: np.ndarray) -> np.ndarray:
    inv = fill_smooth(band_npy(bands_dir, 4, "geod_2ndinv", foot), foot, 1.0)
    r = np.maximum(line_response(inv, 1.5), line_response(inv, 3.0))
    dil = fill_smooth(band_npy(bands_dir, 8, "geod_dilaterate", foot), foot, 1.0)
    gy, gx = np.gradient(dil)
    grad = robust_unit(np.hypot(gy, gx).astype(np.float32), foot)
    out = robust_unit((robust_unit(r.astype(np.float32), foot) * (0.4 + 0.6 * grad)), foot)
    out[~foot] = 0.0
    return out.astype(np.float32)


# --------------------------------------------------------------------------------------------
# K3-H2 — geothermal upflow boost (points; boost only, cannot fill a full budget)
# --------------------------------------------------------------------------------------------

def _clip01(x: float) -> float:
    return float(min(max(x, 0.0), 1.0))


def build_h2_upflow(bands_dir: Path, ddir: Path, foot: np.ndarray) -> tuple[np.ndarray, dict]:
    """Temperature-weighted well/spring + paleo-deposit density with a collinearity vote.

    Uses ONLY temperature/geothermometer/location columns. The CSV's
    ``dist_known_fault_px`` column is label-derived (template manifest warns) and is never
    read. Paleo points (Long/Lat NAD83) are projected with pyproj to EPSG:32611 grid indices.
    Returns (boost surface in [0,1], provenance counts)."""
    H, W = foot.shape
    w_raster = np.zeros((H, W), dtype=np.float32)
    stats: dict = {}
    csv_path = ddir / "external" / "gdr_wellspring_in_footprint.csv"
    n_rows = n_used = 0
    with csv_path.open(newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            n_rows += 1
            def num(key: str) -> float | None:
                try:
                    v = float(row.get(key) or "")
                    return v if np.isfinite(v) else None
                except ValueError:
                    return None
            r, c = num("row"), num("col")
            if r is None or c is None:
                continue
            r, c = int(r), int(c)
            if not (0 <= r < H and 0 <= c < W) or not foot[r, c]:
                continue
            w = 0.0
            t = num("temp_c")
            if t is not None:
                w = max(w, _clip01((t - 15.0) / 85.0))
            geos = [num(k) for k in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c")]
            geos = [g for g in geos if g is not None]
            if geos:
                w = max(w, _clip01((max(geos) - 100.0) / 120.0))
            if w > 0:
                w_raster[r, c] = max(w_raster[r, c], np.float32(w))
                n_used += 1
    stats["wellspring_rows"] = n_rows
    stats["wellspring_weighted_points"] = n_used
    stats["wellspring_unique_pixels"] = int((w_raster > 0).sum())

    paleo_used = 0
    zip_path = ddir / "external" / "paleo_geothermal_regional.zip"
    try:
        from pyproj import Transformer
        tr = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)
        with zipfile.ZipFile(zip_path) as z, z.open("Paleo_geothermal_final.csv") as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace")):
                try:
                    lon, lat = float(row["Long_deg_NAD83"]), float(row["Lat_deg_NAD83"])
                except (KeyError, TypeError, ValueError):
                    continue
                x, y = tr.transform(lon, lat)
                c, r = int((x - 243350.0) // 100.0), int((4508550.0 - y) // 100.0)
                if 0 <= r < H and 0 <= c < W and foot[r, c]:
                    w_raster[r, c] = max(w_raster[r, c], np.float32(0.7))
                    paleo_used += 1
    except Exception as exc:  # paleo is a boost component; failure must be visible, not fatal
        stats["paleo_error"] = f"{type(exc).__name__}: {exc}"
    stats["paleo_in_footprint"] = paleo_used

    density = gaussian_filter(w_raster, 2.0, mode="nearest") + 0.5 * gaussian_filter(w_raster, 6.0, mode="nearest")
    dens_n = robust_unit(density.astype(np.float32), foot)
    hot = (np.where(foot, w_raster, 0.0) > 0).astype(np.float32)
    hot_smooth = gaussian_filter(hot, 1.5, mode="nearest")
    chain = collinearity_vote((hot_smooth > 0.05).astype(np.float32), foot, halflen=5)
    out = robust_unit((dens_n * (0.5 + 0.5 * chain)).astype(np.float32), foot)
    out[~foot] = 0.0
    return out.astype(np.float32), stats


BUILDERS = {
    "K3-H3-scarppair": build_h3_scarppair,
    "K3-H1-worms": build_h1_worms,
    "K3-H4-strain": build_h4_strain,
}

SPECS = {
    "K3-H3-scarppair": dict(
        hypothesis="Corrected-LiDAR crest-base scarp-pair dipole",
        layers=["lidar_scarp_features_u8: step_max, lapneg_max, lappos_max, downface_max, upface_max, coh100, valid (by description)"],
        mimic="Lake Lahontan paleo-shorelines, terrace risers, road cuts, landslide head scarps"),
    "K3-H1-worms": dict(
        hypothesis="Depth-persistent potential-field worms (multi-scale HG-ridge persistence)",
        layers=["rtp(2)", "iso_grav_anom(13)", "geodawn_extensions TMI_up150"],
        mimic="Lithologic contacts and dike margins (potential-field edges without fault offset)"),
    "K3-H4-strain": dict(
        hypothesis="Geodetic strain-localisation ridges",
        layers=["geod_2ndinv(4)", "geod_dilaterate(8)"],
        mimic="Block-rotation strain gradients and GPS/InSAR interpolation artefacts"),
    "K3-H2-upflow": dict(
        hypothesis="Geothermal upflow chains (well/spring + paleo deposits), boost only",
        layers=["gdr_wellspring_in_footprint.csv (temp/geothermometers)", "paleo_geothermal_regional.zip:Paleo_geothermal_final.csv"],
        mimic="Lateral outflow plumes and road/valley sampling bias"),
}

