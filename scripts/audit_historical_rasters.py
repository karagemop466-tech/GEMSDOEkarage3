"""Historical learning only: restore pinned mirrors, inspect saved bytes with canonical validator.

No model training, candidate generation, holdout scoring, or upload occurs here.
Uses the upstream validator unchanged; never treats format checks as release approval.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'evidence/template-inspection'


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical_validator():
    """Verify all source pins before importing unmodified upstream code."""
    for row in json.loads((SNAPSHOT / 'manifest.json').read_text()):
        if sha256(SNAPSHOT / row['path']) != row['sha256']:
            raise ValueError(f"Modified upstream snapshot: {row['path']}")
    sys.path.insert(0, str(SNAPSHOT / 'src'))
    return importlib.import_module('gems32.submission').audit_geotiff


def restore(row, data_dir):
    """Fetch to a temporary file and publish only after size AND digest verification."""
    if not re.fullmatch(r'[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+', row['repo']):
        raise ValueError('Invalid repository')
    if not re.fullmatch(r'[a-f0-9]{40}', row['ref']):
        raise ValueError('Only immutable commit pins are accepted')
    for key in ('path', 'dest'):
        p = Path(row[key])
        if p.is_absolute() or '..' in p.parts or '?' in str(p) or '#' in str(p):
            raise ValueError('Unsafe manifest path')
    dest = (data_dir / row['dest']).resolve()
    if not dest.is_relative_to(data_dir.resolve()):
        raise ValueError('Destination escapes data directory')
    if dest.exists() and dest.stat().st_size == row['bytes'] and sha256(dest) == row['sha256']:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent, suffix='.partial', delete=False) as stream:
            tmp = Path(stream.name)
            subprocess.run(['gh', 'api', f"repos/{row['repo']}/contents/{row['path']}?ref={row['ref']}",
                            '-H', 'Accept: application/vnd.github.raw'],
                           stdout=stream, stderr=subprocess.PIPE, check=True, timeout=120)
        if tmp.stat().st_size != row['bytes'] or sha256(tmp) != row['sha256']:
            raise ValueError(f"Size/digest mismatch: {row['id']}")
        tmp.replace(dest)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    return dest


def binary_rank_correlation(a, b):
    """Exact tied-rank Spearman for binary vectors (Pearson/phi of indicators)."""
    import numpy as np
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    if a.shape != b.shape or a.size == 0:
        raise ValueError('Binary vectors must have identical nonempty shape')
    n, na, nb = a.size, int(a.sum()), int(b.sum())
    den = (na * (n - na) * nb * (n - nb)) ** .5
    return None if den == 0 else float((n * int((a & b).sum()) - na * nb) / den)


def audit(data_dir):
    import numpy as np
    import rasterio
    from scipy.ndimage import distance_transform_edt

    validator = canonical_validator()
    manifest = ROOT / 'registry/historical-audit-inputs.json'
    rows = json.loads(manifest.read_text())['files']
    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = dict(zip((r['id'] for r in rows), pool.map(lambda r: restore(r, data_dir), rows)))
    sample = paths['sample_submission']
    with rasterio.open(sample) as ds:
        foot = np.isfinite(ds.read(1))
        geometry = (ds.crs, ds.shape, ds.transform)
    with rasterio.open(paths['labels']) as ds:
        if (ds.crs, ds.shape, ds.transform) != geometry:
            raise ValueError('Label/template grid mismatch')
        labels = (ds.read(1) > 0) & foot
    masks, results = {}, []
    for row in rows:
        name = row['id']
        if not name.startswith('GEMSDOE'):
            continue
        with rasterio.open(paths[name]) as ds:
            if (ds.crs, ds.shape, ds.transform) != geometry or ds.count != 1:
                raise ValueError(f'Historical grid/band mismatch: {name}')
            arr = ds.read(1)
        mask = np.isfinite(arr) & (arr > 0) & foot
        masks[name] = mask
        try:
            receipt = validator(paths[name], foot, labels, mode='zeros', template_tif=sample)
            # Local paths are implementation details, not public download URLs.
            receipt['geometry_reference'] = 'sample_submission mirror, SHA256 ' + sha256(sample)
        except ValueError as exc:
            receipt = {'all_checks_passed': False, 'error': str(exc)}
        results.append(dict(site=name, source_url=f"https://github.com/{row['repo']}/blob/{row['ref']}/{row['path']}",
                            file=Path(row['path']).name, sha256=sha256(paths[name]),
                            positive_pixels=int(mask.sum()), validator=receipt,
                            unique=None, ok_to_submit=False))
    pairs = []
    for reference, ref_mask in masks.items():
        # Directional overlap: fraction of candidate dots near THIS reference.
        near = distance_transform_edt(~ref_mask) <= 3
        for candidate, cand_mask in masks.items():
            if candidate == reference:
                continue
            overlap = float((cand_mask & near).sum() / cand_mask.sum()) if cand_mask.any() else None
            correlation = binary_rank_correlation(cand_mask[foot], ref_mask[foot])
            pairs.append(dict(candidate=candidate, reference=reference,
                              exact_same_positive_pixels=bool(np.array_equal(cand_mask, ref_mask)),
                              spearman=correlation, fraction_candidate_dots_within_3px=overlap,
                              duplicate_stop=(overlap is not None and overlap > .70) or
                                             (correlation is not None and abs(correlation) > .90)))
    base, champion = masks['GEMSDOE28-base'], masks['GEMSDOE32']
    distance = distance_transform_edt(~labels)
    pruned = base & (distance > 2)
    for result in results:
        name = result['site']
        related = [p for p in pairs if p['candidate'] == name]
        worst = max(related, key=lambda p: p['fraction_candidate_dots_within_3px'] or 0)
        result['partial_registry'] = dict(
            max_overlap_3px=worst['fraction_candidate_dots_within_3px'],
            reference=worst['reference'],
            exact_positive_pixel_duplicates=[p['reference'] for p in related if p['exact_same_positive_pixels']],
            duplicate_stop=any(p['duplicate_stop'] for p in related),
            complete=False)
        # A single threshold violation suffices to reject; absence of a violation
        # in this subset could NEVER certify uniqueness against the full registry.
        if result['partial_registry']['duplicate_stop']:
            result['unique'] = False
        result['champion_relationship'] = dict(
            shared_positive_pixels=int((masks[name] & champion).sum()),
            extra_vs_champion=int((masks[name] & ~champion).sum()),
            missing_vs_champion=int((champion & ~masks[name]).sum()))
    autopsy = dict(base_positive_pixels=int(base.sum()), champion_positive_pixels=int(champion.sum()),
                   removed_pixels=int((base & ~champion).sum()), added_pixels=int((champion & ~base).sum()),
                   exact_base_pruned_within_2px=bool(np.array_equal(pruned, champion)),
                   minimum_champion_catalogue_distance_px=float(distance[champion].min()))
    return dict(schema_version=1, checked_utc=datetime.now(timezone.utc).isoformat(),
                evidence_class='RASTER-AUDIT — historical byte/pixel measurements, NOT HOLDOUT-DTI or organizer scores',
                manifest_sha256=sha256(manifest), source_authentication='owner mirrors only',
                complete_registry=False, continuous_surfaces_checked=False,
                scope='Nine cited best-reported artifacts plus GEMSDOE28 solo base; not a complete novelty registry',
                experiments_run=0, submission_slots_used=0, new_candidate_generated=False,
                rasters=results, pairwise_final_dots=pairs, champion_autopsy=autopsy,
                ok_to_submit=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data')
    parser.add_argument('--out', type=Path, default=ROOT / 'docs/historical-audit.json')
    args = parser.parse_args()
    try:
        result = audit(args.data_dir)
    except Exception as exc:
        # Fail nonzero, never overwrite an existing successful receipt on failure.
        print(f'Historical audit FAILED: {exc}', file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result['champion_autopsy'], indent=2))
    print(f'Historical audit saved: {args.out}. NOT a candidate or upload authorization.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
