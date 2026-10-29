#!/usr/bin/env python3
"""Audit checked-in TIFFs against a pinned grid and one literal duplicate witness.

This is a negative-only audit: one witness can reject a file; it cannot establish
full-registry uniqueness, scientific quality, organizer acceptance or selection.
Run with --fetch to restore only the small, hash-pinned owner mirrors.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.audit_registry import binary_spearman, checked_raster, dilate_disk, ensure_file, sha256
from scripts.check_format import inspect


def audit(cache: Path, fetch: bool = False) -> dict:
    manifest = json.loads((ROOT / 'registry/historical.json').read_text())
    paths = {name: cache / (name + '.tif') for name in ('template', 'lattice')}
    for name, path in paths.items():
        ensure_file(manifest[name], path, fetch)
    with rasterio.open(paths['template']) as template:
        arr = template.read(1)
        foot = np.isfinite(arr) & (template.read_masks(1) != 0)
        geometry = (template.shape, template.crs, template.transform)
    if not foot.any():
        raise ValueError('Template footprint is empty')
    witness, info = checked_raster(paths['lattice'], geometry, foot, binary=True)
    near = dilate_disk(witness, 3)
    rows = []
    # Audit every TIFF retained anywhere under the public docs tree, not just
    # a hand-picked subset; a future added TIFF cannot silently escape this scan.
    for path in sorted((ROOT / 'docs').rglob('*.tif')):
        fmt = inspect(path, paths['template'])
        with rasterio.open(path) as ds:
            if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != geometry:
                raise ValueError(f'{path}: raster geometry/band mismatch')
            a = ds.read(1, masked=False)
        inside = a[foot]
        is_binary = bool(np.all(np.isfinite(inside) & ((inside == 0) | (inside == 1))))
        dots = np.isfinite(a) & (a > 0) & foot
        n_dots = int(dots.sum())
        overlap = float((dots & near).sum() / n_dots) if n_dots else None
        rho = binary_spearman(dots, witness, foot) if is_binary else None
        # Literal all-dots reading ("your dots", every positive pixel, wherever it lies).
        # Reported alongside the footprint-restricted convention above, never instead of it.
        all_pos = np.isfinite(a) & (a > 0)
        n_all = int(all_pos.sum())
        overlap_all = float((all_pos & near).sum() / n_all) if n_all else None
        rows.append({
            'file': str(path.relative_to(ROOT)), 'sha256': sha256(path),
            'in_footprint_binary': is_binary, 'positive_pixels': n_dots,
            'within_3px_fraction': overlap, 'binary_spearman': rho,
            'duplicate_stop': bool(overlap is not None and overlap > .70),
            'positive_pixels_all': n_all,
            'positive_pixels_outside_template_footprint': int((all_pos & ~foot).sum()),
            'within_3px_fraction_all_positive_pixels': overlap_all,
            'literal_all_dots_lattice_rule_pass': bool(overlap_all is not None and overlap_all <= .70),
            'format_diagnostic': fmt,
            'ok_to_submit': False,
        })
    return {
        'schema_version': 1,
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'classification': 'GEOMETRY AND FORMAT DIAGNOSTIC, NOT A SCORE',
        'scope': 'All checked-in docs TIFFs versus one pinned witness; not a complete registry or a surface audit.',
        'input_provenance': 'Hash-pinned public owner mirrors, not authenticated organizer inputs.',
        'template': {'source_url': manifest['template']['source_url'], 'sha256': sha256(paths['template'])},
        'witness': {'source_url': manifest['lattice']['source_url'], 'sha256': sha256(paths['lattice']),
                    'positive_pixels': info['dots'],
                    'uncovered_footprint_pixels': int((foot & ~near).sum())},
        'footprint_pixels': int(foot.sum()),
        'rasters': rows,
        'complete_registry_checked': False, 'new_candidate_generated': False,
        'experiments_run': 0, 'weekly_slots_used': 0,
        'verdict': 'negative', 'ok_to_submit': False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cache', type=Path, default=ROOT / '.cache/historical')
    ap.add_argument('--fetch', action='store_true')
    ap.add_argument('--out', type=Path, default=ROOT / 'evidence/saved-tiffs-literal-20261028.json')
    ap.add_argument('--verify-receipt', type=Path,
                    help='Compare fresh values with a saved report, ignoring only the audit timestamp; do not write output')
    args = ap.parse_args()
    try:
        result = audit(args.cache, args.fetch)
        if args.verify_receipt:
            expected = json.loads(args.verify_receipt.read_text())
            if ({k: v for k, v in result.items() if k != 'checked_utc'} !=
                    {k: v for k, v in expected.items() if k != 'checked_utc'}):
                raise ValueError('Fresh saved-byte audit differs from the committed receipt')
            print('Fresh saved-byte audit matches the receipt (except audit time).')
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        for r in result['rasters']:
            print(f"{r['file']}: overlap={r['within_3px_fraction']}, duplicate_stop={r['duplicate_stop']}, strict_format={r['format_diagnostic']['strict_format_gate_pass']}")
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        print(f'Audit failed closed: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
