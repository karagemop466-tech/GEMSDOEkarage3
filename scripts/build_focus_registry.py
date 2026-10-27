#!/usr/bin/env python3
"""Build registry/focus9_registry.json: the nine focus sites' best rasters (owner-reported
scores), copied from local sister-repo clones into .cache/focus_registry/ with SHA-256 and
dot counts measured here. Manifest format matches karage3.registry_audit expectations
(rasters[].local is relative to --root at audit time; use root=<repo>/.cache with locals
'focus_registry/<file>').

Selection rule (frozen): per site, the highest owner-reported score in the owner's catalogue
for which a raster file exists in the pinned clone. Champion-lineage extras (H19-5 parent,
solo) are added as controls, flagged control=true.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]

# site, repo, clone-relative path, submission id (owner catalogue), owner-reported score
ENTRIES = [
    ("GEMSDOE24", "GEMSDOE24", "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif",
     "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", 0.2477, False),
    ("GEMSDOE25", "GEMSDOE25", "docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif",
     "dotted-h19-5-d2-8-20261002-e56ea318af89-nan", 0.2600, False),
    ("GEMSDOE27", "GEMSDOE27", "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif",
     "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", 0.2449, False),
    ("GEMSDOE28", "GEMSDOE28", "docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif",
     "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", 0.2710, False),
    ("GEMSDOE30", "GEMSDOE30", "docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif",
     "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", 0.2600, False),
    ("GEMSDOE31", "GEMSDOE31", "docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif",
     "h27-4-solo-d28-20261004-8acb75e1-nan", 0.2708, False),
    ("GEMSDOE32", "GEMSDOE32", "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
     "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778, False),
    ("GEMSDOE33", "GEMSDOE33", "docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
     "h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632, False),
    ("GEMSDOE36", "GEMSDOE36", "docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
     "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", 0.2750, False),
    # controls: champion-lineage ancestors (learning/forensics only)
    ("CONTROL-H19-5-parent", "GEMSDOE24", "inputs/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-allfinite.tif",
     "h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan", 0.1922, True),
    ("CONTROL-solo-02708", "GEMSDOE28", "docs/downloads/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite.tif",
     "h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan", 0.2708, True),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(clone: Path) -> str:
    return subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry-root", default="/tmp/registry", help="dir containing sister clones")
    args = ap.parse_args()
    clones = Path(args.registry_root)
    cache = ROOT / ".cache" / "focus_registry"
    cache.mkdir(parents=True, exist_ok=True)

    with rasterio.open(ROOT / ".cache" / "gems_data" / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        tpl_shape, tpl_crs, tpl_tr = ds.shape, ds.crs, ds.transform

    rasters, sites, failures = [], {}, []
    heads: dict[str, str] = {}
    for site, repo, rel, sub_id, score, control in ENTRIES:
        clone = clones / repo
        heads.setdefault(repo, git_head(clone))
        src = clone / rel
        if not src.exists():
            failures.append(dict(site=site, repo=repo, path=rel, error="file missing in clone"))
            print("MISSING", site, rel)
            continue
        dst_name = f"{site.lower()}--{Path(rel).name}"
        dst = cache / dst_name
        shutil.copyfile(src, dst)
        sha = sha256_file(dst)
        with rasterio.open(dst) as ds:
            arr = ds.read(1)
            grid_ok = bool(ds.count == 1 and ds.shape == tpl_shape and ds.crs == tpl_crs and ds.transform == tpl_tr)
        dots = int(((arr > 0) & foot).sum())
        entry = dict(
            site=site, repo=f"buffedlizard55-lab/{repo}", repo_head=heads[repo], path=rel,
            local=f"focus_registry/{dst_name}", sha256=sha, bytes=dst.stat().st_size,
            submission_id=sub_id, owner_reported_score=score,
            score_label="OWNER-REPORTED (no organizer receipt stored; IR-K3-04)",
            dots=dots, grid_ok=grid_ok, control=bool(control),
            site_url=f"https://buffedlizard55-lab.github.io/{repo}/",
        )
        rasters.append(entry)
        if not control:
            sites[site] = entry
        print(f"{site:22s} dots={dots:6d} grid_ok={grid_ok} sha={sha[:12]} {Path(rel).name}")

    out = dict(
        schema_version=1,
        built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        note="Focus-9 best rasters copied from local clones at the recorded HEADs. Scores are OWNER-REPORTED from the owner's catalogue (registry/owner_score_ledger.csv), never ORGANIZER-CONFIRMED.",
        clone_heads=heads, n_failed=len(failures), failures=failures,
        rasters=rasters, site_bests=sites,
    )
    (ROOT / "registry" / "focus9_registry.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote registry/focus9_registry.json ({len(rasters)} rasters, {len(failures)} failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
