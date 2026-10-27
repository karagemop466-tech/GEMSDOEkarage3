#!/usr/bin/env python3
"""Reproduce the pinned historical-mask and lattice audit; this is NOT a model or scorer.

Downloads only immutable GitHub blobs listed in evidence/priority_inputs.json, verifies each
SHA-256, and uses the owner-mirrored sample's finite pixels as a *proxy* footprint. It does
not authenticate the organizer template, compare pre-placement surfaces, inventory the full
registry, evaluate DTI, create a submission, or consume a competition slot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "evidence" / "priority_inputs.json"
PRIORITY = ("24", "25", "27", "28", "30", "31", "32", "33", "36")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_input(item: dict, cache: Path, offline: bool = False) -> Path:
    """Hash-check local bytes, fetching pinned GitHub data atomically if necessary."""
    key = item["id"]
    if not key.isalnum():
        raise ValueError(f"Unsafe input id: {key!r}")
    dest = cache / f"{key}.tif"
    if dest.is_file() and dest.stat().st_size == item["bytes"] and sha256(dest) == item["sha256"]:
        return dest
    if offline:
        raise ValueError(f"{key}: missing or corrupt cached bytes in offline mode")
    cache.mkdir(parents=True, exist_ok=True)
    temporary = cache / f".{key}.partial"
    try:
        with temporary.open("wb") as stream:
            subprocess.run(
                ["gh", "api", f"repos/{item['repository']}/contents/{item['path']}?ref={item['ref']}",
                 "-H", "Accept: application/vnd.github.raw"],
                stdout=stream, stderr=subprocess.PIPE, check=True, timeout=180,
            )
        if temporary.stat().st_size != item["bytes"] or sha256(temporary) != item["sha256"]:
            raise ValueError(f"{key}: downloaded bytes did not match the pinned digest and size")
        temporary.replace(dest)
    finally:
        temporary.unlink(missing_ok=True)
    return dest


def disk(radius: int) -> np.ndarray:
    """A closed Euclidean disk; points exactly radius pixels away count as overlap."""
    yy, xx = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    return xx * xx + yy * yy <= radius * radius


def budget_bound(uncovered: int, budget: int) -> dict:
    """Smallest possible overlap fraction with a single comparator, not a score."""
    if type(uncovered) is not int or type(budget) is not int or uncovered < 0 or budget <= 0:
        raise ValueError("uncovered must be a non-negative integer and budget a positive integer")
    overlap = max(0, budget - uncovered)
    return {
        "candidate_dots": budget,
        "minimum_overlap_count": overlap,
        "minimum_overlap_fraction": overlap / budget,
        # Rational comparison avoids a rounding-based false pass at 70%.
        "necessarily_exceeds_70_percent": overlap * 10 > budget * 7,
    }


def _meta(src) -> tuple:
    return src.crs, tuple(src.transform)[:6], src.height, src.width


def _read_aligned(path: Path, template_meta: tuple) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as src:
        if src.count != 1 or _meta(src) != template_meta:
            raise ValueError(f"{path}: must be single-band and exactly match the proxy grid")
        data = src.read(1)
        return data, {"dtype": src.dtypes[0], "nodata": None if src.nodata is None else str(src.nodata)}


def build_audit(files: dict[str, Path], entries: dict[str, dict]) -> dict:
    with rasterio.open(files["footprint"]) as template:
        if template.count != 1 or template.crs is None:
            raise ValueError("Proxy template has no CRS or is not single-band")
        raw_foot = template.read(1)
        foot = np.isfinite(raw_foot) & (template.read_masks(1) > 0)
        if not np.any(foot):
            raise ValueError("Empty proxy footprint")
        grid = _meta(template)
        grid_info = {"crs": str(template.crs), "shape": [template.height, template.width],
                     "transform": list(tuple(template.transform)[:6]), "footprint_pixels": int(foot.sum())}

    labels_raw, _ = _read_aligned(files["labels"], grid)
    labels = (labels_raw == 1) & foot
    lattice_raw, _ = _read_aligned(files["lattice"], grid)
    lattice = np.isfinite(lattice_raw) & (lattice_raw > 0) & foot
    if not lattice.any():
        raise ValueError("Registered lattice has no positive pixels in the proxy footprint")
    coverage = ndimage.binary_dilation(lattice, structure=disk(3))
    uncovered = int(np.count_nonzero(foot & ~coverage))

    masks, rows = {}, []
    for key in PRIORITY:
        arr, meta = _read_aligned(files[key], grid)
        inside = arr[foot]
        if not np.isfinite(inside).all() or not np.all((inside == 0) | (inside == 1)):
            raise ValueError(f"{key}: historical footprint is not a finite binary mask")
        mask = foot & (arr == 1)
        count = int(mask.sum())
        if count == 0:
            raise ValueError(f"{key}: zero historical dots; overlap denominator is undefined")
        masks[key] = mask
        item = entries[key]
        rows.append({
            "site": f"GEMSDOE{key}", "source_url": item["url"],
            "research_download_url": f"https://github.com/{item['repository']}/raw/{item['ref']}/{item['path']}",
            "filename": Path(item["path"]).name, "file_sha256": item["sha256"],
            "in_footprint_mask_sha256": hashlib.sha256(np.packbits(mask[foot]).tobytes()).hexdigest(),
            "dots": count, "lattice_overlap_count": int(np.count_nonzero(mask & coverage)),
            "lattice_overlap_fraction": int(np.count_nonzero(mask & coverage)) / count,
            "single_band_grid_match_proxy": True, "inside_finite_binary": True,
            "dtype": meta["dtype"], "nodata": meta["nodata"],
            "outside_all_nan": bool(np.isnan(arr[~foot]).all()),
            "whole_grid_finite_and_in_range": bool(np.isfinite(arr).all() and np.all((arr >= 0) & (arr <= 1))),
            "positive_outside_footprint": int(np.count_nonzero(np.isfinite(arr[~foot]) & (arr[~foot] > 0))),
        })

    # Dilation once per reference; each of the 72 directional fractions uses all candidate dots.
    coverages = {key: ndimage.binary_dilation(mask, structure=disk(3)) for key, mask in masks.items()}
    comparisons = []
    for candidate, mask in masks.items():
        denominator = int(mask.sum())
        for reference, cover in coverages.items():
            if candidate == reference:
                continue
            numerator = int(np.count_nonzero(mask & cover))
            comparisons.append({"candidate": f"GEMSDOE{candidate}", "reference": f"GEMSDOE{reference}",
                                "overlap_count": numerator, "candidate_dots": denominator,
                                "fraction": numerator / denominator,
                                "exceeds_70_percent": numerator * 10 > denominator * 7})
    for row in rows:
        directed = [c for c in comparisons if c["candidate"] == row["site"]]
        nearest = max(directed, key=lambda c: c["fraction"])
        row["maximum_historical_overlap"] = nearest["fraction"]
        row["maximum_overlap_reference"] = nearest["reference"]
        row["unique_vs_other_eight_historical_masks"] = not any(c["exceeds_70_percent"] for c in directed)

    catalogue_collar = ndimage.binary_dilation(labels, structure=disk(2))
    base, champion, augmented = masks["31"], masks["32"], masks["36"]
    lineage = {
        "25_and_30_in_footprint_masks_identical": bool(np.array_equal(masks["25"], masks["30"])),
        "31_minus_32_dots": int(np.count_nonzero(base & ~champion)),
        "32_minus_31_dots": int(np.count_nonzero(champion & ~base)),
        "32_equals_31_after_2px_catalogue_collar": bool(np.array_equal(champion, base & ~catalogue_collar)),
        "36_minus_32_dots": int(np.count_nonzero(augmented & ~champion)),
        "32_minus_36_dots": int(np.count_nonzero(champion & ~augmented)),
        "proxy_sample_ones_match_label_ones": bool(np.array_equal((raw_foot == 1) & foot, labels)),
        "proxy_sample_positive_pixels": int(np.count_nonzero((raw_foot == 1) & foot)),
    }
    return {
        "schema_version": 1, "kind": "GEOMETRY-AUDIT — not a score",
        "computed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "Nine pinned historical binary masks and one registered lattice; not a full registry or a surface test.",
        "footprint_provenance": "Hash-pinned owner mirror; NOT an authenticated organizer sample.",
        "grid": grid_info,
        "lattice": {"filename": Path(entries["lattice"]["path"]).name,
                    "sha256": entries["lattice"]["sha256"], "source_url": entries["lattice"]["url"],
                    "registry_entry": json.loads(INPUTS.read_text())["lattice_registry_entry"],
                    "dots": int(lattice.sum()), "covered_footprint_pixels": int(np.count_nonzero(foot & coverage)),
                    "uncovered_footprint_pixels": uncovered,
                    "counting_bound": budget_bound(uncovered, 37654),
                    "max_dots_not_ruled_out_by_this_single_bound": (uncovered * 10) // 3,
                    "definition": "Positive pixels at Euclidean distance <=3 pixels; candidate dots must be inside the proxy footprint."},
        "lineage": lineage, "historical_rasters": rows, "directional_comparisons": comparisons,
        "new_experiments": 0, "competition_slots_used": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache" / "historical")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "priority-audit.json")
    parser.add_argument("--offline", action="store_true", help="Fail if any pinned input is missing or corrupt")
    args = parser.parse_args()
    try:
        manifest = json.loads(INPUTS.read_text())
        entries = {item["id"]: item for item in manifest["files"]}
        required = {"footprint", "labels", "lattice", *PRIORITY}
        if len(entries) != len(manifest["files"]) or set(entries) != required:
            raise ValueError("Input manifest does not contain exactly one entry for each required id")
        files = {key: fetch_input(entries[key], args.cache, args.offline) for key in sorted(required)}
        report = build_audit(files, entries)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix(args.output.suffix + ".partial")
        temp.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        temp.replace(args.output)
        print(f"Geometry audit written to {args.output}; no experiment, score, or submission was produced.")
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"Audit failed; no new receipt was written: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
