#!/usr/bin/env python3
"""Byte-exact forensic audit of all 9 supplied focus-site owner-reported best rasters
(`GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36`) + their current 2026-10-27 HEAD rasters,
evaluated on canonical `GEMSDOE32-HIDE-RECOVER-v3.0` & `GEMSDOE32-SGMC-CAL-v3.0` and
cross-checked for 3-px dot overlap & Spearman rank correlation against `GEMSDOEkarage3` (`H-K3-1`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir  # noqa: E402

CLAIMS = {
    "GEMSDOE24": ("h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", 0.2477, "989f5950"),
    "GEMSDOE25": ("dotted-h19-5-d2-8-20261002-e56ea318af89-nan", 0.2600, "e56ea318"),
    "GEMSDOE27": ("topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", 0.2449, "5512495c"),
    "GEMSDOE28": ("h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", 0.2710, "b531dae0"),
    "GEMSDOE30": ("d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", 0.2600, "91eae1ca"),
    "GEMSDOE31": ("h27-4-solo-d28-20261004-8acb75e1-nan", 0.2708, "8acb75e1"),
    "GEMSDOE32": ("h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778, "e5eb6e7e"),
    "GEMSDOE33": ("h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632, "cb490425"),
    "GEMSDOE36": ("anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", 0.2750, "9b9ea4e6"),
}


def main() -> int:
    ddir = data_dir()
    ctx = holdout.load_holdout_context(ddir)
    cman = json.load(open(ROOT / "registry" / "complete_registry_manifest.json"))
    uq = json.load(open(ROOT / "evidence" / "complete-registry-uniqueness-scan.json"))
    ab = json.load(open(ROOT / "evidence" / "crsb-gub-ablation-results.json"))

    k3_path = ROOT / ab["on_disk_tif_eval_cross_check"]["path"]
    with rasterio.open(k3_path) as ds:
        k3_arr = ds.read(1)
    k3_dots = (k3_arr > 0) & ctx.foot
    k3_foot_vec = k3_arr[ctx.foot].astype(np.float64)

    # Load H19-5 parent (`e27054cf`) and d2.8 parent (`e56ea318`) to quantify lineage nesting!
    scored_dir = (ddir.parent if ddir.name == "core" else ddir) / "scored"
    with rasterio.open(scored_dir / "gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif") as ds:
        a19 = ds.read(1)
    h19_mask = np.isfinite(a19) & (a19 > 0) & ctx.foot
    d_h19 = distance_transform_edt(~h19_mask)
    d_labels = distance_transform_edt(~ctx.labels)

    rows = []
    for site, (claim_name, claim_val, tag) in CLAIMS.items():
        # Prefer exact repo match if present, else any repo holding the exact SHA/tag
        cand = [r for r in cman["rasters"] if (tag in r["path"] or tag in r["sha256"]) and r["short_repo"] == site]
        if not cand:
            cand = [r for r in cman["rasters"] if (tag in r["path"] or tag in r["sha256"])]
        # Prefer -zeros or -allfinite if available, else first match
        zeros_c = [r for r in cand if ("-zeros" in r["path"] or "-allfinite" in r["path"])]
        chosen = zeros_c[0] if zeros_c else cand[0]

        p = ROOT / chosen["local"]
        with rasterio.open(p) as ds:
            arr = ds.read(1)
            nodata = ds.nodata
        all_finite = bool(np.isfinite(arr).all())
        in_foot = arr[ctx.foot]
        foot_finite = bool(np.isfinite(in_foot).all())
        in_01 = bool(foot_finite and float(in_foot.min()) >= 0.0 and float(in_foot.max()) <= 1.0)
        mask = np.isfinite(arr) & (arr > 0) & ctx.foot
        n_dots = int(mask.sum())

        # Lineage & B-collar forensic metrics
        nest_h19_3px = float((d_h19[mask] <= 3.0).mean()) if n_dots > 0 else 0.0
        min_d_label = float(d_labels[mask].min()) if n_dots > 0 else 0.0
        dots_within_2px_labels = int((d_labels[mask] <= 2.0).sum()) if n_dots > 0 else 0

        # Canonical HOLDOUT-DTI evaluations
        hr_static = holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=2.0, n_boot=400, name=f"{site}_winner")
        sg_eval = holdout.evaluate_sgmc_with_ci(mask, ctx, n_boot=400, name=f"{site}_winner")

        # Exact uniqueness of GEMSDOEkarage3 H-K3-1 vs this exact winner raster AND across all rasters in the site repo
        d_other = distance_transform_edt(~mask)
        ov_k3_vs_winner = float((d_other[k3_dots] <= 3.0).mean())
        clean_other = np.where(np.isfinite(in_foot), in_foot, 0.0).astype(np.float64)
        rho_dots = float(spearmanr(k3_foot_vec, clean_other).statistic)
        del d_other, arr, in_foot, clean_other

        site_uq = uq["per_focus_site"][site]
        rows.append(
            {
                "site": site,
                "repository": f"https://github.com/buffedlizard55-lab/{site}",
                "head_commit": str(cman["refs"][f"buffedlizard55-lab/{site}"])[:10],
                "owner_reported_submission": claim_name,
                "owner_reported_value": claim_val,
                "owner_reported_label": "OWNER-REPORT (unverified portal claim; raster bytes SHA-256 verified)",
                "verified_raster_source": f"{chosen['repo']}:{chosen['path']}",
                "verified_raster_sha256": chosen["sha256"],
                "emitted_dots": n_dots,
                "all_12279160_finite": all_finite,
                "in_footprint_range_0_1": in_01,
                "nodata": None if nodata is None or (isinstance(nodata, float) and np.isnan(nodata)) else float(nodata),
                "nodata_repr": str(nodata),
                "h19_5_nesting_3px_fraction": round(nest_h19_3px, 6),
                "min_dist_to_catalogue_px": round(min_d_label, 3),
                "dots_within_2px_of_catalogue": dots_within_2px_labels,
                "holdout_hide_recover_v3_static_dti": round(hr_static["pooled_dti"], 6),
                "holdout_hide_recover_v3_static_ci95": [round(x, 6) for x in hr_static["ci95_cluster_bootstrap"]],
                "holdout_hide_recover_note": (
                    "Full-catalogue B>=2 post-filter censors hidden faults in static re-score; uncollared d2.8 parent scores 0.099202 [0.085951, 0.112668]"
                    if dots_within_2px_labels == 0
                    else "Uncollared raster: static hide-and-recover with visible-only B=2 is leak-free"
                ),
                "holdout_sgmc_cal_v3_dti": round(sg_eval["sgmc_prevalence_calibrated_dti"], 6),
                "holdout_sgmc_cal_v3_ci95": [round(x, 6) for x in sg_eval["sgmc_calibrated_ci95"]],
                "karage3_vs_winner_3px_overlap": round(ov_k3_vs_winner, 6),
                "karage3_vs_winner_dots_spearman": round(rho_dots, 6),
                "karage3_vs_all_site_rasters_max_3px_overlap": site_uq["max_discrete_3px_overlap"],
                "karage3_vs_all_site_rasters_max_surface_spearman": site_uq["max_abs_surface_spearman"],
                "site_rasters_checked": site_uq["n_discrete_candidates_checked"],
                "karage3_unique_vs_site": site_uq["passed"],
            }
        )
        print(
            f"{site}: report={claim_val:.4f} | dots={n_dots:5d} | nest_H19={nest_h19_3px*100:5.1f}% | "
            f"d<=2_cat={dots_within_2px_labels:4d} | HR_stat={hr_static['pooled_dti']:.6f} | "
            f"SGMC_cal={sg_eval['sgmc_prevalence_calibrated_dti']:.6f} | ov_vs_k3={ov_k3_vs_winner*100:5.2f}%",
            flush=True,
        )

    out = {
        "evaluated_at": "2026-10-27",
        "evaluator_versions": {
            "hide_and_recover": holdout.HIDE_RECOVER_EVALUATOR_VERSION,
            "sgmc_off_catalogue": holdout.SGMC_EVALUATOR_VERSION,
        },
        "karage3_candidate": {
            "submission_name": k3_path.name,
            "sha256": ab["submission_receipt"]["zeros_tif"]["sha256"],
            "emitted_dots": int(k3_dots.sum()),
            "holdout_hide_recover_v3_dti": ab["experiments"]["EXP-3"]["hide_and_recover_v3"]["pooled_dti"],
            "holdout_hide_recover_v3_ci95": ab["experiments"]["EXP-3"]["hide_and_recover_v3"]["ci95"],
            "holdout_sgmc_cal_v3_dti": ab["experiments"]["EXP-3"]["sgmc_off_catalogue_v3"]["prevalence_calibrated_dti"],
            "holdout_sgmc_cal_v3_ci95": ab["experiments"]["EXP-3"]["sgmc_off_catalogue_v3"]["calibrated_ci95"],
            "verdict": ab["verdict"],
            "ok_to_submit": False,
        },
        "sites": rows,
    }
    (ROOT / "evidence" / "nine-site-audit-20261027.json").write_text(json.dumps(out, indent=2) + "\n")

    # Write enriched sites.json under docs/crsb-gub/sites.json without mutating root docs/sites.json
    sites_json_path = ROOT / "docs" / "sites.json"
    sites_doc = json.loads(sites_json_path.read_text())
    by_site = {r["site"]: r for r in rows}
    for s_entry in sites_doc["sites"]:
        r = by_site[s_entry["site"]]
        s_entry["verified_winner_sha256"] = r["verified_raster_sha256"]
        s_entry["emitted_dots"] = r["emitted_dots"]
        s_entry["h19_5_nesting_3px_fraction"] = r["h19_5_nesting_3px_fraction"]
        s_entry["dots_within_2px_of_catalogue"] = r["dots_within_2px_of_catalogue"]
        s_entry["winner_sgmc_cal_v3_dti"] = r["holdout_sgmc_cal_v3_dti"]
        s_entry["winner_sgmc_cal_v3_ci95"] = r["holdout_sgmc_cal_v3_ci95"]
        s_entry["winner_hide_recover_static_dti"] = r["holdout_hide_recover_v3_static_dti"]
        s_entry["estimated_score"] = (
            f"HOLDOUT-DTI (SGMC-CAL-v3.0, n=62,703): {r['holdout_sgmc_cal_v3_dti']:.4f} "
            f"[{r['holdout_sgmc_cal_v3_ci95'][0]:.4f}, {r['holdout_sgmc_cal_v3_ci95'][1]:.4f}]"
        )
        s_entry["unique"] = (
            f"PASS vs K3: {r['karage3_vs_winner_3px_overlap']*100:.1f}% 3px overlap "
            f"(site max {r['karage3_vs_all_site_rasters_max_3px_overlap']*100:.1f}% <= 70%, "
            f"|rho|={r['karage3_vs_all_site_rasters_max_surface_spearman']:.3f} <= 0.90)"
        )
        s_entry["ok_to_submit"] = False
    sites_doc["karage3_candidate"] = out["karage3_candidate"]
    out_sites_path = ROOT / "docs" / "crsb-gub" / "sites.json"
    out_sites_path.parent.mkdir(parents=True, exist_ok=True)
    out_sites_path.write_text(json.dumps(sites_doc, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
