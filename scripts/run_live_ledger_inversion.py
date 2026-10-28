#!/usr/bin/env python3
# Vendored from buffedlizard55-lab/GEMSDOE32@8a733107 (karage3 edits: multi-owner sites; reads registry/owner_score_ledger.csv).
"""Fit and validate the Live-Ledger Inversion (LLI) on every locally restored live-scored raster.

Inputs:  evidence/live_ledger_rasters.json (from scripts/fetch_live_ledger_rasters.py) and the
         restored competition data (sample/labels/training features/LiDAR/SGMC + H19-5 raster).
Outputs: evidence/live_ledger_inversion.json  (fit, factor effects, LOO / leave-site-out validation)
         .cache/gems_work/lli_design.npz      (per-raster stratum aggregates; git-ignored cache)

All live scores are OWNER-REPORT.  Every model output for an unscored raster is a PROJECTION.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32 import ledger_inversion as li  # noqa: E402
from gems32.paths import data_dir, work_dir  # noqa: E402

H195 = "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"
CHAMP = ROOT / "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"


def read1(p: Path, band: int = 1) -> np.ndarray:
    with rasterio.open(p) as ds:
        return ds.read(band)


def digitize(d: np.ndarray, edges: list[float], codes: list[int]) -> np.ndarray:
    idx = np.digitize(d, edges, right=True)
    return np.asarray(codes, np.int8)[idx]


def build_spec(ddir: Path, design: str) -> tuple[li.StrataSpec, dict]:
    foot = np.isfinite(read1(ddir / "sample_submission.tif"))
    labels = (read1(ddir / "labels.tif") > 0) & foot
    active = foot & ~labels
    d_cat = distance_transform_edt(~labels)
    # distance-to-catalogue factor; reference level 0 = far (> 50 px)
    cat_lv = digitize(d_cat, [1.01, 2.01, 3.01, 5.01, 10.01, 20.01, 50.01], [1, 2, 3, 4, 5, 6, 7, 0])
    cat_lab = [">50", "1", "1.4-2", "2.2-3", "3-5", "5-10", "10-20", "20-50"]
    h = read1(ddir / H195)
    h = np.isfinite(h) & (h > 0) & foot
    d_h = distance_transform_edt(~h)
    h_lv = digitize(d_h, [0.01, 1.01, 2.01, 5.01], [1, 2, 3, 4, 0])
    h_lab = [">5", "on", "1", "1.4-2", "2.2-5"]
    names, levels, nlev, labs = ["d_catalogue_px", "d_H19-5_px"], [cat_lv, h_lv], [8, 5], [cat_lab, h_lab]
    meta = {"design": design}
    if design == "S3":
        # finer H19-5 halo bins around the 3-px uniqueness boundary, coarser catalogue bins
        cat_lv = digitize(d_cat, [2.01, 3.01, 5.01, 10.01, 30.01], [1, 2, 3, 4, 5, 0])
        cat_lab = [">30", "1-2", "2.2-3", "3.2-5", "5-10", "10-30"]
        h_lv = digitize(d_h, [0.01, 1.01, 2.01, 3.01, 4.01, 5.01, 8.01, 15.01], [1, 2, 3, 4, 5, 6, 7, 8, 0])
        h_lab = [">15", "on", "1", "1.4-2", "2.2-3", "3.2-4", "4.1-5", "5-8", "8-15"]
        names, levels, nlev, labs = ["d_catalogue_px", "d_H19-5_px"], [cat_lv, h_lv], [6, 9], [cat_lab, h_lab]
    if design in ("S1", "S2"):
        slope = read1(ddir / "training_features.tif", 19).astype(np.float32)
        slope[~np.isfinite(slope) | (slope < -1e30)] = np.nan
        q = np.nanquantile(slope[active], [0.25, 0.5, 0.75])
        s_lv = np.zeros(slope.shape, np.int8)
        ok = np.isfinite(slope)
        s_lv[ok] = np.digitize(slope[ok], q, right=True).astype(np.int8)
        names.append("det_elev_slope_quartile"); levels.append(s_lv); nlev.append(4)
        labs.append(["Q1(flat)", "Q2", "Q3", "Q4(steep)"])
        meta["slope_quartile_edges"] = [float(x) for x in q]
        valid = read1(ddir / "external/lidar_scarp_features_u8.tif", 12) > 0
        step = read1(ddir / "external/lidar_scarp_features_u8.tif", 3).astype(np.float32)
        qq = np.quantile(step[active & valid], [0.25, 0.5, 0.75])
        l_lv = np.zeros(step.shape, np.int8)
        l_lv[valid] = (1 + np.digitize(step[valid], qq, right=True)).astype(np.int8)
        names.append("lidar_step_max"); levels.append(l_lv); nlev.append(5)
        labs.append(["no-LiDAR", "Q1", "Q2", "Q3", "Q4(strong)"])
        meta["lidar_step_quartile_edges_u8"] = [float(x) for x in qq]
        sg = read1(ddir / "external/derived_sgmc_faults_100m_u8.tif") > 0
        d_sg = distance_transform_edt(~sg)
        names.append("d_SGMC_le3px"); levels.append((d_sg <= 3.0).astype(np.int8)); nlev.append(2)
        labs.append([">3", "<=3"])
    if design == "S2":
        dep = read1(ddir / "training_features.tif", 15).astype(np.float32)
        dep[~np.isfinite(dep) | (dep < -1e30)] = np.nan
        q = np.nanquantile(dep[active], [1 / 3, 2 / 3])
        d_lv = np.zeros(dep.shape, np.int8)
        ok = np.isfinite(dep)
        d_lv[ok] = np.digitize(dep[ok], q, right=True).astype(np.int8)
        names.append("depth_to_basement_tercile"); levels.append(d_lv); nlev.append(3)
        labs.append(["T1(shallow)", "T2", "T3(deep)"])
        meta["depth_tercile_edges"] = [float(x) for x in q]
    if design == "S4":
        # H47-1 scarp-foot test: split the H19-5 halo by side relative to the nearest ridge pixel's
        # detrended elevation (downslope = lower than the ridge pixel it is adjacent to).
        cat_lv = digitize(d_cat, [2.01, 3.01, 5.01, 10.01, 30.01], [1, 2, 3, 4, 5, 0])
        cat_lab = [">30", "1-2", "2.2-3", "3.2-5", "5-10", "10-30"]
        elev = read1(ddir / "training_features.tif", 12).astype(np.float32)
        elev[~np.isfinite(elev) | (elev < -1e30)] = np.nan
        _, (iy, ix) = distance_transform_edt(~h, return_indices=True)
        e_ridge = elev[iy, ix]
        down = np.isfinite(elev) & np.isfinite(e_ridge) & (elev < e_ridge)
        band = digitize(d_h, [0.01, 1.01, 2.01, 3.01, 5.01], [1, 2, 3, 4, 5, 0])   # 0 far, 1 on, 2 d=1, 3 1.4-2, 4 2.2-3, 5 3.2-5
        h_lv = np.zeros(d_h.shape, np.int8)
        h_lv[band == 1] = 1
        for j, b in enumerate([2, 3, 4, 5]):
            h_lv[(band == b) & ~down] = 2 + 2 * j
            h_lv[(band == b) & down] = 3 + 2 * j
        h_lab = [">5", "on", "1-up", "1-down", "1.4-2-up", "1.4-2-down", "2.2-3-up", "2.2-3-down", "3.2-5-up", "3.2-5-down"]
        names, levels, nlev, labs = ["d_catalogue_px", "d_H19-5_side"], [cat_lv, h_lv], [6, 10], [cat_lab, h_lab]
        meta["side_rule"] = "downslope if det_elev(pixel) < det_elev(nearest H19-5 ridge pixel)"
    for lv in levels:
        lv[~active] = 0
    spec = li.StrataSpec(names=names, levels=levels, n_levels=nlev, level_labels=labs, active=active)
    meta.update(n_strata=int(spec.n_strata), n_params=int(li.n_params(spec)), active_pixels=int(active.sum()))
    return spec, meta


def ledger_inputs(ddir: Path) -> list[dict]:
    led = json.loads((ROOT / "evidence" / "live_ledger_rasters.json").read_text())
    rows = [r for r in led["rows"] if r.get("status") == "ok"]
    # rasters restored by restore_data.py that the GitHub matcher could not resolve unambiguously
    extra = [
        ("GEMSDOE/5GEMSDOE", "gemsdoe-ens12-adopted-7f00890a", 0.1563, ddir / "scored/gemsdoe-ens12-adopted-7f00890a.tif"),
        ("21GEMSDOE", "h19-4-reference-20260930-691e4dfa (= H19-4 bytes)", 0.1894,
         ddir / "scored/gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif"),
    ]
    out = [{"site": r["site"], "submission": r["submission"], "score": float(r["score"]), "path": ROOT / r["local"],
            "sha256": r.get("sha256")} for r in rows]
    have = {o["submission"] for o in out}
    for site, sub, sc, p in extra:
        if sub not in have and p.exists():
            out.append({"site": site, "submission": sub, "score": sc, "path": p, "sha256": None})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--designs", default="S0,S1,S2")
    ap.add_argument("--ridges", default="1e-7,1e-6,1e-5")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "live_ledger_inversion.json"))
    a = ap.parse_args()
    ddir = data_dir()
    wdir = work_dir()
    wdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    items = ledger_inputs(ddir)
    with rasterio.open(ddir / "sample_submission.tif") as ds:
        tpl = (ds.shape, ds.crs, ds.transform)
    result = {"schema_version": 1, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "instrument": "LLI-v1 (Live-Ledger Inversion; src/gems32/ledger_inversion.py); multi-start fit + warm-started LOO / leave-site-out",
              "score_evidence_class": "OWNER-REPORT live scores; model outputs for unscored rasters are PROJECTIONS",
              "designs": {}}
    for design in a.designs.split(","):
        spec, meta = build_spec(ddir, design)
        rows, used, skipped, digests = [], [], [], {}
        for it in items:
            try:
                with rasterio.open(it["path"]) as ds:
                    if (ds.shape, ds.crs, ds.transform) != tpl or ds.count < 1:
                        skipped.append({"submission": it["submission"], "reason": "grid_mismatch"})
                        continue
                    arr = ds.read(1).astype(np.float32)
            except Exception as exc:  # unreadable files are reported, never silently dropped
                skipped.append({"submission": it["submission"], "reason": f"read_error {type(exc).__name__}"})
                continue
            arr = np.where(np.isfinite(arr), arr, 0.0)
            if (arr[spec.active] < -1e-6).any() or (arr[spec.active] > 1 + 1e-6).any():
                skipped.append({"submission": it["submission"], "reason": "values outside [0,1] in scored domain"})
                continue
            arr[~spec.active] = 0.0
            dig = hashlib.sha256(np.round(arr[spec.active], 5).tobytes()).hexdigest()[:16]
            if dig in digests:
                digests[dig]["aliases"].append({"site": it["site"], "submission": it["submission"], "score": it["score"]})
                continue
            row = li.design_row(arr, spec)
            if row["N"] <= 0:
                skipped.append({"submission": it["submission"], "reason": "empty in scored domain"})
                continue
            rec = {"site": it["site"], "submission": it["submission"], "score": it["score"], "digest": dig,
                   "N": row["N"], "dots": row["dots"], "binary": row["binary"], "aliases": []}
            digests[dig] = rec
            rows.append(row)
            used.append(rec)
        # identical prediction masks scored under several names: use the mean live score
        s = np.array([np.mean([u["score"]] + [al["score"] for al in u["aliases"]]) for u in used])
        A = np.stack([r["A"] for r in rows])
        B = np.stack([r["B"] for r in rows])
        N = np.array([r["N"] for r in rows])
        np.savez_compressed(wdir / f"lli_design_{design}.npz", A=A, B=B, N=N, s=s, sizes=spec.sizes)
        sites = np.array([u["site"].split("-")[0] for u in used])
        site_ids = np.unique(sites, return_inverse=True)[1]
        # Multi-start full fit (6 random restarts around the stratum-free start), then leave-one-out and
        # leave-site-out refits WARM-STARTED from the full fit.  Cold-started refits of this non-convex
        # objective were found to wander between basins (champion LOO 0.197 vs in-sample 0.286).
        rng = np.random.default_rng(3)
        kpar = li.n_params(spec)

        def multistart(rg):
            base = li.fit(A, B, N, s, spec, ridge=rg)
            bestf = base
            for _ in range(6):
                th0 = np.concatenate([[base["theta"][0]], rng.normal(0, 1.0, kpar - 1)])
                f = li.fit(A, B, N, s, spec, ridge=rg, theta0=th0)
                if f["cost"] < bestf["cost"]:
                    bestf = f
            return bestf

        best = None
        tuning = []
        for rg in [float(x) for x in a.ridges.split(",")]:
            f_rg = multistart(rg)
            lo = li.loo(A, B, N, s, spec, ridge=rg, theta0=f_rg["theta"])
            tuning.append({"ridge": rg, "loo_mae": lo["mae"], "loo_rmse": lo["rmse"], "loo_spearman": lo["spearman"],
                           "in_sample_mae": float(np.mean(np.abs(f_rg["pred"] - s)))})
            if best is None or lo["mae"] < best[1]["mae"]:
                best = (rg, lo, f_rg)
        rg, lo, fit = best
        ls = li.loo(A, B, N, s, spec, groups=site_ids, ridge=rg, theta0=fit["theta"])
        eff = li.factor_effects(fit["theta"], spec)
        champ_i = next((i for i, u in enumerate(used) if "h33-h33-2-b2" in u["submission"]), None)
        per = []
        for i, u in enumerate(used):
            per.append({"site": u["site"], "submission": u["submission"], "live": float(s[i]),
                        "fit": float(fit["pred"][i]), "loo": float(lo["pred"][i]), "leave_site_out": float(ls["pred"][i]),
                        "N": float(u["N"]), "binary": u["binary"], "n_aliases": len(u["aliases"])})
        result["designs"][design] = {
            "meta": meta, "n_unique_rasters": len(used), "n_skipped": len(skipped), "skipped": skipped,
            "ridge_selected_by_loo_mae": rg, "ridge_tuning": tuning,
            "fit": {"in_sample_mae": float(np.mean(np.abs(fit["pred"] - s))), "g_public_truth_pixels_full_footprint_scale": fit["g"],
                    "theta": [float(x) for x in fit["theta"]], "success": fit["success"]},
            "loo": {k: v for k, v in lo.items() if k != "pred"},
            "leave_site_out": {k: v for k, v in ls.items() if k != "pred"},
            "factor_effects_multiplicative": eff,
            "champion_index": champ_i,
            "per_raster": per,
        }
        print(f"[{design}] n={len(used)} strata={spec.n_strata} params={li.n_params(spec)} ridge={rg:g} "
              f"in-sample MAE={np.mean(np.abs(fit['pred'] - s)):.4f} LOO MAE={lo['mae']:.4f} rho={lo['spearman']:.3f} "
              f"LSO MAE={ls['mae']:.4f} rho={ls['spearman']:.3f} G={fit['g']:.0f}  ({time.time() - t0:.0f}s)", flush=True)
        for k, v in eff.items():
            print("   ", k, {kk: round(vv, 3) for kk, vv in v.items()})
    Path(a.out).write_text(json.dumps(result, indent=1) + "\n")
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
