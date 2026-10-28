"""Fail-closed evidence screening, not an upload selector or evaluator.

Checks self-reported evidence for consistency; it cannot independently establish
that an inventory is current and complete or that the measurements are genuine.
"""
import json
import math
import sys

def finite(x):
    return type(x) in (int,float) and math.isfinite(x)

def assess(card):
    reasons=[]
    if not isinstance(card, dict):
        return {'verdict': 'negative', 'ok_to_submit': False, 'selector_required': True, 'reasons': ['invalid run card']}
    def require(ok, reason):
        if not ok: reasons.append(reason)
    # Never let a density-filtered summary override literal registry evidence.
    def literal_failures(node, path='card'):
        if isinstance(node, dict):
            for key, value in node.items():
                here = f'{path}.{key}'
                if key == 'literal_all_rasters_final_passed':
                    require(value is True, f'{here}: literal registry failed')
                if key in ('within_3px_fraction', 'literal_5px_calibration_lattice_overlap'):
                    require(finite(value) and 0 <= value <= .70, f'{here}: duplicate or invalid overlap')
                literal_failures(value, here)
        elif isinstance(node, list):
            for i, value in enumerate(node):
                literal_failures(value, f'{path}[{i}]')
    literal_failures(card)
    require(bool(card.get('assigned_lane')), 'missing assigned method lane')
    h=card.get('holdout') if isinstance(card.get('holdout'), dict) else {}
    require(h.get('evidence_class')=='HOLDOUT-DTI' and bool(h.get('evaluator_version')), 'missing versioned HOLDOUT-DTI')
    require(type(h.get('withheld_positives')) is int and h['withheld_positives']>0, 'missing withheld positives')
    require(finite(h.get('dti')) and 0<=h['dti']<=1, 'missing valid holdout DTI')
    interval=h.get('ci95')
    require(isinstance(interval,list) and len(interval)==2 and all(finite(x) for x in interval) and finite(h.get('dti')) and 0<=interval[0]<=h['dti']<=interval[1]<=1, 'missing valid holdout 95% CI')
    ci=h.get('paired_delta_ci95')
    require(isinstance(ci,list) and len(ci)==2 and all(finite(x) for x in ci) and 0<ci[0]<=ci[1], 'no paired holdout improvement')
    require(h.get('same_evaluator_current_best') is True, 'current same-evaluator baseline not established')
    auc=card.get('feature_auc')
    require(isinstance(auc,list) and bool(auc) and all(finite(x) and 0<=x<=1 and max(x,1-x)<=.90 for x in auc), 'missing or leaking feature canaries')
    registry = card.get('registry') if isinstance(card.get('registry'), dict) else {}
    # Aggregate 'complete' flags from legacy cards silently excluded dense and
    # calibration rasters. Never promote without an explicit literal audit.
    literal = registry.get('literal_all_rasters_final_passed')
    legacy = card.get('correlation_and_overlap_vs_registry')
    if isinstance(legacy, dict) and legacy.get('literal_all_rasters_final_passed') is False:
        literal = False
    require(literal is True, 'literal all-registry final audit absent or failed')
    inventory = registry.get('inventory_sha256')
    inventory_ok = (isinstance(inventory, list) and bool(inventory)
                    and all(isinstance(x, str) and len(x) == 64 and all(c in '0123456789abcdef' for c in x) for x in inventory)
                    and len(set(inventory)) == len(inventory))
    manifest = registry.get('manifest_sha256')
    manifest_ok = isinstance(manifest, str) and len(manifest) == 64 and all(c in '0123456789abcdef' for c in manifest)
    require(inventory_ok and manifest_ok, 'missing nonempty unique registry inventory or manifest digest')
    for stage in ('surface','final_dots'):
        r=registry.get(stage) if isinstance(registry.get(stage), dict) else {}
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
        require(r.get('complete') is True and surface_ok and final_ok,
                f'{stage} uniqueness incomplete or duplicate')
    require(not card.get('release_review'), 'superseded release evidence; rerun literal registry checks')
    v=card.get('validator') if isinstance(card.get('validator'), dict) else {}
    for key in ('saved_bytes_checked','single_band','finite_inside','range_0_1','crs_match','shape_match','transform_match'):
        require(v.get(key) is True, f'validator: {key}')
    sha=card.get('raster_sha256')
    require(isinstance(sha,str) and len(sha)==64 and all(c in '0123456789abcdef' for c in sha), 'missing raster SHA256')
    require(v.get('raster_sha256') == sha and isinstance(sha, str), 'validator not bound to candidate bytes')
    require(bool(card.get('submission_name')) and isinstance(card.get('note'),str) and 0<len(card['note'])<=140, 'invalid submission name/note')
    return {'verdict':'negative' if reasons else 'promote','ok_to_submit':False,'selector_required':True,'reasons':reasons}

if __name__=='__main__':
    result=assess(json.load(open(sys.argv[1])))
    print(json.dumps(result,indent=2))
    sys.exit(0 if result['verdict']=='promote' else 2)
