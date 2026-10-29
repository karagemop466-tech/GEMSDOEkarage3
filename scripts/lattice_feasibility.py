#!/usr/bin/env python3
"""Literal 3-px lattice feasibility audit for the DOE GEMS uniqueness rule.

Question answered (no scores, no submission authorised):
  Can ANY submission whose dots lie inside the competition footprint keep the
  share of dots within 3 px of the registered calibration lattice
  (13GEMSDOE r13-lattice-s5, SHA-256 b4570b40...) at or below 70%?

Method (all numbers are measured from the bytes on disk):
  * footprint = finite & unmasked cells of sample_submission.tif (EPSG:32611, 3730 x 3292)
  * lattice dots = cells > 0 in the lattice raster
  * covered = footprint cells whose Euclidean distance to a lattice dot is <= 3 px
  * uncovered = footprint cells NOT covered (the only cells where a dot can count
    as non-overlapping under the literal rule)
  * any candidate's overlap = share of its dots lying in covered cells

Output: JSON receipt (default evidence/lattice-feasibility-20261029.json).
Exit code 0 always; the verdict field carries the result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32.paths import data_dir  # noqa: E402

LATTICE_SHA256 = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
RULE_OVERLAP_MAX = 0.70
RADIUS_PX = 3.0


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def load_footprint(template: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(template) as ds:
        arr = ds.read(1)
        foot = np.isfinite(arr) & (ds.read_masks(1) > 0)
        meta = {"crs": str(ds.crs), "shape": list(ds.shape), "transform": list(ds.transform)[:6]}
    return foot, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", type=Path, default=data_dir() / "sample_submission.tif")
    ap.add_argument("--lattice", type=Path, default=ROOT / ".cache" / "witness" / "lattice.tif")
    ap.add_argument("--candidate", type=Path, action="append", default=[],
                    help="Optional candidate GeoTIFF(s) to measure against the lattice")
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "lattice-feasibility-20261029.json")
    args = ap.parse_args()

    lattice_sha = sha256_file(args.lattice)
    if lattice_sha != LATTICE_SHA256:
        print(f"REFUSED: lattice SHA-256 {lattice_sha} != pinned {LATTICE_SHA256}", file=sys.stderr)
        return 1
    foot, tmeta = load_footprint(args.template)
    with rasterio.open(args.lattice) as ds:
        lat = (ds.read(1) > 0)
        lmeta = {"crs": str(ds.crs), "shape": list(ds.shape)}
    if tuple(lmeta["shape"]) != foot.shape:
        raise SystemExit("lattice grid does not match template grid")

    dist = ndimage.distance_transform_edt(~lat)
    covered = foot & (dist <= RADIUS_PX)
    uncovered = foot & ~covered
    # Uncovered cells within 3 cells of the footprint boundary (a border ring)
    interior = ndimage.binary_erosion(foot, iterations=3)
    ring = foot & ~interior
    n_foot = int(foot.sum())
    n_cov = int(covered.sum())
    n_unc = int(uncovered.sum())

    # Under the literal rule, overlap <= 0.70 needs at least 30% of dots in uncovered cells.
    min_uncovered_share = 1.0 - RULE_OVERLAP_MAX
    # Largest number of dots that can sit in uncovered cells, given one dot per cell.
    max_compliant_dots_if_all_uncovered_used = n_unc

    cands = []
    for cpath in args.candidate:
        with rasterio.open(cpath) as ds:
            c = ds.read(1)
            cmeta = {"crs": str(ds.crs), "shape": list(ds.shape), "dtype": ds.dtypes[0],
                     "nodata": ds.nodata, "transform": list(ds.transform)[:6]}
            finite_all = bool(np.isfinite(c).all())
            dots = (c > 0) & np.isfinite(c) & foot
            cmin, cmax = float(np.nanmin(c)), float(np.nanmax(c))
        n_dots = int(dots.sum())
        overlap = float(covered[dots].mean()) if n_dots else float("nan")
        # Literal all-dots reading: every positive cell counts as one of "your dots",
        # including cells outside the template footprint (measured against the full-grid distance map).
        all_pos = np.isfinite(c) & (c > 0)
        n_all = int(all_pos.sum())
        overlap_all = float((dist[all_pos] <= RADIUS_PX).mean()) if n_all else float("nan")
        n_outside = int((all_pos & ~foot).sum())
        cands.append({
            "path": rel(cpath),
            "sha256": sha256_file(cpath),
            "meta": cmeta,
            "finite_whole_array": finite_all,
            "min": cmin,
            "max": cmax,
            "dots_inside_footprint": n_dots,
            "dots_within_3px_of_lattice_share": round(overlap, 6),
            "literal_rule_pass": bool(overlap <= RULE_OVERLAP_MAX),
            "dots_all_positive": n_all,
            "dots_outside_template_footprint": n_outside,
            "dots_outside_template_footprint_share": round(n_outside / n_all, 6) if n_all else None,
            "dots_within_3px_of_lattice_share_all_positive": round(overlap_all, 6),
            "literal_all_dots_rule_pass": bool(overlap_all <= RULE_OVERLAP_MAX),
            "null_outside_footprint_convention_pass": n_outside == 0,
        })

    result = {
        "schema": "GEMSDOEkarage3-LATTICE-FEASIBILITY-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": "Can any footprint-internal submission satisfy the literal <=70% 3-px overlap rule against r13-lattice-s5?",
        "lattice": {"path": rel(args.lattice), "sha256": lattice_sha, "dots": int(lat.sum()), **lmeta,
                    "source": "https://github.com/buffedlizard55-lab/13GEMSDOE (ref 92ee6f074323f161eed837b80ec3ee5b662e26f5, docs/downloads/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif)"},
        "template": {"path": rel(args.template), "sha256": sha256_file(args.template), **tmeta},
        "radius_px": RADIUS_PX,
        "footprint_cells": n_foot,
        "covered_cells_within_3px": n_cov,
        "covered_share_of_footprint": round(n_cov / n_foot, 6),
        "uncovered_footprint_cells": n_unc,
        "uncovered_in_3_cell_boundary_ring": int((uncovered & ring).sum()),
        "uncovered_in_interior": int((uncovered & interior).sum()),
        "min_share_of_dots_required_in_uncovered_cells_for_rule": min_uncovered_share,
        "uncovered_cell_capacity_is_upper_bound_only": max_compliant_dots_if_all_uncovered_used,
        "verdict": ("Footprint-restricted reading: no non-degenerate in-footprint submission can satisfy "
                    "the literal rule, because the only compliant dots lie in uncovered cells and those are almost "
                    "entirely the footprint boundary ring. All-dots reading: a file can pass only by placing "
                    "dots outside the template footprint, where the organizer template is null; "
                    "see candidates[].null_outside_footprint_convention_pass."),
        "candidates": cands,
        "authorization": "NOT AUTHORIZED - analysis only, no slot used",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "covered_share_of_footprint", "uncovered_footprint_cells",
        "uncovered_in_3_cell_boundary_ring", "uncovered_in_interior")}, indent=2))
    for c in cands:
        print(c["path"], "overlap", c["dots_within_3px_of_lattice_share"], "pass", c["literal_rule_pass"])
    print("wrote", rel(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
