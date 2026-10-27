#!/usr/bin/env python3
"""Reopen nine pinned historical files for format diagnostics, never upload approval.

Run the priority-raster audit first to restore the inputs. This script does not contact
DrivenData, create a prediction, authenticate the owner mirror, or select a slot.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

if __package__:
    from .validate_geotiff import validate
else:
    from validate_geotiff import validate

ROOT = Path(__file__).resolve().parents[1]


def audit(cache: Path) -> dict:
    report = json.loads((ROOT / 'docs/priority-audit.json').read_text())
    inputs = json.loads((ROOT / 'evidence/priority_inputs.json').read_text())
    expected = {x['id']: x['sha256'] for x in inputs['files']}
    expected_template = expected['footprint']
    results = []
    for item in report['historical_rasters']:
        site = item['site']
        ident = site.removeprefix('GEMSDOE')
        if not ident.isdigit():
            raise ValueError('Invalid site identifier')
        result = validate(cache / f'{ident}.tif', cache / 'footprint.tif')
        if (result['raster_sha256'] != item['file_sha256']
                or result['raster_sha256'] != expected.get(ident)
                or result['template_sha256'] != expected_template
                or not result['core_checks_passed'] or not result['inside_binary']):
            raise ValueError(f'{site}: pinned digest or saved-byte checks failed')
        fields = ('raster_sha256', 'template_sha256', 'inside_footprint_pixels', 'inside_nonfinite',
                  'inside_masked', 'inside_out_of_range', 'inside_min', 'inside_max', 'inside_binary',
                  'outside_footprint_all_null_or_nan', 'whole_grid_finite_and_in_range',
                  'whole_grid_unmasked', 'finite_out_of_range_anywhere', 'checks', 'core_checks_passed')
        results.append({key: result[key] for key in fields} | {'site': site, 'filename': item['filename']})
    if len(results) != 9 or len({row['site'] for row in results}) != 9:
        raise ValueError('Incomplete historical audit inventory')
    return {'kind': 'READ-ONLY-HISTORICAL-FORMAT-AUDIT; not organizer authentication, score or submission approval',
            'checked_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'template_provenance': 'hash-pinned owner-mirrored sample, not authenticated organizer template',
            'outside_encoding_accepted_by_portal': None, 'rasters': results,
            'new_candidate_created': False, 'ok_to_submit': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/historical')
    parser.add_argument('--output', type=Path, default=ROOT / 'evidence/historical-format-audit.json')
    args = parser.parse_args()
    try:
        receipt = audit(args.cache)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + '.partial')
        temporary.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
        temporary.replace(args.output)
        print(f"Verified {len(receipt['rasters'])} historical files; no candidate is approved. Receipt: {args.output}")
        return 0
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        print(f'Historical format audit failed; existing receipt unchanged: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
