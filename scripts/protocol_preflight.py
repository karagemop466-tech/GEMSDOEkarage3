"""Fail closed when the literal registry rule makes a budget impossible.

The geometric bound is conditional on the pinned mirrored footprint and lattice.
It is not a geological score or organizer authentication.
"""
import json
from pathlib import Path
from scripts.audit_registry import dot_bound

ROOT = Path(__file__).resolve().parents[1]


def literal_lattice_bound(budget: int) -> dict:
    """Minimum literal overlap any `budget`-dot file has with the pinned lattice (conditional duplicate-stop evidence)."""
    if budget <= 0:
        raise ValueError("budget must be positive")
    witness = json.loads((ROOT / 'evidence/geometry_audit.json').read_text())
    bound = dot_bound(budget, witness['lattice']['uncovered_footprint_pixels'])
    bound['rule'] = 'literal any-registry 3-pixel overlap rule'
    return bound


def require_budget_not_proven_duplicate(budget: int) -> None:
    """Refuse budgets that provably exceed the literal overlap threshold."""
    bound = literal_lattice_bound(budget)
    if bound['duplicate_stop_proven']:
        raise ValueError(
            'Literal any-registry overlap with the pinned lattice is at least '
            f"{bound['minimum_overlap_fraction']:.6%} for {budget} dots; duplicate stop."
        )
