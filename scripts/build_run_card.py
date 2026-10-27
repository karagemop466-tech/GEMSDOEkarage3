#!/usr/bin/env python3
"""Publish this zero-experiment negative card, bound to a forensic audit.

This is not a general-purpose release selector and cannot authorize a TIFF.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    path = ROOT / "docs/data/historical-audit.json"
    audit = json.loads(path.read_text())
    if audit.get("kind") != "GEOMETRY-AUDIT, NOT A SCORE" or not audit.get("no_new_experiment"):
        raise ValueError("Expected the historical-only forensic audit")
    manifest = ROOT / "data/focus_registry.json"
    if audit.get("manifest_sha256") != hashlib.sha256(manifest.read_bytes()).hexdigest():
        raise ValueError("Forensic audit does not match the registry manifest")
    output = ROOT / "docs/data/current-run.json"
    if output.exists():
        prior = json.loads(output.read_text())
        if not (str(prior.get("run_id", "")).startswith("gems-karage3-preflight-") and
                prior.get("verdict") == "negative" and prior.get("experiments_run") == 0 and
                prior.get("weekly_slots_used") == 0 and prior.get("raster_sha256") is None and
                prior.get("holdout_dti", {}).get("value") is None):
            raise ValueError("Refusing to overwrite a non-preflight or nonempty run card")
    now = datetime.now(timezone.utc)
    lattice = audit["lattice"]
    if not lattice["budget_lower_bound"] > .7:
        raise ValueError("The required duplicate-stop evidence is absent")
    card = {
        "schema_version": 1,
        "run_id": "gems-karage3-preflight-" + now.strftime("%Y%m%dT%H%M%SZ"),
        "created_utc": now.isoformat(),
        "hypothesis": "PROPOSED ONLY: multi-scale gravity–magnetic signed edge-offset persistence beneath weak relief; not an assigned lane and not tested.",
        "mechanism": "Relative cross-strike edge displacement persisting across spatial scales may indicate a buried structural discontinuity.",
        "named_non_fault_mimic": "Unfaulted lithologic contacts, intrusions and airborne survey/processing artifacts may generate comparable offsets.",
        "holdout_dti": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": None, "withheld_positives": None,
                        "value": None, "ci_95": None, "status": "NOT RUN; no comparable new holdout or calibrated organizer estimate."},
        "leakage_canaries": {"status": "NOT RUN; no lane or model constructed", "features_tested": 0},
        "correlation_overlap_vs_registry": {
            "candidate_surface_spearman": None, "candidate_final_dot_overlap": None,
            "status": "NOT RUN for a new candidate; pre-placement necessary-condition stop.",
            "witness_sha256": lattice["source"]["sha256"], "witness_budget": lattice["budget_example"],
            "witness_uncovered": lattice["uncovered_beyond_3px"], "unavoidable_overlap_fraction": lattice["budget_lower_bound"],
            "scope": "Single registered lattice witness, not full registry."},
        "raster_sha256": None,
        "validator_output": {"status": "NOT RUN: no new candidate raster", "no_nan_inside": None, "values_in_0_1": None,
                             "crs_matches": None, "shape_matches": None, "transform_matches": None,
                             "organizer_acceptance": "unknown"},
        "submission_name": None, "note": "No new candidate or slot selected; do not submit.", "verdict": "negative",
        "experiments_run": 0, "weekly_slots_used": 0,
        "blockers": [
            "No single assigned method paragraph in this prompt.",
            "Literal all-registry overlap rule is necessarily violated for the illustrated champion-sized budget.",
            "No current complete surface/final-dot registry snapshot, same-protocol best, or fold-local holdout in this checkout.",
            "Shared GEMSDOE32 CLI wrappers silently binarize continuous predictions; upstream issue 37 is open.",
            "Organizer-authenticated data and current account quota/receipts are unavailable. Core mirrors and the shared derived feature stack were rebuilt in ignored cache, which may be absent in another checkout."
        ],
        "geometry_audit_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "geometry_audit": "historical-audit.json",
        "official_hidden_score_estimate": None, "slot_selector": "Separate step required; not run."
    }
    if len(card["note"]) > 140:
        raise ValueError("Note exceeds 140 characters")
    output.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(f"Wrote {output}: negative; no new raster, holdout or slot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
