"""Validate the boundary between an audited TIFF cohort and unassessed files.

This module validates hashes and inventory classification only. It does not
measure raster uniqueness, run holdouts, validate GeoTIFF format, or authorize
submission.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def inventory(root: Path) -> dict:
    root = Path(root)
    audit_path = root / 'evidence/saved-tiffs-literal-20261028.json'
    unassessed_path = root / 'evidence/unassessed-tiffs-inventory-20261029.json'
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    unassessed = json.loads(unassessed_path.read_text(encoding='utf-8'))
    audited_rows = audit.get('rasters')
    extra_rows = unassessed.get('files')
    if not isinstance(audited_rows, list) or not isinstance(extra_rows, list):
        raise ValueError('TIFF inventory records must contain lists')

    audited = [row.get('file') for row in audited_rows]
    extras = [row.get('path') for row in extra_rows]
    if (not audited or len(audited) != len(set(audited)) or not extras
            or len(extras) != len(set(extras)) or set(audited) & set(extras)):
        raise ValueError('TIFF inventory has empty, repeated, or overlapping paths')

    current = {str(path.relative_to(root)) for path in (root / 'docs').rglob('*.tif')}
    if set(audited) | set(extras) != current:
        raise ValueError('Current TIFFs do not match the audited cohort plus explicit unassessed inventory')

    for row in audited_rows:
        path = (root / row['file']).resolve()
        if (not path.is_relative_to(root / 'docs') or not path.is_file()
                or sha256(path) != row.get('sha256') or row.get('duplicate_stop') is not True
                or row.get('ok_to_submit') is not False):
            raise ValueError(f"Invalid or changed audited TIFF record: {row.get('file')}")
    for row in extra_rows:
        path = (root / row['path']).resolve()
        if (not path.is_relative_to(root / 'docs') or not path.is_file()
                or sha256(path) != row.get('sha256') or row.get('status') != 'UNASSESSED'
                or row.get('do_not_submit') is not True):
            raise ValueError(f"Invalid or changed unassessed TIFF record: {row.get('path')}")

    return {'audit': audit, 'audited_paths': sorted(audited),
            'unassessed': unassessed, 'unassessed_paths': sorted(extras)}
