"""Fail-closed evidence screening, not an upload selector or an evaluator.

The caller supplies measurements; this function checks their internal consistency,
not their provenance. In particular, the registry inventory must itself be independently
verified as complete and current before the separate selector can act.
"""
import json
import math
import sys


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def assess(card):
    if not isinstance(card, dict):
        return {'verdict': 'negative', 'ok_to_submit': False, 'selector_required': True,
                'reasons': ['invalid run card']}
    reasons = []

    def require(ok, reason):
        if not ok:
            reasons.append(reason)

    require(isinstance(card.get('assigned_lane'), str) and bool(card['assigned_lane'].strip()), 'missing assigned method lane')
    h = card.get('holdout') if isinstance(card.get('holdout'), dict) else {}
    require(h.get('evidence_class') == 'HOLDOUT-DTI' and bool(h.get('evaluator_version')), 'missing versioned HOLDOUT-DTI')
    require(type(h.get('withheld_positives')) is int and h['withheld_positives'] > 0, 'missing withheld positives')
    dti = h.get('dti')
    require(finite(dti) and 0 <= dti <= 1, 'missing valid holdout DTI')
    interval = h.get('ci95')
    require(isinstance(interval, list) and len(interval) == 2 and all(finite(x) for x in interval)
            and finite(dti) and 0 <= interval[0] <= dti <= interval[1] <= 1,
            'missing valid holdout 95% CI containing point estimate')
    ci = h.get('paired_delta_ci95')
    require(isinstance(ci, list) and len(ci) == 2 and all(finite(x) for x in ci)
            and 0 < ci[0] <= ci[1] <= 1, 'no paired holdout improvement')
    require(h.get('same_evaluator_current_best') is True, 'current same-evaluator baseline not established')
    auc = card.get('feature_auc')
    require(isinstance(auc, list) and bool(auc) and all(finite(x) and 0 <= x <= .90 for x in auc), 'missing or leaking feature canaries')
    registry = card.get('registry') if isinstance(card.get('registry'), dict) else {}
    inventory = registry.get('inventory')
    inventory_ok = (isinstance(inventory, list) and len(inventory) > 0
                    and all(digest(x) for x in inventory) and len(set(inventory)) == len(inventory))
    require(inventory_ok and digest(registry.get('manifest_sha256')), 'missing nonempty pinned registry inventory')
    for stage in ('surface', 'final_dots'):
        r = registry.get(stage) if isinstance(registry.get(stage), dict) else {}
        rows = r.get('comparisons')
        valid_rows = (inventory_ok and isinstance(rows, list) and len(rows) == len(inventory)
                      and all(isinstance(x, dict) and digest(x.get('sha256'))
                              and finite(x.get('abs_spearman')) and 0 <= x['abs_spearman'] <= .90
                              and finite(x.get('overlap_3px')) and 0 <= x['overlap_3px'] <= .70
                              for x in rows)
                      and {x['sha256'] for x in rows} == set(inventory))
        require(r.get('complete') is True and valid_rows, f'{stage} uniqueness incomplete or duplicate')
    v = card.get('validator') if isinstance(card.get('validator'), dict) else {}
    for key in ('saved_bytes_checked', 'single_band', 'finite_inside', 'range_0_1', 'crs_match', 'shape_match', 'transform_match'):
        require(v.get(key) is True, f'validator: {key}')
    sha = card.get('raster_sha256')
    require(digest(sha), 'missing raster SHA256')
    require(digest(sha) and v.get('sha256') == sha, 'validator not bound to candidate bytes')
    name, note = card.get('submission_name'), card.get('note')
    require(isinstance(name, str) and bool(name.strip()) and isinstance(note, str) and 0 < len(note) <= 140, 'invalid submission name/note')
    return {'verdict': 'negative' if reasons else 'promote', 'ok_to_submit': False,
            'selector_required': True, 'reasons': reasons}


if __name__ == '__main__':
    with open(sys.argv[1]) as fh:
        result = assess(json.load(fh))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['verdict'] == 'promote' else 2)
