"""Fail-closed candidate evidence gate. Does not select or submit a weekly slot.

The CLI independently reopens the candidate and reference with validate_geotiff.py; it
cannot independently authenticate an organizer template, or prove a producer's holdout
and registry receipts. Those fields are explicit prerequisites, not self-proving facts.
No private evaluator or submission writer is implemented here.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def sha256_string(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def interval(value, low, high):
    return (isinstance(value, list) and len(value) == 2 and all(finite(x) for x in value)
            and low <= value[0] <= value[1] <= high)


def assess(card, inspected=None, strict_inspected=None):
    """Evaluate metadata and independently produced saved-byte inspections.

    `promote` means eligible for the separate selector, never automatic upload approval.
    False or missing evidence fails closed. Caller-supplied scientific receipts still need
    reproducible, pinned provenance; this function cannot prove they are truthful.
    """
    reasons = []
    card = card if isinstance(card, dict) else {}

    def mapping(value):
        return value if isinstance(value, dict) else {}

    def require(ok, reason):
        if not ok:
            reasons.append(reason)

    require(isinstance(card.get('assigned_lane'), str) and bool(card['assigned_lane'].strip()),
            'missing assigned method lane')
    experiments = card.get('experiments_run')
    elapsed = card.get('elapsed_seconds')
    require(type(experiments) is int and 1 <= experiments <= 3, 'experiment count missing or outside budget')
    require(finite(elapsed) and 0 <= elapsed <= 7200, 'elapsed time missing or outside budget')
    require(isinstance(card.get('hypothesis'), str) and bool(card['hypothesis'].strip())
            and isinstance(card.get('mechanism'), str) and bool(card['mechanism'].strip())
            and isinstance(card.get('non_fault_mimic'), str) and bool(card['non_fault_mimic'].strip()),
            'missing hypothesis, mechanism, or named non-fault mimic')

    h = mapping(card.get('holdout'))
    require(h.get('evidence_class') == 'HOLDOUT-DTI' and isinstance(h.get('evaluator_version'), str)
            and bool(h['evaluator_version'].strip()), 'missing versioned HOLDOUT-DTI')
    require(type(h.get('withheld_positives')) is int and h['withheld_positives'] > 0,
            'missing withheld positives')
    dti = h.get('dti')
    require(finite(dti) and 0 <= dti <= 1, 'missing valid holdout DTI')
    ci = h.get('ci95')
    require(interval(ci, 0, 1) and finite(dti) and ci[0] <= dti <= ci[1],
            'missing valid holdout 95% CI containing the estimate')
    paired = h.get('paired_delta')
    paired_ci = h.get('paired_delta_ci95')
    require(finite(paired) and interval(paired_ci, -1, 1) and 0 < paired_ci[0] <= paired <= paired_ci[1],
            'no paired holdout improvement with a strictly positive 95% CI')
    baseline = mapping(h.get('baseline'))
    require(h.get('same_evaluator_current_best') is True
            and baseline.get('evaluator_version') == h.get('evaluator_version')
            and sha256_string(h.get('fold_manifest_sha256'))
            and baseline.get('fold_manifest_sha256') == h.get('fold_manifest_sha256')
            and finite(baseline.get('dti')) and 0 <= baseline['dti'] <= 1
            and finite(dti) and finite(paired) and abs((dti - baseline['dti']) - paired) <= 1e-6,
            'current same-evaluator, same-fold baseline not established')
    require(h.get('whole_segment_buffered') is True and h.get('catalogue_features_visible_only') is True
            and h.get('visible_faults_masked_pixel_exactly') is True,
            'fold-local leakage controls missing')

    auc = card.get('feature_auc')
    names = card.get('feature_names')
    require(isinstance(auc, list) and bool(auc) and type(card.get('feature_count')) is int
            and len(auc) == card['feature_count']
            and isinstance(names, list) and len(names) == len(auc)
            and all(isinstance(name, str) and bool(name.strip()) for name in names)
            and len(set(names)) == len(names)
            and all(finite(x) and 0.10 <= x <= 0.90 for x in auc),
            'missing, incomplete, or leaking feature canaries (two-sided AUC)')

    registry = mapping(card.get('registry'))
    ids = registry.get('reference_ids')
    ids_valid = (isinstance(ids, list) and bool(ids)
                 and all(isinstance(i, str) and bool(i.strip()) for i in ids)
                 and len(set(ids)) == len(ids))
    require(ids_valid, 'missing or invalid registry inventory')
    stages = []
    for stage in ('surface', 'final_dots'):
        r = mapping(registry.get(stage))
        stages.append(r)
        require(r.get('complete') is True and type(r.get('expected_rasters')) is int
                and ids_valid and r['expected_rasters'] == len(ids)
                and type(r.get('checked_rasters')) is int and r['checked_rasters'] == len(ids)
                and type(r.get('failed_rasters')) is int and r['failed_rasters'] == 0
                and sha256_string(r.get('manifest_sha256')) and sha256_string(r.get('candidate_sha256'))
                and finite(r.get('max_abs_spearman')) and 0 <= r['max_abs_spearman'] <= .90
                and finite(r.get('max_overlap_3px')) and 0 <= r['max_overlap_3px'] <= .70,
                f'{stage} uniqueness incomplete or duplicate')
        records = r.get('comparisons')
        records_valid = (isinstance(records, list) and bool(records)
                         and all(isinstance(row, dict) for row in records))
        require(records_valid, f'{stage} missing per-reference comparisons')
        if not records_valid:
            continue
        names = [row.get('reference_id') for row in records]
        coverage = (ids_valid and all(isinstance(name, str) and bool(name.strip()) for name in names)
                    and len(set(names)) == len(names) and set(names) == set(ids))
        require(coverage, f'{stage} registry comparison coverage mismatch')
        valid_values = all(finite(row.get('spearman')) and abs(row['spearman']) <= .90
                           and finite(row.get('overlap_3px')) and 0 <= row['overlap_3px'] <= .70
                           for row in records)
        require(valid_values, f'{stage} duplicate or invalid per-reference measurement')
        if valid_values:
            max_rho = max(abs(row['spearman']) for row in records)
            max_overlap = max(row['overlap_3px'] for row in records)
            require(finite(r.get('max_abs_spearman')) and finite(r.get('max_overlap_3px'))
                    and math.isclose(max_rho, r['max_abs_spearman'], abs_tol=1e-12)
                    and math.isclose(max_overlap, r['max_overlap_3px'], abs_tol=1e-12),
                    f'{stage} summary does not match per-reference comparisons')
    require(sha256_string(stages[0].get('manifest_sha256'))
            and stages[0].get('manifest_sha256') == stages[1].get('manifest_sha256')
            and stages[0].get('expected_rasters') == stages[1].get('expected_rasters'),
            'surface and final-dot comparisons do not use the same complete registry')

    sha = card.get('raster_sha256')
    require(sha256_string(sha), 'missing raster SHA256')
    require(stages[1].get('candidate_sha256') == sha, 'final-dot registry evidence is not bound to raster bytes')
    v = mapping(card.get('validator'))
    require(v.get('template_organizer_authenticated') is True and sha256_string(v.get('template_sha256')),
            'organizer-template authenticity not established')
    policy = v.get('outside_policy')
    require(v.get('outside_encoding_policy_resolved') is True
            and policy in ('null_or_nan', 'allfinite') and isinstance(inspected, dict)
            and inspected.get('outside_footprint_all_null_or_nan' if policy == 'null_or_nan'
                              else 'whole_grid_finite_and_in_range') is True
            and (policy != 'allfinite' or inspected.get('whole_grid_unmasked') is True),
            'outside-footprint encoding/portal behavior unresolved or mismatched')
    # Current pinned shared writer and holdout CLI silently threshold probabilities. Binary
    # candidates are the only safe contract until the shared template issue is fixed.
    require(card.get('output_kind') == 'binary', 'shared template probability contract is not fixed')
    require(isinstance(inspected, dict) and inspected.get('core_checks_passed') is True
            and inspected.get('raster_sha256') == sha
            and inspected.get('template_sha256') == v.get('template_sha256')
            and inspected.get('inside_binary') is True,
            'independent saved-byte candidate/template inspection missing or mismatched')
    # Preserve the parallel gate's stricter simultaneous raw-range + outside-null
    # diagnostic. An embedded finite-valued mask can satisfy both locally; neither
    # this check nor a metadata assertion proves actual organizer acceptance.
    diagnostic = mapping(card.get('format_diagnostic'))
    diagnostic_checks = mapping(diagnostic.get('checks'))
    strict_checks = ('template_epsg32611_and_100m_unrotated', 'geotiff',
                     'self_contained_no_sidecars', 'single_band', 'float32',
                     'crs_shape_transform_match_template', 'inside_finite_and_in_range',
                     'inside_not_masked', 'no_positive_outside_footprint',
                     'all_cell_finite_range', 'outside_null_or_nan')
    require(diagnostic.get('strict_format_gate_pass') is True
            and diagnostic.get('sha256') == sha and sha256_string(sha)
            and diagnostic.get('template_sha256') == v.get('template_sha256')
            and all(diagnostic_checks.get(key) is True for key in strict_checks)
            and isinstance(strict_inspected, dict) and strict_inspected.get('strict_format_gate_pass') is True
            and strict_inspected.get('sha256') == sha
            and strict_inspected.get('template_sha256') == v.get('template_sha256')
            and all(mapping(strict_inspected.get('checks')).get(key) is True for key in strict_checks),
            'missing independently verified strict outside/null and raw-array range diagnostic')
    require(isinstance(card.get('submission_name'), str) and bool(card['submission_name'].strip())
            and isinstance(card.get('note'), str) and 0 < len(card['note']) <= 140,
            'invalid submission name/note')
    return {'verdict': 'negative' if reasons else 'promote', 'ok_to_submit': False,
            'selector_required': True, 'reasons': reasons}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('card', type=Path)
    parser.add_argument('--raster', type=Path, help='Exact saved candidate bytes to reopen')
    parser.add_argument('--template', type=Path, help='Exact organizer template bytes to reopen')
    args = parser.parse_args()
    inspected = None
    strict_inspected = None
    inspection_error = None
    if args.raster and args.template:
        try:
            # Kept optional so a missing rasterio install still returns a negative decision.
            from validate_geotiff import validate
            from check_format import inspect
            inspected = validate(args.raster, args.template)
            strict_inspected = inspect(args.raster, args.template)
        except Exception as exc:  # All inspection failures must remain negative.
            inspection_error = f'{type(exc).__name__}: {exc}'
    try:
        result = assess(json.loads(args.card.read_text()), inspected, strict_inspected)
    except (OSError, ValueError, TypeError) as exc:
        result = {'verdict': 'negative', 'ok_to_submit': False, 'selector_required': True,
                  'reasons': [f'could not parse card: {exc}']}
    if inspection_error:
        result['reasons'].append(f'saved-byte inspection failed: {inspection_error}')
    print(json.dumps(result, indent=2))
    return 0 if result['verdict'] == 'promote' else 2


if __name__ == '__main__':
    raise SystemExit(main())
