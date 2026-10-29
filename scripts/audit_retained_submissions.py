#!/usr/bin/env python3
"""Audit retained TIFFs against a pinned mirror and a literal registry witness.

No training, placement, slot selection, or modification of raster bytes occurs.
A single duplicate witness is sufficient to reject; it never proves uniqueness.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import rasterio
from scripts.audit_registry import ROOT, MANIFEST, boundary_ring_share, ensure_file, dilate_disk, sha256
from scripts.validate_raster import audit as format_audit


def audit(cache: Path, fetch: bool = False) -> dict:
    manifest = json.loads(MANIFEST.read_text())
    for key, filename in (("template", "template.tif"), ("lattice", "lattice.tif")):
        ensure_file(manifest[key], cache / filename, fetch)
    template = cache / "template.tif"
    with rasterio.open(template) as ds:
        footprint = np.isfinite(ds.read(1)) & (ds.read_masks(1) != 0)
    with rasterio.open(cache / "lattice.tif") as ds:
        near = dilate_disk((ds.read(1) > 0) & footprint, 3)
    rows = []
    for path in sorted((ROOT / "docs/downloads").glob("*.tif")):
        fmt = format_audit(path, template)
        with rasterio.open(path) as ds:
            if ds.shape != footprint.shape or ds.count != 1:
                raise ValueError(f"Unsupported retained raster: {path}")
            values = ds.read(1)
        dots = np.isfinite(values) & (values > 0) & footprint
        n = int(dots.sum())
        overlap = float(near[dots].mean()) if n else None
        rows.append(dict(file=str(path.relative_to(ROOT)), sha256=sha256(path),
                         dots=n, lattice_overlap_3px=overlap,
                         duplicate_stop=overlap is not None and overlap > .70,
                         boundary_ring_share=boundary_ring_share(dots, footprint),
                         boundary_gaming_refusal=bool(overlap is not None and overlap <= .70
                                                      and (boundary_ring_share(dots, footprint) or 0) >= .5),
                         format=fmt, verdict="negative", ok_to_submit=False,
                         surface_check="Not reproduced: cached pre-placement surface absent"))
    return dict(schema_version=1, evidence_class="GEOMETRY-AUDIT, NOT A SCORE",
                protocol="any registry raster; no lattice or density exemptions",
                template=manifest['template'], witness=manifest['lattice'],
                scope="One pinned witness; sufficient for duplicate stop, insufficient to promote",
                experiments_run=0, weekly_slots_used=0, rasters=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/historical')
    parser.add_argument('--out', type=Path, default=ROOT / 'evidence/retained-submissions-audit-20261028.json')
    args = parser.parse_args()
    result = audit(args.cache, args.fetch)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps([{k: r[k] for k in ('file', 'sha256', 'lattice_overlap_3px', 'duplicate_stop')} for r in result['rasters']], indent=2))


if __name__ == '__main__':
    main()
