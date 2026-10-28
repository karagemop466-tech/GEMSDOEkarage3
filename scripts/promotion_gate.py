"""Fail-closed screen of a run card; never allocates a DrivenData slot.

Rule 1 is literal at *both* stages: correlation > 0.90 or more than 70% of
candidate-support pixels within 3 px of any registered raster stops the run.
This screen also conservatively rejects strong anticorrelation (|rho| > 0.90).
Lattices and dense rasters are not exempt. Null-calibrated overlap is an extra
diagnostic, never a substitute for literal overlap.

This screen checks the integrity of the card's claims, not the truth or
freshness of those claims. The selector must independently bind the recorded
measurements to saved raster bytes, a complete frozen registry, and a matched
holdout before considering a real weekly slot.
"""
from __future__ import annotations

import json
import math
import sys

# Only literal 3-pixel fields implement the user's stop rule. An unrelated
# 5-pixel calibration metric neither proves compliance nor triggers this stop.
LITERAL_KEYS = ('within_3px_fraction', 'literal_overlap_3px', 'max_literal_overlap_3px')
OVERLAP_METRIC = 'literal-directional-fraction-within-3px'
# A required member of the known frozen registry, not proof of completeness.
KNOWN_WITNESS_SHA256 = 'b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2'
# This exact shared implementation has open truth/visible buffer and zero-truth
# FP-pooling defects. A byte-identical copy is provenance, not correctness.
BLOCKED_HOLDOUT_IMPLEMENTATIONS = {
    '9ce9cf359f4d7b7fa844dd8f208ec00c3e6c15afef5d724d9014320b944d318d',
}
PROTOCOL_AUDITS = (
    'whole_fault_segments', 'truth_visible_buffer', 'visible_only_catalogue_features',
    'visible_pixels_masked_exactly', 'zero_truth_false_positives_conserved',
)


def is_commit(value):
    return isinstance(value, str) and len(value) == 40 and all(c in '0123456789abcdef' for c in value)


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def is_sha256(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in '0123456789abcdef' for c in value))


def assess(card):
    reasons = []
    if not isinstance(card, dict):
        return {'verdict': 'negative', 'ok_to_submit': False, 'eligible_for_selector': False,
                'technically_eligible': False, 'selector_required': True, 'selector_approval': False,
                'slot_used': False, 'reasons': ['invalid run card']}

    def require(ok, reason):
        if not ok:
            reasons.append(reason)

    literal_issues = []

    def walk(node, path='card'):
        # A disclosed violation anywhere cannot be waived by a p0/excess field.
        if isinstance(node, dict):
            for key, value in node.items():
                if key in LITERAL_KEYS and (not finite(value) or not 0 <= value <= .70):
                    literal_issues.append(f'{path}.{key}')
                else:
                    walk(value, f'{path}.{key}')
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f'{path}[{i}]')
    walk(card)
    if literal_issues:
        reasons.append(f'{len(literal_issues)} literal overlap value(s) missing, invalid or above 0.70; first: {literal_issues[0]}')

    for key in ('assigned_lane', 'hypothesis', 'mechanism', 'named_non_fault_mimic'):
        require(isinstance(card.get(key), str) and bool(card[key].strip()), f'missing {key}')
    require(type(card.get('experiments_run')) is int and 1 <= card['experiments_run'] <= 3
            and finite(card.get('elapsed_seconds')) and 0 <= card['elapsed_seconds'] <= 7200,
            'experiment count or time budget missing/exceeded')
    h = card.get('holdout') if isinstance(card.get('holdout'), dict) else {}
    require(h.get('evidence_class') == 'HOLDOUT-DTI' and isinstance(h.get('evaluator_version'), str)
            and bool(h['evaluator_version'].strip()), 'missing versioned HOLDOUT-DTI')
    require(type(h.get('withheld_positives')) is int and h['withheld_positives'] > 0, 'missing withheld positives')
    require(finite(h.get('dti')) and 0 <= h['dti'] <= 1, 'missing valid holdout DTI')
    interval = h.get('ci95')
    require(isinstance(interval, list) and len(interval) == 2 and all(finite(x) for x in interval)
            and finite(h.get('dti')) and 0 <= interval[0] <= h['dti'] <= interval[1] <= 1,
            'missing valid holdout 95% CI')
    ci = h.get('paired_delta_ci95')
    require(isinstance(ci, list) and len(ci) == 2 and all(finite(x) for x in ci)
            and 0 < ci[0] <= ci[1] <= 1, 'no paired holdout improvement')
    require(h.get('same_evaluator_current_best') is True and finite(h.get('current_best_dti'))
            and finite(h.get('dti')) and 0 <= h['current_best_dti'] < h['dti'],
            'current same-evaluator baseline not established or not beaten')
    implementation = h.get('holdout_implementation_sha256')
    require(is_commit(h.get('shared_template_commit')) and is_sha256(h.get('evaluator_sha256'))
            and is_sha256(implementation) and implementation not in BLOCKED_HOLDOUT_IMPLEMENTATIONS,
            'shared evaluator provenance missing or implementation has unresolved protocol defects')
    fold_hash = h.get('fold_assignment_sha256')
    protocol = h.get('protocol_audit') if isinstance(h.get('protocol_audit'), dict) else {}
    require(is_sha256(fold_hash) and is_sha256(protocol.get('report_sha256'))
            and all(protocol.get(key) is True for key in PROTOCOL_AUDITS),
            'missing complete fold/buffer/leakage/FP protocol audit')
    baseline = h.get('current_best') if isinstance(h.get('current_best'), dict) else {}
    baseline_ci, baseline_dti = baseline.get('ci95'), baseline.get('dti')
    baseline_ok = (baseline.get('evidence_class') == 'HOLDOUT-DTI'
                   and baseline.get('evaluator_version') == h.get('evaluator_version')
                   and baseline.get('evaluator_sha256') == h.get('evaluator_sha256')
                   and baseline.get('holdout_implementation_sha256') == implementation
                   and baseline.get('fold_assignment_sha256') == fold_hash
                   and baseline.get('withheld_positives') == h.get('withheld_positives')
                   and finite(baseline_dti) and baseline_dti == h.get('current_best_dti')
                   and isinstance(baseline_ci, list) and len(baseline_ci) == 2
                   and all(finite(x) for x in baseline_ci)
                   and 0 <= baseline_ci[0] <= baseline_dti <= baseline_ci[1] <= 1
                   and finite(h.get('dti')) and h['dti'] > baseline_dti)
    require(baseline_ok, 'current best not evidenced on the same evaluator, implementation, folds and positives')
    require(h.get('withheld_unit') == 'whole-fault-segment' and finite(h.get('buffer_m'))
            and h['buffer_m'] > 0 and h.get('catalogue_features_visible_only') is True
            and h.get('visible_faults_masked_pixel_exactly') is True and h.get('predictions_fold_local') is True,
            'whole-segment buffered fold-local visible-only holdout not established')
    require(h.get('pooled') is True and h.get('alpha') == .2 and h.get('beta') == .8
            and h.get('radius_m') == 300 and h.get('kernel') == 'triangular',
            'pooled official DTI parameters not established')
    auc, names = card.get('feature_auc'), card.get('feature_names')
    require(isinstance(names, list) and bool(names)
            and all(isinstance(x, str) and bool(x.strip()) for x in names)
            and len(set(names)) == len(names) and isinstance(auc, list) and len(auc) == len(names)
            and all(finite(x) and 0 <= x <= 1 and max(x, 1 - x) <= .90 for x in auc),
            'missing or leaking per-feature canaries')

    registry = card.get('registry') if isinstance(card.get('registry'), dict) else {}
    # A card describing the primary rule as calibrated is ambiguous even if it
    # also contains a field labelled literal. It needs a fresh literal audit.
    require('null-calibrated' not in str(registry.get('duplicate_rule', '')).lower(),
            'calibrated primary duplicate rule cannot establish literal compliance')
    require(registry.get('literal_all_rasters_final_passed') is True,
            'literal all-registry final audit absent or failed')
    legacy = card.get('correlation_and_overlap_vs_registry')
    if isinstance(legacy, dict) and legacy.get('literal_all_rasters_final_passed') is False:
        require(False, 'legacy literal all-registry final audit failed')
    inventory = registry.get('inventory_sha256')
    inventory_ok = (isinstance(inventory, list) and bool(inventory)
                    and all(is_sha256(x) for x in inventory) and len(set(inventory)) == len(inventory)
                    and KNOWN_WITNESS_SHA256 in inventory)
    require(inventory_ok and is_sha256(registry.get('manifest_sha256')),
            'missing nonempty unique registry inventory or manifest digest')
    for stage in ('surface', 'final_dots'):
        r = registry.get(stage) if isinstance(registry.get(stage), dict) else {}
        comparisons = r.get('comparisons')
        rows_ok = isinstance(comparisons, list) and bool(comparisons) and all(isinstance(x, dict) for x in comparisons)
        if rows_ok:
            ids = [x.get('sha256') for x in comparisons]
            rows_ok = (inventory_ok and all(is_sha256(x) for x in ids)
                       and len(ids) == len(inventory) and len(set(ids)) == len(ids)
                       and set(ids) == set(inventory)
                       and all(finite(x.get('abs_spearman')) and 0 <= x['abs_spearman'] <= .90
                               and finite(x.get('overlap_3px')) and 0 <= x['overlap_3px'] <= .70
                               and ('literal_overlap_3px' not in x or x['literal_overlap_3px'] == x['overlap_3px'])
                               for x in comparisons))
        metrics_ok = (r.get('overlap_metric') == OVERLAP_METRIC
                      and type(r.get('support_count')) is int and r['support_count'] > 0
                      and isinstance(r.get('support_definition'), str) and bool(r['support_definition'].strip())
                      and is_sha256(r.get('support_sha256')) and is_sha256(r.get('surface_sha256'))
                      and (stage != 'final_dots' or r.get('candidate_raster_sha256') == card.get('raster_sha256')))
        extrema_ok = (rows_ok and finite(r.get('max_abs_spearman')) and finite(r.get('max_overlap_3px'))
                      and r['max_abs_spearman'] == max(x['abs_spearman'] for x in comparisons)
                      and r['max_overlap_3px'] == max(x['overlap_3px'] for x in comparisons))
        require(r.get('complete') is True and metrics_ok and extrema_ok,
                f'{stage} literal uniqueness incomplete or duplicate')
    require(not card.get('release_review'), 'superseded release evidence; rerun literal registry checks')
    v = card.get('validator') if isinstance(card.get('validator'), dict) else {}
    for key in ('saved_bytes_checked', 'geotiff', 'single_band', 'dtype_float32', 'finite_inside',
                'inside_unmasked', 'self_contained_tiff', 'range_0_1', 'whole_array_finite_range',
                'outside_policy_checked', 'outside_null_or_nan', 'crs_match', 'shape_match', 'transform_match'):
        require(v.get(key) is True, f'validator: {key}')
    sha = card.get('raster_sha256')
    require(is_sha256(sha), 'missing raster SHA256')
    require(is_sha256(sha) and v.get('raster_sha256') == sha, 'validator not bound to candidate bytes')
    name = card.get('submission_name')
    require(isinstance(name, str) and name.endswith('.tif') and bool(name.strip())
            and '/' not in name and '\\' not in name and '\x00' not in name
            and isinstance(card.get('note'), str) and 0 < len(card['note']) <= 140,
            'invalid submission name/note')
    verdict = 'negative' if reasons else 'promote'
    # This is an evidence screen, not the separately required slot selector.
    # Even a complete-looking card must not itself authorize an upload.
    return {'verdict': verdict, 'ok_to_submit': False, 'eligible_for_selector': verdict == 'promote',
            'technically_eligible': verdict == 'promote', 'selector_required': True,
            'selector_approval': False, 'slot_used': False, 'reasons': reasons}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as stream:
        result = assess(json.load(stream))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['verdict'] == 'promote' else 2)
