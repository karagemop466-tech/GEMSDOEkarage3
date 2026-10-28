"""Regression tests for literal protocol enforcement, not claims of model quality."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
from gems32.release_gate import compare_registry
from scripts.protocol_preflight import require_budget_not_proven_duplicate

ROOT = Path(__file__).resolve().parents[1]


def test_normal_budget_stops_and_small_budget_is_only_necessary_condition():
    with pytest.raises(SystemExit, match='literal any-registry'):
        require_budget_not_proven_duplicate(37654)
    assert require_budget_not_proven_duplicate(1000) is None
    with pytest.raises(ValueError):
        require_budget_not_proven_duplicate(0)


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
    card = json.loads((ROOT / 'docs/run-card.json').read_text())
    review = json.loads((ROOT / 'docs/review-run-card.json').read_text())
    sites = json.loads((ROOT / 'docs/sites.json').read_text())
    assert card['verdict'] == review['verdict'] == 'negative'
    assert not card['ok_to_submit'] and not review['ok_to_submit']
    assert sites['promoted_candidate'] is None
    assert review['experiments_run'] == review['weekly_slots_used'] == 0
    assert all(r['estimated_score'] is None and not r['ok_to_submit'] for r in sites['sites'])
    assert 'DO NOT SUBMIT' in (ROOT / 'README.md').read_text()
