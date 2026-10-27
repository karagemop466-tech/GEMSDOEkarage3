from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
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

    # Verify cached 4-channel SMGC stack on disk
    smgc_path = work_dir() / "smgc_extra_4ch.npy"
    assert smgc_path.exists()
    arr = np.load(smgc_path, mmap_mode="r")
    assert arr.shape == (3730, 3292, 4)
    assert arr.dtype == np.float32
    assert np.isfinite(arr[::8, ::8, :]).all()


def test_promoted_submission_geotiff_and_run_card():
    rc_path = ROOT / "docs" / "run-card.json"
    assert rc_path.exists()
    rc = json.loads(rc_path.read_text())

    assert rc["verdict"] == "promote"
    assert rc["ok_to_submit"] is True
    assert 0 < len(rc["note"]) <= 140
    assert rc["leakage_canary"]["passed"] is True
    assert rc["leakage_canary"]["max_oriented_auc"] <= 0.90
    assert rc["correlation_overlap_vs_registry"]["max_rank_correlation"] <= 0.90
    assert rc["correlation_overlap_vs_registry"]["max_dot_overlap_3px"] <= 0.70

    tif_path = ROOT / rc["submission_file"]
    assert tif_path.exists()
    sha = hashlib.sha256(tif_path.read_bytes()).hexdigest()
    assert sha == rc["raster_sha256"]

    ddir = data_dir()
    ctx = holdout.load_holdout_context(ddir)
    audit = submission.audit_geotiff(
        tif_path,
        ctx.foot,
        ctx.labels,
        mode="zeros",
        template_tif=ddir / "sample_submission.tif",
    )
    assert audit["all_checks_passed"] is True
    assert all(audit["checks"].values()), f"Failed checks: {audit['checks']}"
    assert audit["emitted_positive_pixels"] == 37654
    assert audit["on_catalogue_positive_pixels"] == 0
    assert audit["full_grid_finite_pixels"] == 12279160

    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert ds.shape == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert ds.nodata is None
        assert np.isfinite(arr).all()
        assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0

    # Verify CLI promotion_gate.py
    pg = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "promotion_gate.py"), str(rc_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    pg_out = json.loads(pg.stdout)
    assert pg_out["verdict"] == "promote"
    assert pg_out["reasons"] == []
