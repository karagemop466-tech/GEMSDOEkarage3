#!/usr/bin/env python3
"""Measure literal uniqueness of one candidate against every raster in the filtered registry.

Inputs: registry/complete_registry_manifest.json (filtered inventory, NOT a proven complete
registry - see its `note`). Each unique SHA-256 is streamed from the pinned codeload tarball
of its repo@ref, verified against the manifest SHA-256, and measured in memory (nothing is
written to disk except the JSON result).

Per raster:
  * geometry must equal the template grid (CRS, shape, transform); otherwise the row is
    recorded as NOT_COMPARABLE and counted (fail-closed; never silently dropped).
  * overlap = fraction of candidate dots within 3 px (Euclidean) of any reference dot,
    reference dots = reference cells > 0 inside the template footprint.
  * spearman = rank correlation over a deterministic random subsample (seed 0, 1,000,000
    footprint cells) of footprint cells. Subsample estimate, not the exact full-footprint value.

Usage:
  python scripts/measure_registry_overlap.py CANDIDATE.tif --template T.tif \
      --manifest registry/complete_registry_manifest.json --out OUT.json
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from scipy.ndimage import distance_transform_edt
from scipy.stats import rankdata

OVERLAP_STOP = 0.70
RHO_STOP = 0.90
SUBSAMPLE = 1_000_000
SEED = 0


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch_repo_members(repo: str, ref: str, wanted: set[str]) -> dict[str, bytes]:
    """Stream one codeload tarball and return {rel_path: bytes} for wanted paths."""
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    found: dict[str, bytes] = {}
    with urllib.request.urlopen(url, timeout=300) as resp, tarfile.open(fileobj=resp, mode="r|gz") as tf:
        for member in tf:
            if not member.isfile() or "/" not in member.name:
                continue
            rel = member.name.split("/", 1)[1]
            if rel in wanted:
                src = tf.extractfile(member)
                if src is not None:
                    found[rel] = src.read()
                    if len(found) == len(wanted):
                        break
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    with rasterio.open(args.template) as t:
        tmpl = t.read(1)
        tgrid = (t.crs.to_epsg(), t.shape, tuple(t.transform)[:6])
    F = np.isfinite(tmpl)
    fidx = np.flatnonzero(F.ravel())
    rng = np.random.default_rng(SEED)
    sub = np.sort(rng.choice(fidx, size=min(SUBSAMPLE, fidx.size), replace=False))

    with rasterio.open(args.candidate) as c:
        cand = c.read(1)
        cgrid = (c.crs.to_epsg(), c.shape, tuple(c.transform)[:6])
    if cgrid != tgrid:
        raise SystemExit(f"candidate geometry {cgrid} != template {tgrid}")
    cand_dots = (cand > 0) & F
    cand_idx = np.nonzero(cand_dots)
    n_dots = int(cand_dots.sum())
    cand_sub = cand.ravel()[sub].astype(np.float64)
    cand_rank = rankdata(cand_sub)
    cand_sub_finite = np.isfinite(cand_sub)

    man = json.loads(args.manifest.read_text())
    unique: dict[str, dict] = {}
    for r in man["rasters"]:
        if r.get("status") == "ok":
            unique.setdefault(r["sha256"], r)
    by_repo = defaultdict(list)
    for r in unique.values():
        by_repo[(r["repo"], r["ref"])].append(r)

    rows: list[dict] = []
    t0 = time.time()
    for n_repo, ((repo, commit), items) in enumerate(sorted(by_repo.items()), 1):
        wanted = {it["path"] for it in items}
        try:
            members = fetch_repo_members(repo, commit, wanted)
        except Exception as exc:  # fail-closed: record and keep going
            for it in items:
                rows.append({"repo": repo, "path": it["path"], "sha256": it["sha256"],
                             "status": "FETCH_ERROR", "error": str(exc)[:200]})
            continue
        for it in items:
            blob = members.get(it["path"])
            if blob is None:
                rows.append({"repo": repo, "path": it["path"], "sha256": it["sha256"], "status": "MISSING_IN_TARBALL"})
                continue
            if sha256_bytes(blob) != it["sha256"]:
                rows.append({"repo": repo, "path": it["path"], "sha256": it["sha256"], "status": "HASH_MISMATCH"})
                continue
            try:
                with MemoryFile(blob) as mf, mf.open() as ds:
                    if ds.count != 1:
                        rows.append({"repo": repo, "path": it["path"], "sha256": it["sha256"],
                                     "status": "NOT_COMPARABLE", "reason": f"bands={ds.count}"})
                        continue
                    rgrid = (ds.crs.to_epsg() if ds.crs else None, ds.shape, tuple(ds.transform)[:6])
                    if rgrid != tgrid:
                        rows.append({"repo": repo, "path": it["path"], "sha256": it["sha256"],
                                     "status": "NOT_COMPARABLE", "reason": f"grid={rgrid[0]},{rgrid[1]}"})
                        continue
                    refarr = ds.read(1).astype(np.float64)
            except Exception as exc:
                rows.append({"repo": repo, "path": it["path"], "sha256": it["sha256"],
                             "status": "READ_ERROR", "error": str(exc)[:200]})
                continue
            ref_dots = (refarr > 0) & F
            if not ref_dots.any():
                rows.append({"repo": repo, "path": it["path"], "sha256": it["sha256"],
                             "status": "COMPARED_NO_DOTS", "overlap": 0.0, "spearman": None})
                continue
            dist = distance_transform_edt(~ref_dots)
            within = int((dist[cand_idx] <= 3.0).sum()) if n_dots else 0
            overlap = within / n_dots if n_dots else None
            ref_sub = refarr.ravel()[sub]
            ok = np.isfinite(ref_sub) & cand_sub_finite
            if ok.sum() > 2:
                rr = rankdata(ref_sub[ok])
                rho = float(np.corrcoef(cand_rank[ok], rr)[0, 1]) if np.std(rr) > 0 and np.std(cand_rank[ok]) > 0 else None
            else:
                rho = None
            rows.append({
                "repo": repo, "path": it["path"], "sha256": it["sha256"], "status": "COMPARED",
                "ref_dots": int(ref_dots.sum()), "overlap": overlap, "spearman_subsample": rho,
                "fail_overlap_gt_0p70": bool(overlap is not None and overlap > OVERLAP_STOP),
                "fail_spearman_abs_gt_0p90": bool(rho is not None and abs(rho) > RHO_STOP),
            })
        print(f"[{n_repo}/{len(by_repo)}] {repo}@{commit[:7]} rasters={len(items)} elapsed={time.time()-t0:.0f}s", flush=True)

    compared = [r for r in rows if r["status"] == "COMPARED"]
    bad_status = [r for r in rows if r["status"] not in ("COMPARED", "COMPARED_NO_DOTS")]
    overlaps = [r["overlap"] for r in compared if r["overlap"] is not None]
    fails = [r for r in compared if r.get("fail_overlap_gt_0p70") or r.get("fail_spearman_abs_gt_0p90")]
    worst = max(compared, key=lambda r: r["overlap"] or 0.0) if compared else None
    summary = {
        "candidate": str(args.candidate),
        "candidate_sha256": hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        "candidate_dots": n_dots,
        "unique_sha256_in_manifest": len(unique),
        "rasters_compared": len(compared),
        "rasters_not_comparable_or_error": len(bad_status),
        "max_overlap": max(overlaps) if overlaps else None,
        "worst_raster": (worst or {}).get("path"),
        "count_literal_fails": len(fails),
        "literal_fail_examples": [r["path"] for r in fails[:10]],
        "fail_closed": bool(bad_status or fails),
        "manifest_literal_registry_complete": bool(man.get("literal_registry_complete")),
        "manifest_note": man.get("note"),
        "spearman_method": f"subsample n={SUBSAMPLE} seed={SEED}",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    out = {"summary": summary, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n")
    print(json.dumps(summary, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
