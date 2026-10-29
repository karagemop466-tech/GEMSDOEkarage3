"""Regression test: the saved lattice-feasibility receipt is internally consistent and pins the lattice."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "evidence" / "lattice-feasibility-20261029.json"


def test_receipt_pins_lattice_and_is_consistent():
    r = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert r["lattice"]["sha256"] == "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
    assert r["lattice"]["dots"] == 206895
    assert r["footprint_cells"] == 5167373
    assert r["covered_cells_within_3px"] + r["uncovered_footprint_cells"] == r["footprint_cells"]
    assert r["uncovered_in_3_cell_boundary_ring"] + r["uncovered_in_interior"] == r["uncovered_footprint_cells"]
    assert r["uncovered_in_3_cell_boundary_ring"] == 6580
    assert r["uncovered_footprint_cells"] == 6649
    assert abs(r["min_share_of_dots_required_in_uncovered_cells_for_rule"] - 0.30) < 1e-9
    assert "forbids selecting these lattice holes" in r["verdict"]
    assert "does not prove that no evidence-driven raster could pass" in r["verdict"]
    for c in r["candidates"]:
        assert c["literal_rule_pass"] is False
        assert c["dots_within_3px_of_lattice_share"] > 0.70
        assert c["finite_whole_array"] is True
        assert 0.0 <= c["min"] and c["max"] <= 1.0
