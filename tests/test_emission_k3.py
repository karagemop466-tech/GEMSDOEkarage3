import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from karage3.emission_k3 import greedy_coverage, poisson_disk_thin_priority, top_n_mask  # noqa: E402


def _grid(n=40):
    foot = np.ones((n, n), dtype=bool)
    rng = np.random.default_rng(7)
    surf = rng.random((n, n)).astype(np.float32)
    return surf, foot


def test_top_n():
    surf, foot = _grid()
    m = top_n_mask(surf, foot, 25)
    assert int(m.sum()) == 25
    assert surf[m].min() >= np.partition(surf.ravel(), -25)[-25] - 1e-6


def test_poisson_spacing_and_budget():
    surf, foot = _grid()
    m = poisson_disk_thin_priority(surf > 0, surf, min_dist_px=2.8, max_add=30)
    assert int(m.sum()) == 30
    # no two selected dots closer than 2.8 px (second-nearest distance via sequential check)
    pts = np.argwhere(m)
    for i, p in enumerate(pts):
        d = np.hypot(*(pts - p).T)
        d[i] = np.inf
        assert d.min() >= 2.8 - 1e-6


def test_greedy_prefix_and_coverage():
    surf, foot = _grid()
    rank = surf / surf.max()
    mask, diag, order = greedy_coverage(rank, foot, 20, candidate_top=400)
    assert int(mask.sum()) == 20 and len(order) == 20
    pre = np.zeros_like(mask)
    for r, c in order[:10]:
        pre[r, c] = True
    assert int(pre.sum()) == 10 and (pre & mask).sum() == 10  # budgets are prefixes
    assert diag["gain_first"] >= diag["gain_last"] - 1e-6
