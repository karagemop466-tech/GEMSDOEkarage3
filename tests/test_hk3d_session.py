"""Unit and end-to-end regression tests for Session 5 Lane H-K3D (TGSF-BVCD).

Runs cleanly both with `.cache/` present and on clean CI checkouts without `.cache/`.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "src", ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from gems32 import crsb_gub  # noqa: E402
from karage3 import hk3d_tgsf, holdout_v32_ref  # noqa: E402
from scripts import promotion_gate, validate_raster  # noqa: E402


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_ir_k3_27_deposit_ty_column_vetoes_tufa_mimics() -> None:
    src = Path(crsb_gub.__file__).read_text(encoding="utf-8")
    assert '"Deposit_ty"' in src, "IR-K3-27 regression: Deposit_ty must be checked before Dep_Type/Type"


def test_strict_lidar_channel_isolation_61_to_55() -> None:
    assert hk3d_tgsf.LIDAR_GLOBAL_COLS_61 == {45, 46, 47, 48, 54, 60}
    assert len(hk3d_tgsf.MNOLIDAR_COL_INDICES_55) == 55
    for c in hk3d_tgsf.LIDAR_GLOBAL_COLS_61:
        assert c not in hk3d_tgsf.MNOLIDAR_COL_INDICES_55


def test_fold_grain_alignment_and_binary_emitter_unit() -> None:
    rng = np.random.default_rng(42)
    h, w = 80, 80
    foot = np.ones((h, w), dtype=bool)
    foot[:4, :] = False
    vis = np.zeros((h, w), dtype=bool)
    vis[20:60, 40] = True  # N-S fault trace

    field = rng.uniform(0.1, 1.0, size=(h, w)).astype(np.float32)
    align = hk3d_tgsf.compute_fold_grain_alignment(field, vis, foot)
    assert align.shape == (h, w)
    assert np.isfinite(align).all()
    assert float(align[foot].min()) >= 0.80 and float(align[foot].max()) <= 1.20
    assert float(align[~foot].max()) == 0.0

    crsb_mock = rng.uniform(0.0, 1.0, size=(h, w, 16)).astype(np.float32)
    hk3d_mock = rng.uniform(0.0, 1.0, size=(h, w, 4)).astype(np.float32)
    p_oof = rng.uniform(0.05, 0.95, size=(h, w)).astype(np.float32)
    surf, grain = hk3d_tgsf.build_hk3d_surface(
        p_oof, crsb_mock, hk3d_mock, vis, foot, return_grain=True
    )
    assert surf.shape == (h, w) and grain.shape == (h, w)
    assert np.isfinite(surf).all()
    assert float(surf[~foot].max()) == 0.0

    from scipy.ndimage import distance_transform_edt
    elig_b3 = foot & (~vis) & (distance_transform_edt(~vis) > 3.0)
    dots, diag = hk3d_tgsf.emit_hk3d_binary(
        surf, vis, elig_b3, foot, budget=25, min_sep_px=3.3, b_collar_px=3.0
    )
    assert dots.dtype == bool and int(dots.sum()) == 25
    assert not bool((dots & vis).any()), "Zero on-catalogue leakage violated"
    assert not bool((dots & ~elig_b3).any()), "B=3 collar violated"
    assert diag["n_emitted"] == 25


def test_holdout_v32_fp_conserving_counts_zero_truth_cells() -> None:
    from gems32 import holdout
    from gems32.metric import kernel
    from scipy.ndimage import distance_transform_edt

    h, w = 40, 40
    foot = np.ones((h, w), dtype=bool)
    sl0 = (slice(0, 20), slice(0, 40))
    sl1 = (slice(20, 40), slice(0, 40))

    # Cell 0 has 1 truth pixel at (10, 10); Cell 1 has 0 truth pixels (#41 test)
    t0_grid = np.zeros((20, 40), dtype=bool)
    t0_grid[10, 10] = True
    k_dg0 = kernel(distance_transform_edt(~t0_grid))
    d_vis = np.full((20, 40), 20.0, dtype=np.float32)

    cell0 = holdout.PreparedCell(
        key="draw20_fold0", seed=20, fold=0, bbox=sl0,
        active_sub=np.ones((20, 40), dtype=bool),
        truth_coords=(np.array([10]), np.array([10])),
        k_dg_sub=k_dg0, n_truth=1, d_vis_sub=d_vis,
    )
    cell1 = holdout.PreparedCell(
        key="draw20_fold1", seed=20, fold=1, bbox=sl1,
        active_sub=np.ones((20, 40), dtype=bool),
        truth_coords=(np.array([], dtype=int), np.array([], dtype=int)),
        k_dg_sub=np.zeros((20, 40), dtype=np.float32), n_truth=0, d_vis_sub=d_vis,
    )
    # Also fill fold2 and fold3 with 0 truth & 0 emitted so per_quadrant_dti resolves all 4 folds
    empty_cells = [
        holdout.PreparedCell(
            key=f"draw20_fold{f}", seed=20, fold=f, bbox=sl1,
            active_sub=np.zeros((20, 40), dtype=bool),
            truth_coords=(np.array([], dtype=int), np.array([], dtype=int)),
            k_dg_sub=np.zeros((20, 40), dtype=np.float32), n_truth=0, d_vis_sub=d_vis,
        )
        for f in (2, 3)
    ]
    ctx = holdout.HoldoutContext(
        foot=foot, labels=np.zeros((h, w), dtype=bool), sgmc_off=np.zeros((h, w), dtype=bool),
        near_visible=np.zeros((h, w), dtype=bool), quad=np.zeros((h, w), dtype=np.int8),
        quad_bboxes={0: sl0, 1: sl1, 2: sl1, 3: sl1},
        cells=[cell0, cell1, *empty_cells],
        sgmc_truth_coords=(np.array([], dtype=int), np.array([], dtype=int)),
        sgmc_k_dg=np.zeros((h, w), dtype=np.float32), sgmc_n_truth=0,
        sgmc_quad_truth_coords={}, sgmc_quad_n_truth={}, visible_by_cell={},
    )
    pred = np.zeros((h, w), dtype=bool)
    pred[10, 10] = True  # exact hit in cell0 -> TP=1, FP=0 in cell0
    pred[30, 10:20] = True  # 10 pure FPs in zero-truth cell1!
    res = holdout_v32_ref.evaluate_censored_or_standard_multi(pred, ctx, n_boot=20)
    # Without #41 fix, pooled DTI would be 1/(1+0) = 1.0! With #41 fix, FP=10 -> 1 / (1 + 0.2*10) = 1/3!
    assert abs(res["pooled_dti"] - (1.0 / 3.0)) < 1e-6
    assert res["folds"]["draw20_fold1"]["fp"] == 10.0


def test_hk3d_saved_geotiff_run_card_witness_and_site_determinism() -> None:
    card = json.loads((ROOT / "docs" / "hk3d" / "run-card.json").read_text(encoding="utf-8"))
    ev_card = json.loads((ROOT / "evidence" / "hk3d_run_card.json").read_text(encoding="utf-8"))
    canary = json.loads((ROOT / "evidence" / "leakage-canary-61ch.json").read_text(encoding="utf-8"))
    witness = json.loads((ROOT / "evidence" / "hk3d-literal-witness-audit-20261028.json").read_text(encoding="utf-8"))

    assert card == ev_card
    assert canary["passed"] is True and canary["n_features_tested"] == 61
    assert canary["max_oriented_auc"] <= 0.90

    gate = promotion_gate.assess(card)
    assert card["verdict"] == gate["verdict"] == "negative"
    assert card["ok_to_submit"] is False and gate["ok_to_submit"] is False
    assert len(card["note"]) <= 140
    assert card["experiments_run"] == 3

    # Verify E3 (20,000 <= 22,163) empirical lattice test & E2 B=3 SGMC/FRAG500M findings
    e1 = card["experiments"]["E1_B2_37654"]
    e2 = card["experiments"]["E2_B3_Depletion_37654"]
    e3 = card["experiments"]["E3_HighPrec_20000"]
    assert e2["frag500m_24cell"]["pooled_dti"] > e1["frag500m_24cell"]["pooled_dti"]
    assert e2["live_diagnostics"]["sgmc_prevalence_calibrated_dti"] > card["experiments"]["CTRL_champion_02778_rule"]["sgmc_cal_dti"]
    assert e3["live_diagnostics"]["emitted_dots"] == 20000 <= 22163
    assert e3["live_diagnostics"]["literal_3px_overlap_vs_r13_lattice"] > 0.99

    tif_path = ROOT / card["submission_file"]
    zip_path = ROOT / card["zip_submission_file"]
    assert tif_path.is_file() and zip_path.is_file()
    assert _sha256_bytes(tif_path.read_bytes()) == card["raster_sha256"] == witness["candidate_sha256"]
    assert _sha256_bytes(zip_path.read_bytes()) == card["zip_sha256"]
    assert witness["duplicate_stop"] is True and witness["within_3px_fraction"] > 0.70

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.namelist() == [tif_path.name]
        assert _sha256_bytes(zf.read(tif_path.name)) == card["raster_sha256"]

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert ds.shape == (3730, 3292)
        assert ds.crs.to_epsg() == 32611
        assert [round(float(x), 4) for x in ds.transform[:6]] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]
        assert ds.nodata is None
        arr = ds.read(1)
        assert int(np.isfinite(arr).sum()) == 3730 * 3292
        assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
        assert int((arr > 0.5).sum()) == 37654

    # Deterministic site build check
    pages = [ROOT / "docs" / "hk3d" / "index.html", ROOT / "docs" / "hk3d" / "how-to-submit.html"]
    before = [p.read_bytes() for p in pages]
    subprocess.run([sys.executable, "scripts/build_hk3d_site.py"], cwd=ROOT, check=True)
    assert before == [p.read_bytes() for p in pages]
    for p in pages:
        txt = p.read_text(encoding="utf-8")
        assert "DO NOT SUBMIT" in txt
        assert "OK TO SUBMIT? YES" not in txt
        assert "OK TO DOWNLOAD AND SUBMIT: YES" not in txt


import unittest  # noqa: E402


class HK3DSessionUnittestSuite(unittest.TestCase):
    def test_all_hk3d_invariants(self) -> None:
        test_ir_k3_27_deposit_ty_column_vetoes_tufa_mimics()
        test_strict_lidar_channel_isolation_61_to_55()
        test_fold_grain_alignment_and_binary_emitter_unit()
        test_holdout_v32_fp_conserving_counts_zero_truth_cells()
        test_hk3d_saved_geotiff_run_card_witness_and_site_determinism()

