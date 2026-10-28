"""Shared literal-uniqueness budget preflight for experiment runners.

A registered raster's raw 3-pixel neighborhood is part of the active user
protocol; null-calibrated overlap is supplementary and cannot waive the rule.
The pinned lattice witness covers all but 6,649 footprint pixels within 3 px.
For any fixed dot budget whose pigeonhole lower bound exceeds 70%, stop before
placement rather than target gaps or relax the threshold.
"""
import json
from pathlib import Path

from scripts.audit_registry import dot_bound

ROOT = Path(__file__).resolve().parents[1]


def literal_lattice_bound(budget: int) -> dict:
    """Return the necessary literal-overlap lower bound for a registered witness."""
    if budget <= 0:
        raise ValueError("budget must be positive")
    witness = json.loads((ROOT / 'evidence/geometry_audit.json').read_text())
    bound = dot_bound(budget, witness['lattice']['uncovered_footprint_pixels'])
    bound['rule'] = 'literal raw overlap must not exceed 70%; pigeonhole lower bound above 70% is a pre-placement stop'
    return bound


def require_budget_not_proven_duplicate(budget: int) -> None:
    """Stop when the literal overlap rule is mathematically impossible at this budget."""
    bound = literal_lattice_bound(budget)
    if bound['duplicate_stop_proven']:
        raise ValueError(
            'Literal any-registry overlap with the pinned lattice is necessarily '
            f"{bound['minimum_overlap_fraction']:.6%} or greater for {budget} dots "
            f"({bound['minimum_overlap_dots']}/{budget}); this exceeds 70%. "
            'Do not place dots or relax the rule.'
        )
