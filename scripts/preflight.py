#!/usr/bin/env python3
"""Fail-closed, zero-experiment feasibility check for the literal registry rule.

A counting bound can prove a budget impossible; it cannot prove a smaller
candidate unique, scientifically useful, or approved. It never selects a slot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(audit_path: Path, manifest_path: Path, dots: int) -> dict:
    if dots <= 0:
        raise ValueError("dots must be positive")
    audit = json.loads(audit_path.read_text())
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if audit.get("kind") != "GEOMETRY-AUDIT, NOT A SCORE" or audit.get("manifest_sha256") != manifest_hash:
        raise ValueError("Audit is missing, has the wrong kind, or does not match the pinned manifest")
    footprint = audit["grid"]["footprint_pixels"]
    uncovered = audit["lattice"]["uncovered_beyond_3px"]
    if not isinstance(footprint, int) or not isinstance(uncovered, int) or not 0 <= uncovered <= footprint:
        raise ValueError("Invalid lattice counts")
    if dots > footprint:
        raise ValueError("distinct in-footprint dots cannot exceed the footprint size")
    covered_min = max(0, dots - uncovered)
    bound = Fraction(covered_min, dots)
    fails = bound > Fraction(7, 10)  # equality is allowed; strictly greater is the stop
    return {
        "kind": "GEOMETRY-AUDIT, NOT A SCORE",
        "audit_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
        "scope": "One pinned lattice witness; no surface or final-dot registry audit was performed here.",
        "distinct_in_footprint_dots": dots, "uncovered_pixels": uncovered,
        "lower_bound_numerator": bound.numerator, "lower_bound_denominator": bound.denominator,
        "lower_bound_fraction": float(bound),
        "witness": audit["lattice"]["source"],
        "budget_necessarily_exceeds_70_percent": fails,
        "decision": "DUPLICATE-STOP" if fails else "NOT PROVEN IMPOSSIBLE; NOT A UNIQUENESS PASS",
        "assigned_lane_present_in_this_request": False,
        "new_tif_generated": False, "selector_approval": False, "submission_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dots", type=int, required=True)
    parser.add_argument("--audit", type=Path, default=ROOT / "docs/data/historical-audit.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/focus_registry.json")
    args = parser.parse_args()
    result = check(args.audit, args.manifest, args.dots)
    print(json.dumps(result, indent=2, allow_nan=False))
    # A non-proven bound is inconclusive, not permission to proceed. Keep both
    # outcomes nonzero so shell pipelines cannot confuse this with a gate pass.
    return 1 if result["budget_necessarily_exceeds_70_percent"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
