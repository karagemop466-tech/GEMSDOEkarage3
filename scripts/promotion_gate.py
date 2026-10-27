"""Fail-closed evidence decision. Does not replace template evaluator or writer."""
import json
import math
import sys

def finite(x):
    return type(x) in (int,float) and math.isfinite(x)

def assess(card):
    if not isinstance(card, dict):
        return {"verdict":"negative", "ok_to_submit":False, "selector_required":True, "reasons":["run card must be a JSON object"]}
    reasons=[]
    def mapping(value):
        return value if isinstance(value, dict) else {}
    def require(ok, reason):
        if not ok: reasons.append(reason)
    require(isinstance(card.get('assigned_lane'),str) and bool(card['assigned_lane'].strip()), 'missing assigned method lane')
    h=mapping(card.get('holdout'))
    require(h.get('evidence_class')=='HOLDOUT-DTI' and isinstance(h.get('evaluator_version'),str) and bool(h['evaluator_version'].strip()), 'missing versioned HOLDOUT-DTI')
    require(type(h.get('withheld_positives')) is int and h['withheld_positives']>0, 'missing withheld positives')
    require(finite(h.get('dti')) and 0<=h['dti']<=1, 'missing valid holdout DTI')
    interval=h.get('ci95')
    require(isinstance(interval,list) and len(interval)==2 and all(finite(x) for x in interval) and 0<=interval[0]<=interval[1]<=1, 'missing valid holdout 95% CI')
    if isinstance(interval,list) and len(interval)==2 and all(finite(x) for x in interval) and finite(h.get('dti')):
        require(interval[0]<=h['dti']<=interval[1], 'holdout DTI outside its 95% CI')
    ci=h.get('paired_delta_ci95')
    require(isinstance(ci,list) and len(ci)==2 and all(finite(x) for x in ci) and 0<ci[0]<=ci[1]<=1, 'no paired holdout improvement')
    require(h.get('same_evaluator_current_best') is True, 'current same-evaluator baseline not established')
    auc=card.get('feature_auc')
    require(isinstance(auc,list) and bool(auc) and all(finite(x) and 0<=x<=.90 for x in auc), 'missing or leaking feature canaries')
    for stage in ('surface','final_dots'):
        r=mapping(mapping(card.get('registry')).get(stage))
        require(r.get('complete') is True and finite(r.get('max_abs_spearman')) and 0<=r['max_abs_spearman']<=.90 and finite(r.get('max_overlap_3px')) and 0<=r['max_overlap_3px']<=.70, f'{stage} uniqueness incomplete or duplicate')
    v=mapping(card.get('validator'))
    for key in ('saved_bytes_checked','single_band','finite_inside','range_0_1','crs_match','shape_match','transform_match'):
        require(v.get(key) is True, f'validator: {key}')
    sha=card.get('raster_sha256')
    require(isinstance(sha,str) and len(sha)==64 and all(c in '0123456789abcdef' for c in sha), 'missing raster SHA256')
    require(isinstance(card.get('submission_name'),str) and bool(card['submission_name'].strip()) and isinstance(card.get('note'),str) and 0<len(card['note'])<=140, 'invalid submission name/note')
    return {'verdict':'negative' if reasons else 'promote','ok_to_submit':False,'selector_required':True,'reasons':reasons}

if __name__=='__main__':
    result=assess(json.load(open(sys.argv[1])))
    print(json.dumps(result,indent=2))
    sys.exit(0 if result['verdict']=='promote' else 2)
