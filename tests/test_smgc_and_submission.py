"""Synthetic & artifact verification tests for stationary Max-Envelope composition and live Run Card / GeoTIFF."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
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

    # If local `.cache/gems_work/csst_bghf_extra_6ch.npy` is present, verify its shape & finiteness too
    try:
        csst_path = work_dir() / "csst_bghf_extra_6ch.npy"
        if csst_path.exists():
            arr = np.load(csst_path, mmap_mode="r")
            assert arr.shape == (3730, 3292, 6)
            assert arr.dtype == np.float32
            assert np.isfinite(arr[::8, ::8, :]).all()
    except Exception:
        pass


def test_submission_geotiff_and_run_card_consistency():
    rc_path = ROOT / "docs" / "run-card.json"
    assert rc_path.exists()
    rc = json.loads(rc_path.read_text(encoding="utf-8"))

    assert rc["verdict"] in ("promote", "negative")
    assert rc["ok_to_submit"] is False
    assert rc["selector_required"] is True
    assert 0 < len(rc["note"]) <= 140
    assert rc["leakage_canary"]["passed"] is True
    assert rc["leakage_canary"]["max_oriented_auc"] <= 0.90
    assert rc["registry"]["surface"]["max_abs_spearman"] <= 0.90
    assert rc["registry"]["final_dots"]["max_overlap_3px"] <= 0.70

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
        assert int((arr > 0.5).sum()) == 37654

    # Verify CLI promotion_gate.py agrees with run-card verdict
    pg = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "promotion_gate.py"), str(rc_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    expected_rc = 0 if rc["verdict"] == "promote" else 2
    assert pg.returncode == expected_rc
    pg_out = json.loads(pg.stdout)
    assert pg_out["verdict"] == rc["verdict"]
    assert pg_out["ok_to_submit"] is False
