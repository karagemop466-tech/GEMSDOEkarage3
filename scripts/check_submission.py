#!/usr/bin/env python3
"""Independent submission validator CLI (wraps the shared writer's audit_geotiff).

Usage: PYTHONPATH=src python scripts/check_submission.py <file.tif> [--mode zeros|nan]
Exit 0 only if every check passes: single-band float32, EPSG:32611, 3730x3292, exact
transform, footprint finite in [0,1] (kills DrivenData 'Predicted values must be in
range [0, 1]'), outside-footprint convention, zero on-catalogue dots."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from karage3.paths import data_dir  # noqa: E402
from karage3.submission import audit_geotiff  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tif")
    ap.add_argument("--mode", default="zeros", choices=["zeros", "nan"])
    args = ap.parse_args()
    ddir = data_dir()
    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(ddir / "labels.tif") as ds:
        labels = ds.read(1) >= 1
    try:
        receipt = audit_geotiff(Path(args.tif), foot, labels, mode=args.mode,
                                template_tif=ddir / "sample_submission.tif")
    except Exception as exc:
        print(json.dumps(dict(ok=False, error=f"{type(exc).__name__}: {exc}"), indent=2))
        return 1
    receipt["ok"] = bool(receipt["all_checks_passed"])
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
