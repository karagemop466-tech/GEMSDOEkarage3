"""Live-score covariate instrument: what explains OWNER-REPORTED leaderboard scores.

Scope and honesty contract
--------------------------
Every number this module produces is fitted to **OWNER-REPORT** scores from
``docs/score-ledger.csv`` (the owner's transcription of DrivenData submission screens).  None of
those scores has an organizer receipt binding it to exact raster bytes (IR-32-SCORE-01), so the
outputs of this module are *diagnostics about the portfolio*, never leaderboard-score
predictions and never promotion evidence.  A projection must not be written as a score.

What it adds beyond ``docs/research/instrument-calibration.md`` (which re-scores 12 stored
artifacts on local holdout instruments): a covariate-level audit across every ledger row whose
raster bytes are locally pinned.  The features are *intrinsic to the submitted raster* (dot
count, catalogue proximity, family overlap, self-kernel redundancy), so the question answered is
"which design covariates of a submission co-vary with its reported live score", including the
size of the gap between the champion family and every other detector family.

Matching rules (deterministic, auditable)
-----------------------------------------
A ledger row is joined to a local GeoTIFF by, in order:
1. exact equality of normalized names (lowercase, alphanumeric only, variant suffixes
   ``-zeros/-nan/-allfinite/-nanoutside/-zero/-hard`` stripped);
2. containment of one normalized name in the other (site prefixes such as ``gemsdoe32-`` are
   tolerated), preferring same-repo files and then the shortest stem;
3. intersection of *strong* hash tokens (``[0-9a-f]{8,}`` containing at least one letter a-f and
   at least one digit), which excludes calendar-date runs such as ``20261004``.
Every match records the rule that produced it, and the caller is expected to audit the printed
join table; ambiguous matches must be excluded, not guessed.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt

VARIANT_SUFFIXES = ("zeros", "nan", "allfinite", "nanoutside", "zero", "hard", "candidate")
_TOKEN_RE = re.compile(r"[0-9a-f]{8,}")
DISK3 = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)


def normalize_name(name: str) -> str:
    """Lowercase alphanumeric key with extension and variant suffixes removed."""
    s = name.lower()
    s = re.sub(r"\.(tif|tiff)$", "", s)
    changed = True
    while changed:
        changed = False
        for suf in VARIANT_SUFFIXES:
            if s.endswith("-" + suf) or s.endswith("_" + suf):
                s = s[: -(len(suf) + 1)]
                changed = True
    return re.sub(r"[^a-z0-9]", "", s)


def strong_tokens(name: str) -> set[str]:
    """Hash-like tokens that cannot be calendar dates: >=8 hex chars, >=1 letter, >=1 digit."""
    out = set()
    for tok in _TOKEN_RE.findall(name.lower()):
        if any(c in "abcdef" for c in tok) and any(c.isdigit() for c in tok):
            out.add(tok)
    return out


@dataclass
class LedgerRow:
    site: str
    submission: str
    score: float
    source_url: str
    raw_score: str


def parse_ledger(path: Path) -> tuple[list[LedgerRow], list[dict]]:
    """Parse the score ledger; return (scored rows, excluded rows with reasons)."""
    import csv

    scored, excluded = [], []
    with Path(path).open() as fh:
        for r in csv.DictReader(fh):
            site = r.get("site", "")
            raw = r.get("score", "")
            if site.startswith("DrivenData") or site.lower().startswith("drivendata"):
                excluded.append({"site": site, "submission": r.get("submission", ""),
                                 "raw_score": raw, "reason": "other teams' leaderboard rows; no local raster"})
                continue
            try:
                score = float(raw)
            except ValueError:
                excluded.append({"site": site, "submission": r.get("submission", ""),
                                 "raw_score": raw, "reason": "score not a single parseable number"})
                continue
            if not 0.0 <= score <= 1.0:
                excluded.append({"site": site, "submission": r.get("submission", ""),
                                 "raw_score": raw, "reason": "score outside [0,1]"})
                continue
            scored.append(LedgerRow(site=site, submission=r.get("submission", ""), score=score,
                                    source_url=r.get("source_url", ""), raw_score=raw))
    return scored, excluded


@dataclass
class Candidate:
    path: Path
    stem: str
    repo: str

    @property
    def norm(self) -> str:
        return normalize_name(self.stem)

    @property
    def tokens(self) -> set[str]:
        return strong_tokens(self.stem)


def match_row(row: LedgerRow, candidates: list[Candidate]) -> tuple[Candidate | None, str]:
    """Deterministic ledger-row -> local-raster join; returns (candidate, rule) with rule '' if none.

    Containment requires the shorter normalized name to be at least 12 characters: without that
    guard, a generic stem like ``submission`` (10 chars) "contains into" every ledger name that
    happens to contain the word, and files get joined to the wrong rows.
    """
    want = normalize_name(row.submission)
    want_tokens = strong_tokens(row.submission)
    if not want:
        return None, ""

    MIN_CONTAIN = 12

    def site_tag(c: Candidate) -> int:
        return 0 if c.repo.lower() == row.site.lower() else 1

    exact = [c for c in candidates if c.norm == want]
    if exact:
        return min(exact, key=lambda c: (site_tag(c), len(c.stem))), "exact-normalized"

    contains = [c for c in candidates
                if (want in c.norm and min(len(want), len(c.norm)) >= MIN_CONTAIN)
                or (c.norm in want and min(len(want), len(c.norm)) >= MIN_CONTAIN)]
    if contains:
        return min(contains, key=lambda c: (site_tag(c), len(c.stem))), "containment"

    token = [c for c in candidates if c.tokens & want_tokens]
    if token:
        return min(token, key=lambda c: (site_tag(c), len(c.stem))), "hash-token"
    return None, ""


def read_mask(path: Path, footprint: np.ndarray) -> np.ndarray:
    """Positive pixels of a raster restricted to the footprint, validated against the grid."""
    import rasterio

    with rasterio.open(path) as ds:
        if ds.shape != footprint.shape:
            raise ValueError(f"{path}: shape {ds.shape} != footprint {footprint.shape}")
        arr = ds.read(1)
    mask = np.isfinite(arr) & (arr > 0) & footprint
    return mask


def mask_digest(mask: np.ndarray) -> str:
    return hashlib.sha256(np.packbits(np.asarray(mask, bool)).tobytes()).hexdigest()


def within3_fraction(mask: np.ndarray, reference: np.ndarray) -> float:
    """Fraction of ``mask`` dots within 3 px of a ``reference`` dot (directional)."""
    mask = np.asarray(mask, bool)
    reference = np.asarray(reference, bool)
    if not mask.any():
        return float("nan")
    if not reference.any():
        return 0.0
    near = binary_dilation(reference, structure=DISK3)
    return float(near[mask].mean())


@dataclass
class RasterFeatures:
    dots: int
    log10_dots: float
    frac_on_catalogue: float
    frac_within3_catalogue: float
    median_dist_catalogue_px: float
    frac_within3_h195: float
    frac_within3_champion: float
    mean_self_kernel: float


def raster_features(mask: np.ndarray, catalogue: np.ndarray, h195: np.ndarray,
                    champion: np.ndarray) -> RasterFeatures:
    """Intrinsic covariates of one submission mask (no truth beyond public catalogues)."""
    from gems32.metric import credit_audit

    mask = np.asarray(mask, bool)
    catalogue = np.asarray(catalogue, bool)
    n = int(mask.sum())
    if n == 0:
        raise ValueError("empty mask")
    on_cat = int((mask & catalogue).sum())
    if catalogue.any():
        dist = distance_transform_edt(~catalogue)
        med = float(np.median(dist[mask]))
    else:
        med = float("inf")
    audit = credit_audit(mask.astype(np.float64))
    return RasterFeatures(
        dots=n,
        log10_dots=float(np.log10(n)),
        frac_on_catalogue=on_cat / n,
        frac_within3_catalogue=within3_fraction(mask, catalogue),
        median_dist_catalogue_px=med,
        frac_within3_h195=within3_fraction(mask, h195),
        frac_within3_champion=within3_fraction(mask, champion),
        mean_self_kernel=float(audit.mean_self_kernel),
    )


FEATURE_ORDER = ("log10_dots", "frac_within3_h195", "frac_within3_catalogue",
                 "frac_on_catalogue", "mean_self_kernel")


def spearman(x: list[float] | np.ndarray, y: list[float] | np.ndarray) -> tuple[float, float]:
    """Spearman rho and two-sided p-value."""
    from scipy.stats import spearmanr

    r = spearmanr(np.asarray(x, float), np.asarray(y, float))
    return float(r.statistic), float(r.pvalue)


def loo_linear_regression(x: np.ndarray, y: np.ndarray) -> dict:
    """Leave-one-out refit of a standardized linear regression; returns fit-quality diagnostics.

    x: (n, p) feature matrix; y: (n,) targets.  Predictions are on held-out folds only.
    """
    from sklearn.linear_model import LinearRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = x.shape[0]
    if n < 4:
        raise ValueError("LOO needs at least 4 rows")
    preds = np.empty(n)
    for i in range(n):
        keep = np.arange(n) != i
        model = make_pipeline(StandardScaler(), LinearRegression())
        model.fit(x[keep], y[keep])
        preds[i] = float(model.predict(x[i:i + 1])[0])
    resid = y - preds
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    rho, p = spearman(preds, y)
    return {
        "n": int(n),
        "loo_r2": 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
        "loo_mae": float(np.mean(np.abs(resid))),
        "loo_spearman": rho,
        "loo_spearman_p": p,
        "predictions": preds.tolist(),
    }


def full_fit_coefficients(x: np.ndarray, y: np.ndarray, names: list[str]) -> list[dict]:
    """Standardized coefficients of the full-sample fit, for direction/size reading only."""
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler

    x = np.asarray(x, float)
    y = np.asarray(y, float)
    sx = StandardScaler().fit_transform(x)
    sy = StandardScaler().fit_transform(y.reshape(-1, 1)).ravel()
    model = LinearRegression().fit(sx, sy)
    return [{"feature": nm, "standardized_beta": float(b)}
            for nm, b in zip(names, model.coef_)]


def lattice_hole_bound(lattice_mask: np.ndarray, footprint: np.ndarray) -> dict:
    """Exact pigeonhole quantification of the calibration-lattice novelty stop (IR-42-UNIQ-01).

    A dot set passes the literal "<=70% of dots within 3 px of the lattice" rule only if at
    least 30% of its dots sit in *holes*: footprint pixels farther than 3 px from every lattice
    dot.  With ``h`` hole pixels, the largest passing dot count is ``h / 0.3``; any submission
    with more dots than that fails the literal rule no matter where it places them.
    """
    lattice_mask = np.asarray(lattice_mask, bool) & footprint
    footprint = np.asarray(footprint, bool)
    near = binary_dilation(lattice_mask, structure=DISK3)
    holes = footprint & ~near
    h = int(holes.sum())
    total = int(footprint.sum())
    return {
        "footprint_pixels": total,
        "lattice_dots": int(lattice_mask.sum()),
        "hole_pixels": h,
        "footprint_within3_of_lattice": (total - h) / total if total else float("nan"),
        "max_dots_that_could_pass_literal_rule": int(np.floor(h / 0.3)) if h else 0,
        "rule": "dots_in_holes >= 0.3 * dots  <=>  dots <= holes/0.3",
    }
