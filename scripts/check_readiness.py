"""Inventory local prerequisites, not scientific validity or submission approval.

The JSON report is a timestamped snapshot; caches are ignored and may not exist on the
reader's machine. Hash verification of owner mirrors does not authenticate organizer data.
"""
import datetime
import json
from pathlib import Path

if __package__:
    from .audit_historical_rasters import ROOT, SNAPSHOT, sha256
else:
    from audit_historical_rasters import ROOT, SNAPSHOT, sha256


def readiness():
    pins = json.loads((SNAPSHOT / 'manifest.json').read_text())
    source_ok = bool(pins) and all((SNAPSHOT / r['path']).is_file()
                                   and sha256(SNAPSHOT / r['path']) == r['sha256'] for r in pins)
    lane_path = ROOT / 'registry/lane.json'
    lane = json.loads(lane_path.read_text()) if lane_path.exists() else {}
    lane = lane if isinstance(lane, dict) else {}
    receipt = json.loads((ROOT / 'evidence/cache-restoration.json').read_text())
    expected_stack = receipt['feature_stack']['sha256']
    cache_paths = (ROOT / '.cache/feature_stack.npy', ROOT / '.cache/shared-feature-stack.npy',
                   ROOT / '.cache/gems_work/feature_stack.npy')
    existing_caches = [path for path in cache_paths if path.is_file()]
    cache = next((path for path in existing_caches if sha256(path) == expected_stack), None)
    registry = json.loads((SNAPSHOT / 'registry/focus_registry_manifest.json').read_text())
    cached = sum((ROOT / r['local']).is_file() for r in registry['rasters'])
    core = json.loads((SNAPSHOT / 'registry/data_manifest.json').read_text())['files']
    core_checks = []
    for r in core:
        if r['group'] != 'core':
            continue
        options = (ROOT / 'data' / r['dest'], ROOT / '.cache/gems_data' / r['dest'],
                   ROOT / '.cache/shared-data' / r['dest'])
        match = next((path for path in options if path.is_file() and sha256(path) == r['sha256']), None)
        core_checks.append(dict(id=r['id'], present_and_hash_verified=match is not None,
                                path=str(match.relative_to(ROOT)) if match else None))
    checks = [
        dict(id='canonical_source_snapshot', passed=source_ok,
             detail='Unmodified pinned upstream source snapshot; not an organizer authentication'),
        dict(id='assigned_method_lane', passed=isinstance(lane.get('method'), str) and bool(lane['method'].strip()),
             detail='A coordinator-assigned lane is required; it must not be invented'),
        dict(id='core_mirror_data', passed=bool(core_checks) and all(c['present_and_hash_verified'] for c in core_checks), details=core_checks,
             detail='Owner mirrors only; not organizer-authenticated'),
        dict(id='cached_feature_stack', passed=cache is not None,
             detail=(f'{cache.relative_to(ROOT)} matches recorded 35-channel build SHA-256' if cache else
                     'No local cache matching the recorded build SHA-256; it can be restored/rebuilt')),
        dict(id='complete_registry', passed=False,
             detail=f'{cached}/{len(registry["rasters"])} pinned registry paths present; fresh inventory and surfaces unverified'),
        dict(id='same_evaluator_baseline', passed=False, detail='No baseline rerun in this checkout'),
    ]
    return dict(schema_version=2, checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
                ready_for_experiment=all(c['passed'] for c in checks), ok_to_submit=False, checks=checks,
                limitations='This local snapshot will become stale. File availability and a matching digest are not scientific validation or organizer authentication.')


if __name__ == '__main__':
    result = readiness()
    (ROOT / 'docs/readiness.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ready_for_experiment'] else 2)
