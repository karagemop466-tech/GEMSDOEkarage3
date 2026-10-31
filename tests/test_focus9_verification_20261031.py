"""Regression checks for the 2026-10-31 focus-site receipts.

These tests do not recompute the distance transforms (that is scripts/verify_focus9_20261031.py,
about 75 s). They check that the stored receipts still match the files on disk, that the
literal-uniqueness flags are what the receipt says, and that the leaderboard snapshot matches
the values recorded from the public page.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'evidence/focus9-verification-20261031.json'
LEADER = ROOT / 'evidence/leaderboard-snapshot-20261031.json'


def _receipt():
    return json.loads(RECEIPT.read_text())


def test_receipt_exists_and_is_labelled_as_measurement_not_score():
    r = _receipt()
    assert 'NOT A SCORE' in r['evidence_class']
    assert 'NOT A SUBMISSION APPROVAL' in r['evidence_class']


def test_file_hashes_match_disk():
    r = _receipt()
    for site, meta in r['files'].items():
        path = list((ROOT / 'docs/downloads').glob(f'{site}-*.tif'))
        assert len(path) == 1, site
        raw = path[0].read_bytes()
        assert hashlib.sha256(raw).hexdigest() == meta['sha256'], site
        assert meta['file'] == path[0].name, site


def test_every_focus_file_fails_literal_uniqueness_against_another_focus_file():
    r = _receipt()
    assert set(r['literal_70pct_rule_unique_among_focus_files']) == set(r['files'])
    assert not any(r['literal_70pct_rule_unique_among_focus_files'].values())
    for site, row in r['within_3px_share_of_row_dots_near_column_dots'].items():
        assert max(row.values()) > 0.70, site


def test_gems32_is_strict_subset_of_gems25_by_6436_dots():
    r = _receipt()
    pair = r['dot_set_relations']['GEMSDOE25|GEMSDOE32']
    assert pair['b_minus_a'] == 0
    assert pair['a_minus_b'] == 6436


def test_mechanism_steps_are_all_inside_two_pixels_of_known_traces():
    m = _receipt()['mechanism_vs_known_fault_mask']
    s1 = m['steps']['GEMSDOE25->GEMSDOE31']
    s2 = m['steps']['GEMSDOE31->GEMSDOE32']
    assert s1['removed'] == 3891 and s1['removed_within_1px_of_known'] == 3891
    assert s2['removed'] == 2545 and s2['removed_within_2px_of_known'] == 2545
    assert s1['removed_on_known_trace'] == 0 and s2['removed_on_known_trace'] == 0
    assert m['GEMSDOE32_dots_within_2px_of_known'] == 0
    assert m['known_positive_cells_in_labels_tif'] == 60988


def test_zero_outside_files_are_flagged_as_irregular():
    r = _receipt()
    flagged = {line.split(':')[0] for line in r['irregularities']}
    assert flagged == {'GEMSDOE30', 'GEMSDOE32', 'GEMSDOE33', 'GEMSDOE36'}


def test_leaderboard_snapshot_values():
    snap = json.loads(LEADER.read_text())
    scores = {int(k): v for k, v in snap['scores_by_rank'].items()}
    assert len(scores) == 50
    assert scores[1] == pytest.approx(0.4544)
    assert scores[50] == pytest.approx(0.3195)
    assert 0.4413 not in scores.values()
    assert snap['checks']['prompt_value_0_4413_in_ranks_1_50'] is False
    assert snap['checks']['prompt_value_0_3195_rank'] == 50
    # Scores must be non-increasing with rank.
    ordered = [scores[i] for i in range(1, 51)]
    assert ordered == sorted(ordered, reverse=True)
