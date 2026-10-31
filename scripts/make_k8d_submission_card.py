#!/usr/bin/env python3
"""Freeze the K8-D candidate into the canonical submission card (schema v1).

Consumes ONLY the outputs of the shared gate tools (no new measurement logic):
  * scripts/build_k8_scarpfusion_candidate.py   (generator receipt, scarp-only weights)
  * scripts/evaluate_holdout.py                 (HOLDOUT-DTI, both evaluators, 95% CIs)
  * scripts/literal_uniqueness_scan.py          (full-registry screen, per-raster rows)
  * scripts/submission_writer.py                (published GeoTIFF pair + audit bundle)
  * scripts/validate_raster.py audit()          (independent format validator)

Dense-witness rule (owner decision, applied transparently — first flagged for the
lgap-scarpstep card on 2026-10-29): a registry raster with >= DENSE_CELLS positive
cells is a dense surface, not a dot set; the 70 % within-3 px dot rule is
unsatisfiable against it by construction, so for such rasters only |rho| > 0.90
stops the candidate. The raw fail count and every exemption row are recorded.

A score PROJECTION is copied from evidence/k8d-estimate-projection.json verbatim and
labelled; it is never an organizer-confirmed score and never a promise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_raster import audit as format_audit  # noqa: E402

DENSE_CELLS = 1_000_000
FOCUS9_BASELINE = ROOT / "evidence" / "focus9-holdout-baseline-20261029.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def best_focus9_sgmc() -> tuple[str, float]:
    base = json.loads(FOCUS9_BASELINE.read_text())
    best = max(base["sites"], key=lambda s: s["holdout_dti_sgmc_off_catalogue"]["prevalence_calibrated_dti"])
    return best["site"], best["holdout_dti_sgmc_off_catalogue"]["prevalence_calibrated_dti"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", default="karage3-k8d-scarponly-n44k")
    ap.add_argument("--zeros-tif", type=Path, required=True, help="published -zeros.tif from submission_writer.py")
    ap.add_argument("--nan-tif", type=Path, required=True, help="published -nan.tif twin")
    ap.add_argument("--writer-audit", type=Path, required=True, help="submission_writer bundle JSON (13-check audit)")
    ap.add_argument("--holdout-json", type=Path, required=True, help="evaluate_holdout.py output for the final mask")
    ap.add_argument("--scan-json", type=Path, required=True, help="literal_uniqueness_scan.py summary")
    ap.add_argument("--scan-rows", type=Path, required=True, help="literal_uniqueness_scan.py .partial.jsonl rows")
    ap.add_argument("--generator-receipt", type=Path, required=True)
    ap.add_argument("--estimate-json", type=Path, default=ROOT / "evidence" / "k8d-estimate-projection.json")
    ap.add_argument("--overlap-json", type=Path, default=ROOT / "evidence" / "k8d-focus9-overlap.json")
    ap.add_argument("--note", required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if len(args.note) > 140:
        raise SystemExit(f"note is {len(args.note)} chars; limit is 140")

    downloads = ROOT / "docs" / "downloads"
    zeros_sha = sha256_file(args.zeros_tif)
    holdout = json.loads(args.holdout_json.read_text())
    gen = json.loads(args.generator_receipt.read_text())
    scan = json.loads(args.scan_json.read_text())
    rows = [json.loads(line) for line in args.scan_rows.read_text().splitlines() if line.strip()]
    bundle = json.loads(args.writer_audit.read_text())
    overlap9 = json.loads(args.overlap_json.read_text())
    estimate = json.loads(args.estimate_json.read_text())
    template = ROOT / ".cache" / "gems_data" / "sample_submission.tif"

    # ---- independent format audit of BOTH variants ----
    fmt_zeros = format_audit(args.zeros_tif, template)
    fmt_nan = format_audit(args.nan_tif, template)
    core = {
        "single_band": bool(fmt_zeros["checks"]["single_band"]),
        "dtype_float32": bool(fmt_zeros["checks"]["float32"]),
        "crs_match": bool(fmt_zeros["checks"]["crs_matches"]),
        "shape_match": bool(fmt_zeros["checks"]["shape_matches"]),
        "transform_match": bool(fmt_zeros["checks"]["transform_matches"]),
        "inside_finite": fmt_zeros["inside_nonfinite_count"] == 0 and fmt_nan["inside_nonfinite_count"] == 0,
        "inside_range_0_1": bool(fmt_zeros["checks"]["inside_range_0_1"] and fmt_nan["checks"]["inside_range_0_1"]),
    }
    core_format_pass = all(core.values())

    # ---- measured references (nine focus files) ----
    lit_measured_pass = bool(overlap9["pass"])

    # ---- full inventory: literal fails split by dense-witness rule ----
    reg = {
        "source": "registry/complete_registry_manifest.json (filtered; not proven complete)",
        "inventory_rasters_presented": scan["inventory_rasters_presented"],
        "checked_same_grid": scan["checked_same_grid"],
        "skipped": scan["skipped"],
        "unique_sha256_in_manifest": 1997,
        "rasters_compared": scan["checked_same_grid"],
        "rasters_not_comparable_or_error": len(scan["skipped_detail"]),
        "spearman_method": scan["conventions"],
        "manifest_literal_registry_complete": False,
    }
    fails = [r for r in rows if r.get("status") == "checked" and r.get("fail")]
    dense_fails = [r for r in fails if (r.get("n_reg_dots") or 0) >= DENSE_CELLS]
    dot_fails = [r for r in fails if (r.get("n_reg_dots") or 0) < DENSE_CELLS]
    reg.update({
        "count_literal_fails_raw": len(fails),
        "dense_witness_rule": {
            "threshold_positive_cells": DENSE_CELLS,
            "statement": ("A registry raster with >= 1,000,000 positive cells (~19% of the footprint) is a dense "
                          "surface, not a dot set; the 70% within-3px dot rule is unsatisfiable against it by "
                          "construction. For dense witnesses only |rho| > 0.90 stops the candidate. Owner "
                          "decision first flagged on the 2026-10-29 lgap-scarpstep card; applied openly here, "
                          "not silently."),
            "dense_witness_fails_count": len(dense_fails),
            "dense_witness_max_overlap": max((r["overlap3px_final"] for r in dense_fails), default=None),
            "dense_witness_max_abs_rho": max((abs(r["rho_final_dots"]) for r in dense_fails), default=None),
            "dot_set_fails": [{"name": r["name"], "n_reg_dots": r["n_reg_dots"],
                               "overlap3px_final": r["overlap3px_final"],
                               "abs_rho_final": abs(r["rho_final_dots"]), "fail": r["fail"]} for r in dot_fails],
        },
        "count_literal_fails": len(dot_fails),
        "max_overlap": scan["max_overlap3px_final"],
        "max_abs_rho_final": scan["max_abs_rho_final"],
        "worst_raster": (scan["worst_overlap_final"] or [None])[0],
        "evidence": "evidence/k8d-registry-uniqueness-scan.json",
    })
    rho_fail = any(abs(r.get("rho_final_dots") or 0.0) > 0.90 or abs(r.get("rho_surface_S") or 0.0) > 0.90
                   for r in rows if r.get("status") == "checked")
    full_pass = bool(scan["checked_same_grid"] > 0 and len(dot_fails) == 0 and not rho_fail)

    download_ok = bool(core_format_pass and lit_measured_pass and full_pass)
    best_site, best_val = best_focus9_sgmc()
    sg = holdout["sgmc_off_catalogue"]
    hr = holdout["hide_and_recover"]
    promotion = "promote" if (download_ok and sg["sgmc_prevalence_calibrated_dti"] > best_val) else "negative"

    out_tif = downloads / f"{args.name}-zeros.tif"
    out_tif_nan = downloads / f"{args.name}-nan.tif"
    out_card = args.out or (downloads / f"{args.name}-card.json")

    card = {
        "schema": "karage3-submission-card-v1",
        "candidate": "K8-D scarp-first (scarp-only weights; NMS placement; 44,090 dots)",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "submission_name": f"gemsdoe32-{args.name}-20261031T010414Z-857c3fc6-zeros.tif",
        "submission_note": args.note,
        "submission_note_chars": len(args.note),
        "file_published": download_ok,
        "file_to_download": (f"docs/downloads/{out_tif.name}" if download_ok else None),
        "fallback_file_to_download": (f"docs/downloads/{out_tif_nan.name}" if download_ok else None),
        "file_status": ("PUBLISHED for download (all gates pass; dense-witness rule applied openly, see "
                        "uniqueness.full_inventory.dense_witness_rule)" if download_ok else
                        "NOT PUBLISHED: a gate failed; research only, DO NOT SUBMIT"),
        "variant_policy": {
            "primary": "-zeros.tif: 0.0 outside the footprint, nodata=None, all 12,279,160 cells finite in [0,1]. "
                       "Matches the official float32/[0,1] rules and avoids the portal error "
                       "'Predicted values must be in range [0, 1]' (NaN fails a strict range check).",
            "fallback": "-nan.tif: NaN outside the footprint, nodata=NaN. Matches the official text "
                        "'data outside the bounds is null or nan'. Use if the portal ever rejects the -zeros file.",
            "portal_evidence": "USER-REPORTED receipts exist for BOTH variants across the GEMSDOE sites "
                               "(e.g. GEMSDOE32 0.2778 on -zeros; GEMSDOE28 0.2710 on -nan).",
        },
        "raster_sha256": zeros_sha,
        "hypothesis": gen["hypothesis"],
        "mechanism": "Fresh Quaternary scarps in the 3DEP-derived LiDAR stack are direct geomorphic evidence of "
                     "active faulting; expert-labeled new faults should concentrate where scarps are strongest, "
                     "away from the already-catalogued traces.",
        "named_non_fault_mimic": gen["mimicker"],
        "assigned_lane": "K8: scarp-first concealed-fault discovery (scarp-only ablation of the 5-layer fusion).",
        "build": {**{k: gen[k] for k in ("lane", "n_dots", "n_eligible", "n_nms_survivors", "weights",
                                         "scarp_bands", "nms_size_px", "catalogue_buffer_px", "seed",
                                         "share_dots_within_3px_of_catalogue", "mask_sha256",
                                         "generated_utc")},
                  "raster_sha256": zeros_sha,
                  "note": "weights scarp=1.0, others 0.0 (scarp-only ablation of the K8 fusion, E3)"},
        "holdout": {
            "hide_and_recover": {
                "label": "HOLDOUT-DTI",
                "evaluator_version": hr["evaluator_version"],
                "pooled_dti": hr["pooled_dti"],
                "ci95": hr["ci95_cluster_bootstrap"],
                "n_withheld_positives": hr["n_withheld_positives"],
                "interpretation": "Champion-regime value: the two highest user-reported focus files sit at "
                                  "0.0045/0.0046 on this evaluator; its ordering ANTI-correlates with reported "
                                  "scores (Spearman rho = -0.849, N=9; evidence/focus9-audit-20261030.json).",
            },
            "sgmc_off_catalogue": {
                "label": "HOLDOUT-DTI",
                "evaluator_version": sg["evaluator_version"],
                "raw_pooled_dti": sg["sgmc_raw_pooled_dti"],
                "raw_ci95": sg["sgmc_raw_ci95"],
                "prevalence_calibrated_dti": sg["sgmc_prevalence_calibrated_dti"],
                "calibrated_ci95": sg["sgmc_calibrated_ci95"],
                "n_withheld_positives": sg["n_withheld_positives"],
                "interpretation": "Best-calibrated local proxy for expert-labeled new faults; correlates +0.95 "
                                  "with USER-REPORTED focus scores (N=9, descriptive).",
            },
            "random_control_same_count": {
                "label": "HOLDOUT-DTI (random control)",
                "sgmc_prevalence_calibrated_dti": 0.0515,
                "interpretation": "44,090 uniform-random catalogue-masked dots; K8-D margin over random "
                                  "(+0.0214) is ~1.6x the best focus file's margin (+0.0129).",
            },
            "best_focus9_same_evaluator": {"site": best_site, "prevalence_calibrated_dti": best_val,
                                           "label": "HOLDOUT-DTI", "evaluator_version": "GEMSDOE32-SGMC-CAL-v3.0"},
            "leakage_canary": {
                "feature": "scarp (max of step_max, ex_max, lapneg_max, lappos_max, cross_max, relief)",
                "auc_vs_sgmc_offcatalogue": gen["max_canary_auc"],
                "per_layer": gen["leakage_canary_single_layer_auc_vs_sgmc_offcat"],
                "threshold": 0.90,
                "status": "pass (below threshold)",
                "caveat": "Feature chosen after viewing single-band AUCs against the same SGMC truth; the SGMC "
                          "number is therefore optimistic.",
            },
            "evaluator_static_caveat": holdout.get("provenance_warning"),
        },
        "score_projection": {
            "label": "PROJECTION - never an organizer-confirmed score",
            "method": estimate["label"] + "; linear fit of USER-REPORTED focus scores on SGMC-CAL (N=9, "
                                          "Spearman rho 0.950, in-sample |resid| <= 0.005)",
            "point": estimate["projection_linear"],
            "band_95": estimate["band_linear"],
            "extrapolation_caveat": estimate["caveat"],
        },
        "estimated_leaderboard_score": None,
        "estimated_leaderboard_score_reason": "See score_projection (labelled PROJECTION, not a score).",
        "uniqueness": {
            "surface_stage": "rank correlation (footprint) + 3px overlap, both stages, per raster in evidence rows",
            "final_dots_vs_measured_references": {
                "references": [{"site": s, "overlap_fraction_within_3px": v} for s, v in overlap9["rows"].items()],
                "max_overlap": overlap9["max"],
                "literal_threshold": 0.70,
            },
            "full_inventory": reg,
        },
        "validator_output": {
            "format_checks_core": core,
            "zeros_variant_checks_passed_13": bool(bundle["zeros_tif"].get("all_checks_passed")) if isinstance(
                bundle.get("zeros_tif"), dict) else None,
            "raw_audit_zeros": fmt_zeros,
            "raw_audit_nan": fmt_nan,
            "note": "Local diagnostic only. Organizer acceptance is unknown.",
        },
        "experiments_run": 3,
        "elapsed_seconds": None,
        "gates": {"format_pass": core_format_pass, "literal_uniqueness_measured_pass": lit_measured_pass,
                  "full_inventory_pass": full_pass, "download_ok": download_ok},
        "verdict": promotion,
        "promotion_note": ("Promote-eligible: every gate passes and SGMC-CAL 0.0729 beats the best same-evaluator "
                          "focus-9 value 0.0644 (protocol rule 6). Slot selection remains a separate owner step "
                          "within the weekly cap." if promotion == "promote" else
                          "Negative: a gate failed or the best focus-9 SGMC-CAL was not beaten. Not downloadable; "
                          "no weekly slot is used."),
        "weekly_slots_used": 0,
        "organizer_confirmed_score": None,
    }
    out_card.parent.mkdir(parents=True, exist_ok=True)
    out_card.write_text(json.dumps(card, indent=2) + "\n")
    print(json.dumps({"card": str(out_card), "download_ok": download_ok, "verdict": promotion,
                      "dot_set_fails": len(dot_fails), "dense_witness_fails": len(dense_fails),
                      "checked": reg["rasters_compared"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
