#!/usr/bin/env python3
"""Feasibility measurement (not a candidate): how much of the footprint is already
within 3 px of ANY binary registry submission, with and without the 13GEMSDOE
calibration lattice. Answers: is a literally-unique (<=70% within-3px) placement
possible at all, and what is the dot ceiling implied by the lattice?

Reads only the hash-bound restored registry; writes evidence/registry-union-coverage-20261029.json.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from karage3.registry_audit import _load_registry_array  # noqa: E402  (shared loader)

MANIFEST = ROOT / "registry" / "complete_registry_manifest.json"
TEMPLATE = ROOT / ".cache" / "gems_data" / "sample_submission.tif"
OUT = ROOT / "evidence" / "registry-union-coverage-20261029.json"
LATTICE_NAME = "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
DISK3 = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)


def main() -> int:
    man = json.loads(MANIFEST.read_text())
    with rasterio.open(TEMPLATE) as tpl:
        foot = np.isfinite(tpl.read(1)) & (tpl.read_masks(1) > 0)
        template = {"shape": tpl.shape, "crs": tpl.crs, "transform": tpl.transform}
    union_all = np.zeros(foot.shape, bool)
    union_nolat = np.zeros(foot.shape, bool)
    used = skipped = lattice_dots = 0
    skipped_rows = []
    seen: set[str] = set()
    for entry in man["rasters"]:
        arr, row = _load_registry_array(entry, ROOT, template)
        if arr is None:
            skipped += 1
            skipped_rows.append({"repo": entry["repo"], "path": entry["path"], "status": row.get("status")})
            continue
        vals = arr[foot]
        if not np.isfinite(vals).all():
            skipped += 1
            skipped_rows.append({"repo": entry["repo"], "path": entry["path"], "status": "nonfinite_inside_footprint"})
            continue
        dots = (arr > 0.0) & foot
        digest = str(hash(np.packbits(dots).tobytes()))
        if digest in seen or not dots.any():
            continue
        seen.add(digest)
        used += 1
        near = binary_dilation(dots, structure=DISK3)
        union_all |= near
        if Path(entry["path"]).name != LATTICE_NAME:
            union_nolat |= near
        else:
            lattice_dots = int(dots.sum())
    n = int(foot.sum())
    out = {
        "schema": "GEMSDOEkarage3-REGISTRY-UNION-COVERAGE-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": "Feasibility of the literal <=70% within-3px rule; not a candidate and not a score.",
        "manifest_sha256_note": "registry/complete_registry_manifest.json (filtered inventory, literal_registry_complete=false)",
        "footprint_cells": n,
        "unique_binary_registry_masks_used": used,
        "rasters_skipped_missing_malformed": skipped,
        "footprint_share_within_3px_of_any_registry_dot_incl_lattice": round(float(union_all[foot].mean()), 6),
        "footprint_share_within_3px_of_any_registry_dot_excl_lattice": round(float(union_nolat[foot].mean()), 6),
        "footprint_cells_uncovered_incl_lattice": int((foot & ~union_all).sum()),
        "footprint_cells_uncovered_excl_lattice": int((foot & ~union_nolat).sum()),
        "lattice_dots": lattice_dots,
        "skipped_rows": skipped_rows[:50],
        "reading": ("A candidate must put >=30% of its dots in cells NOT within 3 px of the lattice to pass the literal rule "
                    "against it alone; the lattice's uncovered cells bound the dot count (see scripts/protocol_preflight.py)."),
    }
    OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in out if k != "skipped_rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
