"""Emission (surface -> dotted mask) for karage3.

``poisson_disk_thin_priority`` is the template's fixed-spacing selector, copied verbatim from
GEMSDOE32 ``src/gems32/hypotheses.py`` (see PROVENANCE.md) so D2.8 controls are exact.
``greedy_coverage`` is the new K3-H5 arm: lazy-greedy (CELF) maximum coverage under the
competition's own 300 m triangular kernel, where each candidate dot's marginal gain is the
surface-rank mass it newly covers. Fixed-spacing Poisson is surface-blind; greedy spacing
adapts to where the surface actually puts mass.
"""
from __future__ import annotations

import heapq

import numpy as np
from scipy.ndimage import distance_transform_edt

from .metric import kernel as _kernel


def poisson_disk_thin_priority(
    candidates_mask: np.ndarray,
    priority: np.ndarray,
    min_dist_px: float = 2.8,
    existing_dots: np.ndarray | None = None,
    max_add: int | None = None,
) -> np.ndarray:
    """Greedy priority-ordered Poisson-disk selector enforcing Euclidean distance >= min_dist_px.
    (Verbatim template copy.)"""
    H, W = candidates_mask.shape
    selected = np.zeros((H, W), dtype=bool)
    blocked = np.zeros((H, W), dtype=bool)

    r_int = int(np.ceil(min_dist_px))
    dy_grid, dx_grid = np.mgrid[-r_int:r_int + 1, -r_int:r_int + 1]
    disk_offs = np.argwhere((dy_grid * dy_grid + dx_grid * dx_grid) < (min_dist_px * min_dist_px - 1e-6)) - r_int

    if existing_dots is not None and existing_dots.any():
        dist_ex = distance_transform_edt(~existing_dots)
        blocked |= dist_ex < (min_dist_px - 1e-6)

    elig = candidates_mask & ~blocked
    yy, xx = np.nonzero(elig)
    if yy.size == 0:
        return selected

    scores = priority[yy, xx]
    order = np.argsort(-scores, kind="mergesort")
    yy = yy[order]
    xx = xx[order]

    added = 0
    dy_off = disk_offs[:, 0]
    dx_off = disk_offs[:, 1]
    for r, c in zip(yy, xx):
        if blocked[r, c]:
            continue
        selected[r, c] = True
        added += 1
        if max_add is not None and added >= max_add:
            break
        nr = r + dy_off
        nc = c + dx_off
        ok = (nr >= 0) & (nr < H) & (nc >= 0) & (nc < W)
        blocked[nr[ok], nc[ok]] = True

    return selected


def top_n_mask(surface: np.ndarray, foot: np.ndarray, n: int) -> np.ndarray:
    """Mask of the n highest surface pixels inside the footprint."""
    s = np.where(foot, np.asarray(surface, dtype=np.float32), -np.inf)
    flat = s.ravel()
    idx = np.argpartition(flat, -n)[-n:]
    m = np.zeros(flat.shape, dtype=bool)
    m[idx] = True
    return m.reshape(s.shape) & foot


_OFFSETS: list[tuple[int, int, float]] | None = None


def _offsets() -> list[tuple[int, int, float]]:
    global _OFFSETS
    if _OFFSETS is None:
        out = []
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                k = float(_kernel(np.hypot(dy, dx)))
                if k > 0.0:
                    out.append((dy, dx, k))
        _OFFSETS = out
    return _OFFSETS


def greedy_coverage(
    rank: np.ndarray,
    foot: np.ndarray,
    n_dots: int,
    candidate_top: int = 300_000,
    seed: int = 3,
) -> tuple[np.ndarray, dict]:
    """Lazy-greedy (CELF) maximum kernel coverage of the surface-rank mass.

    Candidates: the ``candidate_top`` highest-rank footprint pixels. Gain of dot x =
    sum over the 300 m kernel disk of rank(y) * k(|x-y|) * (1 - cover(y)), where cover is the
    running max-kernel field of already-selected dots. Returns (mask, diagnostics) with the
    realised gain curve summary. Deterministic given the rank raster (seed only breaks exact
    float ties in heap order via index ordering)."""
    H, W = foot.shape
    rank = np.asarray(rank, dtype=np.float32)
    cand = top_n_mask(rank, foot, min(candidate_top, int(foot.sum())))
    yy, xx = np.nonzero(cand)
    offs = _offsets()

    cover = np.zeros((H, W), dtype=np.float32)
    selected = np.zeros((H, W), dtype=bool)

    def gain(r: int, c: int) -> float:
        g = 0.0
        for dy, dx, k in offs:
            nr, nc = r + dy, c + dx
            if 0 <= nr < H and 0 <= nc < W:
                g += float(rank[nr, nc]) * k * (1.0 - float(cover[nr, nc]))
        return g

    heap: list[tuple[float, int, int, int]] = []
    for i, (r, c) in enumerate(zip(yy.tolist(), xx.tolist())):
        heap.append((-gain(r, c), i, r, c))
    heapq.heapify(heap)

    gains: list[float] = []
    stale_pops = 0
    while heap and len(gains) < n_dots:
        neg_g, i, r, c = heapq.heappop(heap)
        if selected[r, c]:
            continue
        g_now = gain(r, c)
        if g_now < -neg_g - 1e-12:  # stale upper bound: reinsert with fresh gain
            stale_pops += 1
            heapq.heappush(heap, (-g_now, i, r, c))
            continue
        selected[r, c] = True
        gains.append(float(g_now))
        for dy, dx, k in offs:
            nr, nc = r + dy, c + dx
            if 0 <= nr < H and 0 <= nc < W and k > cover[nr, nc]:
                cover[nr, nc] = np.float32(k)

    diag = dict(
        n_candidates=int(yy.size), n_selected=int(selected.sum()),
        stale_pops=int(stale_pops),
        gain_first=float(gains[0]) if gains else 0.0,
        gain_last=float(gains[-1]) if gains else 0.0,
        gain_median=float(np.median(gains)) if gains else 0.0,
        covered_rank_mass=float((rank * cover)[foot].sum() / max(float(rank[foot].sum()), 1e-9)),
    )
    return selected & foot, diag
