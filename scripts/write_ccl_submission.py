#!/usr/bin/env python3
"""Write, validate and card the K3-CCL candidate (lane K3-CCL, 2026-10-28).

Uses only shared tools: scripts/submission_writer.py (zeros-outside TIFF + zip),
scripts/validate_raster.audit (saved-byte checks), scripts/check_submission.py (--strict-finite),
the pinned 13GEMSDOE lattice witness from data/focus_registry.json, and scripts/promotion_gate.py.
Writes docs/ccl/downloads/*, evidence/ccl_run_card.json and docs/ccl/run-card.json.
No number here is a leaderboard score.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from submission_writer import write_validated_submission  # noqa: E402
from scripts.validate_raster import audit as validate_audit  # noqa: E402
from promotion_gate import assess  # noqa: E402

DDIR = ROOT / ".cache" / "gems_data"
OUT = ROOT / "docs" / "ccl" / "downloads"
TS = "20261028T0700Z"
LATTICE = DDIR / "scored" / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    # Archived runner: do not reach any filesystem writes or candidate placement.
    raise SystemExit('STOP: historical experiment runner is disabled; no assigned lane, '
                     'shared holdout defects and the literal duplicate-stop remain unresolved.')
    from scripts.protocol_preflight import require_budget_not_proven_duplicate, require_shared_protocol_ready
    require_budget_not_proven_duplicate(37654)
    require_shared_protocol_ready()
    exp = json.loads((ROOT / "evidence/ccl_experiments.json").read_text())
    live = json.loads((ROOT / "evidence/ccl_live.json").read_text())
    lli = json.loads((ROOT / "evidence/ccl_lli_projection.json").read_text())
    dots = np.load(ROOT / ".cache/gems_work/ccl_live_dots.npy")
    assert int(dots.sum()) == live["emission"]["dots"] == 37654 and live["emission"]["b_px"] == 5.0
    e2 = exp["results"]["E2_CCL_CREST"]
    hr = f"HR={e2['pooled_dti']:.3f}"
    lo = min(v["projected_dti"]["ccl_live_dots_b5.npy"] for v in lli["designs"].values())
    hi = max(v["projected_dti"]["ccl_live_dots_b5.npy"] for v in lli["designs"].values())
    note = (f"GEMSDOEkarage3 K3-CCL catalogue-completion crest d2.8 B5 37654d | {hr} holdout; "
            f"LLI proj {lo:.3f}-{hi:.3f} not score")
    assert len(note) <= 140, len(note)

    bundle = write_validated_submission(dots.astype(np.float32), slug="karage3-k3-ccl-crest-b5-37654",
                                        candidate_meta={"candidate_id": "K3-CCL-CREST-B5",
                                                        "description": "K3-CCL research artifact; DUPLICATE STOP - DO NOT SUBMIT",
                                                        "submission_note_zeros": note,
                                                        "submission_note_nan": note,
                                                        "slot_decision": "DO-NOT-SUBMIT-DUPLICATE-STOP"},
                                        ddir=DDIR, out_dir=OUT, timestamp_tag=TS)
    zeros = OUT / bundle["zeros_tif"]["filename"]
    nan_tif = OUT / bundle["nan_tif"]["filename"]
    nan_tif.unlink(missing_ok=True)
    (OUT / bundle["nan_tif"]["filename"]).with_suffix(".zip").unlink(missing_ok=True)       # NaN-outside variant fails the whole-array range check; not shipped
    digest8 = zeros.name.split("-")[-2]
    name = f"KARAGE3-K3-CCL-{digest8.upper()}"

    template = DDIR / "sample_submission.tif"
    val = validate_audit(zeros, template)
    chk = subprocess.run([sys.executable, str(ROOT / "scripts/check_submission.py"), str(zeros),
                          "--template", str(template), "--strict-finite"], capture_output=True, text=True)
    with rasterio.open(template) as ds:
        foot = (ds.read_masks(1) != 0) & np.isfinite(ds.read(1))
    with rasterio.open(zeros) as ds:
        arr = ds.read(1)
        grid_ok = (ds.count == 1, ds.crs == rasterio.crs.CRS.from_epsg(32611))
    saved_dots = np.isfinite(arr) & (arr > 0) & foot
    assert np.array_equal(saved_dots, dots.astype(bool) & foot), "saved bytes differ from emitted dots"
    with rasterio.open(LATTICE) as ds:
        lat = np.isfinite(ds.read(1)) & (ds.read(1) > 0) & foot
    dlat = distance_transform_edt(~lat)
    lattice_ov = float((dlat[saved_dots] <= 3).mean())
    uncovered = int((foot & (dlat > 3)).sum())

    fa = live["final_dots_audit"]
    supp = fa.get("supplementary_unmeasurable_check", {})
    non_space = [r for r in live["final_dots_top15_overlap"] if not r.get("space_filling")]
    worst_discriminating = max((r["within_3px_fraction"] for r in non_space), default=None)
    paired = exp["paired_vs_control"]["E2_CCL_CREST"]
    card = {
        "schema_version": 1,
        "run_id": "k3-ccl-20261028",
        "assigned_lane": "K3-CCL Catalogue-Completion Learner (self-assigned this session; recorded in research/2026-10-28-ccl.md)",
        "hypothesis": ("Uncatalogued faults are the missing pieces of catalogued fault systems (tip continuations, "
                       "parallel splays, linkage zones); a learner trained on simulated catalogue incompleteness "
                       "with visible-catalogue geometry recovers them better than physics alone."),
        "mechanism": ("HistGradientBoosting on 34 shared stack channels + 5 LiDAR scarp bands + 6 visible-catalogue "
                      "geometry features (distance, along-strike vs perpendicular offset, strike alignment, density, "
                      "tip distance); crest-first Poisson-disk dots d=2.8 px; catalogue collar B=5 px."),
        "named_non_fault_process": ("Catalogue-proximity bias: hidden catalogue FRAGMENTS near visible traces are easy "
                                    "holdout targets but live new faults are depleted within ~5 px of the catalogue "
                                    "(live-ledger strata); lithologic contacts and flight-line levelling mimic potential-field edges."),
        "experiments_run": 3,
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": exp["evaluator_version"],
            "withheld_positives": int(e2["n_withheld_positives"]),
            "dti": round(e2["pooled_dti"], 6),
            "ci95": [round(x, 6) for x in e2["ci95_cluster_bootstrap"]],
            "b_visible_px": exp["b_visible_px"],
            "paired_delta_vs": "CONTROL = champion bytes re-scored in the same run (0.004515; documented censoring artefact)",
            "paired_delta_ci95": [round(x, 6) for x in paired["delta_ci95"]],
            "same_evaluator_current_best": False,
            "same_evaluator_current_best_reason": ("Archived current best (SMGC 0.107297 [0.0930, 0.1209]) cannot be regenerated: "
                                                   "its runner is disabled and smgc_extra_4ch.npy is absent. Unpaired: E2 lower CI "
                                                   "0.133 > SMGC upper CI 0.121."),
            "mechanism_ablation_E1_minus_E3": exp["paired_E1_vs_E3_mechanism"],
            "crest_E2_minus_E1": exp["paired_E2_vs_E1"],
            "live_file_note": "Holdout arms used B=2; live file uses B=5 chosen from live-ledger strata, not holdout-validated.",
        },
        "live_ledger_projection": {"label": "LIVE-LEDGER PROJECTION — NOT A SCORE", "range": [lo, hi],
                                    "file": "evidence/ccl_lli_projection.json", "reading": lli["reading"]},
        "feature_auc": [round(v["raw_auc"], 4) for k, v in exp["leakage_canary"]["features"].items()
                        if not k.startswith("MODEL_")],
        "leakage_canary_max_single_feature_oriented_auc": exp["leakage_canary"]["single_feature_max"],
        "registry": {
            "manifest": live["manifest"],
            "manifest_sha256": sha(ROOT / "registry/complete_registry_manifest.json"),
            "surface_pre_placement": {"worst_abs_spearman": live["surface_audit"]["worst_abs_spearman"],
                                      "worst_raster": live["surface_audit"]["worst_raster"],
                                      "duplicates": live["surface_audit_n_duplicates"],
                                      "unmeasurable": live["surface_audit"]["malformed_or_missing"]},
            "final_dots": {"null_calibrated_passed": fa.get("passed"),
                           "literal_rule_passed": fa.get("literal_rule_passed"),
                           "literal_duplicates": fa.get("literal_duplicates"),
                           "worst_abs_spearman": fa.get("worst_abs_spearman"),
                           "worst_spearman_raster": fa.get("worst_spearman_raster"),
                           "worst_within_3px_fraction_any": fa.get("worst_within_3px_fraction"),
                           "worst_overlap_raster": fa.get("worst_overlap_raster"),
                           "worst_within_3px_fraction_non_space_filling": worst_discriminating,
                           "supplementary_unmeasurable": {k: supp.get(k) for k in ("n", "n_comparable")} |
                           {"duplicates": len(supp.get("duplicates", [])),
                            "literal_duplicates": len(supp.get("literal_duplicates", []))}},
            "literal_lattice_witness": {"raster": "buffedlizard55-lab/13GEMSDOE r13-lattice-s5 (sha256 b4570b40...)",
                                        "within_3px_fraction": lattice_ov,
                                        "uncovered_footprint_pixels": uncovered,
                                        "pigeonhole_max_dots_passable": int(uncovered / 0.30)},
            "literal_all_rasters_final_passed": False,
        },
        "raster_sha256": sha(zeros),
        "zip_sha256": bundle["zeros_zip"]["sha256"],
        "files": {"tif": str(zeros.relative_to(ROOT)), "zip": str((OUT / bundle["zeros_zip"]["filename"]).relative_to(ROOT))},
        "validator": {"saved_bytes_checked": True, "single_band": bool(grid_ok[0]), "crs_epsg_32611": bool(grid_ok[1]),
                      "raster_sha256": sha(zeros), "validate_raster": val,
                      "check_submission_strict_finite": {"returncode": chk.returncode, "stdout": chk.stdout[-1500:]},
                      "shared_writer_audit": bundle["zeros_tif"].get("audit")},
        "submission_name": name,
        "note": note,
        "verdict": None,
        "ok_to_submit": False,
        "slot_selected": False,
        "organizer_score": None,
        "organizer_receipt": None,
        "session_branch": "arena/8c748fe3-gemsdoekarage3",
    }
    v = card["validator"]
    for k in ("finite_inside", "range_0_1", "crs_match", "shape_match", "transform_match"):
        v[k] = bool(_find(val, k))
    gate = assess(card)
    card["promotion_gate"] = gate
    n_dup = len(fa.get("duplicates", []))
    card["registry"]["final_dots"]["duplicates_null_calibrated"] = fa.get("duplicates", [])
    card["verdict"] = "negative"
    card["verdict_reason"] = (f"DUPLICATE STOP: final dots exceed 70% within-3-px overlap with {n_dup} registry rasters even under "
                              "the null-calibrated rule (catalogue-halo lane: 57GEMSDOE strand surfaces, GEMSDOE77 collar35, "
                              "GEMSDOE3 coverage, GEMSDOE86 fault-halo); literal lattice rule also fails. Holdout gate passed "
                              "(HOLDOUT-DTI 0.146 vs archived best 0.107) but live-ledger projection ~0.10 is far below 0.2778. "
                              "Research artifact only - DO NOT SUBMIT.")
    text = json.dumps(card, indent=2, default=str).replace(str(ROOT) + "/", "") + "\n"   # repo-relative paths
    (ROOT / "evidence/ccl_run_card.json").write_text(text)
    (ROOT / "docs/ccl/run-card.json").write_text(text)
    print(json.dumps({"tif": card["files"]["tif"], "sha256": card["raster_sha256"], "name": name, "note": note,
                      "note_len": len(note), "lattice_ov": lattice_ov, "uncovered": uncovered,
                      "check_rc": chk.returncode, "gate": gate}, indent=1))
    print(chk.stdout[-800:])
    return 0


def _find(node, key):
    """Locate a boolean check in the nested validate_raster report (key names vary by section)."""
    aliases = {"finite_inside": ("inside_all_finite",), "range_0_1": ("inside_range_0_1",),
               "crs_match": ("crs_matches",), "shape_match": ("shape_matches",),
               "transform_match": ("transform_matches",)}[key]
    stack = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            for k2, v2 in n.items():
                if k2 in aliases and isinstance(v2, bool):
                    return v2
                stack.append(v2)
        elif isinstance(n, list):
            stack.extend(n)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
