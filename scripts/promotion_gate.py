"""Fail-closed metadata gate. Never replaces canonical pixel/evaluator validation.

A promote result means eligible for a separate selector, not upload permission.
Metadata is not cryptographic proof that its producer ran the claimed checks.
"""
import json
import math
import sys


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def mapping(x):
    return x if isinstance(x, dict) else {}


def text(x):
    return isinstance(x, str) and bool(x.strip())


def digest(x):
    return isinstance(x, str) and len(x) == 64 and all(c in '0123456789abcdef' for c in x)


def interval(x, lower=0, upper=1):
    return (isinstance(x, list) and len(x) == 2 and all(finite(n) for n in x)
            and lower <= x[0] <= x[1] <= upper)


def assess(card):
    reasons = []

    def require(ok, reason):
        if not ok:
            reasons.append(reason)

    require(isinstance(card, dict), 'run card must be a JSON object')
    card = mapping(card)
    require(text(card.get('assigned_lane')), 'missing assigned method lane')
    count = card.get('experiments_run')
    require(type(count) is int and 0 <= count <= 3, 'experiment count missing or over budget')
    elapsed = card.get('experiment_elapsed_seconds')
    require(finite(elapsed) and 0 <= elapsed <= 7200, 'elapsed experiment budget missing or exceeded')
    h = mapping(card.get('holdout'))
    require(h.get('evidence_class') == 'HOLDOUT-DTI' and text(h.get('evaluator_version')),
            'missing versioned HOLDOUT-DTI')
    require(type(h.get('withheld_positives')) is int and h['withheld_positives'] > 0,
            'missing withheld positives')
    score = h.get('dti')
    require(finite(score) and 0 <= score <= 1, 'missing valid holdout DTI')
    ci = h.get('ci95')
    require(interval(ci) and finite(score) and ci[0] <= score <= ci[1],
            'missing valid holdout 95% CI containing point estimate')
    paired = h.get('paired_delta_ci95')
    require(interval(paired, -1, 1) and paired[0] > 0, 'no paired holdout improvement')
    baseline = mapping(h.get('baseline'))
    require(h.get('same_evaluator_current_best') is True
            and text(h.get('evaluator_version'))
            and baseline.get('evaluator_version') == h.get('evaluator_version')
            and digest(h.get('fold_manifest_sha256'))
            and baseline.get('fold_manifest_sha256') == h.get('fold_manifest_sha256')
            and finite(baseline.get('dti')) and 0 <= baseline['dti'] <= 1
            and finite(score) and score > baseline['dti'],
            'current same-evaluator/fold baseline improvement not established')
    auc = card.get('feature_auc')
    require(isinstance(auc, list) and bool(auc)
            and all(finite(x) and 0 <= x <= .90 for x in auc),
            'missing or leaking feature canaries')
    registry = mapping(card.get('registry'))
    ids = registry.get('reference_ids')
    inventory_valid = (isinstance(ids, list) and bool(ids) and all(text(i) for i in ids)
                       and len(set(ids)) == len(ids))
    require(inventory_valid, 'missing nonempty registry inventory')
    for stage in ('surface', 'final_dots'):
        r = mapping(registry.get(stage))
        records = r.get('comparisons')
        records_valid = isinstance(records, list) and bool(records) and all(isinstance(c, dict) for c in records)
        require(r.get('complete') is True and records_valid, f'{stage} uniqueness incomplete')
        if not records_valid:
            continue
        names = [c.get('reference_id') for c in records]
        require(inventory_valid and all(text(n) for n in names) and len(set(names)) == len(names)
                and set(names) == set(ids or []), f'{stage} registry comparison coverage mismatch')
        for c in records:
            rho, overlap = c.get('spearman'), c.get('overlap_3px')
            require(finite(rho) and abs(rho) <= .90 and finite(overlap) and 0 <= overlap <= .70,
                    f'{stage} duplicate or invalid measurement: {c.get("reference_id")}')
    v = mapping(card.get('validator'))
    for key in ('saved_bytes_checked', 'single_band', 'finite_inside', 'range_0_1',
                'crs_match', 'shape_match', 'transform_match'):
        require(v.get(key) is True, f'validator: {key}')
    sha = card.get('raster_sha256')
    require(digest(sha), 'missing raster SHA256')
    require(digest(sha) and v.get('raster_sha256') == sha, 'validator not bound to candidate bytes')
    require(text(card.get('submission_name')) and text(card.get('note')) and len(card['note']) <= 140,
            'invalid submission name/note')
    return {'verdict': 'negative' if reasons else 'promote', 'ok_to_submit': False,
            'selector_required': True, 'reasons': reasons}


def main():
    try:
        with open(sys.argv[1]) as stream:
            card = json.load(stream)
        result = assess(card)
    except (OSError, ValueError, IndexError) as exc:
        result = {'verdict': 'negative', 'ok_to_submit': False, 'selector_required': True,
                  'reasons': [f'Cannot load run card: {exc}']}
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['verdict'] == 'promote' else 2


if __name__ == '__main__':
    raise SystemExit(main())
