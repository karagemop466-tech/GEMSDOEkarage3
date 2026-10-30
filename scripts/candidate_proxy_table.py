#!/usr/bin/env python3
"""Measure every format-valid repo candidate on the same axes (research only, no submission).

For each GeoTIFF passed on the command line (or the default list of repo candidates):
  * official format gate (scripts/check_format.py logic, imported, not forked)
  * dots = finite cells > 0 inside the footprint
  * share of dots within 3 px / 1 px of a CATALOGUE fault (labels.tif)
  * HOLDOUT-DTI, catalogue hide-and-recover (shared evaluator GEMSDOE32-HIDE-RECOVER-v3.0)
  * HOLDOUT-DTI, off-catalogue SGMC prevalence-calibrated (GEMSDOE32-SGMC-CAL-v3.0)
  * literal lattice overlap (share of dots within 3 px of the pinned r13-lattice-s5 dots)

Every label is HOLDOUT-DTI (with evaluator version, withheld-positive count, 95% CI) or a
descriptive geometric share. None of these is a leaderboard estimate; the README records
that no local proxy has been calibrated against organizer scores.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32.paths import data_dir  # noqa: E402
import evaluate_holdout  # noqa: E402
import check_format  # noqa: E402

LATTICE = ROOT / ".cache" / "witness" / "lattice.tif"
LATTICE_SHA256 = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
OUT = ROOT / "evidence" / "candidate-proxy-table-20261030.json"

DEFAULT = [
    "docs/quarantine/geoconduit-hybrid/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-nan.tif",
    "docs/downloads/gemsdoe32-hk3-smgc-maxenv-axial28-37654-20261027T213000Z-c886c782-nan.tif",
    "docs/downloads/gemsdoe32-karage3-consensus-hgrad-k37654-20261029T183206Z-4786d9bd-nan.tif",
    "docs/downloads/karage3-k3-fuse-greedy-b2-20261027T212847Z-80117cd2-nan.tif",
    "docs/quarantine/h1-seismic-gravity-basin/gemsdoe32-karage3-h1-seismic-gravity-basin-20261029T182309Z-91540319-nan.tif",
    "docs/quarantine/karage3-unique-offcat/karage3-unique-offcat-20261029T180337Z-6a8c2368-nan.tif",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def share_within(src: np.ndarray, dst: np.ndarray, r: float) -> float:
    n = int(src.sum())
    if n == 0 or not dst.any():
        return 0.0
    d = ndimage.distance_transform_edt(~dst)
    return float((d[src] <= r).sum() / n)


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] or [ROOT / p for p in DEFAULT]
    ddir = data_dir()
    template = ddir / "sample_submission.tif"
    labels = ddir / "labels.tif"
    if sha256_file(LATTICE) != LATTICE_SHA256:
        print("REFUSED: lattice hash mismatch", file=sys.stderr)
        return 2
    with rasterio.open(labels) as ds:
        lab = ds.read(1)
    catalogue = lab == 1
    with rasterio.open(LATTICE) as ds:
        la = ds.read(1).astype(np.float64)
    lattice = np.isfinite(la) & (la > 0)

    rows = []
    for p in paths:
        p = p if p.is_absolute() else ROOT / p
        fmt = check_format.inspect(p, template)
        with rasterio.open(p) as ds:
            a = ds.read(1).astype(np.float64)
        dots = np.isfinite(a) & (a > 0) & (lab != -1)
        row = {
            "file": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
            "sha256": sha256_file(p),
            "official_format_gate_pass": bool(fmt["format_gate_pass"]),
            "format_failed_checks": sorted(k for k, v in fmt["checks"].items() if not v),
            "n_dots_in_footprint": int(dots.sum()),
            "share_dots_within_3px_of_catalogue": round(share_within(dots, catalogue, 3.0), 6),
            "share_dots_within_1px_of_catalogue": round(share_within(dots, catalogue, 1.0), 6),
            "lattice_overlap_within_3px": round(share_within(dots, lattice, 3.0), 6),
            "literal_rule_vs_lattice_pass": share_within(dots, lattice, 3.0) <= 0.70,
        }
        if row["official_format_gate_pass"] and dots.any():
            hd = evaluate_holdout.evaluate_path(p, b_visible_px=0.0, ddir=ddir, name=p.stem)
            h = hd["hide_and_recover"]
            s = hd["sgmc_off_catalogue"]
            row["holdout_catalogue_hide_and_recover"] = {
                "score_label": "HOLDOUT-DTI", "evaluator_version": h["evaluator_version"],
                "pooled_dti": round(h["pooled_dti"], 6),
                "ci95": [round(h["ci95_cluster_bootstrap"][0], 6), round(h["ci95_cluster_bootstrap"][1], 6)],
                "n_withheld_positives": h["n_withheld_positives"],
            }
            row["holdout_off_catalogue_sgmc_calibrated"] = {
                "score_label": "HOLDOUT-DTI", "evaluator_version": s["evaluator_version"],
                "prevalence_calibrated_dti": round(s["sgmc_prevalence_calibrated_dti"], 6),
                "ci95": [round(float(v), 6) for v in s["sgmc_calibrated_ci95"]],
                "n_withheld_positives": s["n_withheld_positives"],
            }
        else:
            row["holdout"] = "NOT RUN: fails the official format gate or has no dots (evaluator refuses non-conforming grids)"
        rows.append(row)
        print(f"{row['file'][-70:]:70s} fmt={row['official_format_gate_pass']!s:5} dots={row['n_dots_in_footprint']:6d} "
              f"nearCat3={row['share_dots_within_3px_of_catalogue']:.4f} lattice={row['lattice_overlap_within_3px']:.4f}")

    receipt = {
        "schema": "candidate-proxy-table-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lattice_sha256": LATTICE_SHA256,
        "labels_sha256": sha256_file(labels),
        "template_sha256": sha256_file(template),
        "rows": rows,
        "scope": "Descriptive proxies only. HOLDOUT-DTI is a catalogue/SGMC proxy, not an organizer score. "
                 "Lattice = one registry raster, not the complete registry.",
        "ok_to_submit": False,
    }
    OUT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
