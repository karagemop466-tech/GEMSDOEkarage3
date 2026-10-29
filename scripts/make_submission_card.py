#!/usr/bin/env python3
"""Freeze one candidate into the downloads folder with its JSON run card.

Reads the outputs of the gate tools (already run) and writes:
  docs/downloads/<name>.tif              the file to download, ONLY if download_ok (bytes unmodified)
                                         otherwise .cache/research/<name>.tif (not published)
  docs/downloads/<name>-card.json        the single run card (protocol rule 5)
  evidence/<name>-holdout.json           full evaluator output (HOLDOUT-DTI)
  evidence/<name>-registry.json          full-inventory uniqueness rows

Verdict logic is explicit and conservative:
  * download_ok   = format pass AND literal overlap/Spearman pass vs every measured reference
                    AND full-inventory audit has zero literal fails and zero fetch/grid errors.
  * promotion     = "negative" unless the candidate beats the best same-evaluator focus-9
                    HOLDOUT-DTI (protocol rule 6). Slot selection is never made here.

This does not claim organizer acceptance and does not estimate a leaderboard score.
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
sys.path.insert(0, str(ROOT / "src"))

from validate_raster import audit as format_audit  # noqa: E402  (shared format validator)

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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tif", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--note", required=True)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--build-json", type=Path, required=True)
    ap.add_argument("--overlap-json", type=Path, required=True)
    ap.add_argument("--holdout-json", type=Path, required=True)
    ap.add_argument("--registry-json", type=Path, required=True)
    ap.add_argument("--canary-auc", type=float, required=True)
    ap.add_argument("--canary-feature", required=True)
    ap.add_argument("--hypothesis", required=True)
    ap.add_argument("--mechanism", required=True)
    ap.add_argument("--mimic", required=True)
    args = ap.parse_args()

    if len(args.note) > 140:
        raise SystemExit(f"note is {len(args.note)} chars; limit is 140")

    downloads = ROOT / "docs" / "downloads"
    # Publish the TIF only when every gate passes. Otherwise it stays out of the public
    # downloads folder (git-ignored research cache) so it cannot be mistaken for a submission.
    out_tif = downloads / f"{args.name}.tif"
    out_card = downloads / f"{args.name}-card.json"
    ev_holdout = ROOT / "evidence" / f"{args.name}-holdout.json"
    ev_registry = ROOT / "evidence" / f"{args.name}-registry.json"

    build = json.loads(args.build_json.read_text())
    overlap = json.loads(args.overlap_json.read_text())
    holdout = json.loads(args.holdout_json.read_text())
    registry = json.loads(args.registry_json.read_text())

    raster_sha = sha256_file(args.tif)
    if build["raster_sha256"] != raster_sha:
        raise SystemExit("staged raster hash differs from build sidecar; rebuild")
    if overlap["candidate_sha256"] != raster_sha or registry["summary"]["candidate_sha256"] != raster_sha:
        raise SystemExit("gate outputs were not produced from this exact raster")

    fmt = format_audit(args.tif, args.template)
    fmt_checks = {
        "single_band_float32": bool(fmt["checks"]["single_band"] and fmt["checks"]["float32"]),
        "crs_shape_transform_match_template": bool(fmt["checks"]["crs_matches"] and fmt["checks"]["shape_matches"]
                                                    and fmt["checks"]["transform_matches"]),
        "inside_footprint_no_nan_or_masked": bool(fmt["inside_nonfinite_count"] == 0 and fmt["inside_masked_count"] == 0),
        "inside_footprint_values_in_0_1": bool(fmt["checks"]["inside_range_0_1"]),
        "outside_footprint_null_matches_template": bool(fmt["outside_template_null_pass"]),
        "core_format_pass": bool(fmt["core_format_pass"]),
    }
    format_pass = all(fmt_checks.values())

    refs = [r for r in overlap["references"]]
    lit_pass_measured = not overlap["any_literal_fail"] and all(r.get("overlap_fraction") is not None for r in refs)
    reg = registry["summary"]
    full_pass = (reg["rasters_compared"] > 0 and reg["rasters_not_comparable_or_error"] == 0
                 and reg["count_literal_fails"] == 0)
    download_ok = bool(format_pass and lit_pass_measured and full_pass)

    best_site, best_val = best_focus9_sgmc()
    cand_sgmc = holdout["sgmc_off_catalogue"]
    # Protocol rule 6: promote only if every gate passes AND the same-evaluator holdout beats the best focus-9 value.
    promotion = ("promote" if (download_ok and cand_sgmc["sgmc_prevalence_calibrated_dti"] > best_val)
                 else "negative")

    # Copy bytes unmodified; publish only when download_ok.
    if download_ok:
        out_tif.parent.mkdir(parents=True, exist_ok=True)
        dest_tif = out_tif
    else:
        dest_tif = ROOT / ".cache" / "research" / f"{args.name}.tif"
        dest_tif.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.tif, dest_tif)
    if sha256_file(dest_tif) != raster_sha:
        raise SystemExit("copy changed bytes")
    shutil.copyfile(args.holdout_json, ev_holdout)
    shutil.copyfile(args.registry_json, ev_registry)

    hr = holdout["hide_and_recover"]
    card = {
        "schema": "karage3-submission-card-v1",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "submission_name": args.name,
        "submission_note": args.note,
        "submission_note_chars": len(args.note),
        "file_published": download_ok,
        "file_to_download": (f"docs/downloads/{args.name}.tif" if download_ok else None),
        "file_status": ("PUBLISHED for download (all gates pass)" if download_ok else
                        "NOT PUBLISHED: fails the literal full-inventory uniqueness gate; research only, DO NOT SUBMIT"),
        "blocking_reasons": [] if download_ok else [
            f"{reg['count_literal_fails']} of {reg['rasters_compared']} compared registry rasters exceed the 70% literal overlap rule",
            "Dense registry surfaces (>=1,000,000 positive cells) make the literal dot rule unsatisfiable; owner decision required",
            "Sparse registry dot sets are overlapped by this file (see evidence registry rows)",
        ],
        "raster_sha256": raster_sha,
        "hypothesis": args.hypothesis,
        "mechanism": args.mechanism,
        "named_non_fault_mimic": args.mimic,
        "build": build,
        "holdout": {
            "hide_and_recover": {
                "label": "HOLDOUT-DTI",
                "evaluator_version": hr["evaluator_version"],
                "pooled_dti": hr["pooled_dti"],
                "ci95": hr["ci95_cluster_bootstrap"],
                "n_withheld_positives": hr["n_withheld_positives"],
                "interpretation": "Zero by construction: every dot is >3 px from the catalogue; this evaluator scores withheld catalogue segments.",
            },
            "sgmc_off_catalogue": {
                "label": "HOLDOUT-DTI",
                "evaluator_version": cand_sgmc["evaluator_version"],
                "raw_pooled_dti": cand_sgmc["sgmc_raw_pooled_dti"],
                "raw_ci95": cand_sgmc["sgmc_raw_ci95"],
                "prevalence_calibrated_dti": cand_sgmc["sgmc_prevalence_calibrated_dti"],
                "calibrated_ci95": cand_sgmc["sgmc_calibrated_ci95"],
                "n_withheld_positives": cand_sgmc["n_withheld_positives"],
            },
            "best_focus9_same_evaluator": {"site": best_site, "prevalence_calibrated_dti": best_val,
                                           "label": "HOLDOUT-DTI", "evaluator_version": "GEMSDOE32-SGMC-CAL-v3.0"},
            "leakage_canary": {
                "feature": args.canary_feature,
                "auc_vs_sgmc_offcatalogue": args.canary_auc,
                "threshold": 0.90,
                "status": "pass (below threshold)" if args.canary_auc <= 0.90 else "FAIL: leakage suspected",
                "caveat": "Feature chosen after viewing single-band AUCs against the same SGMC truth; the SGMC number is therefore optimistic.",
            },
            "evaluator_static_caveat": holdout["provenance_warning"],
        },
        "uniqueness": {
            "surface_stage": "rank correlation (footprint) is reported per reference; see overlap block",
            "final_dots_vs_measured_references": {
                "references": [{"name": r["name"], "overlap_fraction": r["overlap_fraction"],
                                "spearman_footprint": r["spearman_footprint"]} for r in refs],
                "max_overlap": overlap["max_overlap_fraction"],
                "literal_threshold": 0.70,
            },
            "full_inventory": {
                "source": "registry/complete_registry_manifest.json (filtered; not proven complete)",
                "unique_sha256": reg["unique_sha256_in_manifest"],
                "rasters_compared": reg["rasters_compared"],
                "rasters_not_comparable_or_error": reg["rasters_not_comparable_or_error"],
                "count_literal_fails": reg["count_literal_fails"],
                "max_overlap": reg["max_overlap"],
                "worst_raster": reg["worst_raster"],
                "spearman_method": reg["spearman_method"],
                "manifest_literal_registry_complete": reg["manifest_literal_registry_complete"],
                "evidence": f"evidence/{args.name}-registry.json",
            },
        },
        "validator_output": {"format_checks": fmt_checks, "raw_audit": fmt,
                             "note": "Local diagnostic only. Organizer acceptance is unknown."},
        "gates": {"format_pass": format_pass, "literal_uniqueness_measured_pass": lit_pass_measured,
                  "full_inventory_pass": full_pass, "download_ok": download_ok},
        "estimated_leaderboard_score": None,
        "estimated_leaderboard_score_reason": "Not estimable: no local proxy reproduces the portal ordering (see evidence/focus9-holdout-baseline-20261029.json).",
        "verdict": promotion,
        "promotion_note": ("Negative: does not beat the best same-evaluator focus-9 HOLDOUT-DTI (protocol rule 6), and the full-inventory uniqueness gate fails. Not downloadable; no weekly slot is used."),
        "weekly_slots_used": 0,
        "organizer_confirmed_score": None,
    }
    out_card.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"card": str(out_card.relative_to(ROOT)), "download_ok": download_ok,
                      "format_pass": format_pass, "full_inventory_pass": full_pass, "verdict": promotion},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
