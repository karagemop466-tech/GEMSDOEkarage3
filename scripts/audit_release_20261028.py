"""Recheck saved artifacts against one literal registry witness; never train or upload.

A failing witness is sufficient to reject, never sufficient to approve. Official
organizer provenance, full-registry surface checks and holdout reruns remain separate.
"""
from pathlib import Path
import json
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scripts.audit_historical import fetch, sha256_file
from scripts.audit_registry import boundary_ring_share
from scripts.validate_raster import audit

ROOT = Path(__file__).resolve().parents[1]


def run():
    manifest = json.loads((ROOT / 'data/focus_registry.json').read_text())
    cache = ROOT / '.cache/release-audit'
    template = fetch(manifest['inputs']['template'], cache)
    lattice = fetch(manifest['inputs']['lattice'], cache)
    with rasterio.open(template) as ds:
        footprint = (ds.read_masks(1) != 0) & np.isfinite(ds.read(1))
        grid = (ds.shape, ds.crs, ds.transform)
    with rasterio.open(lattice) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid:
            raise ValueError('Witness grid mismatch')
        a = ds.read(1)
        support = np.isfinite(a) & (a > 0) & footprint
    distance = distance_transform_edt(~support)
    rows = []
    for path in sorted((ROOT / 'docs/downloads').glob('*.tif')):
        result = audit(path, template)
        with rasterio.open(path) as ds:
            if (ds.shape, ds.crs, ds.transform) != grid or ds.count != 1:
                overlap, n = None, 0
            else:
                a = ds.read(1)
                dots = np.isfinite(a) & (a > 0) & footprint
                n = int(dots.sum())
                overlap = float((distance[dots] <= 3).mean()) if n else None
        rows.append(dict(file=str(path.relative_to(ROOT)), sha256=sha256_file(path),
                         dots=n, within_3px_fraction=overlap,
                         duplicate_stop=overlap is not None and overlap > .70,
                         boundary_ring_share=boundary_ring_share(dots, footprint) if n else None,
                         boundary_gaming_refusal=bool(overlap is not None and overlap <= .70 and n
                                                      and (boundary_ring_share(dots, footprint) or 0) >= .5),
                         validator=result, ok_to_submit=False))
    return dict(schema_version=1, evidence_class='GEOMETRY / SAVED-BYTE AUDIT — NOT A SCORE',
                date_utc='2026-10-28', witness=manifest['inputs']['lattice'],
                template=manifest['inputs']['template'],
                footprint_pixels=int(footprint.sum()),
                witness_uncovered_pixels=int((footprint & (distance > 3)).sum()),
                scope='One pinned registered lattice; not a complete registry or a surface audit.',
                rows=rows, verdict='negative', ok_to_submit=False,
                experiments_run=0, weekly_slots_used=0,
                reason='Existing artifacts fail literal any-registry overlap gate; no new method lane supplied.')


if __name__ == '__main__':
    result = run()
    target = ROOT / 'evidence/release-audit-20261028.json'
    target.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({r['file']: r['within_3px_fraction'] for r in result['rows']}, indent=2))
