from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import rasterio

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



def test_optional_cached_smgc_stack():
    smgc_path = work_dir() / "smgc_extra_4ch.npy"
    if not smgc_path.exists():
        pytest.skip("historical derived feature cache is not present")
    arr = np.load(smgc_path, mmap_mode="r")
    assert arr.shape == (3730, 3292, 4)
    assert arr.dtype == np.float32
    assert np.isfinite(arr[::8, ::8, :]).all()


def test_historical_smgc_fails_literal_registry_and_is_not_approved():
    rc = json.loads((ROOT / "evidence/hk3_smgc_run_card.json").read_text())
    assert rc["correlation_and_overlap_vs_registry"]["literal_all_rasters_final_passed"] is False
    assert rc["correlation_and_overlap_vs_registry"]["literal_5px_calibration_lattice_probe"]["within_3px_fraction"] > 0.70
    tif_path = ROOT / rc["submission_file"]
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == rc["raster_sha256"]
    # This inspects bytes, not the missing official template or portal acceptance.
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1 and np.isfinite(arr).all()
        assert float(arr.min()) >= 0 and float(arr.max()) <= 1
    pg = subprocess.run([sys.executable, str(ROOT / "scripts/promotion_gate.py"),
                         str(ROOT / "evidence/hk3_smgc_run_card.json")], capture_output=True, text=True)
    assert pg.returncode == 2
    assert json.loads(pg.stdout)["verdict"] == "negative"
    assert json.loads((ROOT / "docs/run-card.json").read_text())["verdict"] == "negative"
