from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems32 import smgc  # noqa: E402
from gems32.paths import work_dir  # noqa: E402


def test_smgc_extra_stack_and_stationary_envelope():
    rng = np.random.default_rng(42)
    h, w = 64, 64
    foot = np.ones((h, w), dtype=bool)
    foot[:4, :] = False
    visible = np.zeros((h, w), dtype=bool)
    visible[32, 32] = True

    p_dual = rng.uniform(0.0, 1.0, size=(h, w)).astype(np.float32)
    s_exp = rng.uniform(0.0, 1.0, size=(h, w)).astype(np.float32)
    far_crest = rng.uniform(0.0, 1.0, size=(h, w)).astype(np.float32)
    p4_sharp = rng.uniform(0.0, 1.0, size=(h, w)).astype(np.float32)
    vis_relay = rng.uniform(0.0, 1.0, size=(h, w)).astype(np.float32)

    surf = smgc.compose_smgc_max_envelope_surface(
        s_exp=s_exp,
        p_dual=p_dual,
        far_crest=far_crest,
        p4_sharp=p4_sharp,
        vis_relay=vis_relay,
        visible_mask=visible,
        region_mask=foot,
    )
    assert surf.shape == (h, w)
    assert surf.dtype == np.float32
    assert np.isfinite(surf).all()
    assert float(surf.min()) >= 0.0 and float(surf.max()) <= 1.0
    assert float(surf[~foot].max()) == 0.0

    csst_path = work_dir() / "csst_bghf_extra_6ch.npy"
    if csst_path.exists():
        arr = np.load(csst_path, mmap_mode="r")
        assert arr.shape == (3730, 3292, 6)
        assert arr.dtype == np.float32
        assert np.isfinite(arr[::8, ::8, :]).all()


def test_cached_smgc_stack_integration():
    smgc_path = work_dir() / "smgc_extra_4ch.npy"
    if not smgc_path.exists():
        pytest.skip("Restore ignored SMGC feature cache for integration check")
    arr = np.load(smgc_path, mmap_mode="r")
    assert arr.shape == (3730, 3292, 4)
    assert arr.dtype == np.float32
    assert np.isfinite(arr[::8, ::8, :]).all()


def test_retracted_submission_geotiff_and_run_card():
    rc_path = ROOT / "docs" / "run-card.json"
    assert rc_path.exists()
    rc = json.loads(rc_path.read_text(encoding="utf-8"))

    assert rc["verdict"] == "negative"
    assert rc["ok_to_submit"] is False
    assert 0 < len(rc["note"]) <= 140
    assert rc["leakage_canary"]["passed"] is True
    assert rc["leakage_canary"]["max_oriented_auc"] <= 0.90
    assert rc["correlation_overlap_vs_registry"]["max_rank_correlation"] <= 0.90
    assert rc["correlation_overlap_vs_registry"]["max_dot_overlap_3px"] > 0.70

    tif_path = ROOT / rc["submission_file"]
    assert tif_path.exists()
    sha = hashlib.sha256(tif_path.read_bytes()).hexdigest()
    assert sha == rc["raster_sha256"]

    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert ds.shape == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert ds.nodata is None
        assert np.isfinite(arr).all()
        assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0

    pg = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "promotion_gate.py"), str(rc_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    pg_out = json.loads(pg.stdout)
    assert pg.returncode == 2
    assert pg_out["verdict"] == "negative"
    assert pg_out["ok_to_submit"] is False
    # Historical cards do not meet the literal all-registry rule.
    assert any("literal" in reason for reason in pg_out["reasons"])


class SMGCAndSubmissionTests(unittest.TestCase):
    def test_envelope(self):
        test_smgc_extra_stack_and_stationary_envelope()

    def test_retracted_card(self):
        test_retracted_submission_geotiff_and_run_card()
