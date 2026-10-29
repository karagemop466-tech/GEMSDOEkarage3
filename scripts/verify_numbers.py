#!/usr/bin/env python3
"""Check current decision, hash-bound receipts and published numbers.

This lightweight consistency check does not reproduce the geospatial audit,
prove a complete registry, authenticate organizer inputs, or select a slot.
For an independent fresh raster calculation run audit_saved_tiffs.py with
--verify-receipt. Historical K3 scores remain archived, not release decisions.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.promotion_gate import assess


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def load(path: str):
    return json.loads((ROOT / path).read_text())


def main() -> int:
    checks = []

    def ck(name: str, condition: bool) -> None:
        checks.append(bool(condition))
        print(f"{'PASS' if condition else 'FAIL'} {name}")

    current = load('docs/data/current-run.json')  # independent parallel preflight
    latest = load('docs/data/latest-run.json')
    archived = load('docs/k3c/run-card.json')
    decision = load('docs/current-gate-decision.json')
    audit = load('evidence/saved-tiffs-literal-20261028.json')
    witness = load('evidence/k3c-literal-witness-audit-20261028.json')
    sites = load('docs/sites.json')
    history = load('docs/data/historical-audit.json')

    ck('latest session card is negative, mirrored and binds its nine-site audit',
       latest['verdict'] == 'negative' and latest['ok_to_submit'] is False
       and latest['selector_approval'] is False and latest['slot_selected'] is False
       and latest['raster_sha256'] is None and latest['holdout_dti']['value'] is None
       and latest['experiments_run'] == latest['weekly_slots_used'] == 0
       and sha(ROOT / 'docs/data/latest-run.json') == sha(ROOT / 'evidence/run-card-20261028-session.json')
       == sha(ROOT / 'docs/data/latest-run-card.json')
       and latest['evidence']['historical_audit_sha256'] == sha(ROOT / 'evidence/historical-reaudit-20261028-session.json'))
    ck('current card has no new raster, holdout or slot',
       current['verdict'] == 'negative' and current['ok_to_submit'] is False
       and current['raster_sha256'] is None and current['holdout_dti']['value'] is None
       and current['experiments_run'] == current['weekly_slots_used'] == 0
       and current['slot_selected'] is False)
    ck('parallel preflight card matches its evidence copy',
       sha(ROOT / 'docs/data/current-run.json') == sha(ROOT / 'evidence/run-card-20261028-afbdab50.json'))
    ck('current card binds both saved audit receipts',
       current['geometry_audit_sha256'] == sha(ROOT / 'docs/data/historical-audit.json')
       and current['saved_tiffs_audit_sha256'] == sha(ROOT / 'evidence/saved-tiffs-literal-20261028.json')
       and sha(ROOT / 'docs/data/saved-tiffs-literal-20261028.json') == sha(ROOT / 'evidence/saved-tiffs-literal-20261028.json'))
    ck('lattice geometry and budget bound agree',
       audit['witness']['sha256'] == history['lattice']['source']['sha256']
       and audit['witness']['uncovered_footprint_pixels'] == history['lattice']['uncovered_beyond_3px']
       and current['correlation_overlap_vs_registry']['unavoidable_overlap_fraction']
       == history['lattice']['budget_lower_bound'] > .70)
    rows = audit['rasters']
    paths = {str(p.relative_to(ROOT)) for p in (ROOT / 'docs').rglob('*.tif')}
    ck('all retained TIFFs inventoried exactly once',
       bool(rows) and len(rows) == len(paths) and {r['file'] for r in rows} == paths)
    for row in rows:
        path = (ROOT / row['file']).resolve()
        ck(f"{row['file']} hash and duplicate stop",
           path.is_relative_to(ROOT / 'docs') and path.is_file()
           and sha(path) == row['sha256'] and row['within_3px_fraction'] > .70
           and row['duplicate_stop'] is True and row['ok_to_submit'] is False
           and row['format_diagnostic']['sha256'] == row['sha256'])
    k3c = next((r for r in rows if r['file'] == witness['candidate']), None)
    ck('independent K3C witness agrees with saved-byte audit',
       k3c is not None and k3c['sha256'] == witness['candidate_sha256'] == archived['raster_sha256']
       and k3c['within_3px_fraction'] == witness['within_3px_fraction'] > .70
       and witness['duplicate_stop'] is True and witness['ok_to_submit'] is False)
    for receipt_path in ('evidence/k3c-literal-witness-reaudit-20261028-final.json',
                         'evidence/csst-bghf-literal-witness-reaudit-20261028-final.json'):
        independent = load(receipt_path)
        row = next((r for r in rows if r['file'] == independent['candidate']), None)
        ck(f'{receipt_path} agrees with parallel saved-byte audit',
           row is not None and row['sha256'] == independent['candidate_sha256']
           and row['within_3px_fraction'] == independent['within_3px_fraction'] > .70
           and independent['duplicate_stop'] is True and independent['ok_to_submit'] is False
           and independent['validator']['checks']['geotiff'] is True
           and independent['validator']['checks']['self_contained_tiff'] is True)
    gate = assess(archived)
    ck('archived K3C reassessment and publication agree',
       decision['verdict'] == gate['verdict'] == archived['verdict'] == 'negative'
       and decision['ok_to_submit'] is False and gate['ok_to_submit'] is False
       and decision['eligible_for_selector'] is False
       and decision['raster_sha256'] == archived['raster_sha256'])
    hk3d = load('docs/hk3d/run-card.json')
    hk3d_witness = load('evidence/hk3d-literal-witness-audit-20261028.json')
    hk3d_gate = assess(hk3d)
    hk3d_row = next((r for r in rows if r['file'] == hk3d['submission_file']), None)
    ck('Session 5 H-K3D run card, saved-byte audit and literal witness agree',
       sha(ROOT / 'docs/hk3d/run-card.json') == sha(ROOT / 'evidence/hk3d_run_card.json')
       and hk3d['verdict'] == hk3d_gate['verdict'] == 'negative'
       and hk3d['ok_to_submit'] is False and hk3d_gate['ok_to_submit'] is False
       and hk3d_row is not None and hk3d_row['sha256'] == hk3d['raster_sha256'] == hk3d_witness['candidate_sha256']
       and hk3d_row['within_3px_fraction'] == hk3d_witness['within_3px_fraction'] > .70
       and hk3d_witness['duplicate_stop'] is True and hk3d_witness['ok_to_submit'] is False)
    ck('no promoted site or estimated organizer score',
       sites['promoted_candidate'] is None and sites['promoted_candidate_sha256'] is None
       and sites['promoted_candidate_card'] is None and len(sites['sites']) == 9
       and all(s['estimated_score'] is None and s['ok_to_submit'] is False for s in sites['sites']))
    pages = ('index.html', 'executive-summary.html', 'docs/index.html', 'docs/executive-summary.html',
             'docs/k3c/index.html', 'docs/k3c/how-to-submit.html',
             'docs/hk3d/index.html', 'docs/hk3d/how-to-submit.html')
    ck('current pages say DO NOT SUBMIT and never say YES',
       all('DO NOT SUBMIT' in (ROOT / page).read_text()
           and 'OK TO SUBMIT? YES' not in (ROOT / page).read_text()
           and 'OK TO DOWNLOAD AND SUBMIT: YES' not in (ROOT / page).read_text()
           for page in pages))
    print(f"\n{sum(checks)}/{len(checks)} consistency checks passed (not a score or slot selection).")
    return 0 if all(checks) else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f'FAIL closed: {exc}', file=sys.stderr)
        raise SystemExit(1)
