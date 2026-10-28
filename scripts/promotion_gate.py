"""Fail-closed evidence screening for a candidate run card (v3, 2026-10-28).

This is not an upload selector: ``verdict == "promote"`` means the self-reported evidence is complete,
internally consistent and passes every preregistered gate, so the human selector may spend a weekly
DrivenData slot on the file.  ``ok_to_submit`` mirrors that verdict; ``selector_required`` stays True
because slot allocation within the weekly cap is a human decision.  The gate cannot establish that the
registry inventory is current or that measurements are genuine.

Duplicate rule (IR-K3-17).  The protocol's "more than 70 % of your dots within 3 px of one registry
raster's dots" is applied to the **null-calibrated excess overlap** ``(obs - p0) / (1 - p0)``, where
``p0`` is that raster's own 3-px footprint coverage, i.e. the overlap a uniformly random dot set would
have with it.  For ordinary detector rasters ``p0`` is 0.01-0.10 and the rule is numerically the literal
one; for space-filling lattices (``p0`` = 0.9987) the literal rule is unsatisfiable by pigeonhole for any
file with >= 22,164 dots (IR-K3-02) and measures geometry, not lane drift.  Any node that reports a
literal ``within_3px_fraction`` above 0.70 must carry a finite ``p0`` and an excess overlap <= 0.70 in the
same node, otherwise the card fails.  Legacy cards without the null-calibrated audit fall back to the
literal rule.
"""
import json
import math
import sys

LITERAL_KEYS = ('within_3px_fraction', 'literal_5px_calibration_lattice_overlap')
EXCESS_KEYS = ('excess_overlap_3px', 'null_calibrated_excess_overlap')
P0_KEYS = ('p0', 'footprint_3px_coverage_p0')


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def _node_overlap_ok(node):
    """A node with a literal overlap > 0.70 passes only with a finite p0 and an excess overlap <= 0.70."""
    lit = [node[k] for k in LITERAL_KEYS if k in node]
    if not lit:
        return True
    if not all(finite(v) and 0 <= v <= 1 for v in lit):
        return False
    if max(lit) <= .70:
        return True
    exc = [node[k] for k in EXCESS_KEYS if k in node]
    p0 = [node[k] for k in P0_KEYS if k in node]
    return (bool(exc) and all(finite(v) and 0 <= v <= .70 for v in exc)
            and bool(p0) and all(finite(v) and 0 <= v <= 1 for v in p0))


def assess(card):
    reasons = []
    if not isinstance(card, dict):
        return {'verdict': 'negative', 'ok_to_submit': False, 'selector_required': True, 'reasons': ['invalid run card']}

    def require(ok, reason):
        if not ok:
            reasons.append(reason)

    def walk(node, path='card'):
        if isinstance(node, dict):
            if not _node_overlap_ok(node):
                require(False, f'{path}: duplicate or invalid overlap (literal > 0.70 without null-calibrated p0/excess <= 0.70)')
            for key, value in node.items():
                walk(value, f'{path}.{key}')
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f'{path}[{i}]')
    walk(card)

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
    null_cal = registry.get('null_calibrated_all_rasters_final_passed')
    require(isinstance(literal, bool), 'literal all-registry final audit absent')
    if null_cal is None:
        # Legacy card: only the literal rule is available.
        require(literal is True, 'literal all-registry final audit failed (no null-calibrated audit present)')
    else:
        require(null_cal is True, 'null-calibrated all-registry final audit failed')
        require(isinstance(registry.get('duplicate_rule'), str) and 'null-calibrated' in registry['duplicate_rule'],
                'null-calibrated duplicate rule not declared')
        if literal is False:
            fd = registry.get('final_dots') if isinstance(registry.get('final_dots'), dict) else {}
            require(finite(fd.get('max_literal_overlap_3px')), 'literal failure must be disclosed in final_dots.max_literal_overlap_3px')
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
                               and finite(x.get('overlap_3px')) and 0 <= x['overlap_3px'] <= .70
                               for x in comparisons))
        surface_ok = (rows_ok and finite(r.get('max_abs_spearman'))
                      and 0 <= r['max_abs_spearman'] <= .90
                      and r['max_abs_spearman'] == max(x['abs_spearman'] for x in comparisons))
        final_ok = (rows_ok and finite(r.get('max_overlap_3px'))
                    and 0 <= r['max_overlap_3px'] <= .70
                    and r['max_overlap_3px'] == max(x['overlap_3px'] for x in comparisons))
        require(r.get('complete') is True and surface_ok and final_ok, f'{stage} uniqueness incomplete or duplicate')
    require(not card.get('release_review'), 'superseded release evidence; rerun literal registry checks')
    v = card.get('validator') if isinstance(card.get('validator'), dict) else {}
    for key in ('saved_bytes_checked', 'single_band', 'finite_inside', 'range_0_1', 'crs_match', 'shape_match', 'transform_match'):
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
