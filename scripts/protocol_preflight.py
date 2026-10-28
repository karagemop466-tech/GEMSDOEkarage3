"""Shared strict-literal budget preflight for experiment runners.

The user's current protocol applies the literal 70% / 3 px overlap limit to every registry raster,
including lattices and blankets. If a pinned lattice's uncovered footprint makes that threshold
mathematically impossible for a proposed dot budget, stop before placement. Null-calibrated values
may be reported diagnostically but cannot override this stop.
"""
import json
from pathlib import Path
from scripts.audit_registry import dot_bound

ROOT = Path(__file__).resolve().parents[1]


def literal_lattice_bound(budget: int) -> dict:
    """Minimum literal overlap any `budget`-dot file has with the pinned lattice."""
    if budget <= 0:
        raise ValueError("budget must be positive")
    witness = json.loads((ROOT / 'evidence/geometry_audit.json').read_text())
    bound = dot_bound(budget, witness['lattice']['uncovered_footprint_pixels'])
    bound['rule'] = 'strict literal overlap limit <= 0.70; no null-calibration/lattice exception'
    return bound


def require_budget_not_proven_duplicate(budget: int) -> None:
    """Stop before placement when the literal overlap bound proves duplication."""
    bound = literal_lattice_bound(budget)
    if bound['duplicate_stop_proven']:
        raise ValueError(
            'Strict literal any-registry overlap bound is at least '
            f"{bound['minimum_overlap_fraction']:.6%} for {budget} dots, above 70%; "
            'do not place this budget or seek uncovered lattice holes.'
        )
