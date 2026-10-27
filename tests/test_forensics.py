import itertools
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import spearmanr

from scripts.audit_historical import binary_spearman, lower_overlap_bound
from scripts.preflight import check

ROOT = Path(__file__).resolve().parents[1]


def test_tie_aware_binary_spearman_matches_scipy():
    a = np.array([1, 0, 0, 1, 0, 1, 0, 0], dtype=bool)
    b = np.array([0, 1, 0, 1, 0, 1, 0, 0], dtype=bool)
    actual = binary_spearman(len(a), int(a.sum()), int(b.sum()), int((a & b).sum()))
    assert actual == pytest.approx(spearmanr(a, b).statistic)
    assert binary_spearman(8, 0, 3, 0) is None
    assert binary_spearman(8, 8, 3, 3) is None


def test_pigeonhole_bound_exhaustive():
    # Independently enumerate every subset: the analytic bound is exact.
    for total in range(1, 9):
        for uncovered in range(total + 1):
            for dots in range(1, total + 1):
                covered = set(range(uncovered, total))
                observed = min(len(covered.intersection(s)) for s in itertools.combinations(range(total), dots))
                n, d = lower_overlap_bound(dots, uncovered)
                assert (n, d) == (observed, dots)
    with pytest.raises(ValueError):
        lower_overlap_bound(0, 0)


def test_literal_threshold_is_strict_and_never_grants_approval(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    import hashlib
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({"kind": "GEOMETRY-AUDIT, NOT A SCORE",
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "grid": {"footprint_pixels": 100}, "lattice": {"uncovered_beyond_3px": 3, "source": {}}}))
    equal = check(audit, manifest, 10)
    assert equal["lower_bound_fraction"] == 0.7
    assert equal["budget_necessarily_exceeds_70_percent"] is False
    assert equal["submission_authorized"] is False
    over = check(audit, manifest, 11)
    assert over["budget_necessarily_exceeds_70_percent"] is True
    with pytest.raises(ValueError):
        check(audit, manifest, 101)
    manifest.write_text('{"changed":true}')
    with pytest.raises(ValueError):
        check(audit, manifest, 10)


def test_frozen_evidence_scope_and_lineage():
    evidence = json.loads((ROOT / "docs/data/historical-audit.json").read_text())
    assert len(evidence["sites"]) == 9
    assert len(evidence["pairwise"]) == 72
    assert all(c["duplicate_stop"] for c in evidence["pairwise"])
    assert all(r["lattice_duplicate"] and not r["new_submission_authorized"] for r in evidence["sites"])
    assert evidence["lineage"]["g25_g30_identical_positive_support"]
    assert evidence["lineage"]["g31_not_g32"] == evidence["lineage"]["removed_within_2px_of_labels"] == 2545
    assert evidence["lineage"]["g32_not_g31"] == evidence["lineage"]["g32_not_g36"] == 0
    assert evidence["lineage"]["g36_not_g32"] == 1200
    result = check(ROOT / "docs/data/historical-audit.json", ROOT / "data/focus_registry.json", 37654)
    assert result["budget_necessarily_exceeds_70_percent"]
    assert result["lower_bound_fraction"] == pytest.approx(31005 / 37654)


def test_preflight_cli_never_exits_success_on_inconclusive_budget():
    import subprocess
    import sys

    proc = subprocess.run([sys.executable, "scripts/preflight.py", "--dots", "100"],
                          capture_output=True, text=True, check=False)
    assert proc.returncode == 2
    result = json.loads(proc.stdout)
    assert result["budget_necessarily_exceeds_70_percent"] is False
    assert result["submission_authorized"] is False
    assert "NOT A UNIQUENESS PASS" in result["decision"]
