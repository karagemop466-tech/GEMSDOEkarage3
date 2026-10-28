"""Regression tests for literal protocol enforcement, not claims of model quality."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
from gems32.release_gate import compare_registry
from scripts.protocol_preflight import require_budget_not_proven_duplicate, require_shared_protocol_ready
from scripts.promotion_gate import assess

ROOT = Path(__file__).resolve().parents[1]


def test_preflight_stops_proven_duplicate_budget_and_keeps_lower_budget_inconclusive():
    assert require_budget_not_proven_duplicate(22163) is None  # not an approval
    with pytest.raises(ValueError, match='duplicate stop'):
        require_budget_not_proven_duplicate(22164)
    with pytest.raises(ValueError, match='duplicate stop'):
        require_budget_not_proven_duplicate(37654)
    with pytest.raises(ValueError):
        require_budget_not_proven_duplicate(0)
    # Even a lower budget cannot run until the shared upstream protocol is fixed.
    with pytest.raises(RuntimeError, match='Shared template protocol blocked'):
        require_shared_protocol_ready()


def test_independent_saved_byte_audit_includes_k3c_and_every_public_tiff():
    audit = json.loads((ROOT / 'evidence/saved-tiffs-literal-20261028.json').read_text())
    assert audit['complete_registry_checked'] is False
    assert {r['file'] for r in audit['rasters']} == {
        str(p.relative_to(ROOT)) for p in (ROOT / 'docs').rglob('*.tif')}
    for row in audit['rasters']:
        assert hashlib.sha256((ROOT / row['file']).read_bytes()).hexdigest() == row['sha256']
        assert row['duplicate_stop'] and row['within_3px_fraction'] > .70
        assert not row['ok_to_submit']
    k3c = next(r for r in audit['rasters'] if '/k3c/' in r['file'])
    assert k3c['within_3px_fraction'] == pytest.approx(0.9935199447601848)
    assert not k3c['format_diagnostic']['outside_null_or_nan']
    assert k3c['format_diagnostic']['all_cell_finite_range']


@pytest.mark.parametrize(('script', 'args', 'expected'), [
    ('run_k3c_session.py', [], 'duplicate stop'),
    ('run_csst_ablation.py', [], 'duplicate stop'),
    ('exp1_screen.py', [], 'duplicate stop'),
    ('run_ccl_live.py', ['--budget', '1000'], 'Shared template protocol blocked'),
    ('run_ccl.py', [], 'Shared template protocol blocked'),
])
def test_experiment_entrypoints_stop_direct_cli_before_data_or_fitting(script, args, expected):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args],
                            cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert expected in result.stderr
    assert 'ModuleNotFoundError' not in result.stderr


def test_registry_has_no_lattice_exemption_and_reports_dot_correlation():
    rng = np.random.default_rng(4)
    foot = np.ones((20, 20), bool)
    surface = rng.random(foot.shape)
    other = rng.random(foot.shape)
    dots = np.zeros_like(foot); dots[::3, ::3] = True
    result = compare_registry(surface, dots, foot, {'calibration_lattice': (other, dots)}, stage='final')
    assert result['stop'] and not result['passed']
    assert result['comparisons'][0]['within_3px_fraction'] == 1
    assert result['comparisons'][0]['dots_spearman'] == pytest.approx(1)


def test_retained_byte_audit_covers_all_tiffs_and_refuses_each():
    receipt = json.loads((ROOT / 'evidence/retained-submissions-audit-20261028.json').read_text())
    assert set(r['file'] for r in receipt['rasters']) == set(str(p.relative_to(ROOT)) for p in (ROOT / 'docs/downloads').glob('*.tif'))
    for row in receipt['rasters']:
        assert hashlib.sha256((ROOT / row['file']).read_bytes()).hexdigest() == row['sha256']
        assert row['lattice_overlap_3px'] > .70 and row['duplicate_stop']
        assert row['ok_to_submit'] is False
        assert row['format']['candidate_sha256'] == row['sha256']


def test_active_decisions_agree_and_not_linked_to_organizer_scores():
    card = json.loads((ROOT / 'docs/run-card.json').read_text())          # archived SMGC card (historical)
    review = json.loads((ROOT / 'docs/review-run-card.json').read_text())
    sites = json.loads((ROOT / 'docs/sites.json').read_text())
    current = json.loads((ROOT / 'docs/k3c/run-card.json').read_text())   # current lane card
    decision = json.loads((ROOT / 'docs/current-gate-decision.json').read_text())
    assert card['verdict'] == review['verdict'] == 'negative'
    assert not card['ok_to_submit'] and not review['ok_to_submit']
    assert review['experiments_run'] == review['weekly_slots_used'] == 0
    # The public decision must agree with the current card and the gate re-run on it
    assert decision['verdict'] == current['verdict'] == assess(current)['verdict']
    assert decision['raster_sha256'] == current['raster_sha256']
    if current['verdict'] == 'promote':
        assert sites['promoted_candidate'] == current['submission_name']
    else:
        assert sites['promoted_candidate'] is None
    # Historical nine-site rows never carry an organizer score estimate
    assert all(r['estimated_score'] is None and not r['ok_to_submit'] for r in sites['sites'])
    assert 'DO NOT SUBMIT' in (ROOT / 'README.md').read_text()
    assert current['historical_verdict'] == 'promote'  # retained as history, not the current verdict
    assert current['verdict'] == 'negative' and current['ok_to_submit'] is False
    for page in ('index.html', 'executive-summary.html', 'docs/index.html',
                 'docs/executive-summary.html', 'docs/k3c/index.html', 'docs/k3c/how-to-submit.html'):
        text = (ROOT / page).read_text()
        assert 'OK TO DOWNLOAD AND SUBMIT: YES' not in text
        assert 'OK TO SUBMIT? YES' not in text
        assert 'DO NOT SUBMIT' in text
