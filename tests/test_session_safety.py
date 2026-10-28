"""Synthetic safeguards for the 2026-10-28 negative review; no model is run."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.build_k3c_site import root_decision_html
from scripts.validate_raster import audit
from src.gems32 import submission

ROOT = Path(__file__).resolve().parents[1]


def test_current_run_card_is_negative_and_bound_to_fresh_evidence():
    evidence = ROOT / 'evidence/run-card-20261028-session.json'
    assert evidence.read_bytes() == (ROOT / 'docs/data/latest-run.json').read_bytes()
    card = json.loads(evidence.read_text())
    assert card['verdict'] == 'negative' and card['ok_to_submit'] is False
    assert card['selector_approval'] is False and card['slot_selected'] is False
    assert card['experiments_run'] == card['weekly_slots_used'] == 0
    assert card['raster_sha256'] is None and card['holdout_dti']['value'] is None
    assert card['correlation_overlap_vs_registry']['candidate_final_spearman'] is None
    assert card['submission_name'] is None and len(card['note']) <= 140
    audit_path = ROOT / card['evidence']['historical_nine_site_audit']
    assert hashlib.sha256(audit_path.read_bytes()).hexdigest() == card['evidence']['historical_audit_sha256']
    audit = json.loads(audit_path.read_text())
    assert len(audit['sites']) == 9 and len(audit['pairwise']) == 72
    assert all(row['fraction'] > .70 for row in audit['pairwise'])
    assert card['historical_reference_only']['duplicate_stop'] is True


def test_active_shared_template_is_byte_identical_to_pinned_manifest():
    manifest = json.loads((ROOT / 'registry/shared_template_97597a.json').read_text())
    assert manifest['commit'] == '97597a066d1c61d2c226fdba349716f41b30c1c6'
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected


def test_negative_public_decision_cannot_display_submission_authorization():
    # The publisher re-verifies every retained TIFF and accepts no caller-supplied
    # gate or selector state. The separate synthetic promote test lives in test_gate.
    banner, release = root_decision_html()
    assert 'OK TO SUBMIT? YES' not in banner
    assert 'OK TO SUBMIT? NO' in banner
    assert 'NOT APPROVED' in release


@pytest.mark.parametrize('name', [
    'run_k3c_session', 'run_csst_ablation', 'write_ccl_submission',
    'run_ccl', 'run_ccl_live', 'run_crsb_ablation',
    'exp1_screen', 'exp2_emission', 'exp3_final',
])
def test_historical_runners_stop_before_outputs(name, tmp_path):
    env = {**os.environ, 'GEMS_DATA_DIR': str(tmp_path / 'data'),
           'GEMS_WORK_DIR': str(tmp_path / 'work')}
    result = subprocess.run([sys.executable, f'scripts/{name}.py'], cwd=ROOT,
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert 'STOP: historical experiment runner is disabled' in result.stderr
    assert list(tmp_path.iterdir()) == []


def _write(path, values, nodata=None):
    with rasterio.open(path, 'w', driver='GTiff', width=3, height=3, count=1,
                       dtype='float32', crs='EPSG:32611', nodata=nodata,
                       transform=from_origin(243350, 4508550, 100, 100)) as ds:
        ds.write(np.asarray(values, dtype=np.float32), 1)


def test_shared_mask_defect_and_independent_cli_fail_closed(tmp_path, monkeypatch):
    template, candidate = tmp_path / 'reference.tif', tmp_path / 'masked.tif'
    _write(template, np.zeros((3, 3)))
    values = np.zeros((3, 3)); values[0, 0] = .5
    _write(candidate, values, nodata=.5)
    for key, value in {'EXPECTED_HEIGHT': 3, 'EXPECTED_WIDTH': 3,
                       'EXPECTED_FOOTPRINT_PIXELS': 9, 'EXPECTED_TOTAL_PIXELS': 9}.items():
        monkeypatch.setattr(submission, key, value)
    # Known upstream defect #66, documented rather than privately patched.
    old = submission.audit_geotiff(candidate, np.ones((3, 3), bool),
                                   np.zeros((3, 3), bool), template_tif=template)
    assert old['all_checks_passed'] is True
    fresh = audit(candidate, template)
    assert fresh['inside_masked_count'] == 1 and not fresh['core_format_pass']
    command = [sys.executable, 'scripts/check_submission.py', str(candidate),
               '--template', str(template), '--strict-finite']
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and '[FAILED]' in result.stderr
    assert 'NOT AUTHORIZED' in result.stdout


def test_external_candidate_mask_is_not_implicitly_packaged(tmp_path):
    template, candidate = tmp_path / 'reference.tif', tmp_path / 'external-mask.tif'
    _write(template, np.zeros((3, 3)))
    _write(candidate, np.zeros((3, 3)))
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(candidate, 'r+') as ds:
            ds.write_mask(np.full((3, 3), 255, dtype=np.uint8))
    assert candidate.with_suffix('.tif.msk').exists()
    report = audit(candidate, template)
    assert report['checks']['self_contained_tiff'] is False
    assert report['candidate_sidecars'] and not report['core_format_pass']


def test_archived_csst_pages_are_repeatable_and_do_not_claim_portal_success():
    paths = [ROOT / 'docs/csst-bghf' / p for p in ('index.html', 'executive-summary.html', 'research.md', 'run-card.json')]
    before = [p.read_bytes() for p in paths]
    subprocess.run([sys.executable, 'scripts/build_csst_site.py'], cwd=ROOT, check=True, timeout=30)
    assert before == [p.read_bytes() for p in paths]
    for path in paths[:2]:
        content = path.read_text()
        assert 'DO NOT SUBMIT' in content
        assert '100% GREEN' not in content
        assert 'eliminates the prior' not in content
        assert 'organizer template and portal acceptance are unverified' in content


def test_witness_cli_never_overwrites_a_receipt(tmp_path):
    receipt = tmp_path / 'old.json'
    receipt.write_text('original receipt')
    result = subprocess.run([sys.executable, 'scripts/audit_k3c_literal_witness.py', '--out', str(receipt)],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and 'refusing to overwrite' in result.stderr
    assert receipt.read_text() == 'original receipt'
