"""Necessary, fail-closed duplicate-budget preflight against a pinned witness.

The user's protocol uses *literal* directional overlap, not a calibrated
statistic. One valid witness can prove a violation but cannot certify novelty.
The bound assumes candidate dots are distinct pixels inside the same footprint.
"""
import json
from pathlib import Path

from scripts.audit_registry import dot_bound

ROOT = Path(__file__).resolve().parents[1]


def literal_lattice_bound(budget: int) -> dict:
    """Return a necessary lower bound; only an upper-bound violation is a stop."""
    witness = json.loads((ROOT / 'evidence/geometry_audit.json').read_text())
    bound = dot_bound(budget, witness['lattice']['uncovered_footprint_pixels'])
    bound['rule'] = 'literal directional overlap > 0.70 is a duplicate stop'
    return bound


def require_budget_not_proven_duplicate(budget: int) -> None:
    """Stop before placement if the pinned witness already proves a violation."""
    bound = literal_lattice_bound(budget)
    if bound['duplicate_stop_proven']:
        raise ValueError(
            'duplicate stop: literal overlap with the pinned lattice must be at least '
            f"{bound['minimum_overlap_fraction']:.6%} for {budget} in-footprint dots, "
            'above the 70% limit. See evidence/geometry_audit.json. '
            'A null-calibrated diagnostic does not override the requested rule.'
        )


def require_shared_protocol_ready() -> None:
    """Stop experimental runs until the centrally maintained template is fixed.

    Read-only access prevents patching the shared template here. Never replace
    its missing surface-overlap or buffered whole-segment semantics privately.
    Revisit this guard only after pinning and testing an upstream fix.
    """
    raise RuntimeError(
        'Shared template protocol blocked: surface overlap gate and buffered '
        'whole-segment holdout are not verified. See GEMSDOE32 issues #42 and #60. '
        'A fixed upstream template and regression tests are required before experiments.'
    )
