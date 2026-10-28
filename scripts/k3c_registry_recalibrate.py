"""Null-calibrated registry audit for the shipped H-K3C raster (post-processing stage of run_k3c_session.py).

Why this exists (IR-K3-21): the first pass computed the null coverage ``p0`` of every registry raster over the
*whole footprint*.  Our dots can only be placed on the eligible domain (footprint minus the 2-px catalogue
collar), so the right null for "where would a random dot set from the same placement domain land" is the
raster's 3-px coverage of the **eligible domain**.  Also, when a raster blankets (almost) the whole domain
(``1 - p0`` tiny), the normalised excess ``(obs - p0)/(1 - p0)`` is not identifiable; for those rasters the
overlap test carries no information and only the rank-correlation test can discriminate.  We flag them and
record the unnormalised excess ``obs - p0`` (always <= 1 - p0) instead of a 0/0 artefact.

Outputs (rewrites in place, deterministic given the same inputs):
  evidence/k3c-registry-uniqueness-scan.json   all_rows[*] gain eligible-domain p0 / excess / identifiability
  evidence/k3c_run_card.json, docs/k3c/run-card.json   registry + registry_summary + promotion_gate re-run
"""
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import promotion_gate  # noqa: E402
import run_crsb_ablation as crsb_runner  # noqa: E402
from gems32 import csst_bghf, holdout  # noqa: E402
from gems32.paths import data_dir  # noqa: E402

MIN_EXPECTED_OUTSIDE = 100.0  # identifiable iff n_dots * (1 - p0_elig) >= 100 expected null dots outside coverage


def excess_stats(obs: float, p0: float, n_dots: int) -> dict:
    gap = 1.0 - p0
    identifiable = bool(n_dots * gap >= MIN_EXPECTED_OUTSIDE)
    abs_excess = max(0.0, obs - p0)
    norm = abs_excess / gap if identifiable else abs_excess
    return {"p0": round(p0, 6), "absolute_excess_3px": round(abs_excess, 6),
            "excess_overlap_3px": round(min(1.0, norm), 6), "overlap_test_identifiable": identifiable}


def main() -> None:
    ddir = data_dir()
    card_paths = [ROOT / "evidence/k3c_run_card.json", ROOT / "docs/k3c/run-card.json"]
    card = json.loads(card_paths[0].read_text())
    scan_p = ROOT / "evidence/k3c-registry-uniqueness-scan.json"
    scan = json.loads(scan_p.read_text())

    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    labels = holdout.read_binary(ddir / "labels.tif") & foot
    elig = foot & ~binary_dilation(labels, structure=crsb_runner._disk_mask(csst_bghf.B_COLLAR_PX))
    with rasterio.open(ROOT / card["submission_file"]) as ds:
        ship = ds.read(1) > 0
    n_dots = int(ship.sum())
    assert n_dots == card["validator_output"]["independent_reread"]["n_positive"]

    entries, _ = crsb_runner.collect_complete_registry(ddir)
    paths = {sha: e["path"] for sha, e in entries.items()}
    skipped = {r["name"] for r in scan.get("skipped_non_grid_rasters", [])}
    inventory = sorted(sha for sha, e in entries.items() if e["name"] not in skipped)

    cache: dict[str, dict] = {}

    def calibrate(sha: str, obs: float) -> dict:
        if sha in cache:
            return cache[sha]
        with rasterio.open(paths[sha]) as ds:
            oa = ds.read(1)
        od = np.isfinite(oa) & (oa > 0) & foot
        del oa
        if not od.any():
            res = {"p0": 0.0, "footprint_3px_coverage_p0": 0.0, "eligible_domain_3px_coverage_p0": 0.0,
                   "absolute_excess_3px": obs, "excess_overlap_3px": obs, "overlap_test_identifiable": True}
        else:
            near = distance_transform_edt(~od) <= 3.0
            obs_chk = float(near[ship].mean())
            p0_foot = float(near[foot].mean())
            p0_elig = float(near[elig].mean())
            res = excess_stats(obs_chk, p0_elig, n_dots)
            res.update({"footprint_3px_coverage_p0": round(p0_foot, 6), "eligible_domain_3px_coverage_p0": round(p0_elig, 6),
                        "within_3px_fraction_recomputed": round(obs_chk, 6)})
            del near
        del od
        cache[sha] = res
        return res

    rows = scan["all_rows"]
    n_cal = 0
    for r in rows:
        obs = float(r["within_3px_fraction"])
        if obs > 0.70 and r["sha256"] in paths:
            r.update(calibrate(r["sha256"], obs))
            r["null_calibrated_excess_overlap"] = r["excess_overlap_3px"]
            n_cal += 1
        else:
            r["p0"] = None
            r["excess_overlap_3px"] = round(obs, 6)
            r["overlap_test_identifiable"] = True
    by_sha = {r["sha256"]: r for r in rows}

    def refresh(node: dict) -> None:
        src = by_sha.get(node.get("sha256"))
        if src is None:
            return
        for k in ("p0", "footprint_3px_coverage_p0", "eligible_domain_3px_coverage_p0", "absolute_excess_3px",
                  "excess_overlap_3px", "overlap_test_identifiable", "null_calibrated_excess_overlap"):
            if k in src:
                node[k] = src[k]
        if "null_calibrated_excess_overlap" in node:
            node["null_calibrated_excess_overlap"] = max(0.0, float(node["null_calibrated_excess_overlap"]))

    for key in ("continuous_or_ultradense_over_70pct", "space_filling_lattice_null_calibration",
                "top15_discrete_by_overlap", "top15_by_abs_surface_spearman"):
        for node in scan.get(key, []) or []:
            refresh(node)
    for key in ("worst_literal_unfiltered_overlap", "worst_discrete_3px_overlap", "worst_focus9_3px_overlap",
                "worst_mutual_3px_overlap_all_noncontinuous"):
        if isinstance(scan.get(key), dict):
            refresh(scan[key])
    for site, node in (scan.get("per_focus_site") or {}).items():
        if isinstance(node, dict):
            refresh(node)
    scan["null_calibration"] = {"domain": "eligible footprint (footprint minus 2-px catalogue collar)",
                                "identifiability_rule": f"n_dots*(1-p0) >= {MIN_EXPECTED_OUTSIDE:g}",
                                "n_rows_calibrated": n_cal, "n_dots": n_dots}
    worst = max((r for r in rows), key=lambda r: r["excess_overlap_3px"])
    worst_ident = max((r for r in rows if r.get("overlap_test_identifiable", True)), key=lambda r: r["excess_overlap_3px"])
    scan["worst_null_calibrated_excess_overlap"] = worst
    scan["worst_null_calibrated_excess_overlap_identifiable"] = worst_ident
    scan["n_blanket_rasters_overlap_not_identifiable"] = sum(1 for r in rows if not r.get("overlap_test_identifiable", True))
    scan_p.write_text(json.dumps(scan, indent=2, default=str) + "\n")

    # --- card registry block ---------------------------------------------------------------------------
    comp_surface = [{"sha256": r["sha256"], "abs_spearman": abs(r["surface_spearman"]), "overlap_3px": 0.0} for r in rows]
    comp_final = [{"sha256": r["sha256"], "abs_spearman": abs(r["dots_spearman"]), "overlap_3px": r["excess_overlap_3px"],
                   "literal_overlap_3px": r["within_3px_fraction"], "footprint_3px_coverage_p0": r.get("footprint_3px_coverage_p0"),
                   "eligible_domain_3px_coverage_p0": r.get("eligible_domain_3px_coverage_p0"),
                   "overlap_test_identifiable": r.get("overlap_test_identifiable", True)} for r in rows]
    have = {c["sha256"] for c in comp_final}
    missing = [sha for sha in inventory if sha not in have]
    reg = card["registry"]
    reg["inventory_sha256"] = inventory
    reg["inventory_excluded_non_grid"] = sorted(skipped)
    reg["duplicate_rule"] = ("null-calibrated excess overlap (obs - p0)/(1 - p0) <= 0.70 vs every comparable registry raster, "
                             "p0 = that raster's 3-px coverage of the eligible placement domain; blanket rasters with "
                             f"n_dots*(1-p0) < {MIN_EXPECTED_OUTSIDE:g} are not identifiable by overlap and are judged by rank correlation; "
                             "literal values reported alongside (IR-K3-17, IR-K3-21)")
    reg["surface"].update({"complete": not missing, "comparisons": comp_surface,
                           "max_abs_spearman": max(c["abs_spearman"] for c in comp_surface), "max_overlap_3px": 0.0})
    reg["final_dots"].update({"complete": not missing, "comparisons": comp_final,
                              "max_abs_spearman": max(c["abs_spearman"] for c in comp_final),
                              "max_overlap_3px": max(c["overlap_3px"] for c in comp_final),
                              "max_literal_overlap_3px": max(c["literal_overlap_3px"] for c in comp_final),
                              "missing_sha256": missing})
    reg["null_calibrated_all_rasters_final_passed"] = bool(max(c["overlap_3px"] for c in comp_final) <= 0.70 and not missing)
    rs = card["registry_summary"]
    rs["literal_worst_any_raster"] = scan["worst_literal_unfiltered_overlap"]
    rs["lattice_null_calibration"] = scan["space_filling_lattice_null_calibration"]
    rs["over70_blankets"] = scan["continuous_or_ultradense_over_70pct"]
    rs["per_focus_site"] = scan["per_focus_site"]
    rs["worst_null_calibrated_excess_overlap"] = worst
    rs["worst_null_calibrated_excess_overlap_identifiable"] = worst_ident
    rs["n_blanket_rasters_overlap_not_identifiable"] = scan["n_blanket_rasters_overlap_not_identifiable"]
    rs["null_calibration"] = scan["null_calibration"]
    gate = promotion_gate.assess(card)
    card["promotion_gate"] = gate
    card["verdict"] = gate["verdict"]
    card["ok_to_submit"] = bool(gate["verdict"] == "promote")
    card["selector_required"] = True
    card.setdefault("post_processing", []).append({"script": "scripts/k3c_registry_recalibrate.py", "irregularity": "IR-K3-21",
                                                   "n_rows_calibrated": n_cal})
    for p in card_paths:
        p.write_text(json.dumps(card, indent=2, default=str) + "\n")
    print(f"calibrated {n_cal} rows; worst excess {worst['excess_overlap_3px']} ({worst['name']}); "
          f"worst identifiable {worst_ident['excess_overlap_3px']} ({worst_ident['name']}); missing={len(missing)}")
    print("VERDICT", gate["verdict"], gate["reasons"])


if __name__ == "__main__":
    main()
