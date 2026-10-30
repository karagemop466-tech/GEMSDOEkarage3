#!/usr/bin/env python3
"""Publish the deterministic zero-experiment negative card for this audit.

This command cannot authorize a TIFF or overwrite a non-preflight scientific
run. It uses the independently saved byte-audit timestamp; rebuilding does not
pretend that the audit was performed again.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    output = ROOT / 'docs/data/current-run.json'
    if output.exists():
        prior = json.loads(output.read_text())
        if not (str(prior.get('run_id', '')).startswith('gems-karage3-preflight-')
                and prior.get('verdict') == 'negative' and prior.get('experiments_run') == 0
                and prior.get('weekly_slots_used') == 0 and prior.get('raster_sha256') is None
                and prior.get('holdout_dti', {}).get('value') is None):
            raise ValueError('Refusing to overwrite a non-preflight or nonempty run card')
    path = ROOT / 'docs/data/historical-audit.json'
    history = json.loads(path.read_text())
    if (history.get('kind') != 'GEOMETRY-AUDIT, NOT A SCORE' or not history.get('no_new_experiment')
            or history.get('manifest_sha256') != digest(ROOT / 'data/focus_registry.json')):
        raise ValueError('Historical audit missing, invalid or mismatched to pinned focus manifest')
    evidence = ROOT / 'evidence/saved-tiffs-literal-20261030.json'
    audit = json.loads(evidence.read_text())
    rasters = audit['rasters']
    expected = {str(p.relative_to(ROOT)) for p in (ROOT / 'docs').rglob('*.tif')}
    if ({r['file'] for r in rasters} != expected or not rasters
            or any(digest(ROOT / r['file']) != r['sha256'] or not (r['duplicate_stop'] or r['boundary_gaming_refusal']) for r in rasters)):
        raise ValueError('Saved TIFF audit is stale, incomplete or no longer proves the duplicate stops')
    lat = history['lattice']
    if not lat['budget_lower_bound'] > .7:
        raise ValueError('Required lattice duplicate-stop evidence is absent')
    card = {
        'schema_version': 1,
        'run_id': 'gems-karage3-preflight-20261028-afbdab50',
        'created_utc': audit['checked_utc'],
        'assigned_lane': None,
        'hypothesis': 'Proposed only: multiscale paired potential-field fabric displacement across a buried boundary; no method assigned or tested.',
        'mechanism': 'A persistent cross-boundary displacement of corresponding gravity and magnetic textures may indicate offset basement fabric beneath cover.',
        'named_non_fault_mimic': 'Intrusions or unfaulted lithological contacts can produce similar textures; survey-line artefacts can generate false edges.',
        'holdout_dti': {'evidence_class': 'HOLDOUT-DTI', 'evaluator_version': None,
                        'withheld_positives': None, 'value': None, 'ci_95': None,
                        'status': 'NOT RUN; no new candidate or valid same-protocol comparison.'},
        'leakage_canaries': {'status': 'NOT RUN; no assigned lane or new model', 'features_tested': 0},
        'correlation_overlap_vs_registry': {
            'candidate_surface_spearman': None, 'candidate_surface_overlap': None,
            'candidate_final_spearman': None, 'candidate_final_dot_overlap': None,
            'status': 'NOT RUN for a new candidate. Single-witness proof stops the historical budget; full current registry was not checked.',
            'witness_sha256': lat['source']['sha256'], 'witness_budget': lat['budget_example'],
            'witness_uncovered': lat['uncovered_beyond_3px'], 'unavoidable_overlap_fraction': lat['budget_lower_bound'],
            'scope': 'One registered lattice witness; a duplicate proof, not a complete registry scan.'},
        'raster_sha256': None,
        'validator_output': {'status': 'NOT RUN: no new candidate raster', 'no_nan_inside': None,
                             'values_in_0_1': None, 'crs_matches': None, 'shape_matches': None,
                             'transform_matches': None, 'outside_null_or_nan': None, 'organizer_acceptance': 'unknown'},
        'submission_name': None, 'note': 'No new candidate or slot selected; do not submit.',
        'verdict': 'negative', 'ok_to_submit': False, 'experiments_run': 0,
        'slot_selected': False, 'weekly_slots_used': 0,
        'blockers': [
            'No unambiguous single assigned method paragraph in the supplied prompt.',
            'Literal any-registry rule proves a duplicate at 37,654 dots; lower budgets are not automatically unique.',
            'No current complete surface/final registry snapshot or validated same-protocol current-best comparison.',
            'Pinned shared evaluator/writer explicitly reject non-binary inputs; holdout, surface-gate and masked-pixel validator defects remain open (#60, #41, #61, #42, #66). Read-only upstream access prevents a central fix.',
            'Organizer-authenticated inputs, matched derived feature cache, quota and artifact-linked receipts are unavailable. Owner-mirrored core rasters and raw bands were restored but do not authenticate organizer provenance; portal behavior is unverified.'
        ],
        'geometry_audit_sha256': digest(path), 'geometry_audit': 'historical-audit.json',
        'saved_tiffs_audit_sha256': digest(evidence), 'saved_tiffs_audit': 'saved-tiffs-literal-20261030.json',
        'official_hidden_score_estimate': None, 'slot_selector': 'Separate step required; not run.'
    }
    if len(card['note']) > 140:
        raise ValueError('Note exceeds 140 characters')
    text = json.dumps(card, indent=2, allow_nan=False) + '\n'
    output.write_text(text)
    (ROOT / 'evidence/run-card-20261028-afbdab50.json').write_text(text)
    print('Wrote current negative card; no new raster, experiment or slot.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
