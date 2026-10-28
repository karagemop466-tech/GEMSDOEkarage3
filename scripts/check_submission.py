"""Run a conservative local format diagnostic; never authorize a submission.

The shared template's writer remains unmodified. Its validator currently misses
masked in-footprint values (upstream issue #66). This independent saved-byte
check also refuses external TIFF sidecars and reports outside-footprint policy
separately from the whole-array finite/range diagnostic.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems32.paths import data_dir  # noqa: E402
from scripts.validate_raster import audit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geotiff", type=Path, help="Path to the saved GeoTIFF")
    parser.add_argument("--template", type=Path, default=data_dir() / "sample_submission.tif",
                        help="Organizer template or explicitly identified owner mirror")
    parser.add_argument("--strict-finite", action="store_true",
                        help="Also require whole-array finite [0,1]; not proof of organizer acceptance")
    args = parser.parse_args()
    try:
        report = audit(args.geotiff, args.template)
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        report = {"candidate": str(args.geotiff), "template": str(args.template), "error": str(exc),
                  "core_format_pass": False, "organizer_acceptance": "unknown", "authorization": "NOT AUTHORIZED"}
    passed = report.get("core_format_pass") is True
    if args.strict_finite:
        passed = passed and report.get("whole_array_finite_range_pass") is True
    print(json.dumps(report, indent=2, allow_nan=False))
    if passed:
        print("\n[PASSED] Local format diagnostic only; outside-footprint policy and organizer acceptance "
              "are separate. NOT AUTHORIZED for submission.")
        return 0
    print("\n[FAILED] Local format diagnostic; NOT AUTHORIZED for submission.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
