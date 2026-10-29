#!/usr/bin/env python3
"""Run the shared holdout evaluator on the nine pinned focus-site files.

Every number written here is labelled HOLDOUT-DTI with the evaluator version,
the number of withheld positives and the 95% cluster-bootstrap CI, exactly as
the evaluator reports them. These are STATIC binary diagnostics
(promotion_eligible=false). They are not organizer scores and are not a
predictor of the leaderboard. Run scripts/fetch_focus9_files.py first.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from evaluate_holdout import evaluate_path  # noqa: E402  (shared repo evaluator, unmodified)

REGISTRY = ROOT / "data" / "focus_registry.json"
FILES = ROOT / ".cache" / "focus9"
OUT = ROOT / "evidence" / "focus9-holdout-baseline-20261029.json"
REF_GRID = {"epsg": 32611, "height": 3730, "width": 3292,
            "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def format_checks(path: Path) -> dict:
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype(np.float64)
        epsg = ds.crs.to_epsg() if ds.crs else None
        transform = [float(x) for x in tuple(ds.transform)[:6]]
        finite = np.isfinite(arr)
        return {
            "bands": ds.count,
            "dtype": ds.dtypes[0],
            "epsg": epsg,
            "shape": [ds.height, ds.width],
            "transform_matches_reference": bool(np.allclose(transform, REF_GRID["transform"])),
            "crs_matches_reference": epsg == REF_GRID["epsg"],
            "shape_matches_reference": (ds.height, ds.width) == (REF_GRID["height"], REF_GRID["width"]),
            "nodata": None if ds.nodata is None else str(ds.nodata),
            "nan_cells": int((~finite).sum()),
            "finite_values_in_0_1": bool(np.all((arr[finite] >= 0) & (arr[finite] <= 1))),
            "positive_cells": int((finite & (arr > 0)).sum()),
        }


def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    records = []
    for site in registry["sites"]:
        path = FILES / Path(site["path"]).name
        if sha256_file(path) != site["sha256"]:
            print(f"refusing {site['site']}: SHA-256 mismatch", file=sys.stderr)
            return 2
        res = evaluate_path(path, b_visible_px=0.0, name=site["site"])
        hr = res["hide_and_recover"]
        sg = res["sgmc_off_catalogue"]
        fmt = format_checks(path)
        records.append({
            "site": site["site"],
            "file": path.name,
            "sha256": site["sha256"],
            "source_url": site["source_url"],
            "historical_claim": site["historical_claim"],
            "claim_class": site["claim_class"],
            "format_checks": fmt,
            "holdout_dti_hide_and_recover": {
                "score_label": "HOLDOUT-DTI",
                "evaluator_version": hr["evaluator_version"],
                "pooled_dti": hr["pooled_dti"],
                "ci95_cluster_bootstrap": hr["ci95_cluster_bootstrap"],
                "n_withheld_positives": hr["n_withheld_positives"],
                "n_spatial_clusters": hr["n_spatial_clusters"],
                "fold_mean_dti": hr["fold_mean_dti"],
            },
            "holdout_dti_sgmc_off_catalogue": {
                "score_label": "HOLDOUT-DTI",
                "evaluator_version": sg["evaluator_version"],
                "raw_pooled_dti": sg["sgmc_raw_pooled_dti"],
                "raw_ci95": sg["sgmc_raw_ci95"],
                "prevalence_calibrated_dti": sg["sgmc_prevalence_calibrated_dti"],
                "calibrated_ci95": sg["sgmc_calibrated_ci95"],
                "n_withheld_positives": sg["n_withheld_positives"],
            },
            "evaluator_flags": {
                "mode": res.get("mode"),
                "promotion_eligible": res.get("promotion_eligible"),
                "provenance_warning": res.get("provenance_warning"),
            },
        })
        print(f"{site['site']}: HR={hr['pooled_dti']:.4f} SGMC-cal={sg['sgmc_prevalence_calibrated_dti']:.4f}",
              file=sys.stderr)
    out = {
        "kind": "HOLDOUT-DTI STATIC BINARY DIAGNOSTIC, NOT AN ORGANIZER SCORE",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "registry_sha256": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
        "reference_grid": REF_GRID,
        "sites": records,
        "limitations": [
            "Static binary masks cannot establish fold-local catalogue features (evaluator provenance_warning).",
            "Local ranking does not reproduce portal ordering; these values must not be used as leaderboard estimates.",
            "Portal scores are USER-REPORTED / UNVERIFIED; no organizer receipt was available.",
        ],
    }
    OUT.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
