"""Lane K3-CCL: unit tests for the dot emitter / geometry features and run-card consistency."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from karage3 import ccl
from scripts.promotion_gate import assess

ROOT = Path(__file__).resolve().parents[1]


def test_greedy_dots_respects_separation_budget_and_mask():
    rng = np.random.default_rng(0)
    score = rng.random((60, 60)).astype(np.float32)
    allowed = np.ones_like(score, bool)
    allowed[:, :10] = False
    dots = ccl.greedy_dots(score, allowed, budget=150, min_sep=2.8)
    ys, xs = np.nonzero(dots)
    assert 0 < ys.size <= 150
    assert not dots[:, :10].any()
    d = np.hypot(ys[:, None] - ys[None, :], xs[:, None] - xs[None, :])
    np.fill_diagonal(d, 99)
    assert d.min() >= 2.8


def test_greedy_quota_caps_zone():
    score = np.ones((40, 40), np.float32)
    zone = np.zeros_like(score, bool)
    zone[:20] = True
    dots = ccl.greedy_dots(score, np.ones_like(zone), budget=10_000, min_sep=2.8, quota=[(zone, 5)])
    assert dots[zone].sum() == 5


def test_along_strike_feature_separates_tip_continuation_from_parallel_splay():
    h, w = 80, 80
    vis = np.zeros((h, w), bool)
    vis[40, 10:40] = True                      # E-W trace ending at x=39
    z = np.zeros((h, w), np.float32)
    g = ccl.catalogue_geometry(vis, z + 1.0, z)
    along = g[..., ccl.GEOM_NAMES.index("vis_along_strike")]
    assert along[40, 50] > 0.9                 # beyond the tip, along strike
    assert along[30, 25] < -0.9                # parallel offset, perpendicular to strike
    assert g[40, 25, 0] == 0                   # on the trace: log1p(0)


def test_ccl_run_card_is_negative_and_bound_to_bytes():
    card = json.loads((ROOT / "evidence/ccl_run_card.json").read_text())
    assert card == json.loads((ROOT / "docs/ccl/run-card.json").read_text())
    tif = ROOT / card["files"]["tif"]
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False and card["slot_selected"] is False
    assert assess(card)["verdict"] == "negative"
    assert 0 < len(card["note"]) <= 140
    assert card["registry"]["literal_all_rasters_final_passed"] is False
    assert card["registry"]["final_dots"]["null_calibrated_passed"] is False
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    lo, hi = card["holdout"]["ci95"]
    assert lo <= card["holdout"]["dti"] <= hi
    assert max(max(a, 1 - a) for a in card["feature_auc"]) <= 0.90
    assert "not a score" in card["live_ledger_projection"]["label"].lower()


def test_ccl_tif_format_on_saved_bytes():
    rasterio = pytest.importorskip("rasterio")
    card = json.loads((ROOT / "evidence/ccl_run_card.json").read_text())
    with rasterio.open(ROOT / card["files"]["tif"]) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.crs.to_epsg() == 32611 and ds.shape == (3730, 3292)
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
    assert np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
    assert int((a > 0).sum()) == 37654


def test_ccl_site_is_deterministic_and_says_do_not_submit():
    import scripts.build_ccl_site as b
    for path, text in b.build().items():
        assert path.read_text() == text
        assert "DO NOT SUBMIT" in text or "NO file" in text
