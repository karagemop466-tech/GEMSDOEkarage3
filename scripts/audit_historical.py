#!/usr/bin/env python3
"""Reproduce a *forensic* audit, not a training run or an organizer score.

Fetch immutable, SHA-256-pinned owner-repository files. Measure grid/range,
full-footprint binary Spearman and directed <=3-pixel overlap, and the
lattice pigeonhole bound. This is neither the complete registry nor the
shared hide-and-recover evaluator or submission writer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import tempfile
import urllib.parse
import urllib.request

import numpy as np
import rasterio
import scipy
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "focus_registry.json"
MAX_REFERENCE_BYTES = 16 * 1024 * 1024


class GitHubOnlyRedirect(urllib.request.HTTPRedirectHandler):
    """Do not send a GitHub bearer token to a redirected foreign host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.netloc != "api.github.com":
            raise ValueError("Refusing a redirect outside https://api.github.com")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(record: dict, cache_dir: Path) -> Path:
    """Fetch only immutable GitHub API paths, rejecting corrupt cached bytes."""
    repo, ref, path, expected = (record[k] for k in ("repo", "ref", "path", "sha256"))
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid repository")
    if not re.fullmatch(r"[0-9a-f]{40}", ref) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Expected immutable commit and SHA-256")
    if path.startswith("/") or any(part in ("", ".", "..") for part in path.split("/")):
        raise ValueError("Invalid GitHub file path")
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / (expected + ".tif")
    if target.exists():
        if sha256_file(target) != expected:
            raise ValueError(f"Cached file hash mismatch: {target}")
        return target
    url = f"https://api.github.com/repos/{repo}/contents/{urllib.parse.quote(path, safe='/')}?ref={ref}"
    headers = {"Accept": "application/vnd.github.raw+json", "User-Agent": "GEMSDOEkarage3-forensic-audit"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    req = urllib.request.Request(url, headers=headers)
    # The references are small; stream to a temporary file and atomically publish only after hashing.
    opener = urllib.request.build_opener(GitHubOnlyRedirect())
    with opener.open(req, timeout=90) as response, tempfile.NamedTemporaryFile(dir=cache_dir, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            digest = hashlib.sha256()
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_REFERENCE_BYTES:
                    raise ValueError(f"Reference exceeds {MAX_REFERENCE_BYTES} bytes")
                digest.update(chunk)
                tmp.write(chunk)
            tmp.close()
            if digest.hexdigest() != expected:
                raise ValueError(f"Hash mismatch for {repo}/{path}")
            tmp_path.replace(target)
        finally:
            tmp_path.unlink(missing_ok=True)
    return target


def binary_spearman(n: int, a: int, b: int, intersection: int) -> float | None:
    """Exact tie-aware Spearman for two binary arrays (Pearson on binaries)."""
    if min(a, b) <= 0 or max(a, b) >= n:
        return None
    return (n * intersection - a * b) / math.sqrt(a * (n - a) * b * (n - b))


def lower_overlap_bound(dots: int, uncovered: int) -> tuple[int, int]:
    """Minimum covered positive cells / dots for distinct in-footprint dots."""
    if dots <= 0 or uncovered < 0:
        raise ValueError("dots must be positive and uncovered nonnegative")
    return max(0, dots - uncovered), dots


def read_raster(path: Path, template_profile: dict, footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        checks = {
            "single_band": ds.count == 1,
            "float32": ds.count == 1 and ds.dtypes[0] == "float32",
            "crs_matches_mirror": ds.crs == template_profile["crs"],
            "shape_matches_mirror": ds.shape == template_profile["shape"],
            "transform_matches_mirror": ds.transform == template_profile["transform"],
        }
        if not all(checks.values()):
            raise ValueError(f"Invalid or unaligned raster {path.name}: {checks}")
        arr = ds.read(1)
        valid_mask = ds.read_masks(1) != 0
        inside = arr[footprint]
        finite = np.isfinite(arr)
        checks["inside_all_finite"] = bool(np.isfinite(inside).all())
        checks["inside_not_nodata_or_masked"] = bool(valid_mask[footprint].all())
        checks["inside_range_0_1"] = bool(checks["inside_all_finite"] and (inside >= 0).all() and (inside <= 1).all())
        # Conservative template-footprint interpretation, not an organizer acceptance test.
        outside = arr[~footprint]
        nodata = ds.nodata
        is_null = np.isnan(outside) | ~valid_mask[~footprint]
        checks["outside_footprint_null_conservative"] = bool(is_null.all())
        checks["whole_array_finite_range_diagnostic"] = bool(finite.all() and (arr >= 0).all() and (arr <= 1).all())
        info = {
            "sha256": sha256_file(path),
            "checks": checks,
            "inside_nonfinite": int((~np.isfinite(inside)).sum()),
            "inside_masked": int((~valid_mask[footprint]).sum()),
            "inside_min": float(inside.min()) if checks["inside_all_finite"] and inside.size else None,
            "inside_max": float(inside.max()) if checks["inside_all_finite"] and inside.size else None,
            "nodata": None if nodata is None else ("NaN" if math.isnan(nodata) else float(nodata)),
        }
        if not checks["inside_range_0_1"] or not checks["inside_not_nodata_or_masked"]:
            raise ValueError(f"Invalid or masked inside-footprint values: {path.name}")
        # This forensic analysis is defined on binary support, not arbitrary continuous predictions.
        if not np.all((inside == 0) | (inside == 1)):
            raise ValueError(f"Expected binary historic raster: {path.name}")
        return (arr > 0) & footprint, info


def run(manifest_path: Path = MANIFEST, cache_dir: Path = ROOT / "data" / "cache") -> dict:
    manifest = json.loads(manifest_path.read_text())
    inputs = manifest["inputs"]
    template_path = fetch(inputs["template"], cache_dir)
    labels_path = fetch(inputs["labels"], cache_dir)
    lattice_path = fetch(inputs["lattice"], cache_dir)
    with rasterio.open(template_path) as ds:
        if ds.count != 1 or ds.dtypes[0] != "float32" or ds.crs is None:
            raise ValueError("Invalid template mirror")
        template = ds.read(1)
        foot = (ds.read_masks(1) != 0) & np.isfinite(template)
        if not foot.any():
            raise ValueError("Empty template footprint")
        profile = {"crs": ds.crs, "shape": ds.shape, "transform": ds.transform}
    with rasterio.open(labels_path) as ds:
        if ds.count != 1 or ds.shape != profile["shape"] or ds.crs != profile["crs"] or ds.transform != profile["transform"]:
            raise ValueError("Labels grid differs from template")
        labels = ds.read(1)
        if not (ds.read_masks(1)[foot] != 0).all():
            raise ValueError("Labels are masked inside the template footprint")
    if not np.all((labels[foot] == 0) | (labels[foot] == 1)):
        raise ValueError("Unexpected label encoding inside footprint")
    label_mask = (labels == 1) & foot
    lattice, lattice_info = read_raster(lattice_path, profile, foot)
    if not lattice.any():
        raise ValueError("Lattice has no positive pixels")
    dist_lattice = distance_transform_edt(~lattice)
    covered = foot & (dist_lattice <= 3.0)
    uncovered = int((foot & ~covered).sum())
    total = int(foot.sum())
    masks: dict[str, np.ndarray] = {}
    rows = []
    for record in manifest["sites"]:
        local_path = fetch(record, cache_dir)
        mask, info = read_raster(local_path, profile, foot)
        masks[record["site"]] = mask
        n = int(mask.sum())
        if not n:
            raise ValueError(f"Empty positive support: {record['site']}")
        matches = int((mask & covered).sum())
        rows.append({"site": record["site"], "file": Path(record["path"]).name,
                     "source_url": record["source_url"], "site_url": record["site_url"],
                     "historical_claim": record["historical_claim"], "claim_class": record["claim_class"],
                     "leaderboard_estimate": None, "dots": n, "format": info,
                     "lattice_matches": matches, "lattice_fraction": matches / n,
                     "lattice_duplicate": matches * 10 > n * 7,
                     "new_submission_authorized": False})
    comparisons = []
    # Distance is Euclidean between pixel centres, not a buffered catalogue exclusion.
    for reference_site, reference in masks.items():
        distance = distance_transform_edt(~reference)
        for candidate_site, candidate in masks.items():
            if candidate_site == reference_site:
                continue
            n_candidate, n_ref = int(candidate.sum()), int(reference.sum())
            matches = int((candidate & (distance <= 3.0)).sum())
            intersection = int((candidate & reference).sum())
            rho = binary_spearman(total, n_candidate, n_ref, intersection)
            comparisons.append({"candidate": candidate_site, "reference": reference_site,
                                "candidate_dots": n_candidate, "within_3px": matches,
                                "fraction": matches / n_candidate, "binary_spearman": rho,
                                "identical_positive_support": bool(n_candidate == n_ref == intersection),
                                "duplicate_stop": bool(matches * 10 > n_candidate * 7 or rho is None or abs(rho) > .90)})
    for row in rows:
        comparisons_for_row = [c for c in comparisons if c["candidate"] == row["site"]]
        worst = max(comparisons_for_row, key=lambda c: c["fraction"])
        row["worst_focus_comparator"] = worst["reference"]
        row["worst_focus_fraction"] = worst["fraction"]
        row["duplicate_vs_focus"] = any(c["duplicate_stop"] for c in comparisons_for_row)
    winner, solo, plus = masks["GEMSDOE32"], masks["GEMSDOE31"], masks["GEMSDOE36"]
    removed = solo & ~winner
    dist_labels = distance_transform_edt(~label_mask)
    champion_budget = int(winner.sum())
    lower_n, lower_d = lower_overlap_bound(champion_budget, uncovered)
    return {
        "schema_version": 1, "kind": "GEOMETRY-AUDIT, NOT A SCORE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": sha256_file(manifest_path),
        "software": {"numpy": np.__version__, "scipy": scipy.__version__, "rasterio": rasterio.__version__},
        "scope": "Nine pinned historical files and one lattice witness only; NOT a complete current registry; no prediction surfaces audited.",
        "template_provenance": inputs["template"]["provenance"],
        "grid": {"shape": list(profile["shape"]), "crs": str(profile["crs"]),
                 "transform": list(profile["transform"])[:6], "footprint_pixels": total,
                 "template_positive_pixels": int((template[foot] == 1).sum()),
                 "label_positive_pixels": int(label_mask.sum()),
                 "template_positives_equal_labels": bool(np.array_equal((template == 1) & foot, label_mask))},
        "lattice": {"source": inputs["lattice"], "format": lattice_info,
                    "positive_pixels": int(lattice.sum()), "covered_within_3px": int(covered.sum()),
                    "uncovered_beyond_3px": uncovered, "covered_fraction": int(covered.sum()) / total,
                    "budget_example": champion_budget, "budget_lower_bound_numerator": lower_n,
                    "budget_lower_bound_denominator": lower_d, "budget_lower_bound": lower_n / lower_d,
                    "max_budget_not_proven_to_fail_by_count_alone": (uncovered * 10) // 3},
        "lineage": {"g25_g30_identical_positive_support": bool(np.array_equal(masks["GEMSDOE25"], masks["GEMSDOE30"])),
                    "g31_not_g32": int(removed.sum()), "g32_not_g31": int((winner & ~solo).sum()),
                    "removed_within_2px_of_labels": int((removed & (dist_labels <= 2)).sum()),
                    "g36_not_g32": int((plus & ~winner).sum()), "g32_not_g36": int((winner & ~plus).sum())},
        "sites": rows, "pairwise": comparisons,
        "no_organizer_receipts": True, "no_new_experiment": True, "no_new_tif": True, "weekly_slot_selected": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "data" / "historical-audit.json")
    args = parser.parse_args()
    result = run(args.manifest, args.cache_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Wrote {args.out}; {len(result['sites'])} historical references; no new TIFF or score.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
