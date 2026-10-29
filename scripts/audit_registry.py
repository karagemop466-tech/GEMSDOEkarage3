#!/usr/bin/env python3
"""Reproduce the nine-file geometric audit, without fitting a model.

The listed GitHub rasters are owner-supplied, hash-pinned mirrors, not
organizer-authenticated competition data. A single lattice witness can prove a
failure; this nine-file subset can never establish full-registry uniqueness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote, urlparse

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "historical.json"
VERSION = "gems-karage3-geometry-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def api_path(source: str) -> str:
    parsed = urlparse(source)
    parts = parsed.path.strip("/").split("/")
    if (parsed.scheme != "https" or parsed.netloc != "github.com" or len(parts) < 5
            or parts[2] != "blob" or not re.fullmatch(r"[0-9a-f]{40}", parts[3])):
        raise ValueError(f"Expected immutable GitHub blob URL: {source}")
    owner, repo, _, ref = parts[:4]
    return f"repos/{quote(owner)}/{quote(repo)}/contents/{quote('/'.join(parts[4:]), safe='/')}?ref={ref}"


def ensure_file(entry: dict, path: Path, fetch: bool) -> None:
    expected = entry["raster_sha256"]
    if path.is_file() and sha256(path) == expected:
        return
    if not fetch:
        raise FileNotFoundError(f"Missing or hash-mismatched {path}; use --fetch to restore the pinned bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name, suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            subprocess.run(["gh", "api", api_path(entry["source_url"]), "-H",
                            "Accept: application/vnd.github.raw"], stdout=out, check=True)
        tmp = Path(name)
        if sha256(tmp) != expected:
            raise ValueError(f"SHA-256 mismatch downloading {entry['source_url']}")
        os.replace(tmp, path)
    finally:
        Path(name).unlink(missing_ok=True)


def boundary_ring_share(dots: np.ndarray, footprint: np.ndarray) -> float | None:
    """Share of positive dots lying in the 3-cell edge band of the footprint.

    The lattice witness leaves only 6,649 footprint cells uncovered and 6,580 of
    them are this edge band (see evidence/lattice-feasibility-20261029.json). A
    file that places most of its dots there clears a 3-px test by geometry alone,
    not by geology, so the saved-byte audits record this share as a separate refusal.
    """
    from scipy.ndimage import binary_erosion
    ring = footprint & ~binary_erosion(footprint, iterations=3)
    n = int(dots.sum())
    return float((dots & ring).sum() / n) if n else None


def dilate_disk(mask: np.ndarray, radius: int) -> np.ndarray:
    """Nonwrapping Euclidean integer-pixel disk, inclusive of the radius."""
    if mask.ndim != 2 or radius < 0 or int(radius) != radius:
        raise ValueError("Need a 2-D mask and nonnegative integer radius")
    mask = np.asarray(mask, dtype=bool)
    height, width = mask.shape
    expanded = np.zeros_like(mask)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dy * dy + dx * dx > radius * radius:
                continue
            # Explicit clipping: displacements larger than a tiny image do not wrap.
            if abs(dy) >= height or abs(dx) >= width:
                continue
            src_y = slice(max(0, -dy), min(height, height - dy))
            src_x = slice(max(0, -dx), min(width, width - dx))
            dst_y = slice(max(0, dy), min(height, height + dy))
            dst_x = slice(max(0, dx), min(width, width + dx))
            expanded[dst_y, dst_x] |= mask[src_y, src_x]
    return expanded


def binary_spearman(a: np.ndarray, b: np.ndarray, footprint: np.ndarray) -> float | None:
    """Spearman's rho for two binary rasters, including tied zero ranks.

    Binary Spearman is Pearson's phi on positive indicators. Return None for a
    constant raster; an undefined correlation is not a pass.
    """
    n = int(footprint.sum())
    x = int((a & footprint).sum())
    y = int((b & footprint).sum())
    both = int((a & b & footprint).sum())
    den = x * (n - x) * y * (n - y)
    if den <= 0:
        return None
    return (n * both - x * y) / math.sqrt(den)


def dot_bound(n_dots: int, n_uncovered: int) -> dict:
    """Necessary lower bound; exactly 70% is allowed by the prompt's > rule."""
    if isinstance(n_dots, bool) or isinstance(n_uncovered, bool) or not isinstance(n_dots, int) or not isinstance(n_uncovered, int):
        raise ValueError("counts must be integers")
    if n_dots <= 0 or n_uncovered < 0:
        raise ValueError("dot count must be positive and uncovered nonnegative")
    overlap = max(0, n_dots - n_uncovered)
    fraction = Fraction(overlap, n_dots)
    return {"dots": n_dots, "minimum_overlap_dots": overlap,
            "minimum_overlap_fraction": float(fraction),
            "duplicate_stop_proven": fraction > Fraction(7, 10)}


def checked_raster(path: Path, template_geometry, footprint, *, binary: bool):
    with rasterio.open(path) as ds:
        if ds.driver != "GTiff" or ds.count != 1 or ds.dtypes[0] != "float32":
            raise ValueError(f"{path}: not a single-band float32 GeoTIFF")
        if (ds.shape, ds.crs, ds.transform) != template_geometry:
            raise ValueError(f"{path}: CRS, shape or transform mismatch")
        arr = ds.read(1)
        no_data = ds.nodata
    inside = arr[footprint]
    if not np.isfinite(inside).all() or np.any((inside < 0) | (inside > 1)):
        raise ValueError(f"{path}: invalid values inside footprint")
    if binary and not np.all((inside == 0) | (inside == 1)):
        raise ValueError(f"{path}: not binary; binary rank formula cannot be used")
    dots = (arr > 0) & footprint
    if not dots.any():
        raise ValueError(f"{path}: empty positive support")
    outside = arr[~footprint]
    summary = {
        "sha256": sha256(path), "dots": int(dots.sum()),
        "inside_nonfinite": int((~np.isfinite(inside)).sum()),
        "inside_min": float(inside.min()), "inside_max": float(inside.max()),
        "outside_nan": int(np.isnan(outside).sum()),
        "outside_finite_zero": int((np.isfinite(outside) & (outside == 0)).sum()),
        "nodata": "NaN" if no_data is not None and math.isnan(no_data) else no_data,
    }
    return dots, summary


def audit(manifest: dict, cache: Path, fetch: bool) -> dict:
    entries = [("template", manifest["template"]), ("labels", manifest["labels"]),
               ("lattice", manifest["lattice"])]+[(r["site"], r) for r in manifest["historical"]]
    for name, entry in entries:
        ensure_file(entry, cache / f"{name}.tif", fetch)
    with rasterio.open(cache / "template.tif") as ds:
        if ds.driver != "GTiff" or ds.count != 1 or ds.dtypes[0] != "float32" or ds.crs is None:
            raise ValueError("Unusable mirrored template")
        sample = ds.read(1)
        footprint = np.isfinite(sample) & (ds.read_masks(1) != 0)
        if not footprint.any():
            raise ValueError("Empty template footprint")
        geometry = (ds.shape, ds.crs, ds.transform)
        grid = {"shape": list(ds.shape), "crs": str(ds.crs), "transform": list(ds.transform)[:6],
                "footprint_pixels": int(footprint.sum()), "template_sha256": sha256(cache / 'template.tif')}
    with rasterio.open(cache / "labels.tif") as ds:
        if (ds.shape, ds.crs, ds.transform) != geometry or ds.count != 1:
            raise ValueError("Labels grid mismatch")
        label = (ds.read(1) > 0) & footprint
    sample_positive = (sample > 0) & footprint
    grid["template_positive_pixels"] = int(sample_positive.sum())
    grid["sample_positive_pixels_equal_label_support"] = bool(np.array_equal(sample_positive, label))
    lattice, lattice_info = checked_raster(cache / "lattice.tif", geometry, footprint, binary=True)
    lattice_near = dilate_disk(lattice, 3)
    uncovered = int((footprint & ~lattice_near).sum())
    candidates = {}
    summaries = {}
    for item in manifest["historical"]:
        name = item["site"]
        dots, info = checked_raster(cache / f"{name}.tif", geometry, footprint, binary=True)
        candidates[name] = dots
        summaries[name] = info
        info["lattice_overlap_fraction"] = float((dots & lattice_near).sum() / int(dots.sum()))
        info["budget_bound"] = dot_bound(int(dots.sum()), uncovered)
    # The prompt's directional definition is candidate dots near reference dots.
    pairs = []
    for ref, dots in candidates.items():
        near = dilate_disk(dots, 3)
        for cand, cand_dots in candidates.items():
            if cand == ref:
                continue
            fraction = float((cand_dots & near).sum() / int(cand_dots.sum()))
            rho = binary_spearman(cand_dots, dots, footprint)
            pairs.append({"candidate": cand, "reference": ref,
                          "fraction_candidate_dots_within_3px": fraction,
                          "spearman_binary_footprint": rho,
                          "exact_binary_support_equal": bool(np.array_equal(cand_dots, dots)),
                          "duplicate_stop": rho is None or abs(rho) > 0.90 or fraction > 0.70})
    ref600 = candidates["GEMSDOE25"]
    ref31 = candidates["GEMSDOE31"]
    ref32 = candidates["GEMSDOE32"]
    near_cat2 = dilate_disk(label, 2)
    lineage = {
        "gem31_subset_of_gem25": bool(np.all(~ref31 | ref600)),
        "gem32_equals_gem31_without_label_within_2px": bool(np.array_equal(ref32, ref31 & ~near_cat2)),
        "gem32_subset_of_gem25": bool(np.all(~ref32 | ref600)),
        "gem25_equal_gem30_binary_support": bool(np.array_equal(ref600, candidates['GEMSDOE30'])),
        "gem36_contains_gem32": bool(np.all(~ref32 | candidates['GEMSDOE36'])),
        "gem36_extra_dots_over_gem32": int((candidates['GEMSDOE36'] & ~ref32).sum()),
        "gem31_dots_removed_to_gem32": int(ref31.sum()) - int(ref32.sum()),
    }
    return {
        "version": VERSION, "created_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_class": "GEOMETRY-AUDIT (not a score)",
        "scope": "Pinned owner-supplied mirrors: nine historical rasters and one registered lattice; not a complete registry.",
        "template_provenance": manifest["template"]["provenance"], "grid": grid,
        "lattice": {**lattice_info, "radius_px": 3,
                    "covered_footprint_pixels": int((footprint & lattice_near).sum()),
                    "uncovered_footprint_pixels": uncovered,
                    "bound_for_37654_dots": dot_bound(37654, uncovered)},
        "rasters": summaries, "pairs": pairs, "lineage": lineage,
        "pre_placement_surface_checked": False,
        "note": "A failed comparator proves a duplicate stop. Passing this subset does not establish complete-registry uniqueness, holdout validity or organizer acceptance.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Restore missing pinned files using gh api")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache" / "historical")
    parser.add_argument("--out", type=Path, default=ROOT / "evidence" / "geometry_audit.json")
    args = parser.parse_args()
    try:
        result = audit(json.loads(MANIFEST.read_text()), args.cache, args.fetch)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        print(json.dumps({"output": str(args.out), "version": VERSION, "grid": result["grid"],
                          "lattice": result["lattice"], "lineage": result["lineage"]}, indent=2))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"AUDIT FAILED CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
