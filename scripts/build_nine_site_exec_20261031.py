#!/usr/bin/env python3
"""Build the 2026-10-31 nine-site executive summary page and the session run card.

Inputs (all measured in this session, all in the repo):
  docs/data/nine-site-holdout-20261031.json   HOLDOUT-DTI on the nine focus files (shared evaluator)
  docs/data/nine-site-pairwise-20261031.json  pairwise within-3 px overlap among the nine
  evidence/vgzc-e{1,2}-holdout-20261031.json  HOLDOUT-DTI for the two lab candidates
  evidence/registry-overlap-20261031/*.json   literal registry overlap (both lab candidates + nine)
Outputs:
  docs/nine-site-executive-20261031.html
  docs/data/run-card-20261031-vgzc-e1-e2.json
Every score is labelled. Nothing here authorizes a submission.
"""
from __future__ import annotations

import html
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HOLD = json.loads((ROOT / "docs/data/nine-site-holdout-20261031.json").read_text())
PAIR = json.loads((ROOT / "docs/data/nine-site-pairwise-20261031.json").read_text())
E1 = json.loads((ROOT / "evidence/vgzc-e1-holdout-20261031.json").read_text())
E2 = json.loads((ROOT / "evidence/vgzc-e2-holdout-20261031.json").read_text())
E1F = json.loads((ROOT / "evidence/vgzc-e1-format-20261031.json").read_text())
E2F = json.loads((ROOT / "evidence/vgzc-e2-format-20261031.json").read_text())
CANARY = json.loads((ROOT / "evidence/vgzc-e1-leakage-canary-20261031.json").read_text())
OV = {p.name.replace(".overlap.json", ""): json.loads(p.read_text())
      for p in (ROOT / "evidence/registry-overlap-20261031").glob("*.overlap.json")}
QDIR = ROOT / "evidence/quarantine-vgzc-e1-e2"
E1_TIF = next(QDIR.glob("gemsdoe32-vgzc-zc-stage-*-nan.tif"))
E2_TIF = next(QDIR.glob("gemsdoe32-vgzc-e2-tmivg-coinc-*-nan.tif"))
E1_NAME = "karage3-vgzc-e1-zc-21570"
E2_NAME = "karage3-vgzc-e2-tmivg-coinc-9660"
NOTE_E1 = "E1 vertical-gravity zero-crossing edges x horizontal gradient, 21,570 dots. NOT CLEARED."
NOTE_E2 = "E2 gravity zero-crossing coincident with tmi_vg zero-crossing, 9,660 dots. NOT CLEARED."
assert len(NOTE_E1) <= 140 and len(NOTE_E2) <= 140

rows = HOLD["rows"]  # sorted by SGMC-calibrated DTI, high to low
reported = {r["site"]: r["user_reported_leaderboard"]["value"] for r in rows}
sgm = {r["site"]: r["holdout_sgmc_calibrated"]["calibrated_dti"] for r in rows}

# Linear calibration on the nine (USER-REPORTED vs HOLDOUT-DTI). Used ONLY to label projections.
x = np.array([sgm[s] for s in reported])
y = np.array([reported[s] for s in reported])
b, a = np.polyfit(x, y, 1)
resid_max = float(np.max(np.abs(y - (a + b * x))))


def proj(v):
    return a + b * v


def label_proj(v):
    lo = min(sgm.values())
    hi = max(sgm.values())
    tag = "PROJECTION (inside anchor range)" if lo <= v <= hi else "PROJECTION (EXTRAPOLATED outside anchor range; not a score)"
    return f"{proj(v):.4f} — {tag}"


pair_max = PAIR["max_pairwise_within_3px_per_site"]
min_pair_max = min(pair_max.values())
max_pair_max = max(pair_max.values())

def nine_row(r):
    s = r["site"]
    ov = OV.get(Path(r["file"]).stem, None)
    ov_n70 = ov["n_rasters_over_70pct"] if ov else None
    hr = r["holdout_hide_recover"]
    sg_ = r["holdout_sgmc_calibrated"]
    return dict(site=s, file=r["file"], sha=r["sha256"][:12], dots=r["emitted_dots"],
                reported=reported[s],
                sg=sg_["calibrated_dti"], sg_ci=sg_["ci95"], sg_n=sg_["n_withheld_positives"],
                hr=hr["pooled_dti"], hr_ci=hr["ci95"], hr_n=hr["n_withheld_positives"],
                pair=pair_max[s], n70=ov_n70, proj=proj(sg_["calibrated_dti"]))


nine = [nine_row(r) for r in rows]

def fmt(v, d=4):
    return "—" if v is None else f"{v:.{d}f}"

def ci(c):
    return "—" if not c else f"[{c[0]:.4f}, {c[1]:.4f}]"

def tr(cells, cls=""):
    return f"<tr class=\"{cls}\">" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

nine_html = "\n".join(tr([
    f"<b>{n['site']}</b>" + (" <span class='tag top'>highest proxy</span>" if i == 0 else ""),
    f"<a href='../{html.escape(n['file'])}'>{html.escape(Path(n['file']).name)}</a>",
    f"{n['dots']:,}",
    f"{fmt(n['reported'],4)} <small>USER-REPORTED</small>",
    f"{fmt(n['sg'])} {ci(n['sg_ci'])} <small>HOLDOUT-DTI, SGMC-CAL ({n['sg_n']:,} withheld)</small>",
    f"{fmt(n['proj'])} <small>PROJECTION (fit to the nine)</small>",
    f"{fmt(n['hr'])} {ci(n['hr_ci'])} <small>HOLDOUT-DTI, hide-recover</small>",
    f"Max {n['pair']*100:.1f}% of dots within 3 px of another focus site; literal registry: {n['n70']} rasters &gt;70%",
    "<span class='tag no'>NOT UNIQUE</span> <span class='tag no'>DUPLICATE-STOP</span> <span class='tag no'>NOT CLEARED</span>",
], "") for i, n in enumerate(nine))

e1_pair = None
lab_rows = []
for name, hold, fmt_, tif, ov_key, note, sub_name in [
    ("E1 · H-VGZC zero-crossings", E1, E1F, E1_TIF, "gemsdoe32-vgzc-zc-stage-20261031T000000Z-33f68c4c-nan", NOTE_E1, E1_NAME),
    ("E2 · H-VGZC + tmi_vg coincidence", E2, E2F, E2_TIF, "gemsdoe32-vgzc-e2-tmivg-coinc-20261031T000000Z-14e8fe39-nan", NOTE_E2, E2_NAME),
]:
    hr = hold["hide_and_recover"]
    sgc = hold["sgmc_off_catalogue"]
    o = OV[ov_key]
    lab_rows.append(tr([
        f"<b>{name}</b>",
        f"<a href='../evidence/quarantine-vgzc-e1-e2/{tif.name}'>{tif.name}</a> <small>(quarantined, NOT for download)</small>",
        f"{o['candidate_dots']:,}",
        "—",
        f"{fmt(sgc['sgmc_prevalence_calibrated_dti'])} {ci(sgc['sgmc_calibrated_ci95'])} <small>HOLDOUT-DTI, SGMC-CAL</small>",
        f"{label_proj(sgc['sgmc_prevalence_calibrated_dti'])}",
        f"{fmt(hr['pooled_dti'])} {ci(hr['ci95_cluster_bootstrap'])} <small>HOLDOUT-DTI, {hr['n_withheld_positives']:,} withheld</small>",
        f"Format gate PASS · byte-unique: YES · literal registry: {o['n_rasters_over_70pct']} rasters &gt;70% (max {o['max_candidate_within_3px']*100:.0f}%)",
        "<span class='tag no'>NEGATIVE (below the nine)</span> <span class='tag no'>DUPLICATE-STOP</span> <span class='tag no'>NOT CLEARED</span>",
    ]))

html_doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE nine focus sites — executive summary (2026-10-31)</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f6f7f9;color:#1d2330;line-height:1.45}}
main{{max-width:1240px;margin:0 auto;padding:24px}}
h1{{font-size:1.7rem;margin:.2rem 0}} h2{{margin-top:2rem;border-bottom:2px solid #d9dee7;padding-bottom:.3rem}}
.banner{{background:#7a1f1f;color:#fff;border-radius:10px;padding:18px 20px;font-size:1.1rem}}
.banner b{{font-size:1.25rem}}
.note{{background:#fff;border-left:4px solid #3b6fb6;padding:12px 16px;border-radius:6px;margin:14px 0}}
table{{width:100%;border-collapse:collapse;background:#fff;font-size:.9rem;margin:10px 0}}
th,td{{border:1px solid #d9dee7;padding:8px;vertical-align:top;text-align:left}}
th{{background:#eef2f8}} small{{color:#5b6475;display:block}}
.tag{{display:inline-block;padding:2px 7px;border-radius:999px;font-size:.75rem;font-weight:600;margin:2px 0}}
.tag.top{{background:#e6f4ea;color:#17602b}} .tag.no{{background:#fbe4e4;color:#8a1c1c}}
code{{background:#eef2f8;padding:1px 4px;border-radius:4px}}
</style></head>
<body><main>
<h1>GEMSDOE nine focus sites — executive summary</h1>
<p>Measured 2026-10-31 in this repository. Scope: GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36.</p>

<div class="banner"><b>ANSWER: NO FILE IS CLEARED FOR DOWNLOAD OR SUBMISSION.</b><br>
No file in this table is unique under the project's literal rule, and no new candidate beat the nine on the same holdout proxy. Do not submit any of these files.</div>

<h2>1. Bottom line</h2>
<div class="note">
<ul>
<li><b>Highest measured holdout proxy among the nine:</b> GEMSDOE36 (SGMC-CAL 0.0644) and GEMSDOE32 (0.0641). Their CIs overlap, so the proxy cannot separate them.</li>
<li><b>Highest user-reported leaderboard value among the nine:</b> GEMSDOE32 at 0.2778 (USER-REPORTED, not an organizer receipt). This is the file the user asked about.</li>
<li><b>Uniqueness:</b> the nine are not unique against each other. <b>GEMSDOE25 and GEMSDOE30 are the exact same 44,090 dots</b> (exact mask equality; different file encodings), and both report 0.2600. Pairwise, every site has at least one other site with ≥97.6% of its dots within 3 px.</li>
<li><b>New lab candidates (E1, E2) did not beat the nine:</b> SGMC-CAL 0.0383 and 0.0219 vs the nine's 0.0579–0.0644. Both are quarantined and not for download.</li>
<li><b>Literal uniqueness rule:</b> every candidate, including the nine, trips the 70% dot-overlap rule. {sum(1 for o in OV.values() if o['duplicate_stop'])} of {len(OV)} candidates are DUPLICATE-STOP. The cause is 62 dense registry rasters (each with more than 50% of the footprint as dots), which put 100% of any candidate's dots within 3 px. This is a rule-level blocker and needs an owner decision. It is not a property of any one file.</li>
</ul>
</div>

<h2>2. Submission table (what to download, estimate, uniqueness)</h2>
<div class="note"><b>Read the labels.</b> HOLDOUT-DTI is measured by the shared evaluator on this repo's holdout. PROJECTION is a fit to the nine user-reported values, not a score. USER-REPORTED values come from submission-page reports and have no organizer receipt in this repo. ORGANIZER-CONFIRMED: none.</div>
<table>
<tr><th>Site</th><th>File to download</th><th>Dots</th><th>Leaderboard value</th><th>Holdout (SGMC-CAL, calibrated)</th><th>Estimated score</th><th>Holdout (hide-recover)</th><th>Unique vs the other focus sites / literal registry</th><th>Status</th></tr>
{nine_html}
{''.join(lab_rows)}
</table>

<h2>3. Calibration and consistency</h2>
<div class="note">
<ul>
<li>User-reported leaderboard values vs SGMC-CAL on the nine: Spearman ρ = {PAIR['spearman_user_reported_vs_sgmc_calibrated']['rho']} (n = 9, p = {PAIR['spearman_user_reported_vs_sgmc_calibrated']['p']}). This is a consistency check on 9 points, not a validated predictor.</li>
<li>Linear fit used only for labelled projections: estimate = {a:.4f} + {b:.4f} × SGMC-CAL. In-sample max residual {resid_max:.4f}.</li>
<li><b>Metric disagreement, flagged:</b> hide-recover HOLDOUT-DTI ranks GEMSDOE24/25/27/30 highest (≈0.09–0.10) and GEMSDOE28/31/32/36 lowest (≈0.003–0.03). The leaderboard order is the reverse. Treat hide-recover as NOT predictive of the leaderboard until reconciled.</li>
</ul>
</div>

<h2>4. Leaderboard context (live fetch, not a receipt)</h2>
<div class="note">
<p>Fetched 2026-10-31 from <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">the DrivenData leaderboard</a>: #1 xiaofanhu 0.4544; #2 cfld__ 0.3934; #3 Batik Shirt Brothers 0.3917. Ranks #1–#22 are all ≥ 0.3407 on that page.</p>
<p><b>Flagged discrepancy:</b> the request cites a leaderboard high of 0.4413 and a second value of 0.3195. Neither matches the live page, so they are not used as scores.</p>
</div>

<h2>5. Lab candidates E1 and E2 (negative results)</h2>
<div class="note">
<ul>
<li><b>E1</b> (hypothesis H-VGZC): zero-crossings of the vertical isostatic gravity gradient (<code>iso_grav_anom_vg</code>) ranked by horizontal gradient strength (<code>iso_grav_anom_hg</code>), catalogue traces and sentinel cells excluded, 3 px spacing. Result: negative on the holdout proxy.</li>
<li><b>E2</b>: E1 restricted to zero-crossings that coincide within 1 px with a magnetic <code>tmi_vg</code> zero-crossing. Result: worse.</li>
<li><b>Leakage canary (E1 features alone vs off-catalogue SGMC positives):</b> AUC {CANARY['iso_grav_anom_vg']['auc']} (vg), {CANARY['iso_grav_anom_hg']['auc']} (hg), {CANARY['tmi_vg']['auc']} (tmi_vg). Threshold for leakage is 0.90. No leakage detected.</li>
<li><b>Format:</b> E1 PASS, E2 PASS on <code>check_format.py</code> (official rules). A format pass is not a submission approval.</li>
</ul>
</div>

<h2>6. Irregularities flagged for review</h2>
<div class="note"><ol>
<li>The literal 70% overlap rule cannot be satisfied by any candidate with dots in the footprint while 62 registry rasters cover &gt;50% of it. Owner decision required.</li>
<li>The nine focus files were accepted for scoring (per their leaderboard values), yet all fail our literal rule. Our rule is stricter than the organizer's observed behaviour, or the organizer's duplicate check differs. Not resolved here.</li>
<li>Registry raster <code>apartanish22-droid/ApartGEMSDOE2/…/depth-cond-conductive-under-thin-cover-top37654-…-nan.tif</code> is 98.8% positive. It is the complement of the label map and drives the screen.</li>
<li>The portal error "Predicted values must be in range [0, 1]" has no confirmed cause in this repo. The NaN-outside variant follows the official text ("null or nan"). Obtain the exact file hash and the full portal message before drawing a conclusion.</li>
<li><b>GEMSDOE25 and GEMSDOE30 hold identical dot sets</b> (44,090 dots; exact mask equality, verified 2026-10-31). Different file bytes, same placement. Same user-reported value (0.2600). Flagged for review; the two should not be treated as independent submissions.</li>
<li>The GEMSDOE32 leaderboard value (0.2778) and all other focus values are USER-REPORTED. No organizer receipt exists here.</li>
</ol></div>

<h2>7. Links for manual review</h2>
<div class="note"><ul>
<li>Holdout table (labelled, reproducible): <a href="data/nine-site-holdout-20261031.json">docs/data/nine-site-holdout-20261031.json</a></li>
<li>Pairwise overlap: <a href="data/nine-site-pairwise-20261031.json">docs/data/nine-site-pairwise-20261031.json</a></li>
<li>Run card (JSON, E1/E2): <a href="data/run-card-20261031-vgzc-e1-e2.json">docs/data/run-card-20261031-vgzc-e1-e2.json</a></li>
<li>Registry overlap receipts: <a href="../evidence/registry-overlap-20261031/">evidence/registry-overlap-20261031/</a></li>
<li>Competition leaderboard: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">drivendata.org leaderboard</a></li>
<li>Submission format (official): <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format">problem page, submission format</a></li>
</ul></div>
</main></body></html>
"""

(ROOT / "docs/nine-site-executive-20261031.html").write_text(html_doc)

card = {
    "date": "2026-10-31",
    "lane": "E1 H-VGZC and E2 (2 of 3 allowed experiments)",
    "experiments": [
        {
            "id": "E1",
            "hypothesis": "Zero-crossings of the vertical isostatic gravity gradient, ranked by horizontal gradient strength, mark density-contact edges that are missing from the catalogue.",
            "layers": ["iso_grav_anom_vg", "iso_grav_anom_hg", "labels.tif (catalogue exclusion)"],
            "mechanism": "Sign change of vg coincides with a strong hg maximum at a density contrast edge.",
            "named_non_fault_mimic": "Lithologic contacts, intrusion margins, basin-edge gravity steps.",
            "holdout_dti": {"label": "HOLDOUT-DTI", "evaluator_version": E1["sgmc_off_catalogue"]["evaluator_version"],
                            "sgmc_calibrated": E1["sgmc_off_catalogue"]["sgmc_prevalence_calibrated_dti"],
                            "sgmc_calibrated_ci95": E1["sgmc_off_catalogue"]["sgmc_calibrated_ci95"],
                            "n_withheld_positives": E1["sgmc_off_catalogue"]["n_withheld_positives"],
                            "hide_recover_pooled": E1["hide_and_recover"]["pooled_dti"],
                            "hide_recover_n_withheld": E1["hide_and_recover"]["n_withheld_positives"]},
            "leakage_canary": {"threshold_auc": 0.90, "single_feature_auc": {k: CANARY[k]["auc"] for k in CANARY}},
            "registry_overlap": {"max_candidate_within_3px": OV["gemsdoe32-vgzc-zc-stage-20261031T000000Z-33f68c4c-nan"]["max_candidate_within_3px"],
                                 "max_abs_binary_rho": OV["gemsdoe32-vgzc-zc-stage-20261031T000000Z-33f68c4c-nan"]["max_abs_binary_rho"],
                                 "n_rasters_over_70pct": OV["gemsdoe32-vgzc-zc-stage-20261031T000000Z-33f68c4c-nan"]["n_rasters_over_70pct"],
                                 "file": "evidence/registry-overlap-20261031/gemsdoe32-vgzc-zc-stage-20261031T000000Z-33f68c4c-nan.overlap.json"},
            "raster_sha256": hashlib.sha256(E1_TIF.read_bytes()).hexdigest(),
            "raster_file": f"evidence/quarantine-vgzc-e1-e2/{E1_TIF.name}",
            "validator": {"format_gate_pass": E1F["format_gate_pass"], "checks": E1F["checks"],
                          "inside_nonfinite": E1F["inside_nonfinite"], "inside_out_of_range": E1F["inside_out_of_range"],
                          "outside_null_or_nan": E1F["outside_null_or_nan"]},
            "submission_name": E1_NAME,
            "submission_note": NOTE_E1,
            "verdict": "negative",
            "ok_to_submit": False,
        },
        {
            "id": "E2",
            "hypothesis": "E1 restricted to zero-crossings coincident with a magnetic tmi_vg zero-crossing (independent edge) should raise precision.",
            "layers": ["iso_grav_anom_vg", "iso_grav_anom_hg", "tmi_vg", "labels.tif"],
            "holdout_dti": {"label": "HOLDOUT-DTI", "evaluator_version": E2["sgmc_off_catalogue"]["evaluator_version"],
                            "sgmc_calibrated": E2["sgmc_off_catalogue"]["sgmc_prevalence_calibrated_dti"],
                            "sgmc_calibrated_ci95": E2["sgmc_off_catalogue"]["sgmc_calibrated_ci95"],
                            "n_withheld_positives": E2["sgmc_off_catalogue"]["n_withheld_positives"],
                            "hide_recover_pooled": E2["hide_and_recover"]["pooled_dti"]},
            "registry_overlap": {"max_candidate_within_3px": OV["gemsdoe32-vgzc-e2-tmivg-coinc-20261031T000000Z-14e8fe39-nan"]["max_candidate_within_3px"],
                                 "max_abs_binary_rho": OV["gemsdoe32-vgzc-e2-tmivg-coinc-20261031T000000Z-14e8fe39-nan"]["max_abs_binary_rho"],
                                 "n_rasters_over_70pct": OV["gemsdoe32-vgzc-e2-tmivg-coinc-20261031T000000Z-14e8fe39-nan"]["n_rasters_over_70pct"]},
            "raster_sha256": hashlib.sha256(E2_TIF.read_bytes()).hexdigest(),
            "raster_file": f"evidence/quarantine-vgzc-e1-e2/{E2_TIF.name}",
            "validator": {"format_gate_pass": E2F["format_gate_pass"]},
            "submission_name": E2_NAME,
            "submission_note": NOTE_E2,
            "verdict": "negative",
            "ok_to_submit": False,
        },
    ],
    "nine_site_reference": {
        "highest_holdout_sgmc_calibrated": {"site": rows[0]["site"], "value": rows[0]["holdout_sgmc_calibrated"]["calibrated_dti"],
                                            "ci95": rows[0]["holdout_sgmc_calibrated"]["ci95"]},
        "highest_user_reported": {"site": "GEMSDOE32", "value": 0.2778, "label": "USER-REPORTED"},
        "pairwise_max_per_site": pair_max,
        "literal_registry_duplicate_stop_all_nine": all(o["duplicate_stop"] for k, o in OV.items() if k.startswith("GEMSDOE")),
    },
    "registry_scope": "2,444-entry manifest, 1,997 distinct bytes; 1,981 compared on the same grid; 10 different-grid rasters reported; manifest literal_registry_complete=false",
    "experiments_run": 2,
    "budget_limit": 3,
    "weekly_slots_used": 0,
    "portal_submission_performed": False,
    "organizer_confirmed_scores": [],
    "owner_decisions_required": [
        "Literal 70% dot-overlap rule vs 62 dense registry rasters (any candidate is 100% overlapped).",
        "Whether the organizer's duplicate rule matches this repo's literal rule (the nine were scored).",
        "Reconcile hide-recover HOLDOUT-DTI with SGMC-CAL and with the leaderboard.",
        "GEMSDOE25 and GEMSDOE30 are the same dot set (exact); confirm which was scored and whether it counts twice.",
    ],
    "overall_verdict": "negative — NOT OK TO DOWNLOAD OR SUBMIT",
}
(ROOT / "docs/data/run-card-20261031-vgzc-e1-e2.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
print("wrote docs/nine-site-executive-20261031.html and docs/data/run-card-20261031-vgzc-e1-e2.json")
print("projection fit", round(a, 5), round(b, 5), "max_resid", round(resid_max, 5))
