"""Regression tests for the literal-registry correction and public status."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scripts.promotion_gate import assess
from src.gems32.release_gate import compare_registry

ROOT = Path(__file__).resolve().parents[1]


def test_saved_audit_binds_every_existing_tiff_and_rejects_all():
    report = json.loads((ROOT / 'evidence/release-audit-20261028.json').read_text())
    assert report['experiments_run'] == report['weekly_slots_used'] == 0
    assert report['ok_to_submit'] is False
    assert {r['file'] for r in report['rows']} == {
        str(p.relative_to(ROOT)) for p in (ROOT / 'docs/downloads').glob('*.tif')}
    for row in report['rows']:
        path = ROOT / row['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
        assert row['validator']['candidate_sha256'] == row['sha256']
        assert row['within_3px_fraction'] > .70
        assert row['duplicate_stop'] is True
        assert row['ok_to_submit'] is False
        if path.name.endswith('-zeros.tif'):
            assert row['validator']['whole_array_finite_range_pass'] is True
        else:
            assert row['validator']['whole_array_finite_range_pass'] is False


def test_public_rebuild_deterministic_and_old_narrative_collapsed():
    paths = [ROOT / p for p in ('docs/index.html', 'docs/executive-summary.html',
                                'docs/release-review.html', 'docs/comparison.html')]
    before = [p.read_bytes() for p in paths]
    subprocess.run([sys.executable, 'scripts/build_release_review.py'], cwd=ROOT, check=True)
    assert before == [p.read_bytes() for p in paths]
    for path in paths[:2]:
        text = path.read_text()
        assert text.count('<!-- RELEASE-REVIEW -->') == 1
        assert text.count('<!-- ARCHIVED-BODY -->') <= 1
        assert 'DO NOT SUBMIT' in text
    for name in ('docs/run-card.json', 'docs/crsb-gub/run-card.json'):
        card = json.loads((ROOT / name).read_text())
        assert card['ok_to_submit'] is False
        assert assess(card)['verdict'] == 'negative'


def test_final_rank_check_uses_actual_dots_not_surface():
    foot = np.ones((20, 20), dtype=bool)
    dots = np.zeros_like(foot)
    dots[::4, ::4] = True
    surface = np.arange(400, dtype=float).reshape(20, 20)
    result = compare_registry(surface, dots, foot,
                              {'registered-lattice': (surface[::-1], dots)}, stage='final')
    assert result['stop'] is True
    assert result['comparisons'][0]['spearman'] == 1.0
    assert result['comparisons'][0]['within_3px_fraction'] == 1.0
