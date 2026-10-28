"""Shared fail-closed budget preflight for archived normal-budget experiment runners."""
import json
from pathlib import Path
from scripts.audit_registry import dot_bound

ROOT = Path(__file__).resolve().parents[1]


def require_budget_not_proven_duplicate(budget: int) -> None:
    """A necessary condition only. Passing does NOT authorize placement or a slot."""
    witness = json.loads((ROOT / 'evidence/geometry_audit.json').read_text())
    bound = dot_bound(budget, witness['lattice']['uncovered_footprint_pixels'])
    if bound['duplicate_stop_proven']:
        raise SystemExit(
            'STOP: literal any-registry uniqueness fails before placement: '
            f"at least {bound['minimum_overlap_fraction']:.6%} overlap with the pinned lattice. "
            'No density exemption, new raster, or submission authorized.'
        )
