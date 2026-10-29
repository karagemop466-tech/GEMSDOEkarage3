#!/usr/bin/env python3
"""Literal duplicate measurement of candidate TIFFs against the restored registry.

Rule under test (as written in the project protocol, no exemptions):
  * candidate dots = finite pixels > 0 inside the template footprint;
  * fraction = share of candidate dots lying within 3 px (Euclidean, inclusive)
    of at least one dot of a registry raster on the SAME grid;
  * binary Spearman rho between candidate and registry dot masks over the footprint;
  * duplicate stop if fraction > 0.70 or |rho| > 0.90 (or rho undefined).

Candidates are (a) every checked-in TIFF under docs/ and (b) the nine focus-site
files at their pinned refs. Identical bytes at another path or repository are
NOT exempt: they give fraction 1.0 and are reported as identical-byte copies.
The only exclusion is the candidate's own sole registry entry (same repo+path).

Scope: the FILTERED inventory in registry/complete_registry_manifest.json, restored
by scripts/fetch_unique_registry.py. This is a negative-only screen. It does not
establish completeness, a surface-before-placement check, or organizer acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.audit_registry import ensure_file, sha256  # noqa: E402

REGISTRY_MANIFEST = ROOT / "registry" / "complete_registry_manifest.json"
HISTORICAL = ROOT / "registry" / "historical.json"
FOCUS_REGISTRY = ROOT / "data" / "focus_registry.json"
REGISTRY_CACHE = ROOT / ".cache" / "registry"
HIST_CACHE = ROOT / ".cache" / "historical"
OUT = ROOT / "evidence" / "literal-uniqueness-measure-20261029.json"
RADIUS = 3.0


def load_template_geometry(fetch: bool):
    manifest = json.loads(HISTORICAL.read_text())
    paths = {n: HIST_CACHE / f"{n}.tif" for n in ("template", "lattice")}
    for name, path in paths.items():
        ensure_file(manifest[name], path, fetch)
    with rasterio.open(paths["template"]) as ds:
        arr = ds.read(1)
        foot = np.isfinite(arr) & (ds.read_masks(1) != 0)
        geometry = (ds.shape, ds.crs, ds.transform)
    return geometry, foot, paths


def read_dots(path: Path, geometry, foot):
    try:
        with rasterio.open(path) as ds:
            if ds.count != 1:
                return None, "not single-band"
            if (ds.shape, ds.crs, ds.transform) != geometry:
                return None, "different grid (shape/CRS/transform)"
            arr = ds.read(1)
    except rasterio.errors.RasterioError as e:
        # Hash-verified bytes that GDAL cannot parse: reported as a coverage gap, never silently passed.
        return None, f"unreadable: {str(e)[:200]}"
    dots = np.isfinite(arr) & (arr > 0) & foot
    if not dots.any():
        return None, "empty positive support"
    return dots, None


def phi(n: int, x: int, y: int, both: int):
    """Binary Spearman (Pearson on indicators) from counts over an n-pixel footprint."""
    den = x * (n - x) * y * (n - y)
    if den <= 0:
        return None
    return (n * both - x * y) / math.sqrt(den)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help="restore pinned template/lattice if absent")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--limit", type=int, default=None, help="testing only: first N registry hashes")
    args = ap.parse_args()

    geometry, foot, paths = load_template_geometry(args.fetch)
    n_foot = int(foot.sum())
    lattice_sha = sha256(paths["lattice"])

    reg_manifest = json.loads(REGISTRY_MANIFEST.read_text())
    keys_by_sha: dict[str, set[str]] = defaultdict(set)
    local_by_sha: dict[str, Path] = {}
    for row in reg_manifest["rasters"]:
        key = f"{row['repo']}/{row['path']}"
        keys_by_sha[row["sha256"]].add(key)
        local = REGISTRY_CACHE / row["repo"] / row["path"]
        if row["sha256"] not in local_by_sha and local.is_file():
            local_by_sha[row["sha256"]] = local
    registry_shas = list(keys_by_sha)
    if args.limit:
        registry_shas = registry_shas[: args.limit]

    focus_sites = json.loads(FOCUS_REGISTRY.read_text())["sites"]
    focus_sha_to_site = {s["sha256"]: s["site"] for s in focus_sites}

    # ---- candidates ----
    cands: dict[str, dict] = {}
    cand_specs = [(str(p.relative_to(ROOT)), p, None) for p in sorted((ROOT / "docs").rglob("*.tif"))]
    for s in focus_sites:
        key = f"{s['repo']}/{s['path']}"
        local = local_by_sha.get(s["sha256"])
        cand_specs.append((f"FOCUS:{s['site']}:{s['path']}", local, key))
    for label, path, key in cand_specs:
        if path is None or not Path(path).is_file():
            cands[label] = {"file": label, "error": "missing on disk", "key": key}
            continue
        dots, err = read_dots(Path(path), geometry, foot)
        sha = sha256(Path(path))
        if dots is None:
            cands[label] = {"file": label, "sha256": sha, "error": err, "key": key}
            continue
        rows, cols = np.nonzero(dots)
        cands[label] = {"file": label, "sha256": sha, "key": key, "n_dots": int(dots.sum()),
                        "dot_set_sha256": hashlib.sha256(np.packbits(dots).tobytes()).hexdigest(),
                        "rows": rows, "cols": cols, "dots": dots,
                        "rc": np.column_stack((rows, cols)).astype(np.float64),
                        "fraction_max": 0.0, "fraction_argmax": None, "rho_max": 0.0, "rho_argmax": None,
                        "duplicate_hits": [], "self_match": None, "compared": 0, "vs_focus": {}}
    # Identical-byte copies of each candidate elsewhere in the inventory (reported, never exempt).
    for c in cands.values():
        if "sha256" in c:
            others = sorted(keys_by_sha.get(c["sha256"], set()) - ({c["key"]} if c["key"] else set()))
            c["identical_bytes_elsewhere"] = others

    valid = {k: c for k, c in cands.items() if "dots" in c}

    # ---- registry sweep ----
    skipped = defaultdict(list)
    compared_shas = 0
    for i, sha in enumerate(registry_shas, 1):
        path = local_by_sha.get(sha)
        if path is None:
            skipped["missing_on_disk"].append(sha)
            continue
        reg_dots, err = read_dots(path, geometry, foot)
        if reg_dots is None:
            kind = ("different_grid" if err and "grid" in err else
                    "unreadable" if err and err.startswith("unreadable") else "no_dots_or_unreadable")
            skipped[kind].append(
                f"{path.relative_to(REGISTRY_CACHE)}: {err}")
            continue
        compared_shas += 1
        reg_count = int(reg_dots.sum())
        reg_keys = keys_by_sha[sha]
        reg_label = " | ".join(sorted(reg_keys))[:300]
        # Exact Euclidean nearest-neighbour test (KD-tree on this registry raster's dots):
        # a candidate dot is 'within 3 px' iff some registry dot lies at distance <= 3 (inclusive).
        reg_rc = np.column_stack(np.nonzero(reg_dots)).astype(np.float64)
        tree = cKDTree(reg_rc) if len(reg_rc) else None
        for label, c in valid.items():
            if c["sha256"] == sha and c["key"] and reg_keys == {c["key"]}:
                c["self_match"] = reg_label  # the candidate's own sole registry entry
                continue
            c["compared"] += 1
            if tree is None:
                frac = 0.0
            else:
                # SciPy's distance_upper_bound is EXCLUSIVE; widen by a tiny epsilon so that a dot
                # exactly RADIUS px away counts (inclusive, as in audit_registry.dilate_disk).
                dist, _ = tree.query(c["rc"], k=1, distance_upper_bound=RADIUS + 1e-9)
                frac = float(np.mean(dist <= RADIUS))
            both = int(reg_dots[c["rows"], c["cols"]].sum())
            rho = phi(n_foot, c["n_dots"], reg_count, both)
            if frac > c["fraction_max"]:
                c["fraction_max"], c["fraction_argmax"] = frac, reg_label
            if rho is not None and abs(rho) > c["rho_max"]:
                c["rho_max"], c["rho_argmax"] = abs(rho), reg_label
            if label in valid and sha in focus_sha_to_site:
                c["vs_focus"][focus_sha_to_site[sha]] = max(c["vs_focus"].get(focus_sha_to_site[sha], 0.0), frac)
            if frac > 0.70 or rho is None or abs(rho) > 0.90:
                c["duplicate_hits"].append({"registry_raster": reg_label, "fraction_within_3px": round(frac, 6),
                                            "spearman": None if rho is None else round(rho, 6),
                                            "identical_bytes": bool(c["sha256"] == sha)})
        if i % 250 == 0:
            print(f"progress {i}/{len(registry_shas)}", flush=True)

    # ---- serialise ----
    out_rows = []
    for label in sorted(cands):
        c = cands[label]
        row = {"file": label, "sha256": c.get("sha256"), "dot_set_sha256": c.get("dot_set_sha256"),
               "n_dots": c.get("n_dots"), "identical_bytes_elsewhere": c.get("identical_bytes_elsewhere", []),
               "self_registry_entry": c.get("self_match")}
        if "dots" not in c:
            row["literal_screen_result"] = "NOT-MEASURED: " + str(c.get("error"))
            row["duplicate_stop"] = None
        else:
            row.update({
                "compared_registry_rasters": c["compared"],
                "max_fraction_within_3px": round(c["fraction_max"], 6),
                "argmax_fraction_registry": c["fraction_argmax"],
                "max_abs_spearman": round(c["rho_max"], 6),
                "argmax_spearman_registry": c["rho_argmax"],
                "duplicate_hits_count": len(c["duplicate_hits"]),
                "duplicate_hits_first_20": c["duplicate_hits"][:20],
                "max_fraction_vs_each_focus_site": {k: round(v, 6) for k, v in sorted(c["vs_focus"].items())},
                "duplicate_stop": bool(c["duplicate_hits"]),
            })
            row["literal_screen_result"] = ("DUPLICATE-STOP" if row["duplicate_stop"]
                                            else "PASS-vs-restored-filtered-inventory (screen only)")
        out_rows.append(row)

    receipt = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "rule": {"fraction_within_3px_stop_gt": 0.70, "abs_spearman_stop_gt": 0.90,
                 "distance": "Euclidean, inclusive 3 px", "support": "candidate dots inside template footprint"},
        "template_footprint_pixels": n_foot,
        "lattice_witness_sha256": lattice_sha,
        "registry_source": "registry/complete_registry_manifest.json (FILTERED inventory; not proof of completeness)",
        "registry_unique_sha256": len(registry_shas),
        "registry_unique_sha256_compared": compared_shas,
        "skipped_counts": {k: len(v) for k, v in skipped.items()},
        "skipped_examples": {k: v[:20] for k, v in skipped.items()},
        "surface_before_placement_check": "NOT RUN - candidates are already binary dots; no continuous surface retained",
        "complete_registry_checked": False,
        "candidates": out_rows,
        "verdict": "negative-only screen; a DUPLICATE-STOP is decisive, a PASS is not a uniqueness or organizer certificate",
        "ok_to_submit": False,
        "experiments_run": 0,
        "weekly_slots_used": 0,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    for r in out_rows:
        print(f"{r['file']}: n={r.get('n_dots')} compared={r.get('compared_registry_rasters')} "
              f"max3px={r.get('max_fraction_within_3px')} maxRho={r.get('max_abs_spearman')} "
              f"identical_elsewhere={len(r['identical_bytes_elsewhere'])} -> {r['literal_screen_result']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
