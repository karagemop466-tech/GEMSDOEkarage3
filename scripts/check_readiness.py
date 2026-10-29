"""Inventory measured local prerequisites without training, fabricating scores, or spending slots."""
import json
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from .audit_historical_rasters import ROOT, SNAPSHOT, sha256
else:
    from audit_historical_rasters import ROOT, SNAPSHOT, sha256
import sys as _sys
_sys.path.insert(0, str(ROOT / 'src'))
from gems32.paths import data_dir  # noqa: E402


def readiness():
    pins = json.loads((SNAPSHOT / 'manifest.json').read_text())
    source_ok = bool(pins) and all((SNAPSHOT / r['path']).is_file()
                                   and sha256(SNAPSHOT / r['path']) == r['sha256'] for r in pins)
    active = json.loads((ROOT / 'registry/shared_template_97597a.json').read_text())
    active_ok = bool(active['files']) and all((ROOT / p).is_file() and sha256(ROOT / p) == digest
                                               for p, digest in active['files'].items())
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
        # Look where restore_data.py writes (paths.data_dir()), then the legacy data/ folder.
        candidates = [data_dir() / r['dest'], ROOT / 'data' / r['dest']]
        path = next((c for c in candidates if c.is_file()), candidates[0])
        core_checks.append(dict(id=r['id'], present_and_hash_verified=path.is_file() and sha256(path) == r['sha256']))
    checks = [
        dict(id='canonical_source_snapshot', passed=source_ok,
             detail='Archived pinned upstream scripts + dependency modules recovered; not the feature cache'),
        dict(id='active_shared_template', passed=active_ok,
             detail='Active evaluator, writer and dependencies match pinned GEMSDOE32 commit 97597a; equality is not correctness'),
        dict(id='shared_holdout_protocol', passed=False,
             detail='Open shared issues #60 (buffer), #41 (FP pooling), #61 (leakage); repair upstream and validate before use'),
        dict(id='surface_preview_overlap', passed=False,
             detail='Shared release gate issue #42 ignores preview-dot overlap at surface stage; do not rely on it alone'),
        dict(id='assigned_method_lane', passed=isinstance(lane.get('method'), str) and bool(lane['method'].strip()),
             detail='A single specified parallel-run method lane is required; do not invent one'),
        dict(id='core_mirror_data', passed=len(core_checks) == 4 and all(c['present_and_hash_verified'] for c in core_checks), details=core_checks,
             detail='Owner mirrors only, not organizer-authenticated'),
        dict(id='cached_feature_stack', passed=False,
             detail=f'{cache.relative_to(ROOT)}: {"present but not provenance-validated" if cache.exists() else "absent"}'),
        dict(id='complete_registry', passed=False,
             detail=f'{cached}/{len(registry["rasters"])} pinned registry paths present; continuous surfaces and freshness unverified'),
        dict(id='same_evaluator_baseline', passed=False, detail='No baseline rerun in this checkout'),
    ]
    return dict(schema_version=1, checked_utc=datetime.now(timezone.utc).isoformat(),
                ready_for_experiment=all(c['passed'] for c in checks),
                ok_to_submit=False, checks=checks,
                limitations='Availability is not scientific validation. No lane, dataset provenance, or complete registry is inferred from filenames.',
                snapshot_scope='Availability was measured at script execution; ignored data may be absent in another checkout. Re-run for current local state.')


if __name__ == '__main__':
    result = readiness()
    (ROOT / 'docs/readiness.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ready_for_experiment'] else 2)
