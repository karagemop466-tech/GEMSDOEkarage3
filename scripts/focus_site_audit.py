#!/usr/bin/env python3
"""Independent, reproducible audit of the nine focus-site submissions.

For each focus site (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36) this script:

1. Fetches the file named in the README table at the pinned commit with
   ``gh api`` (raw bytes) and checks its SHA-256 against
   ``registry/complete_registry_manifest.json`` (group ``focus``).
2. Checks the saved bytes against the official format rules quoted from the
   DrivenData problem page: float32, single band, EPSG:32611, 3292 x 3730,
   100 m transform, values in [0, 1], NaN/null allowed only outside the
   footprint.
3. Counts "dots" (finite pixels with value > 0), reports the value set and
   whether the file is binary.
4. Computes the directional literal overlap used by the project's uniqueness
   rule: the fraction of A's dots within 3 px (Euclidean) of B's dots, for all
   ordered pairs of the nine files and against the calibration lattice
   ``r13-lattice-s5`` (``13GEMSDOE``).
5. Computes Spearman rank correlation on footprint pixels against the lattice.
6. Computes HOLDOUT-DTI on the project's hide-and-recover holdout engine
   (``src/karage3/holdout.py``, evaluator ``GEMSDOE32-HIDE-RECOVER-v3.0``).
   These are local holdout estimates, NOT leaderboard scores.

Outputs ``evidence/focus-site-audit-20261029.json``. Nothing here authorizes a
submission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32.paths import data_dir  # noqa: E402
from karage3.holdout import evaluate_hide_and_recover, evaluate_sgmc_with_ci, load_holdout_context  # noqa: E402

RADIUS_PX = 3.0
LATTICE_REL = "scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LATTICE_SHA = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
FOCUS_SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
               "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def _json_safe(x):
    """Replace NaN/inf with None so the evidence file is strict JSON (NaN = no dots / undefined)."""
    if isinstance(x, dict):
        return {k: _json_safe(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_json_safe(v) for v in x]
    if isinstance(x, float) and not np.isfinite(x):
        return None
    return x


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def readme_links() -> dict[str, tuple[str, str, str]]:
    """Return {site: (repo, pinned_commit, path)} parsed from README's historical table."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"\| \[(GEMSDOE\d+)\]\(https://[^)]+\) \| \[`[^`]+`\]\(https://github\.com/([^)]+)\) \|", text)
    out = {}
    for site, link in rows:
        repo, rest = link.split("/blob/", 1)
        ref, path = rest.split("/", 1)
        out[site] = (repo, ref, path)
    missing = set(FOCUS_SITES) - set(out)
    if missing:
        raise SystemExit(f"README table missing sites: {sorted(missing)}")
    return out


def registry_focus() -> dict[tuple[str, str], dict]:
    man = json.loads((ROOT / "registry" / "complete_registry_manifest.json").read_text())
    return {(x["repo"], x["path"]): x for x in man["rasters"] if x["group"] == "focus"}


def fetch(repo: str, ref: str, path: str) -> bytes:
    out = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}", "-H", "Accept: application/vnd.github.raw"],
        capture_output=True, check=True,
    )
    return out.stdout


def dots_of(a: np.ndarray) -> np.ndarray:
    return np.isfinite(a) & (a > 0)


def literal_overlap(a_dots: np.ndarray, b_dots: np.ndarray) -> float:
    """Fraction of A's dots within 3 px of any B dot (directional, literal)."""
    n = int(a_dots.sum())
    if n == 0:
        return float("nan")
    if not b_dots.any():
        return 0.0
    dist_b = distance_transform_edt(~b_dots)
    return float((dist_b[a_dots] <= RADIUS_PX + 1e-9).sum() / n)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=ROOT / ".cache" / "focus")
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "focus-site-audit-20261029.json")
    ap.add_argument("--no-holdout", action="store_true", help="skip HOLDOUT-DTI (faster)")
    args = ap.parse_args()

    args.cache.mkdir(parents=True, exist_ok=True)
    links = readme_links()
    reg = registry_focus()
    ddir = data_dir()

    with rasterio.open(ddir / "sample_submission.tif") as s:
        template = s.read(1)
        t_crs, t_shape, t_tr = str(s.crs), (s.height, s.width), tuple(s.transform)[:6]
    footprint = np.isfinite(template)

    with rasterio.open(ddir / LATTICE_REL) as s:
        lattice = s.read(1)
    lat_dots = dots_of(lattice)
    lat_sha = hashlib.sha256((ddir / LATTICE_REL).read_bytes()).hexdigest()
    cov_mask = (distance_transform_edt(~lat_dots) <= RADIUS_PX + 1e-9) & footprint
    lat_cov = float(cov_mask.sum() / footprint.sum())
    lat_uncovered = int((footprint & ~cov_mask).sum())

    files: dict[str, dict] = {}
    arrays: dict[str, np.ndarray] = {}
    for site in FOCUS_SITES:
        repo, ref, path = links[site]
        raw = fetch(repo, ref, path)
        digest = sha256_bytes(raw)
        ent = reg.get((repo, path))
        local = args.cache / f"{site}.tif"
        local.write_bytes(raw)
        with rasterio.open(local) as s:
            a = s.read(1).astype(np.float32)
            meta = dict(crs=str(s.crs), shape=[s.height, s.width], count=s.count, dtype=s.dtypes[0],
                        transform=list(tuple(s.transform)[:6]), nodata=s.nodata)
        arrays[site] = a
        nan_in = int((~np.isfinite(a) & footprint).sum())
        nan_out = int((~np.isfinite(a) & ~footprint).sum())
        fin = np.isfinite(a)
        vals = a[fin]
        vmin, vmax = (float(vals.min()), float(vals.max())) if vals.size else (None, None)
        outside_nonzero = int((fin & ~footprint & (a != 0)).sum())
        d = dots_of(a)
        files[site] = {
            "repo": repo, "pinned_commit_from_readme": ref, "path": path,
            "registry_ref": ent["ref"] if ent else None,
            "registry_ref_matches_readme": bool(ent and ent["ref"] == ref),
            "bytes": len(raw), "sha256": digest,
            "registry_sha256_match": bool(ent and ent["sha256"] == digest),
            "raster": meta,
            "format_checks": {
                "crs_is_EPSG32611": meta["crs"] == "EPSG:32611",
                "shape_matches_template": meta["shape"] == list(t_shape),
                "transform_matches_template": meta["transform"] == list(t_tr),
                "single_band": meta["count"] == 1,
                "float32": meta["dtype"] == "float32",
                "values_in_0_1_where_finite": bool(vmin is None or (vmin >= 0 and vmax <= 1)),
                "nan_inside_footprint": nan_in,
                "nan_outside_footprint": nan_out,
                "nonzero_outside_footprint": outside_nonzero,
            },
            "value_min": vmin, "value_max": vmax,
            "distinct_finite_values_sample": [float(x) for x in np.unique(vals)[:6]],
            "binary_0_1": bool(np.isin(vals, [0.0, 1.0]).all()) if vals.size else None,
            "dot_count_gt0": int(d.sum()),
            "dots_inside_footprint": int((d & footprint).sum()),
            "lattice_overlap_3px_literal": literal_overlap(d, lat_dots),
        }

    # Pairwise directional literal overlap among the nine focus files.
    dots = {s: dots_of(arrays[s]) for s in FOCUS_SITES}
    pairwise = {}
    for a_site in FOCUS_SITES:
        row = {}
        for b_site in FOCUS_SITES:
            if a_site == b_site:
                continue
            row[b_site] = round(literal_overlap(dots[a_site], dots[b_site]), 6)
        pairwise[a_site] = row

    # Exact set relations (pixel-for-pixel, no tolerance).
    exact = {
        "GEMSDOE32_subset_of_GEMSDOE31": not bool((dots["GEMSDOE32"] & ~dots["GEMSDOE31"]).any()),
        "GEMSDOE31_subset_of_GEMSDOE25": not bool((dots["GEMSDOE31"] & ~dots["GEMSDOE25"]).any()),
        "GEMSDOE32_subset_of_GEMSDOE36": not bool((dots["GEMSDOE32"] & ~dots["GEMSDOE36"]).any()),
        "GEMSDOE25_dot_mask_identical_to_GEMSDOE30": bool((dots["GEMSDOE25"] == dots["GEMSDOE30"]).all()),
        "GEMSDOE31_minus_GEMSDOE32_dots": int((dots["GEMSDOE31"] & ~dots["GEMSDOE32"]).sum()),
        "GEMSDOE31_minus_GEMSDOE32_max_distance_to_visible_fault_px": None,
    }
    with rasterio.open(ddir / "labels.tif") as s_lab:
        visible = s_lab.read(1) > 0
    d_vis = distance_transform_edt(~visible)
    diff = dots["GEMSDOE31"] & ~dots["GEMSDOE32"]
    exact["GEMSDOE31_minus_GEMSDOE32_max_distance_to_visible_fault_px"] = float(d_vis[diff].max()) if diff.any() else None

    # Rank correlation on footprint pixels vs the lattice (sampled, deterministic).
    rng = np.random.default_rng(20261029)
    fy, fx = np.nonzero(footprint)
    pick = rng.choice(fy.size, size=min(400_000, fy.size), replace=False)
    sy, sx = fy[pick], fx[pick]
    lat_s = lattice[sy, sx]
    rho_vs_lattice = {}
    for site in FOCUS_SITES:
        v = np.nan_to_num(arrays[site][sy, sx], nan=0.0)
        rho = spearmanr(v, lat_s).statistic
        rho_vs_lattice[site] = None if rho is None or np.isnan(rho) else round(float(rho), 6)
        files[site]["spearman_vs_lattice_sampled"] = rho_vs_lattice[site]

    holdout = {}
    sgmc = {}
    if not args.no_holdout:
        ctx = load_holdout_context(ddir)
        for site in FOCUS_SITES:
            sg = evaluate_sgmc_with_ci(dots[site] & footprint, ctx, name=site)
            sgmc[site] = {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": sg["evaluator_version"],
                "withheld_positives": int(sg["n_withheld_positives"]),
                "dti": round(float(sg["sgmc_raw_pooled_dti"]), 6),
                "ci95": [round(float(x), 6) for x in sg["sgmc_raw_ci95"]],
                "note": ("Off-catalogue SGMC proxy, raw (uncalibrated) DTI. The prevalence-calibrated variant "
                         "uses a constant fitted to leaderboard numbers and is deliberately not reported."),
            }
        for site in FOCUS_SITES:
            res = evaluate_hide_and_recover(dots[site] & footprint, ctx, name=site)
            holdout[site] = {
                "evidence_class": res["score_label"],
                "evaluator_version": res["evaluator_version"],
                "withheld_positives": int(res["n_withheld_positives"]),
                "dti": round(float(res["pooled_dti"]), 6),
                "ci95": [round(float(x), 6) for x in res["ci95_cluster_bootstrap"]],
                "n_bootstrap_reps": int(res["n_bootstrap_reps"]),
                "note": "Local holdout on visible catalogue faults; not the hidden leaderboard score.",
            }

    card = {
        "schema": "focus-site-audit/1",
        "generated_by": "scripts/focus_site_audit.py",
        "official_metric_source": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "official_masking_source": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
        "template": {"path": "sample_submission.tif", "sha256": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
                     "crs": t_crs, "shape": list(t_shape), "transform": list(t_tr),
                     "footprint_px": int(footprint.sum())},
        "lattice": {"path": LATTICE_REL, "sha256": lat_sha, "sha256_expected": LATTICE_SHA,
                    "dots": int(lat_dots.sum()), "footprint_coverage_within_3px": round(lat_cov, 6),
                    "footprint_px_uncovered_within_3px": lat_uncovered,
                    "min_N_forcing_overlap_above_70pct": int(np.ceil(lat_uncovered / 0.30))},
        "files": files,
        "pairwise_literal_overlap_3px_row_is_A_col_is_B": pairwise,
        "exact_set_relations": exact,
        "holdout_dti_same_evaluator": holdout,
        "offcatalogue_sgmc_raw_dti_same_evaluator": sgmc,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(_json_safe(card), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({s: {"dots": files[s]["dot_count_gt0"], "sha_ok": files[s]["registry_sha256_match"],
                          "lattice_3px": round(files[s]["lattice_overlap_3px_literal"], 6),
                          "holdout_catalogue": holdout.get(s, {}).get("dti"),
                          "sgmc_raw": sgmc.get(s, {}).get("dti")} for s in FOCUS_SITES}, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
