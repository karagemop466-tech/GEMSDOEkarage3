"""Fail-closed evidence screening for a candidate run card (v3, 2026-10-28).

This is not an upload selector: ``verdict == "promote"`` means the self-reported evidence is complete,
internally consistent and passes every preregistered gate, so the human selector may spend a weekly
DrivenData slot on the file.  ``ok_to_submit`` mirrors that verdict; ``selector_required`` stays True
because slot allocation within the weekly cap is a human decision.  The gate cannot establish that the
registry inventory is current or that measurements are genuine.

Duplicate rule (user's active parallel-run protocol): use the literal raw fraction. If more than 70% of
candidate dots lie within 3 px of any registry raster's dots, the candidate fails, regardless of that
raster's coverage, identity, density, or null expectation. Null-calibrated excess overlap may be recorded
as supplementary analysis but never rescues a literal failure. This is intentionally strict: a dense
lattice can make some dot budgets impossible, which is a pre-placement stop rather than permission to
relax or game the rule. Check surface rank-correlation and final-dot overlap against every available
registry reference; an incomplete inventory is not evidence of uniqueness.
"""
import json
import math
import sys

# Only explicit 3-pixel raw overlaps implement the active stop rule. A 5-pixel
# lattice diagnostic is useful evidence, but cannot itself reject or clear a file.
LITERAL_KEYS = ('within_3px_fraction', 'literal_overlap_3px', 'max_literal_overlap_3px')


def _literal_overlap(row, calibrated_claim: bool):
    """Return a 3-px raw overlap; never substitute a null-calibrated excess."""
    for key in ('literal_overlap_3px', 'within_3px_fraction'):
        if key in row:
            return row[key]
    if not calibrated_claim and 'overlap_3px' in row:
        return row['overlap_3px']
    return None


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def _node_overlap_ok(node):
    """Every reported raw overlap is governed by the literal 70% threshold."""
    lit = [node[k] for k in LITERAL_KEYS if k in node]
    return all(finite(v) and 0 <= v <= .70 for v in lit)


def assess(card):
    reasons = []
    if not isinstance(card, dict):
        return {'verdict': 'negative', 'ok_to_submit': False, 'selector_required': True, 'reasons': ['invalid run card']}

    def require(ok, reason):
        if not ok:
            reasons.append(reason)

    overlap_failures = []

    def walk(node, path='card'):
        if isinstance(node, dict):
            if not _node_overlap_ok(node):
                overlap_failures.append(path)
            for key, value in node.items():
                walk(value, f'{path}.{key}')
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f'{path}[{i}]')
    walk(card)
    if overlap_failures:
        examples = ', '.join(overlap_failures[:3])
        suffix = f' (+{len(overlap_failures) - 3} more)' if len(overlap_failures) > 3 else ''
        reasons.append(f'literal raw overlap exceeds 0.70 or is invalid at {len(overlap_failures)} locations: {examples}{suffix}')

    require(bool(card.get('assigned_lane')), 'missing assigned method lane')
    h = card.get('holdout') if isinstance(card.get('holdout'), dict) else {}
    require(h.get('evidence_class') == 'HOLDOUT-DTI' and bool(h.get('evaluator_version')), 'missing versioned HOLDOUT-DTI')
    require(type(h.get('withheld_positives')) is int and h['withheld_positives'] > 0, 'missing withheld positives')
    require(finite(h.get('dti')) and 0 <= h['dti'] <= 1, 'missing valid holdout DTI')
    interval = h.get('ci95')
    require(isinstance(interval, list) and len(interval) == 2 and all(finite(x) for x in interval) and finite(h.get('dti'))
            and 0 <= interval[0] <= h['dti'] <= interval[1] <= 1, 'missing valid holdout 95% CI')
    ci = h.get('paired_delta_ci95')
    require(isinstance(ci, list) and len(ci) == 2 and all(finite(x) for x in ci) and 0 < ci[0] <= ci[1], 'no paired holdout improvement')
    require(h.get('same_evaluator_current_best') is True, 'current same-evaluator baseline not established')
    auc = card.get('feature_auc')
    require(isinstance(auc, list) and bool(auc) and all(finite(x) and 0 <= x <= 1 and max(x, 1 - x) <= .90 for x in auc),
            'missing or leaking feature canaries')

    registry = card.get('registry') if isinstance(card.get('registry'), dict) else {}
    literal = registry.get('literal_all_rasters_final_passed')
    legacy = card.get('correlation_and_overlap_vs_registry')
    if isinstance(legacy, dict) and legacy.get('literal_all_rasters_final_passed') is False:
        literal = False
    require(literal is True, 'literal all-registry final audit failed; null-calibration cannot waive the 70% stop')
    inventory = registry.get('inventory_sha256')
    inventory_ok = (isinstance(inventory, list) and bool(inventory)
                    and all(isinstance(x, str) and len(x) == 64 and all(c in '0123456789abcdef' for c in x) for x in inventory)
                    and len(set(inventory)) == len(inventory))
    manifest = registry.get('manifest_sha256')
    manifest_ok = isinstance(manifest, str) and len(manifest) == 64 and all(c in '0123456789abcdef' for c in manifest)
    require(inventory_ok and manifest_ok, 'missing nonempty unique registry inventory or manifest digest')
    calibrated_claim = 'null-calibrated' in str(registry.get('duplicate_rule', '')).lower()
    for stage in ('surface', 'final_dots'):
        r = registry.get(stage) if isinstance(registry.get(stage), dict) else {}
        comparisons = r.get('comparisons')
        rows_ok = isinstance(comparisons, list) and bool(comparisons) and all(isinstance(x, dict) for x in comparisons)
        if rows_ok:
            ids = [x.get('sha256') for x in comparisons]
            rows_ok = (inventory_ok and all(isinstance(x, str) for x in ids)
                       and len(ids) == len(inventory) and len(set(ids)) == len(ids)
                       and set(ids) == set(inventory))
        raw_values = [_literal_overlap(row, calibrated_claim) for row in comparisons] if rows_ok else []
        raw_ok = (bool(raw_values) and all(finite(x) and 0 <= x <= .70 for x in raw_values)
                  and finite(r.get('max_literal_overlap_3px'))
                  and r.get('max_literal_overlap_3px') <= .70
                  and r.get('max_literal_overlap_3px') == max(raw_values))
        correlations = [x.get('abs_spearman') for x in comparisons] if rows_ok else []
        correlation_ok = (bool(correlations) and all(finite(x) and 0 <= x <= .90 for x in correlations)
                          and finite(r.get('max_abs_spearman'))
                          and r.get('max_abs_spearman') <= .90
                          and r.get('max_abs_spearman') == max(correlations))
        require(r.get('complete') is True and rows_ok and raw_ok and correlation_ok,
                f'{stage} literal overlap / correlation comparison incomplete, inconsistent, or above threshold')
    require(not card.get('release_review'), 'superseded release evidence; rerun literal registry checks')
    v = card.get('validator') if isinstance(card.get('validator'), dict) else {}
    for key in ('saved_bytes_checked', 'single_band', 'finite_inside', 'range_0_1', 'whole_array_finite_range', 'crs_match', 'shape_match', 'transform_match'):
        require(v.get(key) is True, f'validator: {key}')
    sha = card.get('raster_sha256')
    require(isinstance(sha, str) and len(sha) == 64 and all(c in '0123456789abcdef' for c in sha), 'missing raster SHA256')
    require(v.get('raster_sha256') == sha and isinstance(sha, str), 'validator not bound to candidate bytes')
    require(bool(card.get('submission_name')) and isinstance(card.get('note'), str) and 0 < len(card['note']) <= 140,
            'invalid submission name/note')
    verdict = 'negative' if reasons else 'promote'
    return {'verdict': verdict, 'ok_to_submit': verdict == 'promote', 'selector_required': True, 'reasons': reasons}


if __name__ == '__main__':
    result = assess(json.load(open(sys.argv[1])))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['verdict'] == 'promote' else 2)
