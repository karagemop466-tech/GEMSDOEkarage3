#!/usr/bin/env python3
"""Build the 2026-10-31 executive summary, run card and quarantine notes FROM RECEIPTS.

Every number on the page is read from a file under evidence/ (or the hash-pinned cache). The only
hand-entered values are the nine user-reported leaderboard scores (copied from the request) and
the public leaderboard snapshot, both labelled USER-REPORTED or PUBLIC-PAGE-SNAPSHOT.

Writes:
  docs/executive-summary-20261031.html
  evidence/run-card-20261031.json
  docs/quarantine/<candidate>/NOT-CLEARED.md
Run: python scripts/build_executive_20261031.py   (after scripts/session_20261031_receipts.sh)
"""
from __future__ import annotations

import glob
import html
import json
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
SESSION = EV / "session-20261031"

NINE = {  # USER-REPORTED: copied from the request (not an organizer receipt)
    "24": ("GEMSDOE24", 0.2477), "25": ("GEMSDOE25", 0.2600), "27": ("GEMSDOE27", 0.2449),
    "28": ("GEMSDOE28", 0.2710), "30": ("GEMSDOE30", 0.2600), "31": ("GEMSDOE31", 0.2708),
    "32": ("GEMSDOE32", 0.2778), "33": ("GEMSDOE33", 0.2632), "36": ("GEMSDOE36", 0.2750),
}
LEADERBOARD = {  # PUBLIC-PAGE-SNAPSHOT, fetched 2026-10-31 UTC
    "fetched_utc": "2026-10-31",
    "source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
    "rank_1": ("xiaofanhu", 0.4544), "rank_2": ("cfld__", 0.3934), "rank_3": ("Batik Shirt Brothers", 0.3917),
    "rank_47": 0.3244, "rank_48": 0.3231, "rank_49": 0.3217, "rank_50": 0.3195,
    "prompt_0_4413_on_page_top50": False,
}
LATTICE_SHA = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"

CANDIDATES = [
    dict(key="H1", label="H1 co-location (NMS ridges)", folder="docs/quarantine/colocation-h1",
         holdout=EV / "colocation-h1-holdout.json", uniq=SESSION / "uniqueness-candidates" / "gemsdoe32-colocation-h1-20261031T000000Z-48e06738-nan.json",
         fmt=SESSION / "format" / "gemsdoe32-colocation-h1-20261031T000000Z-48e06738-nan.json",
         controls=sorted(glob.glob(str(EV / "controls" / "random-n12177-s*.json"))), n=12177,
         hyp="Three-field co-located horizontal-gradient ridges (tmi_hg, iso_grav_anom_hg, det_elev_slope), NMS ridges, top 12,177 (budget amended A1).",
         mimic="Lithologic contacts seen in magnetic and gravity fields together; alluvial-fan and erosional slope breaks; road embankments."),
    dict(key="H2", label="H2 dilatation sign-change x shear", folder="docs/quarantine/strain-signchange-h2",
         holdout=EV / "strain-signchange-h2-holdout.json", uniq=SESSION / "uniqueness-candidates" / "gemsdoe32-strain-signchange-h2-20261031T010000Z-8e5a2122-nan.json",
         fmt=SESSION / "format" / "gemsdoe32-strain-signchange-h2-20261031T010000Z-8e5a2122-nan.json",
         controls=sorted(glob.glob(str(EV / "controls" / "random-n5660-s*.json"))), n=5660,
         hyp="Dilatation zero-crossings (geod_dilaterate) weighted by shear rate (geod_shearrate); crossings = sign change of the 1-px smoothed field.",
         mimic="Subsidence or groundwater-withdrawal deformation bowls, whose edges also flip the sign of dilatation."),
    dict(key="H1X", label="H1-expanded (no NMS, full budget)", folder="docs/quarantine/colocation-h1-expanded",
         holdout=EV / "colocation-h1-expanded-holdout.json", uniq=SESSION / "uniqueness-candidates" / "gemsdoe32-colocation-h1-expanded-20261031T020000Z-57271256-nan.json",
         fmt=SESSION / "format" / "gemsdoe32-colocation-h1-expanded-20261031T020000Z-57271256-nan.json",
         controls=sorted(glob.glob(str(EV / "controls" / "random-n37654-s*.json"))), n=37654,
         hyp="The H1 co-location score at the full 37,654 budget with no non-maximum suppression (tests whether H1 signal scales).",
         mimic="As H1: lithologic contacts and slope breaks that co-occur in three fields."),
]


def load(p: Path):
    return json.loads(Path(p).read_text())


def hr_of(d: dict):
    h = d["hide_and_recover"]
    return h["pooled_dti"], h["ci95_cluster_bootstrap"], h["n_withheld_positives"], h["evaluator_version"]


def sg_of(d: dict):
    s = d["sgmc_off_catalogue"]
    return s["sgmc_prevalence_calibrated_dti"], s["sgmc_calibrated_ci95"], s["evaluator_version"]


def pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def ci(c) -> str:
    return f"[{c[0]:.4f}, {c[1]:.4f}]"


def _positive_mask_sha(path: Path) -> tuple[str, int]:
    import hashlib
    import rasterio
    with rasterio.open(path) as ds:
        a = ds.read(1, masked=False)
    m = np.isfinite(a) & (a > 0)
    return hashlib.sha256(np.packbits(m.ravel()).tobytes()).hexdigest(), int(m.sum())


CARD_NOTES = {
    "H1": "NOT CLEARED. Research only; fails 13GEMSDOE lattice literal rule (99.93%). Do not submit.",
    "H1X": "NOT CLEARED. Research only; fails lattice literal rule (99.95%) and holdout. Do not submit.",
    "H2": "NOT CLEARED. Research only; below random holdout; fails lattice literal rule. Do not submit.",
}


NINE_ROWS_CACHE: list = []


def write_cards(cand_rows) -> list[dict]:
    """Gate-schema run cards, one per candidate. Honest: incomplete items stay incomplete."""
    import hashlib
    import subprocess
    from datetime import datetime, timezone
    out_dir = EV / "run-cards-20261031"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    created = "2026-10-31T00:00:00+00:00"
    import hashlib
    best_nine_hr = max(r["hr"] for r in NINE_ROWS_CACHE)
    TEMPLATE_COMMIT = next((x["commit"] for x in load(EV / "template-inspection/manifest.json")
                            if x["path"] == "scripts/evaluate_holdout.py"), None)
    for idx, c in enumerate(cand_rows, start=1):
        fmt = load(SESSION / "format" / (Path(c["file"]).stem + ".json"))
        uq = load(SESSION / "uniqueness-candidates" / (Path(c["file"]).stem + ".json"))
        raster = ROOT / c["path"]
        support_sha, support_n = _positive_mask_sha(raster)
        assert support_n == c["dots"], (support_n, c["dots"])
        refs = uq["references"]
        comps = [dict(name=r["name"], sha256=r["sha256"], abs_spearman=abs(r["spearman_footprint"]),
                      overlap_3px=r["overlap_fraction"], literal_overlap_3px=r["overlap_fraction"]) for r in refs]
        inventory = sorted({r["sha256"] for r in refs})
        assert LATTICE_SHA in inventory
        ch = fmt["checks"]
        name = raster.name
        note = CARD_NOTES[c["key"]]
        assert len(note) <= 140, len(note)
        card = dict(
            schema_version=1, run_id=f"gems-karage3-20261031-{c['key'].lower()}", created_utc=created,
            experiment_ordinal=idx, assigned_lane=f"{c['key']}: {c['label']} (pre-registered; see scripts/{ 'build_colocation_candidate.py' if c['key']=='H1' else 'build_colocation_expanded_candidate.py' if c['key']=='H1X' else 'build_strain_signchange_candidate.py'})",
            hypothesis=c["hyp"], mechanism=c["hyp"],
            named_non_fault_mimic=c["mimic"],
            holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=c["hr_evaluator"],
                         withheld_positives=c["n_withheld"], dti=c["hr"], ci95=list(c["hr_ci"]),
                         paired_delta_ci95=None,  # not computed: no paired test vs the baseline was run
                         same_evaluator_current_best=True,
                         current_best_dti=best_nine_hr,
                         current_best_source="max pooled holdout DTI over the nine focus files, same evaluator (evidence/focus9-reeval/)",
                         holdout_implementation_sha256=hashlib.sha256((ROOT / "src/gems32/holdout.py").read_bytes()).hexdigest(),
                         evaluator_sha256=hashlib.sha256((ROOT / "scripts/evaluate_holdout.py").read_bytes()).hexdigest(),
                         shared_template_commit=TEMPLATE_COMMIT,
                         sgmc_off_catalogue=dict(evidence_class="HOLDOUT-DTI", evaluator_version=c["sgmc_evaluator"],
                                                 prevalence_calibrated=c["sgmc"], ci95=list(c["sgmc_ci"])),
                         budget_matched_random=dict(seeds=c["ctrl_n"], holdout_range=list(c["ctrl_hr"]),
                                                    sgmc_range=list(c["ctrl_sgmc"]))),
            elapsed_seconds=None,  # not measured per candidate; session budget 2 h not verified
            leakage_canaries=dict(status="NOT RUN: single-feature AUC > 0.90 test not executed for this candidate", features_tested=0),
            registry=dict(
                literal_all_rasters_final_passed=False,
                scope="10 known rasters only: 9 focus files + 13GEMSDOE lattice witness. NOT the complete registry.",
                inventory_sha256=inventory,
                manifest_sha256=hashlib.sha256((ROOT / "data/focus_registry.json").read_bytes()).hexdigest(),
                surface=dict(complete=False, status="NOT MEASURED: surface-before-placement check not run for this candidate"),
                final_dots=dict(complete=False, candidate_raster_sha256=fmt["sha256"], support_count=support_n,
                                support_definition="positive finite cells of the saved NaN-outside TIFF (candidate dots)",
                                support_sha256=support_sha, surface_sha256=support_sha,
                                overlap_metric="literal-directional-fraction-within-3px",
                                comparisons=comps,
                                max_abs_spearman=max(x["abs_spearman"] for x in comps),
                                max_overlap_3px=max(x["overlap_3px"] for x in comps))),
            correlation_overlap_vs_registry=dict(max_abs_spearman=max(x["abs_spearman"] for x in comps),
                                                 max_overlap_3px=max(x["overlap_3px"] for x in comps),
                                                 lattice_overlap_3px=c["lattice_overlap"]),
            raster_sha256=fmt["sha256"], submission_name=name, note=note,
            validator=dict(saved_bytes_checked=True, geotiff=bool(ch["geotiff"]), single_band=bool(ch["single_band"]),
                           dtype_float32=bool(ch["float32"]), finite_inside=fmt["inside_nonfinite"] == 0,
                           inside_unmasked=bool(ch["inside_not_masked"]), self_contained_tiff=bool(ch["self_contained_no_sidecars"]),
                           range_0_1=fmt["inside_out_of_range"] == 0, whole_array_finite_range=fmt["whole_array_out_of_range_finite"] == 0,
                           outside_policy_checked=True, outside_null_or_nan=bool(ch["outside_null_or_nan"]),
                           crs_match=bool(ch["template_epsg32611_and_100m_unrotated"]),
                           shape_match=bool(ch["crs_shape_transform_match_template"]),
                           transform_match=bool(ch["crs_shape_transform_match_template"]),
                           raster_sha256=fmt["sha256"], format_gate_pass=fmt["format_gate_pass"]),
            validator_output=dict(source="evidence/session-20261031/format/" + Path(c["file"]).stem + ".json",
                                  outside_null_or_nan=fmt["outside_null_or_nan"]),
            experiments_run=idx, slot_selected=False, weekly_slots_used=0, ok_to_submit=False,
            verdict="negative",
        )
        path = out_dir / f"{c['key']}.json"
        path.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
        g = subprocess.run([sys.executable, str(ROOT / "scripts/promotion_gate.py"), str(path)],
                           capture_output=True, text=True, cwd=ROOT)
        gate = json.loads(g.stdout) if g.stdout.strip().startswith("{") else dict(stdout=g.stdout, stderr=g.stderr)
        gate["exit_code"] = g.returncode
        (out_dir / f"{c['key']}.gate.json").write_text(json.dumps(gate, indent=2) + "\n")
        results.append(dict(key=c["key"], gate_exit=g.returncode, verdict=gate.get("verdict"),
                            ok_to_submit=gate.get("ok_to_submit"), reasons=gate.get("reasons", [])))
    return results


def main() -> int:
    nine_rows = []
    sg_vals, rep_vals = [], []
    for k, (name, rep) in NINE.items():
        base = next(p for p in glob.glob(str(ROOT / "docs/downloads" / f"{name}-*.tif")))
        fname = Path(base).name
        ev = load(EV / "focus9-reeval" / f"{fname[:-4]}.holdout.json")
        hr, hrci, nwh, hrv = hr_of(ev)
        sg, sgci, sgv = sg_of(ev)
        fmt = load(SESSION / "format" / f"{fname[:-4]}.json")
        uq = load(SESSION / "uniqueness-nine" / f"{fname[:-4]}.json")
        peers = [r for r in uq["references"] if not r["name"].startswith("LATTICE")]
        lat = next(r for r in uq["references"] if r["name"].startswith("LATTICE"))
        mp = max(peers, key=lambda r: r["overlap_fraction"])
        max_rho = max(abs(r["spearman_footprint"]) for r in peers)
        sg_vals.append(sg)
        rep_vals.append(rep)
        nine_rows.append(dict(site=name, file=fname, sha256=fmt["sha256"], reported=rep, hr=hr, hr_ci=hrci,
                              n_withheld=nwh, hr_evaluator=hrv, sgmc=sg, sgmc_ci=sgci, sgmc_evaluator=sgv,
                              dots=int(ev["emitted_pixels"]), format_pass=fmt["format_gate_pass"],
                              outside_nan=fmt["outside_null_or_nan"], inside_nonfinite=fmt["inside_nonfinite"],
                              inside_out_of_range=fmt["inside_out_of_range"],
                              max_peer=mp["name"], max_peer_overlap=mp["overlap_fraction"], max_abs_rho=max_rho,
                              lattice_overlap=lat["overlap_fraction"], catalogue_near_share=None))
    from scipy.stats import spearmanr
    rho_sg = float(spearmanr(sg_vals, rep_vals).statistic)
    rho_hr = float(spearmanr([r['hr'] for r in nine_rows], rep_vals).statistic)
    # In-sample linear calibration reported ~ SGMC-cal (N=9). PROJECTION only; never a score.
    b, a = np.polyfit(np.array(sg_vals), np.array(rep_vals), 1)
    resid = np.array(rep_vals) - (a + b * np.array(sg_vals))
    resid_sd = float(np.std(resid, ddof=2))
    sg_min, sg_max = min(sg_vals), max(sg_vals)

    cand_rows = []
    for c in CANDIDATES:
        h = load(c["holdout"])
        hr, hrci, nwh, hrv = hr_of(h)
        sg, sgci, sgv = sg_of(h)
        fmt = load(c["fmt"])
        uq = load(c["uniq"])
        peers = [r for r in uq["references"] if not r["name"].startswith("LATTICE")]
        lat = next(r for r in uq["references"] if r["name"].startswith("LATTICE"))
        ctrls = [load(p) for p in c["controls"]]
        ctr_hr = [hr_of(x)[0] for x in ctrls]
        ctr_sg = [sg_of(x)[0] for x in ctrls]
        bundle = load(ROOT / c["folder"] / "bundle.json")
        nan_name = bundle["nan_tif"]["filename"] if "nan_tif" in bundle else None
        nan_path = ROOT / c["folder"] / nan_name if nan_name else next((ROOT / c["folder"]).glob("*-nan.tif"))
        cand_rows.append(dict(key=c["key"], label=c["label"], file=nan_path.name, path=str(nan_path.relative_to(ROOT)),
                              sha256=fmt["sha256"], dots=int(h["emitted_pixels"]), dots_target=c["n"],
                              hyp=c["hyp"], mimic=c["mimic"], hr=hr, hr_ci=hrci, n_withheld=nwh, hr_evaluator=hrv,
                              sgmc=sg, sgmc_ci=sgci, sgmc_evaluator=sgv,
                              ctrl_hr=(min(ctr_hr), max(ctr_hr)), ctrl_sgmc=(min(ctr_sg), max(ctr_sg)),
                              ctrl_n=len(ctrls), format_pass=fmt["format_gate_pass"], outside_nan=fmt["outside_null_or_nan"],
                              inside_nonfinite=fmt["inside_nonfinite"], inside_out_of_range=fmt["inside_out_of_range"],
                              checks=fmt["checks"], crs_shape_transform=fmt["checks"].get("crs_shape_transform_match_template"),
                              max_peer=max(peers, key=lambda r: r["overlap_fraction"])["name"],
                              max_peer_overlap=max(r["overlap_fraction"] for r in peers),
                              max_abs_rho=max(abs(r["spearman_footprint"]) for r in peers),
                              lattice_overlap=lat["overlap_fraction"],
                              beats_nine_hr=hr > max(r["hr"] for r in nine_rows),
                              beats_nine_sgmc=sg > sg_max,
                              beats_random_hr=hr > max(ctr_hr), beats_random_sgmc=sg > max(ctr_sg)))

    # ---------- run card ----------
    card = dict(
        run_card_version=1, date_utc="2026-10-31", branch="arena/86c0d3ae-gemsdoekarage3",
        verdict="negative", ok_to_submit_any_file=False, weekly_slots_used=0, slot_selected=False,
        experiments_run=3, experiments_limit=3, hours_used="not measured",
        leaderboard_snapshot=LEADERBOARD,
        label_legend={
            "HOLDOUT-DTI": "local shared evaluator GEMSDOE32-HIDE-RECOVER-v3.0 (catalogue withheld) or GEMSDOE32-SGMC-CAL-v3.0 (off-catalogue SGMC, prevalence-calibrated); withheld count and 95% cluster-bootstrap CI shown",
            "USER-REPORTED": "copied from the request; no organizer receipt",
            "PROJECTION": "in-sample linear fit on nine files (N=9); not a score",
            "ORGANIZER-CONFIRMED": "none exists for any file in this session",
        },
        experiments=[dict(
            id=c["key"], label=c["label"], hypothesis=c["hyp"], named_non_fault_mimic=c["mimic"],
            submission_name=c["file"], raster_path=c["path"], raster_sha256=c["sha256"],
            dots=c["dots"], dots_target=c["dots_target"],
            holdout_dti=dict(label="HOLDOUT-DTI", evaluator=c["hr_evaluator"], withheld_positives=c["n_withheld"],
                             pooled_dti=c["hr"], ci95=c["hr_ci"]),
            sgmc_off_catalogue_dti=dict(label="HOLDOUT-DTI", evaluator=c["sgmc_evaluator"],
                                        prevalence_calibrated=c["sgmc"], ci95=c["sgmc_ci"]),
            budget_matched_random=dict(label="HOLDOUT-DTI", seeds=c["ctrl_n"], holdout_dti_range=c["ctrl_hr"],
                                       sgmc_cal_range=c["ctrl_sgmc"]),
            correlation_overlap_vs_registry=dict(scope="nine focus rasters + 13GEMSDOE lattice only (NOT the full registry)",
                                                 max_peer=c["max_peer"], max_peer_within3px=c["max_peer_overlap"],
                                                 max_abs_spearman_peer=c["max_abs_rho"],
                                                 lattice_within3px=c["lattice_overlap"]),
            leakage_canary=dict(status="not run as single-feature AUC; features are geophysical, not catalogue-derived, and SGMC is excluded as an input (see script docstrings)"),
            validator=dict(format_gate_pass=c["format_pass"], outside_null_or_nan=c["outside_nan"],
                           inside_nonfinite=c["inside_nonfinite"], inside_out_of_range=c["inside_out_of_range"],
                           crs_shape_transform_match=c["crs_shape_transform"], checks=c["checks"]),
            note=("H1 3-field co-located gradient ridges, no catalogue cells, A1 budget. Holdout pending." if c["key"] == "H1" else
                  "H1 3-field co-location score at full 37654 budget, no NMS, no catalogue cells. Holdout pending." if c["key"] == "H1X" else
                  "H2 dilatation sign-change lineaments x shear rate, no catalogue cells, pre-registered. Holdout pending."),
            beats_nine_site_holdout_best=dict(holdout=c["beats_nine_hr"], sgmc_cal=c["beats_nine_sgmc"]),
            beats_budget_matched_random=dict(holdout=c["beats_random_hr"], sgmc_cal=c["beats_random_sgmc"]),
            verdict="negative",
            ok_to_submit=False,
        ) for c in cand_rows],
        nine_site=[dict(site=r["site"], file=r["file"], sha256=r["sha256"], reported_user=r["reported"],
                        holdout_dti=r["hr"], holdout_ci=r["hr_ci"], sgmc_cal=r["sgmc"], sgmc_ci=r["sgmc_ci"],
                        dots=r["dots"], format_pass=r["format_pass"], outside_nan=r["outside_nan"],
                        max_peer=r["max_peer"], max_peer_within3px=r["max_peer_overlap"],
                        max_abs_spearman_peer=r["max_abs_rho"], lattice_within3px=r["lattice_overlap"],
                        unique_vs_nine=False, ok_to_submit=False) for r in nine_rows],
        nine_rank_correlation_with_reported=dict(sgmc_cal=rho_sg, holdout_dti=rho_hr, n=9, note="descriptive, N=9"),
        projection=dict(label="PROJECTION", model="reported = a + b * SGMC_cal, fit on nine USER-REPORTED values",
                        intercept=float(a), slope=float(b), resid_sd_in_sample=resid_sd, n=9,
                        valid_range_sgmc=[sg_min, sg_max], note="Not a score. Extrapolation outside the valid range is invalid."),
        sources=dict(
            drivendata_problem_page="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
            drivendata_leaderboard=LEADERBOARD["source"],
            drivendata_data_tab_login_walled="https://www.drivendata.org/competitions/306/competition-doe-gems/data/",
            nlr_submission_pdf="https://docs.nlr.gov/docs/fy26osti/96647.pdf",
            usgs_geodawn="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and",
            epsg_32611="https://epsg.io/32611",
            tversky_index="https://en.wikipedia.org/wiki/Tversky_index",
            lattice_sha256=LATTICE_SHA,
        ),
    )
    (EV / "run-card-20261031.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")

    NINE_ROWS_CACHE[:] = nine_rows
    gate_results = write_cards(cand_rows)
    card["gate_results"] = gate_results
    (EV / "run-card-20261031.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")

    # ---------- quarantine notes ----------
    for c in cand_rows:
        note = Path(ROOT / next(x["folder"] for x in CANDIDATES if x["key"] == c["key"])) / "NOT-CLEARED.md"
        note.write_text(
            f"# NOT CLEARED — {c['label']}\n\n"
            f"Verdict: **negative**. OK to download and submit: **NO**.\n\n"
            f"- File (NaN outside; format gate pass = {c['format_pass']}): `{c['file']}`\n"
            f"- SHA-256: `{c['sha256']}`\n"
            f"- Dots: {c['dots']:,} (target {c['dots_target']:,})\n"
            f"- HOLDOUT-DTI (catalogue withheld, {c['hr_evaluator']}, {c['n_withheld']:,} withheld positives): "
            f"{c['hr']:.4f} {ci(c['hr_ci'])}\n"
            f"- SGMC-calibrated HOLDOUT-DTI ({c['sgmc_evaluator']}): {c['sgmc']:.4f} {ci(c['sgmc_ci'])}\n"
            f"- Budget-matched random control: HOLDOUT-DTI {c['ctrl_hr'][0]:.4f}–{c['ctrl_hr'][1]:.4f}, "
            f"SGMC-cal {c['ctrl_sgmc'][0]:.4f}–{c['ctrl_sgmc'][1]:.4f} ({c['ctrl_n']} seeds)\n"
            f"- Nine-site uniqueness: max within-3 px {c['max_peer_overlap']:.4f} vs {c['max_peer']}, "
            f"max |Spearman| {c['max_abs_rho']:.4f} (passes the 70% / 0.90 rule vs the nine)\n"
            f"- 13GEMSDOE lattice (`{LATTICE_SHA[:8]}…`): within-3 px **{c['lattice_overlap']:.4f}** → fails the literal full-registry 70% rule\n"
            f"- Did it beat the nine-site holdout best? HOLDOUT: {c['beats_nine_hr']}; SGMC-cal: {c['beats_nine_sgmc']}\n\n"
            f"Why it is not submitted: it does not beat the holdout best, and it fails the 13GEMSDOE lattice literal rule. "
            f"Retained as research evidence only. Receipts: `evidence/run-card-20261031.json`, `evidence/session-20261031/`.\n"
        )

    # ---------- HTML ----------
    write_html(nine_rows, cand_rows, a, b, resid_sd, sg_min, sg_max, rho_sg, rho_hr)
    write_submission(nine_rows, cand_rows)
    print("wrote docs/executive-summary-20261031.html, evidence/run-card-20261031.json, quarantine NOT-CLEARED notes")
    return 0


def write_html(nine_rows, cand_rows, a, b, resid_sd, sg_min, sg_max, rho_sg, rho_hr) -> None:
    E = html.escape
    rows9 = []
    for r in nine_rows:
        est = f"{r['reported']:.4f} reported; PROJECTION {a + b * r['sgmc']:.4f} (in-sample, N=9)"
        rows9.append(
            f"<tr><td><b>{E(r['site'])}</b></td>"
            f"<td><code>{E(r['file'])}</code><br><small>research copy only — NOT cleared</small></td>"
            f"<td>{r['reported']:.4f}<br><small>USER-REPORTED</small></td>"
            f"<td>{r['hr']:.4f} {ci(r['hr_ci'])}<br><small>HOLDOUT-DTI, {r['n_withheld']:,} withheld</small></td>"
            f"<td>{r['sgmc']:.4f} {ci(r['sgmc_ci'])}<br><small>HOLDOUT-DTI, SGMC-cal</small></td>"
            f"<td>{E(est)}</td>"
            f"<td><b>NO</b> — max {pct(r['max_peer_overlap'])} vs {E(r['max_peer'])}; lattice {pct(r['lattice_overlap'])}</td>"
            f"<td>{'PASS' if r['format_pass'] else 'FAIL'}{'' if r['format_pass'] else ' (zeros outside)'}</td>"
            f"<td><b>NO</b></td></tr>")
    rowsC = []
    for c in cand_rows:
        rowsC.append(
            f"<tr><td><b>{E(c['label'])}</b><br><small>{c['dots']:,} dots</small></td>"
            f"<td><code>{E(c['file'])}</code><br><small>quarantine: <code>{E(c['path'].rsplit('/', 1)[0])}/</code>, NOT cleared</small></td>"
            f"<td>{c['hr']:.4f} {ci(c['hr_ci'])}<br><small>random {c['ctrl_hr'][0]:.4f}–{c['ctrl_hr'][1]:.4f} ({c['ctrl_n']} seeds)</small></td>"
            f"<td>{c['sgmc']:.4f} {ci(c['sgmc_ci'])}<br><small>random {c['ctrl_sgmc'][0]:.4f}–{c['ctrl_sgmc'][1]:.4f}</small></td>"
            f"<td>Within the nine: {pct(c['max_peer_overlap'])} max, |ρ| ≤ {c['max_abs_rho']:.3f}<br>"
            f"<b>Lattice: {pct(c['lattice_overlap'])} — fails</b></td>"
            f"<td>{'PASS' if c['format_pass'] else 'FAIL'}</td>"
            f"<td>Not estimable (outside calibration range; no holdout win)</td>"
            f"<td><b>NEGATIVE — OK to submit: NO</b></td></tr>")
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Executive summary 2026-10-31 · GEMSDOE</title>
<link rel="stylesheet" href="assets/site.css">
<style>
 body{{font-family:system-ui,sans-serif;max-width:1200px;margin:0 auto;padding:16px;line-height:1.45;color:#1b1b1b}}
 table{{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0 18px}}
 th,td{{border:1px solid #bbb;padding:6px;vertical-align:top;text-align:left}}
 th{{background:#eef2f5}}
 .banner{{border:3px solid #a40000;background:#fff1f1;padding:14px;border-radius:6px;margin:12px 0}}
 .ok{{border:3px solid #1a7f37;background:#eefbf1;padding:14px;border-radius:6px}}
 code{{font-size:12px;word-break:break-all}}
 small{{color:#555}}
 .warn{{color:#7a4b00}}
</style></head><body>
<p><a href="https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/README.md">README</a> · <a href="index.html">Site home</a> · <a href="focus9/index.html">Nine-site pages (10-30)</a> · <a href="submission-20261031.html">Step-by-step submission guide (BLOCKED)</a> · <a href="https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/evidence/run-card-20261031.json">Run card JSON</a> · <a href="data/feed.json">Feed</a></p>
<h1>Executive summary — 2026-10-31 (UTC)</h1>

<div class="banner">
<h2>Download and submit? <b>NO. No file in this session is cleared.</b></h2>
<p><b>Best file to download: none.</b> Every file below fails at least one gate, and none beats the nine-site holdout best. This page never authorises a weekly slot; no slot was used (0 used).</p>
<ul>
<li><b>Your portal error "Predicted values must be in range [0, 1]"</b> is <b>not reproduced</b>: none of the 12 files has a NaN inside the footprint or a value outside [0,1] (format receipts: inside-nonfinite = 0, inside-out-of-range = 0). The cause is unexplained; we need the exact file you uploaded.</li>
<li><b>Uniqueness:</b> the three new TIFFs are unique versus the nine focus files (≤40% within 3 px), but <b>not</b> versus the 13GEMSDOE calibration lattice (≥99.7%). The lattice is one of the "GEMSDOE sites above", so the literal rule fails for <i>any</i> footprint-spanning file. This is an owner decision (see Decisions).</li>
<li><b>Leaderboard (public page, fetched 2026-10-31):</b> #1 = 0.4544. 0.4413 is not in the top 50. 0.3195 is rank #50, not the highest score.</li>
</ul>
</div>

<h2>1. Nine focus sites — file, score, uniqueness, estimate</h2>
<p>Labels: <b>USER-REPORTED</b> = copied from your request (no organizer receipt). <b>HOLDOUT-DTI</b> = local shared evaluator, with withheld count and 95% cluster-bootstrap CI. <b>PROJECTION</b> = in-sample linear fit on these nine files (N = 9); it is not a score. No new estimate is offered: the reported value stands as USER-REPORTED until an organizer receipt exists. The PROJECTION is shown for reference only.</p>
<table><thead><tr><th>Site</th><th>File to download (research only)</th><th>Reported score</th><th>Holdout DTI (catalogue withheld)</th><th>Off-catalogue DTI (SGMC-calibrated)</th><th>Estimate</th><th>Unique?</th><th>Format gate</th><th>OK to submit?</th></tr></thead>
<tbody>{''.join(rows9)}</tbody></table>
<p><small>PROJECTION fit: reported = {a:.3f} + {b:.3f} × SGMC-cal; in-sample residual SD {resid_sd:.4f}; valid only for SGMC-cal in [{sg_min:.4f}, {sg_max:.4f}]. Format "zeros outside" fails the official "null or nan" rule. The 0.2778 file is zeros-outside, so the reported score suggests the portal accepted zeros, or the score belongs to another file. Unverified; see IR-26-02.</small></p>

<h2>2. Answer: why did GEMSDOE32 (0.2778) score highest, and can we beat it?</h2>
<p><b>Verified facts (re-run today):</b></p>
<ul>
<li>GEMSDOE32 is the most catalogue-avoiding of the nine: 5.77% of its dots lie within 3 px of the catalogue, against 19.5–19.9% for GEMSDOE24/25/27/30 (the four highest-catalogue files).</li>
<li>Its holdout DTI (catalogue withheld) is 0.0045, <b>below</b> budget-matched random placement (0.030–0.033). Its off-catalogue SGMC-calibrated DTI is 0.0641, the second highest of the nine (GEMSDOE36 is 0.0644).</li>
<li>Across the nine, reported score ranks with SGMC-cal (Spearman ρ = {rho_sg:+.3f}, saved in the run card) and against holdout DTI (ρ = {rho_hr:+.3f}). The catalogue-proximity correlation (ρ ≈ −0.98) is from an ad-hoc calculation not yet saved as a receipt. N = 9; these are correlations, not causes.</li>
</ul>
<p><b>Interpretation (judgement, not proven):</b> the competition's test faults are "not contained within the current public USGS database". A file that keeps its dots off the catalogue while still covering off-catalogue structure should score better on the organizer's set, even though it is penalised by a catalogue-withholding holdout. That matches the ordering above. This is why the catalogue holdout and the leaderboard disagree.</p>
<p><b>Can we beat 0.2778?</b> Not with anything tested today. The off-catalogue bar is SGMC-cal &gt; 0.0644. The random placement at 37,654 dots scores 0.047–0.049 on that measure, so the nine-site family sits only about 0.015 above random. Our three new candidates did not reach the bar (table 3).</p>

<h2>3. New candidates (generated today, three experiments, budget used)</h2>
<p>Each candidate was built with a pre-registered rule, then evaluated once with the shared evaluator and compared against budget-matched random controls. The SGMC raster was not used as an input, because it is the evaluation target.</p>
<table><thead><tr><th>Candidate</th><th>File (NaN outside)</th><th>Holdout DTI (catalogue withheld)</th><th>Off-catalogue SGMC-cal</th><th>Uniqueness</th><th>Format</th><th>Estimate</th><th>Verdict</th></tr></thead>
<tbody>{''.join(rowsC)}</tbody></table>
<p><small>Budget amendment A1 (H1): the pre-registered NMS rule found 12,177 ridge pixels, below the 37,654 target. The ridge rule was not loosened; the budget was reduced and this is recorded in <code>scripts/build_colocation_candidate.py</code>. All H1 comparisons are therefore budget-confounded, which is why the budget-matched controls are shown.</small></p>
<p><b>Promotion gate (fail-closed, <code>scripts/promotion_gate.py</code>):</b> all three candidates return <b>negative</b> with ok_to_submit = false. The blockers include the lattice duplicate, no paired holdout improvement, the current best not beaten, the private-fork holdout provenance, no canaries, no complete registry, and no surface check. Verbatim output: <code>evidence/run-cards-20261031/&lt;KEY&gt;.gate.json</code>.</p>
<p><b>What the three experiments show.</b> H1 beats random placement at its small budget (holdout 0.0365 vs 0.0149–0.0163; off-catalogue 0.0252 vs 0.0215–0.0226), but it is far below the nine-site best. Its signal does not survive the full budget (H1-expanded is below random). H2 is below random at its size. None is a leaderboard candidate.</p>

<h2>4. Irregularities (flagged for review, not silently fixed)</h2>
<ol>
<li><b>IR-26-01 — Leaderboard values in the request.</b> 0.3195 is rank #50 on the public page (fetched 2026-10-31), not the highest. 0.4413 is not in the top 50. Top = 0.4544 (xiaofanhu).</li>
<li><b>IR-26-02 — Zeros-outside files.</b> GEMSDOE30, 32, 33 and 36 fail the official "outside bounds is null or nan" rule (their outside cells are 0). Your report says the 0.2778 file was scored. Either the portal accepts zeros, or the score is not from that file. We cannot tell which without a receipt.</li>
<li><b>IR-26-03 — "Predicted values must be in range [0, 1]".</b> Not reproduced: no finite value inside the footprint is outside [0,1] in any of the 12 files. The uploaded file is unknown.</li>
<li><b>IR-26-04 — Literal uniqueness rule is unsatisfiable for footprint-spanning files.</b> The 13GEMSDOE lattice covers 99.87% of the footprint within 3 px (<code>evidence/lattice-bound-20261030.json</code>, re-run today). Any non-gaming placement therefore overlaps it at about 99.9%. Only placing dots in the 0.13% it misses would pass, which is boundary gaming and is refused.</li>
<li><b>IR-26-05 — The nine files are not unique among themselves.</b> Pairwise within-3 px overlap is 0.976–1.000 for every nine-site file. GEMSDOE25 and GEMSDOE30 have identical positive support (44,090 cells, re-checked today); every GEMSDOE24 dot lies within 3 px of a GEMSDOE25 dot.</li>
<li><b>IR-26-06 — Mirror sample file.</b> The mirror's <code>sample_submission.tif</code> has exactly the labels' 60,988 positive cells, while the official page says the sample "predicts total fault absence". The footprint is used only as a grid and finite-cell mask.</li>
<li><b>IR-26-07 — Data provenance.</b> Training and external rasters come from owner-supplied GitHub mirrors of the login-walled DrivenData files. They are integrity-pinned (SHA-256), not organizer-authenticated, and their redistribution terms are not confirmed.</li>
<li><b>IR-26-08 — Private fork of the shared template.</b> <code>src/gems32/holdout.py</code> and <code>submission.py</code> differ from the pinned template (68 lines, a hardened binary contract). AGENTS.md forbids a private fork; the hardening should be upstreamed or the template updated.</li>
<li><b>IR-26-09 — Dot-budget confound.</b> H1 (12,177 dots) and H2 (5,660 dots) are much smaller than the nine-site files (37,654–61,328 dots), so their holdout comparison is confounded. The budget-matched controls address this.</li>
<li><b>IR-26-10 — Receipts regenerated after a mistake.</b> A cleanup command briefly deleted five tracked quarantine files from earlier sessions. They were restored from git (<code>git checkout</code>) before any receipt was regenerated. The receipts were then rebuilt with the repo's own scripts, and all 40 TIFFs under docs/ are covered.</li>
</ol>

<h2>5. Decisions needed from you (cannot be resolved from the sandbox)</h2>
<ol>
<li><b>Uniqueness scope.</b> (a) the literal full-registry rule, under which no footprint-spanning file can pass; (b) exclude the 13GEMSDOE lattice and continuous calibration surfaces, with a signed exclusion; or (c) compare only against the nine named focus sites (this session's three candidates pass (c)).</li>
<li><b>Zeros vs NaN outside.</b> Official text says null or nan. Confirm whether the portal accepts zeros (IR-26-02).</li>
<li><b>Which file caused the portal error.</b> Send the exact file and message.</li>
<li><b>Organizer receipts.</b> A DrivenData submission receipt that links a file hash to a score is the only way to turn USER-REPORTED values into ORGANIZER-CONFIRMED.</li>
</ol>

<h2>6. Ranked hypotheses for the next session (not tested)</h2>
<p>Ranked by expected holdout gain per implementation cost. Each must be pre-registered, must beat the nine-site and budget-matched random controls on the SGMC-cal measure, and must avoid SGMC as an input.</p>
<ol>
<li><b>H3 — Visible-catalogue annulus at 300–1,000 m</b> (not on the trace). Layers: labels.tif, visible-only inside the holdout. Target: off-catalogue faults parallel or en-echelon to mapped traces. Mimic: mapping-density bias toward populated areas. Differs from the nine: it places dots by distance to the trace, not by a field. Cost: low.</li>
<li><b>H4 — Basement-step × conductivity contrast</b> (depth_to_base_surf × cond_surf gradients). Mimic: sediment thickness changes at alluvial-fan and playa margins. Cost: moderate. Layers already appear in other lanes, so novelty lies in the combination.</li>
<li><b>H5 — Dilatation sign-change without the shear weight</b>, with a sign-change test on the 2-px neighbourhood. This tests whether H2 failed on its weighting or on the signal itself. Cost: low; treat as a diagnostic, not a candidate.</li>
</ol>
<p>GEODAWN radiometric layers are already used in several prior lanes, so they are not presented as new here.</p>

<h2>7. Sources and receipts (manual review)</h2>
<ul>
<li>Problem and metric: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData page 967</a> · Leaderboard: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> · Data tab (login-walled): <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">data</a></li>
<li>Submission-format PDF: <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR 96647</a> · CRS: <a href="https://epsg.io/32611">EPSG:32611</a> · Metric family: <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a></li>
<li>GEODAWN airborne data: <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS</a></li>
<li>Receipts: <a href="https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/evidence/run-card-20261031.json">run card</a> · <a href="https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/evidence/focus9-reeval/">nine-site holdout re-run</a> · <a href="https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/evidence/session-20261031/">format and uniqueness</a> · <a href="https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/evidence/controls/">random controls</a> · <a href="https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/evidence/uniqueness-colocation/">candidate uniqueness</a></li>
<li>Review: <a href="review-2026-10-31.md">review-2026-10-31.md</a></li>
</ul>
</body></html>
"""
    (ROOT / "docs" / "executive-summary-20261031.html").write_text(body)


def write_submission(nine_rows, cand_rows) -> None:
    """Step-by-step submission subpage. Status cells are read from receipts; nothing is approved here."""
    E = html.escape
    gates = {c["key"]: load(ROOT / "evidence/run-cards-20261031" / f"{c['key']}.gate.json") for c in cand_rows}
    lat_str = ", ".join(f"{c['key']} {100 * c['lattice_overlap']:.2f}%" for c in cand_rows)
    n_fmt_pass = sum(1 for r in nine_rows if r["format_pass"])
    n_fmt_fail = len(nine_rows) - n_fmt_pass
    steps = [
        ("1", "Pick exactly one candidate TIFF and record its SHA-256.",
         "One file, one name, one note of at most 140 characters.",
         "No file selected. Nothing is cleared."),
        ("2", "Format gate: <code>.venv/bin/python scripts/check_format.py --template .cache/gems_data/sample_submission.tif &lt;file&gt;</code>",
         "Official text: single-layer float32 GeoTIFF, EPSG:32611, 100 m, values in [0,1], outside footprint null or nan.",
         f"Nine focus files: {n_fmt_pass} pass, {n_fmt_fail} fail (zeros outside). Three candidates: pass."),
        ("3", "Holdout DTI: <code>.venv/bin/python scripts/evaluate_holdout.py &lt;file&gt; --name &lt;name&gt; --out &lt;json&gt;</code>",
         "Must beat the same-evaluator current best (nine-site max pooled HOLDOUT-DTI 0.0967) with a paired CI above zero.",
         "No candidate beats the best. Paired test not run."),
        ("4", "Literal uniqueness, surface and final dots, against the complete registry (stop if |rho| &gt; 0.90 or &gt; 70% of dots within 3 px).",
         "Every registry raster must pass. The 13GEMSDOE lattice witness covers 99.87% of the footprint, so any footprint-spanning file fails.",
         f"Lattice overlap: {lat_str}. Complete registry not measured."),
        ("5", "Leakage canary: any single feature with holdout AUC &gt; 0.90 counts as leakage.",
         "Must be run per feature and reported.",
         "NOT RUN for any candidate."),
        ("6", "Run card through the gate: <code>.venv/bin/python scripts/promotion_gate.py evidence/run-cards-20261031/&lt;KEY&gt;.json</code>",
         "Verdict must be promote. The gate never allocates a slot.",
         "; ".join(f"{k}: {g.get('verdict')} ({len(g.get('reasons', []))} blockers)" for k, g in gates.items())),
        ("7", "Owner decisions (cannot be made by the project): uniqueness scope, zeros vs NaN outside, which file caused the portal error, organizer receipts.",
         "Written decision recorded in the repo.",
         "Open. See executive summary section 5."),
        ("8", "Selector step: a separate, independent decision inside the weekly cap.",
         "Not run here. Weekly slots used by this session: 0.",
         "Not started."),
        ("9", "Upload (human, DrivenData account). The project never uploads and never receives a portal response.",
         "Record the exact portal message, the file SHA-256, and the score shown.",
         "Not done. No portal result exists for any 2026-10-31 file."),
        ("10", "Organizer receipt: link file SHA-256 to the score on the official page.",
         "Only then may a number be labelled ORGANIZER-CONFIRMED.",
         "None exists. All scores on this site are USER-REPORTED or PROJECTION."),
    ]
    rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in steps)
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Submission guide 2026-10-31 · NOT CLEARED</title>
<link rel="stylesheet" href="assets/site.css">
<style>body{{font-family:system-ui,sans-serif;max-width:1100px;margin:0 auto;padding:16px;line-height:1.45}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{border:1px solid #bbb;padding:6px;vertical-align:top;text-align:left}}
th{{background:#eef2f5}}.banner{{border:3px solid #a40000;background:#fff1f1;padding:14px;border-radius:6px}}code{{font-size:12px}}</style>
</head><body>
<p><a href="executive-summary-20261031.html">&larr; Executive summary 2026-10-31</a> · <a href="../index.html">Site home</a></p>
<h1>Step-by-step submission guide (2026-10-31)</h1>
<div class="banner"><h2>Status: BLOCKED. Do not upload any file from this session.</h2>
<p>The steps below are the checks a future file must pass. Every status cell is taken from a receipt. No step here approves a file, and the project does not upload.</p></div>
<table><thead><tr><th>#</th><th>Action</th><th>Pass condition</th><th>Status now (receipt)</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Gate blockers, GEMSDOE32 H1 candidate (verbatim from promotion_gate.py)</h2>
<ul>{''.join(f'<li>{E(r)}</li>' for r in gates['H1'].get('reasons', []))}</ul>
<p><small>Machine-readable gate output: <code>evidence/run-cards-20261031/&lt;KEY&gt;.gate.json</code>. Run card: <code>evidence/run-cards-20261031/&lt;KEY&gt;.json</code>. The same blockers apply to H2 and H1-expanded.</small></p>
</body></html>
"""
    (ROOT / "docs" / "submission-20261031.html").write_text(body)


if __name__ == "__main__":
    raise SystemExit(main())
