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
        # Decide by the bytes, not the filename. 'unique-offcat' carries a '-nan' name but
        # contains NO NaN outside the footprint (zeros outside, positives outside): an
        # IRREGULARITY recorded in README, so its whole-array check is finite and must be True.
        if 'unique-offcat' in path.name:
            assert row['validator']['whole_array_finite_range_pass'] is True
        elif path.name.endswith('-zeros.tif'):
            assert row['validator']['whole_array_finite_range_pass'] is True
        else:
            assert row['validator']['whole_array_finite_range_pass'] is False


def test_public_rebuild_deterministic_and_old_narrative_collapsed():
    paths = [ROOT / p for p in ('docs/crsb-gub/index.html', 'docs/crsb-gub/executive-summary.html',
                                'docs/release-review.html', 'docs/comparison.html')]
    before = [p.read_bytes() for p in paths]
    subprocess.run([sys.executable, 'scripts/build_release_review.py'], cwd=ROOT, check=True)
    assert before == [p.read_bytes() for p in paths]
    for path in paths[:2]:
        text = path.read_text()
        assert text.count('<!-- RELEASE-REVIEW -->') == 1
        assert text.count('<!-- ARCHIVED-BODY -->') <= 1
        assert 'DO NOT SUBMIT' in text
    # The home decision pages are generated from the current lane card by build_k3c_site.py
    home = [ROOT / p for p in ('docs/index.html', 'docs/executive-summary.html')]
    before = [p.read_bytes() for p in home]
    subprocess.run([sys.executable, 'scripts/build_review_status.py'], cwd=ROOT, check=True)
    assert before == [p.read_bytes() for p in home]
    for name in ('docs/run-card.json', 'docs/crsb-gub/run-card.json'):
        card = json.loads((ROOT / name).read_text())
        assert card['ok_to_submit'] is False
        assert assess(card)['verdict'] == 'negative'


def test_pinned_shared_gate_surface_overlap_defect_is_not_treated_as_a_pass():
    # Upstream #42: preview-dot overlap is measured but ignored at the surface
    # stage. The separate promotion screen must enforce it at BOTH stages.
    rng = np.random.default_rng(27)
    foot = np.ones((20, 20), dtype=bool)
    dots = np.zeros_like(foot)
    dots[::4, ::4] = True
    result = compare_registry(rng.random(foot.shape), dots, foot,
                              {'registered-lattice': (rng.random(foot.shape), dots)}, stage='surface')
    assert result['comparisons'][0]['within_3px_fraction'] == 1.0
    assert result['passed'] is True  # Known upstream defect; never a protocol pass.
    final = compare_registry(rng.random(foot.shape), dots, foot,
                             {'registered-lattice': (rng.random(foot.shape), dots)}, stage='final')
    assert final['stop'] is True
