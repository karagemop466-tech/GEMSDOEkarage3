"""Guards for the 2026-10-30 verification receipts. None of these may authorize a submission."""
import json
from pathlib import Path

from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def test_mechanism_receipt_is_negative_and_recomputes():
    m = _load('evidence/focus9-mechanism-audit-20261030.json')
    assert m['ok_to_submit'] is False
    rows = m['rows']
    assert len(rows) == 9
    scores = [r['owner_reported_score_USER_REPORTED'] for r in rows]
    share = [r['share_dots_within_3px_of_catalogue'] for r in rows]
    rho, _ = spearmanr(scores, share)
    assert abs(rho - m['summary']['score_vs_share_near_catalogue_3px']['spearman_rho']) < 1e-3
    sgmc = [r['sgmc_off_catalogue_holdout']['prevalence_calibrated_dti'] for r in rows]
    rho2, _ = spearmanr(scores, sgmc)
    assert abs(rho2 - m['summary']['score_vs_sgmc_off_catalogue_calibrated_dti']['spearman_rho']) < 1e-3
    # Every focus file sits on the lattice witness far above the 70% literal threshold.
    assert all(r['lattice_overlap_within_3px'] > 0.70 for r in rows)


def test_candidate_proxy_table_is_negative_and_bounded():
    t = _load('evidence/candidate-proxy-table-20261030.json')
    assert t['ok_to_submit'] is False
    for row in t['rows']:
        if 'holdout_catalogue_hide_and_recover' not in row:
            # Holdout is recorded as an explicit NOT RUN string for the format-failing candidate.
            assert str(row['holdout']).startswith('NOT RUN')
            continue
        hold = row['holdout_catalogue_hide_and_recover']
        assert hold['score_label'] == 'HOLDOUT-DTI'
        lo, hi = hold['ci95']
        assert lo <= hold['pooled_dti'] <= hi


def test_saved_byte_receipt_2026_10_30_covers_every_docs_tiff():
    audit = _load('evidence/saved-tiffs-literal-20261030.json')
    assert audit['ok_to_submit'] is False
    assert audit['experiments_run'] == audit['weekly_slots_used'] == 0
    assert audit['new_candidate_generated'] is False
    inventoried = {r['file'] for r in audit['rasters']}
    on_disk = {str(p.relative_to(ROOT)) for p in (ROOT / 'docs').rglob('*.tif')}
    assert inventoried == on_disk
    # The only rows allowed to skip the duplicate stop are the zero-overlap H1 files, which are
    # flagged for the registry rule separately in the review (not counted as clearance).
    for r in audit['rasters']:
        assert r['duplicate_stop'] or r['within_3px_fraction'] < 0.01
