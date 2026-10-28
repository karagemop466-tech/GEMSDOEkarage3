from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import rasterio
import pytest

from gems32 import holdout, smgc, submission
from gems32.paths import data_dir, work_dir

ROOT = Path(__file__).resolve().parents[1]


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

    # Verify cached 4-channel SMGC stack on disk
    smgc_path = work_dir() / "smgc_extra_4ch.npy"
    if not smgc_path.exists():
        pytest.skip("Optional ignored SMGC feature cache is absent; synthetic composition passed")
    arr = np.load(smgc_path, mmap_mode="r")
    assert arr.shape == (3730, 3292, 4)
    assert arr.dtype == np.float32
    assert np.isfinite(arr[::8, ::8, :]).all()


def test_superseded_submission_geotiff_and_run_card():
    rc = json.loads((ROOT / "docs" / "run-card.json").read_text())
    assert rc["verdict"] == "negative"
    assert rc["ok_to_submit"] is False
    assert rc["correlation_and_overlap_vs_registry"]["literal_all_rasters_final_passed"] is False
    tif_path = ROOT / rc["submission_file"]
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == rc["raster_sha256"]
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert np.isfinite(arr).all()
        assert 0 <= float(arr.min()) <= float(arr.max()) <= 1
    # Grid/footprint comparison requires the missing template; format is not promotion.
    pg = subprocess.run([sys.executable, str(ROOT / "scripts" / "promotion_gate.py"), str(ROOT / "docs" / "run-card.json")], capture_output=True, text=True)
    assert pg.returncode == 2
    assert json.loads(pg.stdout)["verdict"] == "negative"
