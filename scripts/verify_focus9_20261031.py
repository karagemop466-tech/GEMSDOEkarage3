#!/usr/bin/env python3
"""Re-measure the nine focus-site files that are stored in docs/downloads/.

Session 2026-10-31 verification receipt. For each of GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36
this script reads the local GeoTIFF and records:

* sha256 (full), dtype, CRS, shape, nodata tag;
* NaN count, count of cells equal to 1 (the dot set), count equal to 0, min and max;
* outside-footprint convention (NaN-outside versus zero-outside), checked against the official text
  "data outside the bounds is null or nan" (DrivenData problem page, page 967);
* exact pixel-subset relations between dot sets;
* the share of each file's dots lying within 3 px (Euclidean) of another focus file's dots.

Output: evidence/focus9-verification-20261031.json. Labels: GEOMETRY and FORMAT MEASUREMENTS.
None of these numbers is a score, and nothing in this script approves a file for submission.
The uniqueness pass uses the literal 70 % / 3 px rule, but only among the nine focus files
(the full-registry rule is checked elsewhere, see evidence/k8d-registry-uniqueness-scan.json).

Run: python -m scripts.verify_focus9_20261031
"""
from __future__ import annotations

import glob
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / 'evidence/focus9-verification-20261031.json'
SITES = ['GEMSDOE24', 'GEMSDOE25', 'GEMSDOE27', 'GEMSDOE28', 'GEMSDOE30',
         'GEMSDOE31', 'GEMSDOE32', 'GEMSDOE33', 'GEMSDOE36']
OFFICIAL_SOURCE = 'https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/'
UNIQUE_LIMIT = 0.70
NEAR_PX = 3.0


def _find(site: str) -> Path:
    hits = sorted(glob.glob(str(ROOT / f'docs/downloads/{site}-*.tif')))
    if len(hits) != 1:
        raise FileNotFoundError(f'{site}: expected exactly one file in docs/downloads, found {hits}')
    return Path(hits[0])


def measure(path: Path) -> tuple[dict, np.ndarray]:
    raw = path.read_bytes()
    with rasterio.open(path) as d:
        a = d.read(1)
        meta = dict(
            file=path.name,
            sha256=hashlib.sha256(raw).hexdigest(),
            bytes=len(raw),
            dtype=d.dtypes[0],
            crs=str(d.crs),
            shape=list(a.shape),
            nodata_tag=None if d.nodata is None else str(d.nodata),
        )
    nan = int(np.isnan(a).sum())
    finite = a[np.isfinite(a)]
    meta.update(
        nan_cells=nan,
        cells_equal_1=int((a == 1).sum()),
        cells_equal_0=int((a == 0).sum()),
        finite_min=float(finite.min()),
        finite_max=float(finite.max()),
        finite_values_only_0_or_1=bool(np.isin(finite, [0.0, 1.0]).all()),
        outside_convention='nan' if nan > 0 else 'zero',
    )
    return meta, a == 1


def run() -> dict:
    files, masks = {}, {}
    for s in SITES:
        meta, m = measure(_find(s))
        files[s] = meta
        masks[s] = m

    dist = {s: distance_transform_edt(~masks[s]) for s in SITES}
    subset_rows = {}
    for a in SITES:
        na = int(masks[a].sum())
        row = {}
        for b in SITES:
            if a == b:
                continue
            within = int((masks[a] & (dist[b] <= NEAR_PX)).sum())
            row[b] = round(within / na, 4)
        subset_rows[a] = row

    pairs = {}
    for a in SITES:
        for b in SITES:
            if a >= b:
                continue
            pairs[f'{a}|{b}'] = dict(
                a_minus_b=int((masks[a] & ~masks[b]).sum()),
                b_minus_a=int((masks[b] & ~masks[a]).sum()),
                identical=bool((masks[a] == masks[b]).all()),
            )

    # Mechanism check against the known-fault mask. Organizer (DrivenData forum, "Sep 21" post): the mask
    # is pixel-exact and equal to the provided training fault labels; predicted pixels 1-3 px from a known
    # trace are NOT masked and are penalised as false positives unless a new-fault pixel is nearby.
    labels_path = ROOT / 'docs/downloads/labels.tif'
    with rasterio.open(labels_path) as lab:
        lab_arr = lab.read(1)
    known = lab_arr > 0
    dk = distance_transform_edt(~known)
    ladder = [('GEMSDOE25', 'GEMSDOE31'), ('GEMSDOE31', 'GEMSDOE32')]
    mechanism = {
        'known_positive_cells_in_labels_tif': int(known.sum()),
        'labels_tif_nodata_value': lab.nodata,
        'labels_tif_nodata_cells': int((lab_arr == -1).sum()),
        'steps': {},
        'GEMSDOE32_min_distance_to_known_px': round(float(dk[masks['GEMSDOE32']].min()), 4),
        'GEMSDOE36_min_distance_to_known_px': round(float(dk[masks['GEMSDOE36']].min()), 4),
        'GEMSDOE32_dots_within_2px_of_known': int((masks['GEMSDOE32'] & (dk <= 2)).sum()),
        'GEMSDOE36_dots_within_2px_of_known': int((masks['GEMSDOE36'] & (dk <= 2)).sum()),
    }
    for a, b in ladder:
        removed = masks[a] & ~masks[b]
        mechanism['steps'][f'{a}->{b}'] = dict(
            removed=int(removed.sum()),
            b_is_subset_of_a=bool((masks[b] & ~masks[a]).sum() == 0),
            removed_on_known_trace=int((removed & known).sum()),
            removed_within_1px_of_known=int((removed & (dk <= 1)).sum()),
            removed_within_2px_of_known=int((removed & (dk <= 2)).sum()),
            removed_min_distance_to_known_px=round(float(dk[removed].min()), 4),
        )

    def flag_unique(site: str) -> bool:
        # True when no other focus file has more than 70 % of this site's dots within 3 px.
        return max(subset_rows[site].values()) <= UNIQUE_LIMIT

    return dict(
        schema='focus9-verification-v1',
        generated_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
        evidence_class='GEOMETRY AND FORMAT MEASUREMENT - NOT A SCORE, NOT A SUBMISSION APPROVAL',
        official_format_source=OFFICIAL_SOURCE,
        official_format_text=('float32, single layer, values between 0 and 1, '
                              '"data outside the bounds is null or nan"'),
        files=files,
        within_3px_share_of_row_dots_near_column_dots=subset_rows,
        literal_70pct_rule_unique_among_focus_files={s: flag_unique(s) for s in SITES},
        dot_set_relations=pairs,
        mechanism_vs_known_fault_mask=mechanism,
        irregularities=[
            f'{s}: outside-footprint cells are 0, not NaN; the official text says null or nan'
            for s in SITES if files[s]['outside_convention'] == 'zero'
        ],
        note=('Dot sets are cells equal to 1. The 70 % rule is applied only among the nine focus files. '
              'It is not the full-registry rule. Each number is a measurement of a local file, not a '
              'leaderboard score. No organizer receipt is implied.'),
    )


def main() -> int:
    res = run()
    OUT.write_text(json.dumps(res, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(
        unique_among_focus=res['literal_70pct_rule_unique_among_focus_files'],
        irregularities=res['irregularities'],
    ), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
