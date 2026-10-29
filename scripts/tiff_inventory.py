"""Fail-closed inventory of the TIFFs covered by the pinned negative audit.

Every TIFF under docs must appear exactly once in the saved-byte audit with a
matching hash and a literal duplicate stop. This does not prove a complete
registry comparison, geological quality, organizer acceptance, or submission
readiness; it only prevents added/unclassified files from escaping review.
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
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    rows = audit.get('rasters')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Saved-byte audit must contain raster rows')

    audited = [row.get('file') for row in rows]
    current = {str(path.relative_to(root)) for path in (root / 'docs').rglob('*.tif')}
    if len(audited) != len(set(audited)) or set(audited) != current:
        raise ValueError('Current TIFFs do not match the complete saved-byte audit')

    for row in rows:
        path = (root / row['file']).resolve()
        if (not path.is_relative_to(root / 'docs') or not path.is_file()
                or sha256(path) != row.get('sha256') or row.get('duplicate_stop') is not True
                or row.get('ok_to_submit') is not False
                or row.get('within_3px_fraction') is None
                or row['within_3px_fraction'] <= .70):
            raise ValueError(f"Invalid or changed saved-byte audit record: {row.get('file')}")

    return {'audit': audit, 'audited_paths': sorted(audited),
            'unassessed_paths': []}
