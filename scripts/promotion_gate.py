"""Fail-closed evidence screening: literal user protocol, not a slot selector.

Null-calibrated overlaps may be informative diagnostics, but never replace the
literal per-raster 3-pixel overlap limit. Evidence is self-reported; this gate
cannot verify the registry inventory or the authenticity of organizer data.
"""
import json
import math
import sys

LITERAL_KEYS = ('within_3px_fraction', 'literal_5px_calibration_lattice_overlap', 'max_literal_overlap_3px')

# This exact shared implementation has an open truth/visible buffer defect and
# an open zero-truth FP-pooling defect. Copying it exactly is important, but it
# is not an eligible evaluation instrument until fixed in the shared template.
BLOCKED_HOLDOUT_IMPLEMENTATIONS = {
    '9ce9cf359f4d7b7fa844dd8f208ec00c3e6c15afef5d724d9014320b944d318d',
}
PROTOCOL_AUDITS = (
    'whole_fault_segments', 'truth_visible_buffer', 'visible_only_catalogue_features',
    'visible_pixels_masked_exactly', 'zero_truth_false_positives_conserved',
)


def digest(value, length=64):
    return isinstance(value, str) and len(value) == length and all(c in '0123456789abcdef' for c in value)


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def _node_overlap_ok(node):
    """Reject any disclosed literal overlap above the protocol threshold."""
    values = [node[k] for k in LITERAL_KEYS if k in node]
    return all(finite(v) and 0 <= v <= .70 for v in values)


def assess(card):
    reasons = []
    if not isinstance(card, dict):
        return {'verdict': 'negative', 'technically_eligible': False, 'ok_to_submit': False,
                'selector_required': True, 'selector_approval': False, 'slot_used': False,
                'reasons': ['invalid run card']}

    def require(ok, reason):
        if not ok:
            reasons.append(reason)

    def walk(node, path='card'):
        if isinstance(node, dict):
            if not _node_overlap_ok(node):
                require(False, f'{path}: duplicate or invalid literal overlap (limit 0.70)')
            for key, value in node.items():
                walk(value, f'{path}.{key}')
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f'{path}[{i}]')
    walk(card)

    lane = card.get('assigned_lane')
    require(isinstance(lane, str) and bool(lane.strip()), 'missing assigned method lane')
    require(isinstance(card.get('mechanism'), str) and bool(card['mechanism'].strip()), 'missing mechanism')
    require(isinstance(card.get('named_non_fault_mimic'), str) and bool(card['named_non_fault_mimic'].strip()),
            'missing named non-fault mimic')
    h = card.get('holdout') if isinstance(card.get('holdout'), dict) else {}
    require(h.get('evidence_class') == 'HOLDOUT-DTI' and isinstance(h.get('evaluator_version'), str)
            and bool(h['evaluator_version'].strip()), 'missing versioned HOLDOUT-DTI')
    require(type(h.get('withheld_positives')) is int and h['withheld_positives'] > 0, 'missing withheld positives')
    require(finite(h.get('dti')) and 0 <= h['dti'] <= 1, 'missing valid holdout DTI')
    interval = h.get('ci95')
    require(isinstance(interval, list) and len(interval) == 2 and all(finite(x) for x in interval) and finite(h.get('dti'))
            and 0 <= interval[0] <= h['dti'] <= interval[1] <= 1, 'missing valid holdout 95% CI')
    ci = h.get('paired_delta_ci95')
    require(isinstance(ci, list) and len(ci) == 2 and all(finite(x) for x in ci) and 0 < ci[0] <= ci[1] <= 1,
            'no paired holdout improvement')
    implementation = h.get('holdout_implementation_sha256')
    require(digest(h.get('shared_template_commit'), 40) and digest(h.get('evaluator_sha256'))
            and digest(implementation) and implementation not in BLOCKED_HOLDOUT_IMPLEMENTATIONS,
            'shared evaluator provenance missing or implementation has unresolved protocol defects')
    fold_hash = h.get('fold_assignment_sha256')
    protocol = h.get('protocol_audit') if isinstance(h.get('protocol_audit'), dict) else {}
    require(digest(fold_hash) and digest(protocol.get('report_sha256'))
            and all(protocol.get(key) is True for key in PROTOCOL_AUDITS),
            'missing complete fold/buffer/leakage/FP protocol audit')
    baseline = h.get('current_best') if isinstance(h.get('current_best'), dict) else {}
    baseline_ci = baseline.get('ci95')
    baseline_dti = baseline.get('dti')
    baseline_ok = (baseline.get('evidence_class') == 'HOLDOUT-DTI'
                   and baseline.get('evaluator_version') == h.get('evaluator_version')
                   and baseline.get('evaluator_sha256') == h.get('evaluator_sha256')
                   and baseline.get('holdout_implementation_sha256') == implementation
                   and baseline.get('fold_assignment_sha256') == fold_hash
                   and baseline.get('withheld_positives') == h.get('withheld_positives')
                   and finite(baseline_dti) and isinstance(baseline_ci, list) and len(baseline_ci) == 2
                   and all(finite(x) for x in baseline_ci)
                   and 0 <= baseline_ci[0] <= baseline_dti <= baseline_ci[1] <= 1
                   and finite(h.get('dti')) and h['dti'] > baseline_dti)
    require(h.get('same_evaluator_current_best') is True and baseline_ok,
            'current best not evidenced on the same evaluator, implementation, folds and positives')
    auc = card.get('feature_auc')
    require(isinstance(auc, list) and bool(auc) and all(finite(x) and 0 <= x <= 1 and max(x, 1 - x) <= .90 for x in auc),
            'missing or leaking feature canaries')

    registry = card.get('registry') if isinstance(card.get('registry'), dict) else {}
    literal = registry.get('literal_all_rasters_final_passed')
    legacy = card.get('correlation_and_overlap_vs_registry')
    if isinstance(legacy, dict) and legacy.get('literal_all_rasters_final_passed') is False:
        literal = False
    require(literal is True, 'literal all-registry final audit failed or missing')
    # A calibrated comparison field cannot establish compliance with the literal rule.
    calibrated = 'null-calibrated' in str(registry.get('duplicate_rule', '')).lower()
    fd = registry.get('final_dots') if isinstance(registry.get('final_dots'), dict) else {}
    if 'max_literal_overlap_3px' in fd:
        require(finite(fd['max_literal_overlap_3px']) and 0 <= fd['max_literal_overlap_3px'] <= .70,
                'literal final overlap exceeds 0.70 or is invalid')
    inventory = registry.get('inventory_sha256')
    inventory_ok = (isinstance(inventory, list) and bool(inventory)
                    and all(isinstance(x, str) and len(x) == 64 and all(c in '0123456789abcdef' for c in x) for x in inventory)
                    and len(set(inventory)) == len(inventory))
    manifest = registry.get('manifest_sha256')
    manifest_ok = isinstance(manifest, str) and len(manifest) == 64 and all(c in '0123456789abcdef' for c in manifest)
    require(inventory_ok and manifest_ok, 'missing nonempty unique registry inventory or manifest digest')
    for stage in ('surface', 'final_dots'):
        r = registry.get(stage) if isinstance(registry.get(stage), dict) else {}
        comparisons = r.get('comparisons')
        rows_ok = isinstance(comparisons, list) and all(isinstance(x, dict) for x in comparisons)
        if rows_ok:
            ids = [x.get('sha256') for x in comparisons]
            rows_ok = (inventory_ok and all(isinstance(x, str) for x in ids)
                       and len(ids) == len(inventory) and len(set(ids)) == len(ids)
                       and set(ids) == set(inventory)
                       and all(finite(x.get('abs_spearman')) and 0 <= x['abs_spearman'] <= .90
                               and finite(x.get('literal_overlap_3px' if calibrated else 'overlap_3px'))
                               and 0 <= x['literal_overlap_3px' if calibrated else 'overlap_3px'] <= .70
                               for x in comparisons))
        surface_ok = (rows_ok and finite(r.get('max_abs_spearman'))
                      and 0 <= r['max_abs_spearman'] <= .90
                      and r['max_abs_spearman'] == max(x['abs_spearman'] for x in comparisons))
        final_ok = (rows_ok and finite(r.get('max_overlap_3px'))
                    and 0 <= r['max_overlap_3px'] <= .70
                    and r['max_overlap_3px'] == max(x['literal_overlap_3px' if calibrated else 'overlap_3px'] for x in comparisons))
        require(r.get('complete') is True and surface_ok and final_ok, f'{stage} uniqueness incomplete or duplicate')
    require(not card.get('release_review'), 'superseded release evidence; rerun literal registry checks')
    v = card.get('validator') if isinstance(card.get('validator'), dict) else {}
    for key in ('saved_bytes_checked', 'geotiff', 'single_band', 'float32', 'finite_inside', 'inside_unmasked',
                'self_contained_tiff', 'range_0_1', 'whole_array_finite_range', 'outside_policy_checked',
                'crs_match', 'shape_match', 'transform_match'):
        require(v.get(key) is True, f'validator: {key}')
    sha = card.get('raster_sha256')
    require(isinstance(sha, str) and len(sha) == 64 and all(c in '0123456789abcdef' for c in sha), 'missing raster SHA256')
    require(v.get('raster_sha256') == sha and isinstance(sha, str), 'validator not bound to candidate bytes')
    require(bool(card.get('submission_name')) and isinstance(card.get('note'), str) and 0 < len(card['note']) <= 140,
            'invalid submission name/note')
    verdict = 'negative' if reasons else 'promote'
    # This is a self-reported technical screen, never the independent selector.
    # Neither a card field nor a CLI caller may turn this result into slot approval.
    return {'verdict': verdict, 'technically_eligible': verdict == 'promote',
            'ok_to_submit': False, 'selector_required': True, 'selector_approval': False,
            'slot_used': False, 'reasons': reasons}


if __name__ == '__main__':
    result = assess(json.load(open(sys.argv[1])))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['verdict'] == 'promote' else 2)
