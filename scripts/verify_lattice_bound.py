#!/usr/bin/env python3
"""Reproduce the literal-overlap bound imposed by the registered lattice witness.

Fetches the hash-pinned 13GEMSDOE `r13-lattice-s5` raster (pinned commit and SHA-256 from
registry/historical.json), then computes, on the pinned footprint:

* how many in-footprint cells lie farther than 3 px from every lattice dot;
* the pigeonhole minimum overlap for any support of N cells;
* the largest support N that can still satisfy the literal <= 70 % rule.

It writes evidence/lattice-bound-20261030.json. It is a geometry diagnostic, not a score, and it
does not approve any file. Run: python -m scripts.verify_lattice_bound
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.audit_registry import ensure_file  # noqa: E402

OUT = ROOT / 'evidence/lattice-bound-20261030.json'
BUDGETS = [12000, 20000, 22164, 37654, 44090]


def run(cache: Path = ROOT / '.cache/historical', fetch: bool = True) -> dict:
    manifest = json.loads((ROOT / 'registry/historical.json').read_text())
    lat_src = manifest['lattice']
    lattice = cache / 'lattice.tif'  # same cache name as scripts/audit_saved_tiffs.py
    ensure_file(lat_src, lattice, fetch)
    tmpl_src = manifest['template']
    template = cache / 'template.tif'
    ensure_file(tmpl_src, template, fetch)

    with rasterio.open(template) as t:
        foot = np.isfinite(t.read(1)) & (t.read_masks(1) != 0)
        geom = (t.shape, str(t.crs), tuple(t.transform)[:6])
    with rasterio.open(lattice) as d:
        lat_geom = (d.shape, str(d.crs), tuple(d.transform)[:6])
        L = d.read(1)
    if lat_geom != geom:
        raise ValueError(f'lattice grid {lat_geom} != template grid {geom}')
    dots = np.isfinite(L) & (L > 0)
    dist = distance_transform_edt(~dots)
    uncovered = int((foot & (dist > 3)).sum())
    n_foot = int(foot.sum())
    max_support = int(uncovered / 0.30)  # largest N with (N - uncovered)/N <= 0.70
    result = dict(
        schema='lattice-bound-v1', generated_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
        evidence_class='GEOMETRY DIAGNOSTIC - NOT A SCORE, NOT A SUBMISSION APPROVAL',
        witness=dict(source_url=lat_src.get('source_url'),
                     sha256=hashlib.sha256(lattice.read_bytes()).hexdigest(),
                     pinned_sha256=lat_src.get('raster_sha256')),
        template=dict(source_url=tmpl_src.get('source_url'),
                      sha256=hashlib.sha256(template.read_bytes()).hexdigest(),
                      pinned_sha256=tmpl_src.get('raster_sha256')),
        grid=dict(shape=list(geom[0]), crs=geom[1]),
        footprint_cells=n_foot,
        lattice_dots=int(dots.sum()),
        lattice_dots_outside_footprint=int((dots & ~foot).sum()),
        footprint_coverage_within_3px=round(1 - uncovered / n_foot, 6),
        uncovered_footprint_cells=uncovered,
        pigeonhole_min_overlap_by_support={str(n): round(max(0.0, (n - uncovered) / n), 4) for n in BUDGETS},
        largest_support_meeting_literal_70pct=max_support,
        note='A support above this many cells must exceed 70 % within-3-px overlap with the lattice. '
             'Staying under the limit by placing cells in the uncovered ring is boundary gaming and is refused.',
    )
    return result


def main() -> int:
    res = run()
    assert res['witness']['sha256'] == res['witness']['pinned_sha256'], 'lattice hash does not match pin'
    assert res['template']['sha256'] == res['template']['pinned_sha256'], 'template hash does not match pin'
    OUT.write_text(json.dumps(res, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: res[k] for k in ['uncovered_footprint_cells', 'footprint_coverage_within_3px',
                                          'largest_support_meeting_literal_70pct']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
