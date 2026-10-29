#!/usr/bin/env python3
"""Literal uniqueness screen of one candidate against every registry raster available locally.

Rule (user protocol, rule 1): stop if more than 70% of the candidate's dots lie within 3 px of
one registry raster's dots, or if rank correlation with any registry raster exceeds 0.90.

Measured here, from saved bytes:
  * directional literal overlap: share of candidate dots within 3 px of any dot of registry raster R;
  * reverse overlap: share of R's dots within 3 px of the candidate (for the duplicate check);
  * Pearson correlation of the two binary dot rasters (a proxy; rank correlation on binary rasters is
    dominated by ties, so it is reported as Pearson and labelled as such).

Registry coverage is the union of: the nine GEMSDOE top-site files (fetched at pinned commits) and the
14 'scored' rasters restored from data/registry manifest (SHA-256 verified). This is NOT the complete
DrivenData leaderboard registry; the receipt says so.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_gemsdoe_top9 import CACHE as SITE_CACHE, SITES  # noqa: E402

DDIR = ROOT / ".cache" / "gems_data"
MANIFEST = ROOT / "registry" / "data_manifest.json"
RADIUS_PX = 3.0


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dots_of(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    a = np.where(np.isfinite(a), a, 0)
    return np.argwhere(a > 0)


def registry_paths() -> list[tuple[str, Path, str]]:
    out = []
    for site, _repo, _sha, path, _rep in SITES:
        p = SITE_CACHE / site / Path(path).name
        out.append((site, p, "site-top9"))
    man = json.loads(MANIFEST.read_text())
    for e in man["files"]:
        if e["group"] == "scored":
            out.append((e["id"], DDIR / e["dest"], "scored-manifest"))
    seen, uniq = set(), []
    for name, p, kind in out:
        if not p.exists():
            continue
        h = sha256(p)
        if h in seen:
            continue
        seen.add(h)
        uniq.append((name, p, kind))
    return uniq


def main(candidate: Path, out_json: Path) -> int:
    shape = (3730, 3292)
    cand = dots_of(candidate)
    cm = np.zeros(shape, np.float32)
    cm[cand[:, 0], cand[:, 1]] = 1.0
    cand_tree = cKDTree(cand)
    rows = []
    for name, p, kind in registry_paths():
        rd = dots_of(p)
        rm = np.zeros(shape, np.float32)
        rm[rd[:, 0], rd[:, 1]] = 1.0
        if rd.size == 0:
            fwd = rev = None
        else:
            dist_r, _ = cKDTree(rd).query(cand, k=1)
            fwd = float((dist_r <= RADIUS_PX).mean())
            dist_c, _ = cand_tree.query(rd, k=1)
            rev = float((dist_c <= RADIUS_PX).mean())
        x, y = cm.ravel(), rm.ravel()
        sx, sy = x.std(), y.std()
        pear = float(((x - x.mean()) * (y - y.mean())).mean() / (sx * sy)) if sx and sy else None
        rows.append(dict(registry_item=name, source=kind, file=str(p), sha256=sha256(p),
                         registry_dots=int(rd.shape[0]),
                         candidate_within3px_of_registry=None if fwd is None else round(fwd, 6),
                         registry_within3px_of_candidate=None if rev is None else round(rev, 6),
                         pearson_binary_dots=None if pear is None else round(pear, 6)))
        print(f"{name:55s} fwd={rows[-1]['candidate_within3px_of_registry']} rev={rows[-1]['registry_within3px_of_candidate']} "
              f"pearson={rows[-1]['pearson_binary_dots']}", flush=True)
    worst = max(rows, key=lambda r: (r["candidate_within3px_of_registry"] or 0))
    verdict_70 = worst["candidate_within3px_of_registry"] is not None and worst["candidate_within3px_of_registry"] > 0.70
    verdict_pear = any(r["pearson_binary_dots"] is not None and abs(r["pearson_binary_dots"]) > 0.90 for r in rows)
    rec = dict(
        schema_version=1,
        candidate=str(candidate),
        candidate_sha256=sha256(candidate),
        candidate_dots=int(cand.shape[0]),
        registry_items_checked=len(rows),
        registry_complete=False,
        registry_scope=("Nine GEMSDOE top-site files at pinned commits + 14 SHA-verified scored rasters "
                        "from the owner-mirror manifest. Not the complete DrivenData leaderboard registry."),
        worst_directional_overlap=worst,
        literal_70pct_rule_triggered=bool(verdict_70),
        pearson_gt_0_90_triggered=bool(verdict_pear),
        rows=rows,
    )
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rec, indent=2, allow_nan=False) + "\n")
    print("literal_70pct_rule_triggered", verdict_70, "pearson_triggered", verdict_pear)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_candidate_uniqueness.py CANDIDATE.tif OUT.json")
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2])))
