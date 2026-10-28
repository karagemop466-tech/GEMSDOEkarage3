#!/usr/bin/env python3
"""Experiment 3 of 3 (preregistration): build the single best Exp-2 configuration into a
paired GeoTIFF submission via the shared writer, validate without human intervention,
audit uniqueness (focus-9 genuine gate + literal lattice disclosure), evaluate frozen
gates G1-G5, and write the JSON run card. Verdict `promote` requires ALL gates."""
from __future__ import annotations

import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from karage3.evalutil import load_context, read_mask  # noqa: E402
from karage3.holdout import evaluate_sgmc_with_ci, evaluate_visible_only_holdout  # noqa: E402
from karage3.paths import data_dir, docs_dir, evidence_dir, work_dir  # noqa: E402
from karage3.registry_audit import audit_final_dots, audit_surface, load_manifest  # noqa: E402
from karage3.submission import write_submission_pair  # noqa: E402

LATTICE_SRC = Path("/tmp/registry/GEMSDOE24/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif")


def lattice_audit(final_mask: np.ndarray, foot: np.ndarray) -> dict:
    if not LATTICE_SRC.exists():
        return dict(available=False, note="lattice raster not found in local clones; IR-K3-02 stands on sister measurement")
    lat = read_mask(LATTICE_SRC) & foot
    yy, xx = np.ogrid[-3:4, -3:4]
    dil = binary_dilation(lat, structure=(yy * yy + xx * xx) <= 9)
    uncovered = int((foot & ~dil).sum())
    n = int(final_mask.sum())
    return dict(
        available=True, source="buffedlizard55-lab/GEMSDOE24:inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
        lattice_dots=int(lat.sum()), footprint_coverage_3px=float(dil[foot].mean()),
        uncovered_footprint_px=uncovered,
        candidate_within_3px=float(dil[final_mask].mean()) if n else None,
        pigeonhole_min_overlap_at_this_budget=float(max(n - uncovered, 0) / max(n, 1)),
        note="Literal rule vs this space-filling calibration lattice; reported for disclosure (IR-K3-02), not used as the lane gate.",
    )


def main() -> int:
    from scripts.protocol_preflight import require_shared_protocol_ready
    require_shared_protocol_ready()
    t0 = time.time()
    ddir = data_dir()
    surf_dir = work_dir() / "surfaces"
    ctx = load_context(ddir)
    foot, labels = ctx.foot, ctx.labels
    exp1 = json.loads((evidence_dir() / "exp1_screen.json").read_text())
    exp2 = json.loads((evidence_dir() / "exp2_emission.json").read_text())
    sel = exp2["selected"]
    design = exp2["arms"][sel["arm"]][str(sel["budget"])]
    pooled = design["visible_only"]["pooled"]
    print(f"selected design {sel['arm']} @{sel['budget']}: pooled={pooled['pooled_dti']:.5f}", flush=True)

    greedy_mask = np.load(surf_dir / "K3-EXP2-best-mask.npy") & foot
    d_cat = distance_transform_edt(~labels)
    final_mask = greedy_mask & (d_cat > 2.0)
    n_pruned = int(greedy_mask.sum() - final_mask.sum())
    print(f"greedy dots={int(greedy_mask.sum())} -> B2 production prune removes {n_pruned} -> final={int(final_mask.sum())}",
          flush=True)

    fused = np.load(surf_dir / "K3-FUSE-H3H1.npy")
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    note = (f"KARAGE3 K3 scarppair+worms greedy {int(final_mask.sum())}d B2 | HOLDOUT-DTI "
            f"{pooled['pooled_dti']:.4f} vis-v3 SGMC {design['sgmc']['sgmc_prevalence_calibrated_dti']:.4f} | UNSCORED")
    assert len(note) <= 140, len(note)
    meta = dict(
        candidate_id="K3-FUSE-GREEDY-37654-B2",
        description=("K3 lane: corrected-LiDAR crest-base scarp-pair (IR-K3-01 band fix) rank-fused "
                     "with depth-persistent potential-field worms; greedy 300 m kernel-coverage "
                     "emission; production B=2 catalogue ring prune. Instruments: pooled= "
                     "GEMSDOE32-HOLDOUT-v3-visible-only HOLDOUT-DTI of the design (visible-gated); "
                     "sgmc=GEMSDOE32-SGMC-CAL-v3.0. Fields catalogue_hidden_*/drift_* below carry "
                     "those two instrument values for writer compatibility."),
        catalogue_hidden_mean=float(pooled["pooled_dti"]),
        catalogue_hidden_per_quadrant=design["visible_only"]["per_quadrant_dti"],
        sgmc_prevalence_calibrated_dti=float(design["sgmc"]["sgmc_prevalence_calibrated_dti"]),
        drift_corrected_holdout_mean=float(pooled["pooled_dti"]),
        drift_corrected_per_quadrant=design["visible_only"]["per_quadrant_dti"],
        predicted_leaderboard_dti=None,
        ei_drift_corrected=None,
        slot_decision="PENDING-GATES (see evidence/k3_run_card.json)",
        submission_note_zeros=note + " | id {sha8}",
        submission_note_nan=note + " | id {sha8}",
    )
    dl = docs_dir() / "downloads"
    bundle = write_submission_pair(final_mask, foot, labels,
                                   template_tif=ddir / "sample_submission.tif",
                                   out_dir=dl, slug="k3-fuse-greedy-b2", timestamp_tag=ts,
                                   candidate_meta=meta)
    zeros_path = dl / bundle["zeros_tif"]["filename"]
    zip_path = zeros_path.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(zeros_path, zeros_path.name)
    print(f"wrote {zeros_path.name} sha256={bundle['zeros_tif']['sha256']} + zip", flush=True)

    # exact-final-mask instruments: SGMC valid; visible-gated pooled is construction-censored
    final_sgmc = evaluate_sgmc_with_ci(final_mask, ctx, name="exp3:final-mask")
    final_sgmc.pop("_cal_boots", None)
    final_pooled_censored = evaluate_visible_only_holdout(final_mask, ctx, b_collar_px=2.0,
                                                          name="exp3:final-mask-censored-diag")["pooled"]
    print(f"final-mask SGMC-cal={final_sgmc['sgmc_prevalence_calibrated_dti']:.5f} "
          f"(censored pooled diag={final_pooled_censored['pooled_dti']:.5f})", flush=True)

    manifest = load_manifest(ROOT / "registry" / "focus9_registry.json")
    surf_audit = audit_surface(fused, foot, manifest, root=ROOT / ".cache",
                               template_tif=ddir / "sample_submission.tif")
    dot_audit = audit_final_dots(fused, final_mask, foot, manifest, root=ROOT / ".cache",
                                 template_tif=ddir / "sample_submission.tif",
                                 candidate_values=final_mask.astype(np.float32))
    lat = lattice_audit(final_mask, foot)
    print(f"surface audit worst|rho|={surf_audit['worst_abs_spearman']:.4f}; "
          f"dots worst within3px={dot_audit['worst_within_3px_fraction']:.4f} vs {dot_audit['worst_overlap_raster']}; "
          f"lattice within3px={lat.get('candidate_within_3px')}", flush=True)

    champ_rule = exp1["controls"]["GEMSDOE25"]["visible_only"]["pooled"]
    champ_sgmc = float(exp1["champion_control_sgmc_cal"])
    canary_max = max(c["auc_max"] or 0 for c in exp1["canaries"].values())
    gates = dict(
        G1_pooled_beats_champion_rule=dict(
            pass_=bool(pooled["pooled_dti"] > champ_rule["pooled_dti"]),
            candidate=pooled["pooled_dti"], candidate_ci95=pooled["ci95"],
            control=champ_rule["pooled_dti"], control_ci95=champ_rule["ci95"],
            instrument="GEMSDOE32-HOLDOUT-v3-visible-only pooled HOLDOUT-DTI, 22232 withheld positives"),
        G2_sgmc_veto=dict(
            pass_=bool(design["sgmc"]["sgmc_prevalence_calibrated_dti"] >= 0.9 * champ_sgmc),
            candidate=float(design["sgmc"]["sgmc_prevalence_calibrated_dti"]),
            final_mask_candidate=float(final_sgmc["sgmc_prevalence_calibrated_dti"]),
            threshold=0.9 * champ_sgmc, champion=champ_sgmc,
            instrument="GEMSDOE32-SGMC-CAL-v3.0 HOLDOUT-DTI"),
        G3_genuine_uniqueness=dict(
            pass_=bool(dot_audit["passed"] and surf_audit["passed"]),
            worst_within_3px=dot_audit["worst_within_3px_fraction"],
            worst_overlap_raster=dot_audit["worst_overlap_raster"],
            surface_worst_abs_spearman=surf_audit["worst_abs_spearman"],
            scope="9 focus-site bests + 2 champion-lineage controls (registry/focus9_registry.json)",
            literal_lattice=lat),
        G4_validator=dict(
            pass_=bool(bundle["zeros_tif"]["all_checks_passed"] and bundle["nan_tif"]["all_checks_passed"]),
            zeros=bundle["zeros_tif"]["checks"], nan=bundle["nan_tif"]["checks"]),
        G5_canary=dict(pass_=bool(canary_max <= 0.90), max_auc=float(canary_max),
                       n_features=len(exp1["canaries"])),
    )
    verdict = "promote" if all(g["pass_"] for g in gates.values()) else "negative"
    print("GATES:", {k: v["pass_"] for k, v in gates.items()}, "-> verdict:", verdict, flush=True)

    run_card = dict(
        schema_version=1, lane="K3", generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        hypothesis=("Corrected-LiDAR crest-base scarp-pair (bands by description, fixing IR-K3-01) "
                    "rank-fused with depth-persistent potential-field worms finds catalogue-missing "
                    "faults; greedy 300 m kernel-coverage emission beats fixed 2.8 px dotting."),
        mechanism=("Scarp profile dipole (lapneg crest + lappos base + step + coherence) detects "
                   "sub-grid scarplets; multi-scale HG-ridge persistence detects buried basement "
                   "offsets whose edges survive upward-continuation proxy; CELF greedy places each "
                   "dot where uncovered kernel-weighted rank mass is maximal."),
        non_fault_mimic=("Lake Lahontan paleo-shorelines, terrace risers, road cuts and landslide "
                         "head scarps (H3); lithologic contacts and dike margins (H1)."),
        holdout_dti=dict(
            evidence_class="HOLDOUT-DTI",
            evaluator_version="GEMSDOE32-HOLDOUT-v3-visible-only",
            pooled_dti=pooled["pooled_dti"], ci95=pooled["ci95"],
            n_withheld_positives=pooled["n_withheld_positives"],
            design="FUSE@GREEDY-37654 evaluated with per-cell visible-only B=2 gate (uncensored)",
            champion_rule_control=dict(pooled_dti=champ_rule["pooled_dti"], ci95=champ_rule["ci95"],
                                       note="D2.8 pre-prune mask + visible-B2 gate; literal champion mask is construction-censored (IR-K3-09)"),
            sgmc=dict(evaluator_version="GEMSDOE32-SGMC-CAL-v3.0", evidence_class="HOLDOUT-DTI",
                      design_cal=float(design["sgmc"]["sgmc_prevalence_calibrated_dti"]),
                      design_ci95=design["sgmc"]["sgmc_calibrated_ci95"],
                      final_mask_cal=float(final_sgmc["sgmc_prevalence_calibrated_dti"]),
                      final_mask_ci95=final_sgmc["sgmc_calibrated_ci95"],
                      champion_cal=champ_sgmc),
            leaderboard_estimate="NOT ESTIMABLE (no live-validated calibration in this repo; projection is never a score)",
        ),
        correlation_overlap_vs_registry=dict(
            surface_worst_abs_spearman=surf_audit["worst_abs_spearman"],
            surface_worst_raster=surf_audit["worst_raster"],
            final_worst_within_3px=dot_audit["worst_within_3px_fraction"],
            final_worst_overlap_raster=dot_audit["worst_overlap_raster"],
            final_worst_abs_spearman_phi=dot_audit["worst_abs_spearman"],
            literal_lattice=lat, scope_note=dot_audit["rule"]),
        raster=dict(zeros_file=bundle["zeros_tif"]["filename"], zeros_sha256=bundle["zeros_tif"]["sha256"],
                    zeros_bytes=bundle["zeros_tif"]["size_bytes"], zip_file=zip_path.name,
                    zip_sha256=hashlib.sha256(zip_path.read_bytes()).hexdigest(),
                    nan_file=bundle["nan_tif"]["filename"], nan_sha256=bundle["nan_tif"]["sha256"],
                    dots=int(final_mask.sum()), dots_before_b2=int(greedy_mask.sum()), pruned_b2=n_pruned,
                    on_catalogue_dots=int(bundle["zeros_tif"]["on_catalogue_positive_pixels"])),
        validator=dict(zeros=bundle["zeros_tif"], nan=bundle["nan_tif"]),
        submission=dict(name=bundle["zeros_tif"]["filename"].removesuffix(".tif"),
                        note=bundle["submission_note_zeros"], note_chars=len(bundle["submission_note_zeros"])),
        gates=gates, verdict=verdict,
        ok_to_submit=bool(verdict == "promote"),
        download_research=True,
        organizer_confirmed_score=None,
        owner_reported_champion=dict(submission="h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
                                     score=0.2778, label="OWNER-REPORTED (IR-K3-04)"),
        elapsed_s=round(time.time() - t0, 1),
        experiments_used=3,
    )
    (evidence_dir() / "k3_run_card.json").write_text(json.dumps(run_card, indent=2, default=float) + "\n")
    (evidence_dir() / "exp3_final.json").write_text(json.dumps(
        dict(bundle=bundle, surface_audit=surf_audit, dot_audit=dot_audit, lattice=lat,
             final_sgmc=final_sgmc, final_pooled_censored_diag=final_pooled_censored,
             run_card_ref="evidence/k3_run_card.json"), indent=2, default=float) + "\n")
    print(f"wrote evidence/k3_run_card.json verdict={verdict} ok_to_submit={run_card['ok_to_submit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
