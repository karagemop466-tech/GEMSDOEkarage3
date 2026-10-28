"""Regression for the documented literal lattice pigeonhole bound."""
import json
from pathlib import Path


def test_pinned_budget_bound():
    root = Path(__file__).resolve().parents[1]
    lattice = json.loads((root / "evidence/geometry_audit.json").read_text())["lattice"]
    b = lattice["bound_for_37654_dots"]
    assert b["minimum_overlap_dots"] == max(0, b["dots"] - lattice["uncovered_footprint_pixels"])
    assert b["minimum_overlap_fraction"] == b["minimum_overlap_dots"] / b["dots"]
    assert b["minimum_overlap_fraction"] > 0.70
    assert b["duplicate_stop_proven"] is True
