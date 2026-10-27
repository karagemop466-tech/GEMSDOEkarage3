"""Recheck nine pinned historical TIFFs, NOT new-candidate validation or evaluation.

Requires rasterio, numpy, scipy. Downloads are ignored under data/historical/.
No official template is present: peer grid agreement is not official-grid validation.
"""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]


def main():
    upstream = json.loads((ROOT/'evidence/upstream/GEMSDOE32/evidence/arena48_focus9_overlap.json').read_text())
    masks, rows = {}, []
    first_grid = None
    for winner in upstream['winners']:
        site = winner['site']
        destination = ROOT/'data/historical'/site/Path(winner['file']).name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or destination.stat().st_size == 0:
            endpoint = f"repos/buffedlizard55-lab/{site}/contents/{winner['file']}?ref={winner['repo_ref']}"
            entry = json.loads(subprocess.check_output(['gh','api',endpoint], timeout=90))
            if entry.get('encoding') != 'base64':
                entry = json.loads(subprocess.check_output(['gh','api',f"repos/buffedlizard55-lab/{site}/git/blobs/{entry['sha']}"], timeout=90))
            if entry.get('encoding') != 'base64':
                raise ValueError(f'Unsupported GitHub content encoding: {site}')
            destination.write_bytes(base64.b64decode(entry['content']))
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if digest != winner['sha256']:
            raise ValueError(f'Pinned digest mismatch: {site}')
        with rasterio.open(destination) as ds:
            arr = ds.read(1)
            grid = dict(crs=str(ds.crs),shape=list(ds.shape),transform=list(ds.transform)[:6])
            if first_grid is None:
                first_grid = grid
            if grid != first_grid or ds.count != 1:
                raise ValueError(f'Cannot compare incompatible rasters: {site}')
            finite = np.isfinite(arr)
            masks[site] = finite & (arr > 0)
            rows.append(dict(site=site,sha256=digest,sha256_matches_upstream=True,
                             positive_pixels=int(masks[site].sum()), grid=grid,
                             single_band=ds.count==1,finite_everywhere=bool(finite.all()),
                             finite_values_in_0_1=bool(((arr[finite]>=0)&(arr[finite]<=1)).all()),
                             official_template_match=None))
    pairwise = []
    for site, mask in masks.items():
        distance = distance_transform_edt(~mask)
        for other, other_mask in masks.items():
            if site == other:
                continue
            pairwise.append(dict(candidate=other,reference=site,
                                 candidate_fraction_within_3px=float(np.mean(distance[other_mask]<=3)),
                                 identical_positive_mask=bool(np.array_equal(mask,other_mask))))
    report = dict(evidence_class='LOCAL-RASTER-AUDIT (not HOLDOUT-DTI; no performance measured)',
                  method='Euclidean pixel-centre distance <=3; positive mask = finite & value>0',
                  official_template_available=False, complete_registry_checked=False,
                  surfaces_checked=False, new_submission_generated=False,
                  rasters=rows,pairwise=pairwise)
    target=ROOT/'docs/historical-raster-audit.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(f'Verified {len(rows)} historical rasters; {len(pairwise)} directed comparisons. No new submission generated.')

if __name__ == '__main__':
    main()
