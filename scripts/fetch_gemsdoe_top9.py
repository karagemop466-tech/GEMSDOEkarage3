#!/usr/bin/env python3
"""Fetch and audit the nine GEMSDOE top-site submission TIFFs at their pinned commits.

Scope (honest): this only downloads the files the README cites at a specific commit
(via the GitHub contents API, which `gh` authenticates) and records bytes, SHA-256
and raster facts. It does NOT reproduce any score. Every user-reported score is
recorded as USER-REPORTED / UNVERIFIED.

Output: .cache/site_submissions/ (ignored) and docs/data/gemsdoe-top9-audit.json (tracked).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "site_submissions"
OUT = ROOT / "docs" / "data" / "gemsdoe-top9-audit.json"
TEMPLATE = ROOT / ".cache" / "gems_data" / "sample_submission.tif"

# site, repo, pinned commit (verified with `gh api repos/.../commits/<sha>`), path, user-reported score
SITES = [
    ("GEMSDOE24", "buffedlizard55-lab/GEMSDOE24", "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
     "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477),
    ("GEMSDOE25", "buffedlizard55-lab/GEMSDOE25", "04333cc3fbf7486c56e0324fd07aee684be614dc",
     "docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600),
    ("GEMSDOE27", "buffedlizard55-lab/GEMSDOE27", "b8dd298e10884afffa05436673ac73aeaf850b8c",
     "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", 0.2449),
    ("GEMSDOE28", "buffedlizard55-lab/GEMSDOE28", "ec1d501fd12c8dee9dc062726003639dec9382ff",
     "docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", 0.2710),
    ("GEMSDOE30", "buffedlizard55-lab/GEMSDOE30", "3d5bec2af5f29291617f97c9e2dfe443be6f55c3",
     "docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif", 0.2600),
    ("GEMSDOE31", "buffedlizard55-lab/GEMSDOE31", "cf13282fcd86290f1539f0a86446c8ba7205a79b",
     "docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif", 0.2708),
    ("GEMSDOE32", "buffedlizard55-lab/GEMSDOE32", "012e17b2a115c3c0d5e7885bea625bf9657c99fc",
     "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", 0.2778),
    ("GEMSDOE33", "buffedlizard55-lab/GEMSDOE33", "f52533110fe62cd03e77f1228e9e5ecac412c463",
     "docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif", 0.2632),
    ("GEMSDOE36", "buffedlizard55-lab/GEMSDOE36", "c9ad59ec6f969ed931d089a03044c1567a633e84",
     "docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif", 0.2750),
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(repo: str, sha: str, path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".partial")
    with tmp.open("wb") as out:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/contents/{path}?ref={sha}",
             "-H", "Accept: application/vnd.github.raw"],
            stdout=out, stderr=subprocess.PIPE, check=True, timeout=600,
        )
    tmp.replace(dest)


def inspect(p: Path, template: dict | None) -> dict:
    with rasterio.open(p) as ds:
        a = ds.read(1)
        meta = dict(
            crs=str(ds.crs), shape=list(ds.shape), count=ds.count, dtype=ds.dtypes[0],
            nodata=None if ds.nodata is None else str(ds.nodata),
            transform=list(ds.transform)[:6],
        )
    finite = np.isfinite(a)
    meta["nan_count"] = int((~finite).sum())
    meta["min_finite"] = float(a[finite].min()) if finite.any() else None
    meta["max_finite"] = float(a[finite].max()) if finite.any() else None
    meta["in_0_1_finite"] = bool(finite.any() and (a[finite] >= 0).all() and (a[finite] <= 1).all())
    meta["count_eq_0"] = int((a == 0).sum())
    meta["count_gt_0"] = int((a > 0).sum())
    meta["count_eq_1"] = int((a == 1).sum())
    meta["distinct_values_sample"] = [float(v) for v in np.unique(a[finite])[:8]]
    if template is not None:
        meta["grid_matches_template"] = (
            meta["crs"] == template["crs"] and meta["shape"] == template["shape"]
            and meta["transform"] == template["transform"]
        )
    return meta


def main() -> int:
    template = None
    if TEMPLATE.exists():
        with rasterio.open(TEMPLATE) as ds:
            template = dict(crs=str(ds.crs), shape=list(ds.shape), transform=list(ds.transform)[:6])
    rows = []
    for site, repo, sha, path, reported in SITES:
        dest = CACHE / site / Path(path).name
        if not dest.exists():
            fetch(repo, sha, path, dest)
        row = dict(
            site=site, repo=f"https://github.com/{repo}", commit=sha,
            commit_url=f"https://github.com/{repo}/commit/{sha}",
            file_path=path, file_url=f"https://github.com/{repo}/blob/{sha}/{path}",
            file_name=Path(path).name, bytes=dest.stat().st_size, sha256=sha256(dest),
            user_reported_score=reported,
            score_status="USER-REPORTED / UNVERIFIED (no organizer receipt located)",
        )
        row.update(inspect(dest, template))
        rows.append(row)
        print(site, row["file_name"], row["sha256"][:12], row["nan_count"], row["in_0_1_finite"],
              row["grid_matches_template"], row["count_gt_0"], flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(
        schema_version=1,
        note="Files fetched at pinned commits. Scores are USER-REPORTED from the prompt, not verified.",
        template_grid=template,
        sites=rows), indent=2, allow_nan=False) + "\n")
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
