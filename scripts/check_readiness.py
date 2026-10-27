"""Inventory measured local prerequisites without training, fabricating scores, or spending slots."""
import json
from pathlib import Path

if __package__:
    from .audit_historical_rasters import ROOT, SNAPSHOT, sha256
else:
    from audit_historical_rasters import ROOT, SNAPSHOT, sha256


def readiness():
    pins = json.loads((SNAPSHOT / 'manifest.json').read_text())
    source_ok = all((SNAPSHOT / r['path']).is_file()
                    and sha256(SNAPSHOT / r['path']) == r['sha256'] for r in pins)
    lane_path = ROOT / 'registry/lane.json'
    lane = json.loads(lane_path.read_text()) if lane_path.exists() else {}
    cache = ROOT / '.cache/gems_work/feature_stack.npy'
    registry = json.loads((SNAPSHOT / 'registry/focus_registry_manifest.json').read_text())
    cached = sum((ROOT / r['local']).is_file() for r in registry['rasters'])
    core = json.loads((SNAPSHOT / 'registry/data_manifest.json').read_text())['files']
    core_checks = []
    for r in core:
        if r['group'] != 'core':
            continue
        path = ROOT / 'data' / r['dest']
        core_checks.append(dict(id=r['id'], present_and_hash_verified=path.is_file() and sha256(path) == r['sha256']))
    checks = [
        dict(id='canonical_source_snapshot', passed=source_ok,
             detail='Unmodified pinned upstream scripts + dependency modules recovered; not the feature cache'),
        dict(id='assigned_method_lane', passed=isinstance(lane.get('method'), str) and bool(lane['method'].strip()),
             detail='registry/lane.json has no assigned method; parallel-run lane must not be invented'),
        dict(id='core_mirror_data', passed=all(c['present_and_hash_verified'] for c in core_checks), details=core_checks,
             detail='Owner mirrors only, not organizer-authenticated'),
        dict(id='cached_feature_stack', passed=False,
             detail=f'{cache.relative_to(ROOT)}: {"present but not provenance-validated" if cache.exists() else "absent"}'),
        dict(id='complete_registry', passed=False,
             detail=f'{cached}/{len(registry["rasters"])} pinned registry paths present; continuous surfaces and freshness unverified'),
        dict(id='same_evaluator_baseline', passed=False, detail='No baseline rerun in this checkout'),
    ]
    return dict(schema_version=1, ready_for_experiment=all(c['passed'] for c in checks),
                ok_to_submit=False, checks=checks,
                limitations='Availability is not scientific validation. No lane, dataset provenance, or complete registry is inferred from filenames.')


if __name__ == '__main__':
    result = readiness()
    (ROOT / 'docs/readiness.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ready_for_experiment'] else 2)
