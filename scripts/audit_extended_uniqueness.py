#!/usr/bin/env python3
"""Pass-2 verification (not an experiment): audit the Exp-3 final dots/surface against EVERY
GeoTIFF under the nine focus clones' docs/downloads + inputs trees (not just the 9 bests).
Uses the vendored registry_audit unchanged. Writes evidence/extended_uniqueness.json with
genuine-detector summary (calibration lattice reported separately, IR-K3-02)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from karage3.paths import data_dir, evidence_dir, work_dir  # noqa: E402
from karage3.registry_audit import audit_final_dots  # noqa: E402

REPOS = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry-root", default="/tmp/registry")
    args = ap.parse_args()
    clones = Path(args.registry_root)
    ddir = data_dir()

    rasters = []
    for repo in REPOS:
        for sub in ("docs/downloads", "inputs"):
            base = clones / repo / sub
            if not base.exists():
                continue
            for p in sorted(base.rglob("*.tif")):
                local = f"{repo}/{p.relative_to(clones / repo).as_posix()}"
                rasters.append(dict(repo=f"buffedlizard55-lab/{repo}",
                                    path=p.relative_to(clones / repo).as_posix(),
                                    local=local, sha256=sha256_file(p)))
    manifest = dict(n_failed=0, rasters=rasters)
    print(f"extended registry: {len(rasters)} rasters", flush=True)

    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    card = json.loads((evidence_dir() / "k3_run_card.json").read_text())
    final_tif = ROOT / "docs" / "downloads" / card["raster"]["zeros_file"]
    with rasterio.open(final_tif) as ds:
        final_mask = ds.read(1) > 0
    fused = np.load(work_dir() / "surfaces" / "K3-FUSE-H3H1.npy")

    audit = audit_final_dots(fused, final_mask, foot, manifest, root=clones,
                             template_tif=ddir / "sample_submission.tif",
                             candidate_values=final_mask.astype(np.float32))
    rows = audit["comparisons"]
    lattice_rows = [r for r in rows if "lattice" in str(r.get("path", "")).lower()]
    genuine = [r for r in rows if "lattice" not in str(r.get("path", "")).lower()
               and r.get("within_3px_fraction") is not None]
    genuine_sorted = sorted(genuine, key=lambda r: -(r["within_3px_fraction"] or 0))
    summary = dict(
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        candidate=card["raster"]["zeros_file"], candidate_sha256=card["raster"]["zeros_sha256"],
        registry_rasters=len(rows), unique_masks=audit["unique_pixel_masks_or_surfaces"],
        malformed_or_missing=audit["malformed_or_missing"],
        genuine_worst_within_3px=genuine_sorted[0]["within_3px_fraction"] if genuine_sorted else None,
        genuine_worst_raster=(f"{genuine_sorted[0]['repo']}:{genuine_sorted[0]['path']}" if genuine_sorted else None),
        genuine_top10=[dict(repo=r["repo"], path=r["path"], within_3px=r["within_3px_fraction"],
                            spearman_phi=r["spearman"], dots=r.get("dots")) for r in genuine_sorted[:10]],
        genuine_duplicates_over_70pct=[dict(repo=r["repo"], path=r["path"],
                                            within_3px=r["within_3px_fraction"])
                                       for r in genuine if (r["within_3px_fraction"] or 0) > 0.70],
        lattice_rows=[dict(repo=r["repo"], path=r["path"], within_3px=r.get("within_3px_fraction"),
                           coverage=r.get("footprint_coverage_3px")) for r in lattice_rows],
        worst_abs_spearman_phi=audit["worst_abs_spearman"],
        note="Genuine = all scanned rasters except calibration-lattice paths; lattice literal overlap is a geometric constant (IR-K3-02).",
    )
    (evidence_dir() / "extended_uniqueness.json").write_text(
        json.dumps(dict(summary=summary, audit={k: v for k, v in audit.items() if k != "comparisons"},
                        comparisons=rows), indent=2, default=float) + "\n")
    print(json.dumps(summary, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
