"""Guardrails for historical source refreshes and score provenance."""

import subprocess

import pytest

from scripts import audit_sources


def audit_without_network(site_number, audit_map):
    def denied(*_args, **_kwargs):
        raise subprocess.CalledProcessError(1, "gh")

    # Source refresh is an explicit network operation. Unit tests exercise the
    # safety record without replacing the pinned historical source snapshots.
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(audit_sources, "gh", denied)
    try:
        return audit_sources.audit(site_number, audit_map)
    finally:
        monkeypatch.undo()


def test_focus_site_claims_never_become_receipt_confirmed_or_submission_approval():
    row = audit_without_network(32, {})

    assert row["owner_reported_value"] == 0.2778
    assert row["score_evidence_class"].startswith("USER-REPORTED / UNVERIFIED")
    assert "ORGANIZER-CONFIRMED" not in row["score_evidence_class"]
    assert row["estimated_score"] is None
    assert row["unique"] is None
    assert row["ok_to_submit"] is False
    assert "other_confirmed_submissions" not in row
    assert "other_user_reported_submissions" in row
    assert "no artifact-linked organizer receipt" in row["other_user_reported_submissions"]


def test_incomplete_legacy_holdout_rows_are_not_exposed_as_score_estimates():
    row = audit_without_network(24, {
        "GEMSDOE24": {
            "static_hide_recover_dti": 0.123,
            "sgmc_prevalence_calibrated_dti": 0.456,
            "within_3px_of_02778_champion": 0.25,
        }
    })

    assert "holdout_dti_static_hide_recover" not in row
    assert "holdout_dti_sgmc_calibrated" not in row
    assert row["legacy_holdout_diagnostics"] == "omitted: protocol provenance is incomplete"
    assert row["estimated_score"] is None
    assert row["unique"] is None  # one champion comparison is not fleet-wide uniqueness
    assert row["ok_to_submit"] is False
