"""Regression tests for the literal-registry correction and public status."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import rasterio
from scripts.promotion_gate import assess
from src.gems32.release_gate import compare_registry

ROOT = Path(__file__).resolve().parents[1]


def test_dated_saved_audit_is_not_misrepresented_as_covering_later_tiffs():
    historic = json.loads((ROOT / 'evidence/saved-tiffs-literal-20261028.json').read_text())
    latest = json.loads((ROOT / 'evidence/saved-tiffs-literal-20261029.json').read_text())
    assert latest['experiments_run'] == latest['weekly_slots_used'] == 0
    assert latest['ok_to_submit'] is False
    old_paths = {r['file'] for r in historic['rasters']}
    audited = {r['file'] for r in latest['rasters']}
    current = {str(p.relative_to(ROOT)) for p in (ROOT / 'docs').rglob('*.tif')}
    assert len(old_paths) == 9
    assert old_paths.issubset(audited)
    assert audited == current and len(audited) == 13
    assert audited - old_paths == {
        'docs/quarantine/karage3-unique-offcat/karage3-unique-offcat-20261029T180337Z-6a8c2368-zeros.tif',
        'docs/quarantine/karage3-unique-offcat/karage3-unique-offcat-20261029T180337Z-6a8c2368-nan.tif',
        'docs/quarantine/geoconduit-hybrid/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif',
        'docs/quarantine/geoconduit-hybrid/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-nan.tif',
    }
    for row in latest['rasters']:
        path = ROOT / row['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
        assert row['within_3px_fraction'] > .70 and row['duplicate_stop'] is True
        assert row['ok_to_submit'] is False
        if path.name.endswith('-zeros.tif'):
            assert row['format_diagnostic']['all_cell_finite_range'] is True
        elif path.name.startswith('karage3-unique-offcat-'):
            assert row['format_diagnostic']['all_cell_finite_range'] is True
            with rasterio.open(path) as nan_ds, rasterio.open(path.with_name(path.name.replace('-nan.tif', '-zeros.tif'))) as zero_ds:
                assert int(np.isnan(nan_ds.read(1)).sum()) == 0
                assert np.array_equal(nan_ds.read(1), zero_ds.read(1))
        else:
            assert row['format_diagnostic']['all_cell_finite_range'] is False


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
    release_page = (ROOT / 'docs/release-review.html').read_text()
    assert '13 of the 13 retained TIFFs fail' in release_page
    assert 'NOT ESTABLISHED · not measured' not in release_page
    assert 'gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif' in release_page
    assert 'karage3-unique-offcat-20261029T180337Z-6a8c2368-zeros.tif' in release_page
    assert '<a download' not in release_page
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
