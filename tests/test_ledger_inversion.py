"""Unit tests for the Live-Ledger Inversion instrument (src/gems32/ledger_inversion.py)."""
from __future__ import annotations

import numpy as np

from gems32 import ledger_inversion as li
from gems32.metric import components


def _toy():
    rng = np.random.default_rng(0)
    H, W = 120, 130
    truth = np.zeros((H, W), bool)
    for r in range(10, 110):
        truth[r, 40 + (r // 30)] = True
    truth[60, 5:125] = True
    active = np.ones((H, W), bool)
    active[:3] = False
    return rng, truth, active


def test_design_row_tp_is_exact_against_metric():
    rng, truth, active = _toy()
    pred = np.zeros(truth.shape, np.float32)
    pred[::3, 41] = 1.0
    pred[61, ::3] = 1.0
    pred[rng.integers(0, 120, 200), rng.integers(0, 130, 200)] = 1.0
    pred[30:36, 90:96] = 0.4                               # soft block
    spec = li.StrataSpec(names=["t"], levels=[truth.astype(np.int8)], n_levels=[2],
                         level_labels=[["no", "yes"]], active=active)
    row = li.design_row(pred, spec)
    proj = li.project(row, spec, np.array([0.0, 1.0]))
    ex = components(np.where(active, pred, 0), truth & active)
    assert abs(proj["tp"] - ex["TP_w"]) <= 1e-6 * ex["TP_w"]    # exact identity (kernel-max field stored as float32)
    exact_dti = ex["TP_w"] / (ex["TP_w"] + 0.2 * ex["FP_w"] + 0.8 * ex["FN_w"])
    assert abs(proj["dti"] - exact_dti) < 0.01                # M approximation enters with weight 0.2


def test_fit_recovers_relative_stratum_density():
    """Synthetic ledger: rasters scored by the exact expected-DTI identity under known densities."""
    rng = np.random.default_rng(1)
    H, W = 90, 90
    active = np.ones((H, W), bool)
    lv = np.zeros((H, W), np.int8)
    lv[:, 45:] = 1                                       # right half is the rich stratum
    spec = li.StrataSpec(names=["half"], levels=[lv], n_levels=[2], level_labels=[["L", "R"]], active=active)
    lam_true = np.array([0.002, 0.03])
    A, B, N = [], [], []
    for k in range(14):
        p = np.zeros((H, W), np.float32)
        n = 60 + 40 * k
        frac_right = (k % 7) / 6.0
        nr = int(n * frac_right)
        p[rng.integers(0, H, n - nr), rng.integers(0, 45, n - nr)] = 1
        p[rng.integers(0, H, nr), rng.integers(45, W, nr)] = 1
        r = li.design_row(p, spec)
        A.append(r["A"]); B.append(r["B"]); N.append(r["N"])
    A, B, N = np.array(A), np.array(B), np.array(N)
    s = li.predict_components(A, B, N, spec.sizes, lam_true)["dti"]
    f = li.fit(A, B, N, s, spec, ridge=1e-9)
    ratio = f["lambda"][1] / f["lambda"][0]
    assert 10.0 < ratio < 20.0                              # true ratio 15
    assert np.max(np.abs(f["pred"] - s)) < 2e-3
    lo = li.loo(A, B, N, s, spec, ridge=1e-9, theta0=f["theta"])
    assert lo["mae"] < 5e-3 and lo["spearman"] > 0.9


def test_projection_bounds_and_reference_levels():
    _, truth, active = _toy()
    spec = li.StrataSpec(names=["t"], levels=[truth.astype(np.int8)], n_levels=[2],
                         level_labels=[["no", "yes"]], active=active)
    theta = np.array([np.log(1e-3), np.log(50.0)])
    lam = li.strata_lambda(theta, spec)
    assert np.isclose(lam[1] / lam[0], 50.0)
    eff = li.factor_effects(theta, spec)
    assert np.isclose(eff["t"]["yes"], 50.0) and eff["t"]["no"] == 1.0
    p = np.zeros(truth.shape, np.float32)
    p[::4, ::4] = 1.0
    out = li.project(li.design_row(p, spec), spec, lam)
    assert 0.0 <= out["dti"] <= 1.0
