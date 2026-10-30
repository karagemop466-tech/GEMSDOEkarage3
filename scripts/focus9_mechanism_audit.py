#!/usr/bin/env python3
"""Mechanism + uniqueness audit of the nine focus-site rasters (research only, no submission).

Purpose: test a concrete explanation for the user-reported leaderboard ordering of the
nine focus sites, and measure the literal uniqueness rule on the same files. Nothing here
authorises a submission.

Per focus file (dots = finite cells > 0 inside the competition footprint):
  * n_dots, and the share of dots within 3 px (300 m) and within 1 px of a CATALOGUE fault
    (labels.tif positive cells, i.e. the USGS/INGENIOUS traces the holdout is built on).
  * HOLDOUT-DTI recomputed with the committed shared evaluator (scripts/evaluate_holdout.py,
    evaluator GEMSDOE32-HIDE-RECOVER-v3.0). Label: HOLDOUT-DTI, not a leaderboard estimate.
  * Literal-rule overlap: share of dots within 3 px of the pinned 13GEMSDOE r13-lattice-s5
    witness dots (rule stops at > 70%).
  * Pairwise overlap: share of this file's dots within 3 px of ANY dot of each other focus
    file, and the maximum. Scope is the nine focus files plus the lattice only; this is NOT
    the complete registry, so `literal_rule_pass` is only a focus-9 + lattice result.
  * Spearman rank correlation between the USER-REPORTED score and each mechanism metric
    (N = 9; descriptive only, no inference).

Inputs (all SHA-256 checked before use):
  .cache/gems_data/{labels.tif, sample_submission.tif}  (scripts/restore_data.py --group core)
  .cache/focus9/*.tif                                    (scripts/fetch_focus9_files.py)
  .cache/witness/lattice.tif                             (pinned r13-lattice-s5)
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
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32.paths import data_dir  # noqa: E402
import evaluate_holdout  # noqa: E402  (shared evaluator CLI; not forked)

REGISTRY = ROOT / "data" / "focus_registry.json"  # canonical; registry/focus9_registry.json disagrees on 5 files (see irregularities)
# User-reported scores copied from the request (USER-REPORTED / UNVERIFIED; no organizer receipt).
USER_REPORTED = {"GEMSDOE24": 0.2477, "GEMSDOE25": 0.2600, "GEMSDOE27": 0.2449, "GEMSDOE28": 0.2710,
                 "GEMSDOE30": 0.2600, "GEMSDOE31": 0.2708, "GEMSDOE32": 0.2778, "GEMSDOE33": 0.2632,
                 "GEMSDOE36": 0.2750}
LATTICE = ROOT / ".cache" / "witness" / "lattice.tif"
LATTICE_SHA256 = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
RADIUS_PX = 3.0
RULE_MAX = 0.70
OUT = ROOT / "evidence" / "focus9-mechanism-audit-20261030.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dots_of(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float64)
    return np.isfinite(a) & (a > 0)


def share_within(src: np.ndarray, dst: np.ndarray, r: float) -> float:
    """Share of True cells in `src` lying within Euclidean distance r of a True cell in `dst`."""
    n = int(src.sum())
    if n == 0 or not dst.any():
        return 0.0
    d = ndimage.distance_transform_edt(~dst)
    return float((d[src] <= r).sum() / n)


def main() -> int:
    ddir = data_dir()
    labels_path = ddir / "labels.tif"
    template = ddir / "sample_submission.tif"
    for p, want in [(labels_path, "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"),
                    (template, "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"),
                    (LATTICE, LATTICE_SHA256)]:
        if not p.exists() or sha256_file(p) != want:
            print(f"REFUSED: missing or hash-mismatched input {p}", file=sys.stderr)
            return 2

    reg = json.loads(REGISTRY.read_text())
    rows = reg["sites"]
    assert len(rows) == 9 and {r["site"] for r in rows} == set(USER_REPORTED), [r["site"] for r in rows]
    for r in rows:
        r["owner_reported_score"] = USER_REPORTED[r["site"]]

    with rasterio.open(labels_path) as ds:
        lab = ds.read(1)
    catalogue = lab == 1
    footprint = lab != -1

    lattice_dots = dots_of(LATTICE)
    with rasterio.open(LATTICE) as ds:
        assert ds.crs.to_epsg() == 32611 and ds.shape == (3730, 3292)

    files = {}
    for r in rows:
        p = ROOT / ".cache" / "focus9" / Path(r["path"]).name  # fetch_focus9_files.py uses data/focus_registry.json
        if not p.exists():
            print(f"REFUSED: focus file not fetched: {p}", file=sys.stderr)
            return 2
        if sha256_file(p) != r["sha256"]:
            print(f"REFUSED: sha mismatch {p.name}", file=sys.stderr)
            return 2
        files[r["site"]] = (p, r, dots_of(p))

    out_rows = []
    for site, (p, r, d) in files.items():
        n = int(d.sum())
        others = {s: share_within(d, dd, RADIUS_PX) for s, (_, _, dd) in files.items() if s != site}
        # Pairwise shares are the share of THIS file's dots covered by the OTHER file's dots.
        worst_other = max(others, key=others.get)
        hd = evaluate_holdout.evaluate_path(p, b_visible_px=0.0, ddir=ddir, name=site)
        h = hd["hide_and_recover"]
        out_rows.append({
            "site": site,
            "file": p.name,
            "sha256": r["sha256"],
            "owner_reported_score_USER_REPORTED": r["owner_reported_score"],
            "n_dots": n,
            "share_dots_within_3px_of_catalogue": round(share_within(d, catalogue, RADIUS_PX), 6),
            "share_dots_within_1px_of_catalogue": round(share_within(d, catalogue, 1.0), 6),
            "holdout_dti": {
                "score_label": "HOLDOUT-DTI",
                "evaluator_version": h["evaluator_version"],
                "pooled_dti": round(h["pooled_dti"], 6),
                "ci95": [round(h["ci95_cluster_bootstrap"][0], 6), round(h["ci95_cluster_bootstrap"][1], 6)],
                "n_withheld_positives": h["n_withheld_positives"],
            },
            "sgmc_off_catalogue_holdout": {
                "score_label": "HOLDOUT-DTI",
                "evaluator_version": hd["sgmc_off_catalogue"].get("evaluator_version"),
                "prevalence_calibrated_dti": round(float(hd["sgmc_off_catalogue"]["sgmc_prevalence_calibrated_dti"]), 6),
                "calibrated_ci95": [round(float(v), 6) for v in hd["sgmc_off_catalogue"]["sgmc_calibrated_ci95"]],
                "n_withheld_positives": hd["sgmc_off_catalogue"].get("n_withheld_positives"),
            },
            "lattice_overlap_within_3px": round(share_within(d, lattice_dots, RADIUS_PX), 6),
            "literal_rule_vs_lattice_pass": share_within(d, lattice_dots, RADIUS_PX) <= RULE_MAX,
            "max_overlap_within_3px_vs_other_focus_file": {"site": worst_other, "share": round(others[worst_other], 6)},
            "overlap_within_3px_vs_other_focus_files": {k: round(v, 6) for k, v in others.items()},
        })

    scores = [x["owner_reported_score_USER_REPORTED"] for x in out_rows]
    def rho(key_fn):
        vals = [key_fn(x) for x in out_rows]
        s = spearmanr(scores, vals)
        return {"spearman_rho": round(float(s.statistic), 4), "p_value": round(float(s.pvalue), 4), "n": len(vals)}
    summary = {
        "score_vs_share_near_catalogue_3px": rho(lambda x: x["share_dots_within_3px_of_catalogue"]),
        "score_vs_holdout_dti": rho(lambda x: x["holdout_dti"]["pooled_dti"]),
        "score_vs_n_dots": rho(lambda x: x["n_dots"]),
        "score_vs_sgmc_off_catalogue_calibrated_dti": rho(lambda x: x["sgmc_off_catalogue_holdout"]["prevalence_calibrated_dti"]),
        "caveat": "N=9 descriptive only; USER-REPORTED scores; not a calibration. Holdout DTI and "
                  "near-catalogue share are not leaderboard estimates.",
    }

    receipt = {
        "schema": "focus9-mechanism-audit-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": "Do the top user-reported focus files differ from the catalogue in a way that explains the ordering, and do they pass the literal lattice rule?",
        "labels_sha256": sha256_file(labels_path),
        "template_sha256": sha256_file(template),
        "lattice_sha256": LATTICE_SHA256,
        "catalogue_positive_cells": int(catalogue.sum()),
        "footprint_cells": int(footprint.sum()),
        "rows": out_rows,
        "summary": summary,
        "registry_used": "data/focus_registry.json",
        "scope": "Nine focus files + lattice only. NOT the complete registry. Not a submission authorisation.",
        "ok_to_submit": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for x in out_rows:
        print(f"{x['site']:9s} score={x['owner_reported_score_USER_REPORTED']:.4f} n={x['n_dots']:6d} "
              f"near_cat3={x['share_dots_within_3px_of_catalogue']:.4f} "
              f"holdout={x['holdout_dti']['pooled_dti']:.4f} "
              f"lattice={x['lattice_overlap_within_3px']:.4f} "
              f"max_pair={x['max_overlap_within_3px_vs_other_focus_file']['share']:.4f}")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
