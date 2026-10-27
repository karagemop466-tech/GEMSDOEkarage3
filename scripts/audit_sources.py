"""Refresh pinned GitHub evidence, not organizer score receipts."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SITES = [24,25,27,28,30,31,32,33,36]
CLAIMS = {24:('h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan',.2477),25:('dotted-h19-5-d2-8-20261002-e56ea318af89-nan',.2600),27:('topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan',.2449),28:('h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan',.2710),30:('d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca',.2600),31:('h27-4-solo-d28-20261004-8acb75e1-nan',.2708),32:('h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros',.2778),33:('h33d-analog-tip-stepover-r30-20261004-cb490425926e',.2632),36:('anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros',.2750)}
def gh(path):
    return subprocess.check_output(['gh','api',path], timeout=60)
def audit(n):
    repo=f'buffedlizard55-lab/GEMSDOE{n}'
    result={'site':f'GEMSDOE{n}', 'repository':f'https://github.com/{repo}', 'owner_reported_submission':CLAIMS[n][0], 'owner_reported_value':CLAIMS[n][1], 'evidence_class':'OWNER-REPORT — not ORGANIZER-CONFIRMED', 'estimated_score':None,'unique':None,'ok_to_submit':False}
    try:
        meta=json.loads(gh(f'repos/{repo}'))
        commit=json.loads(gh(f'repos/{repo}/commits/{meta["default_branch"]}'))['sha']
        result['commit']=commit
        for path in ['README.md','registry/current_status.json']:
            try:
                import base64
                entry=json.loads(gh(f'repos/{repo}/contents/{path}?ref={commit}'))
                data=base64.b64decode(entry['content'])
                dest=ROOT/'evidence'/'upstream'/f'GEMSDOE{n}'/path
                dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
                result.setdefault('sources',[]).append({'url':f'https://github.com/{repo}/blob/{commit}/{path}','local':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest()})
            except subprocess.CalledProcessError:
                pass
    except (subprocess.SubprocessError,KeyError,ValueError) as exc:
        result['error']=str(exc)
    return result
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        rows=list(pool.map(audit,SITES))
    # Preserve the independently pinned historical audit on refresh.
    from build_comparison import enrich
    audit_path=ROOT/'evidence/upstream/GEMSDOE32/evidence/arena48_focus9_overlap.json'
    if audit_path.exists():
        enrich(rows,json.loads(audit_path.read_text()))
    target=ROOT/'docs'/'sites.json'
    target.write_text(json.dumps({'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sites':rows},indent=2)+'\n')
