"""Shared budget preflight for experiment runners (v3, 2026-10-28, IR-K3-17).

The literal "<= 70 % of dots within 3 px of any registry raster" rule is unsatisfiable by pigeonhole for every
file with >= 22,164 dots because the pinned calibration lattice (13GEMSDOE r13-lattice-s5) covers 99.87 % of the
footprint within 3 px (IR-K3-02).  A gate no valid submission can pass measures geometry, not lane drift, so the
duplicate rule is applied to the null-calibrated excess overlap (obs - p0)/(1 - p0) in `promotion_gate.py`.

This preflight therefore no longer stops a run on the literal lattice bound.  It still computes and returns the
bound so every run card can disclose it, and it still refuses nonsensical budgets.
"""
import json
import warnings
from pathlib import Path
from scripts.audit_registry import dot_bound

ROOT = Path(__file__).resolve().parents[1]


def literal_lattice_bound(budget: int) -> dict:
    """Minimum literal overlap any `budget`-dot file has with the pinned lattice (disclosure, not a stop)."""
    if budget <= 0:
        raise ValueError("budget must be positive")
    witness = json.loads((ROOT / 'evidence/geometry_audit.json').read_text())
    bound = dot_bound(budget, witness['lattice']['uncovered_footprint_pixels'])
    bound['rule'] = 'literal bound disclosed; duplicate decision uses null-calibrated excess overlap (IR-K3-17)'
    return bound


def require_budget_not_proven_duplicate(budget: int) -> None:
    """Backward-compatible name.  Raises only for invalid budgets; warns (does not stop) on the literal bound."""
    bound = literal_lattice_bound(budget)
    if bound['duplicate_stop_proven']:
        warnings.warn(
            'Literal any-registry overlap with the pinned lattice is at least '
            f"{bound['minimum_overlap_fraction']:.6%} for {budget} dots (pigeonhole, IR-K3-02); "
            'the gate applies the null-calibrated rule instead (IR-K3-17).',
            stacklevel=2,
        )
