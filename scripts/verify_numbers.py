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
    audit = load('evidence/saved-tiffs-literal-20261029.json')
    historic_audit = load('evidence/saved-tiffs-literal-20261028.json')
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
       and current['saved_tiffs_audit_sha256'] == sha(ROOT / 'evidence/saved-tiffs-literal-20261029.json')
       and current['saved_tiffs_audit'] == 'saved-tiffs-literal-20261029.json'
       and len(historic_audit['rasters']) == 9
       and sha(ROOT / 'docs/data/saved-tiffs-literal-20261028.json') == sha(ROOT / 'evidence/saved-tiffs-literal-20261028.json')
       and sha(ROOT / 'docs/data/saved-tiffs-literal-20261029.json') == sha(ROOT / 'evidence/saved-tiffs-literal-20261029.json'))
    ck('lattice geometry and budget bound agree',
       audit['witness']['sha256'] == history['lattice']['source']['sha256']
       and audit['witness']['uncovered_footprint_pixels'] == history['lattice']['uncovered_beyond_3px']
       and current['correlation_overlap_vs_registry']['unavoidable_overlap_fraction']
       == history['lattice']['budget_lower_bound'] > .70)
    rows = audit['rasters']
    paths = {str(p.relative_to(ROOT)) for p in (ROOT / 'docs').rglob('*.tif')}
    audited_paths = {r['file'] for r in rows}
    historical_paths = {r['file'] for r in historic_audit['rasters']}
    offcat = load('docs/quarantine/karage3-unique-offcat/karage3-unique-offcat-20261029T180337Z-6a8c2368-zeros-metadata.json')
    hgeo_review = load('docs/data/candidate-review-20261029.json')
    later_hashes = {
        'docs/quarantine/geoconduit-hybrid/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif': '064348774a950f22cd677b52c8e27778066ef2947505630ff4074fc6e4eeaf43',
        'docs/quarantine/geoconduit-hybrid/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-nan.tif': 'dafa1e375a57735f6f64091f8b36050b5dda9c72b325ad97327d9d49a76ce1f3',
        'docs/quarantine/karage3-unique-offcat/karage3-unique-offcat-20261029T180337Z-6a8c2368-zeros.tif': '34cef5830612502ad24dc67314b70b38e636fa8fc644f5997f0456fe7c10c54e',
        'docs/quarantine/karage3-unique-offcat/karage3-unique-offcat-20261029T180337Z-6a8c2368-nan.tif': '80fac268d8cf8ef12f6213207072c1e476b132f6642357478058a41bd2f4d390',
    }
    ck('dated 9-file receipt remains immutable; fresh 13-file witness audit covers current docs TIFFs',
       len(historical_paths) == 9 and historical_paths.issubset(audited_paths)
       and audited_paths == paths and len(rows) == 13
       and all(sha(ROOT / path) == digest for path, digest in later_hashes.items())
       and offcat['ok_to_submit'] is False and offcat['verdict'] == 'negative'
       and offcat['estimated_leaderboard_score'] is None
       and 'NOT ESTABLISHED' in offcat['uniqueness_status']
       and hgeo_review['verdict'] == 'negative'
       and hgeo_review['raster_sha256'] == '064348774a950f22cd677b52c8e27778066ef2947505630ff4074fc6e4eeaf43'
       and hgeo_review['registry_checks']['registry_completeness'] == 'NOT ESTABLISHED')
    h1 = load('docs/data/run-card-20261029-h1.json')
    h1_files = list((ROOT / 'evidence/quarantine/h1-seismic-gravity-basin').glob('*.tif'))
    ck('inherited H1 candidate remains quarantined with negative run-card and no public download',
       h1['verdict'] == 'negative' and h1['ok_to_submit'] is False
       and h1['slot_selected'] is False and h1['holdout_dti']['value'] == 0.0
       and h1['raster_path'].startswith('evidence/quarantine/h1-seismic-gravity-basin/')
       and len(h1_files) == 2
       and not list((ROOT / 'docs/downloads').glob('*h1-seismic-gravity-basin*.tif')))
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
