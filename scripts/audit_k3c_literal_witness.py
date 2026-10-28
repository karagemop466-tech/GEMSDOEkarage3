#!/usr/bin/env python3
"""Recheck the historical K3C TIFF against one pinned registry witness.

A witness failure is sufficient to stop; a pass cannot prove uniqueness. The
sample is an owner mirror, not authenticated organizer data. No model is run.
"""
from pathlib import Path
import json
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scripts.audit_historical import fetch, sha256_file
from scripts.validate_raster import audit

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'docs/k3c/downloads/gemsdoekarage3-h-k3c-csst-bghf-24cell-d31-b37654-20261028T175133Z-3586582f-zeros.tif'


def run():
    manifest = json.loads((ROOT / 'data/focus_registry.json').read_text())
    cache = ROOT / '.cache/literal-k3c'
    template = fetch(manifest['inputs']['template'], cache)
    witness = fetch(manifest['inputs']['lattice'], cache)
    with rasterio.open(template) as ds:
        footprint = (ds.read_masks(1) != 0) & np.isfinite(ds.read(1))
        grid = ds.shape, ds.crs, ds.transform
    with rasterio.open(witness) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid or ds.count != 1:
            raise ValueError('Witness grid mismatch')
        a = ds.read(1)
        support = np.isfinite(a) & (a > 0) & footprint
    if not support.any():
        raise ValueError('Empty witness support')
    with rasterio.open(CANDIDATE) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid or ds.count != 1:
            raise ValueError('Candidate grid mismatch')
        a = ds.read(1)
        dots = np.isfinite(a) & (a > 0) & footprint
    n = int(dots.sum())
    if not n:
        raise ValueError('Empty candidate support')
    fraction = float((distance_transform_edt(~support)[dots] <= 3).mean())
    return {
        'scope': 'One pinned owner-mirror template and one registered lattice. Not an organizer-authenticated template, complete registry, surface audit, or new experiment.',
        'template': manifest['inputs']['template'], 'witness': manifest['inputs']['lattice'],
        'candidate': str(CANDIDATE.relative_to(ROOT)), 'candidate_sha256': sha256_file(CANDIDATE),
        'dots_inside_footprint': n, 'within_3px_fraction': fraction,
        'duplicate_stop': fraction > .70, 'validator': audit(CANDIDATE, template),
        # A single witness cannot establish authorization, even if it passes.
        'verdict': 'negative', 'ok_to_submit': False,
    }


if __name__ == '__main__':
    result = run()
    path = ROOT / 'evidence/k3c-literal-witness-audit-20261028.json'
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'within_3px_fraction': result['within_3px_fraction'],
                      'duplicate_stop': result['duplicate_stop'], 'ok_to_submit': False}, indent=2))
