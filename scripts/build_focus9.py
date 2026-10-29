#!/usr/bin/env python3
"""Build the nine per-site executive summaries and the comparison table.

Sources (all verified by this script before rendering):
  data/focus_registry.json                      pinned file, SHA-256, commit, portal claim
  docs/data/historical-audit.json               format checks, lattice overlap, pairwise overlap
  evidence/focus9-holdout-baseline-20261029.json HOLDOUT-DTI values from the shared evaluator

Every submission status is NO. The gate in scripts/promotion_gate.py is the
authority; this page only reports it. Run with --check to verify without writing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "focus_registry.json"
AUDIT = ROOT / "docs" / "data" / "historical-audit.json"
BASELINE = ROOT / "evidence" / "focus9-holdout-baseline-20261029.json"
OUT = ROOT / "docs" / "focus9"
EXPECTED = [f"GEMSDOE{x}" for x in (24, 25, 27, 28, 30, 31, 32, 33, 36)]
LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
RULES = "https://docs.nlr.gov/docs/fy26osti/96647.pdf"
LATTICE_NOTE = ("Calibration lattice 13GEMSDOE r13-lattice-s5 (206,895 dots) lies within 3 px of 99.87% "
                "of the audited footprint. This is one witness and does not prove universal impossibility.")


def esc(v) -> str:
    return escape(str(v), quote=True)


def load_sources() -> tuple[dict, dict, dict]:
    registry = json.loads(REGISTRY.read_text())
    audit = json.loads(AUDIT.read_text())
    baseline = json.loads(BASELINE.read_text())
    reg = {r["site"]: r for r in registry["sites"]}
    aud = {r["site"]: r for r in audit["sites"]}
    base = {r["site"]: r for r in baseline["sites"]}
    if set(reg) != set(EXPECTED) or set(aud) != set(EXPECTED) or set(base) != set(EXPECTED):
        raise ValueError("Source files do not contain exactly the nine focus sites")
    for site in EXPECTED:
        if reg[site]["sha256"] != aud[site]["format"]["sha256"] or reg[site]["sha256"] != base[site]["sha256"]:
            raise ValueError(f"SHA-256 disagreement for {site}")
        if reg[site]["historical_claim"] != aud[site]["historical_claim"]:
            raise ValueError(f"Claim disagreement for {site}")
        if aud[site].get("new_submission_authorized") is not False:
            raise ValueError(f"{site} would authorize a submission; this page cannot render that")
    if audit.get("manifest_sha256") != hashlib.sha256(REGISTRY.read_bytes()).hexdigest():
        raise ValueError("Audit was not produced from the current registry")
    if baseline.get("registry_sha256") != hashlib.sha256(REGISTRY.read_bytes()).hexdigest():
        raise ValueError("Baseline was not produced from the current registry")
    return reg, aud, base


def pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def ci(pair) -> str:
    return f"[{pair[0]:.4f}, {pair[1]:.4f}]"


def page(title: str, body: str) -> str:
    # Pages live in docs/focus9/, so the docs root is ../ (assets, decision home).
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · GEMSDOE focus-9</title>
<link rel="stylesheet" href="../assets/site.css"></head>
<body><main class="wrap" style="padding:28px 0 60px;max-width:1000px;margin:auto">
<p><a href="index.html">Focus-9 summary home</a> · <a href="../index.html">Decision home</a> · <a href="{LEADERBOARD}">Official leaderboard</a> · <a href="{RULES}">Official rules (PDF)</a></p>
{body}
</main></body></html>
"""


BANNER = """<div style="border:3px solid #b00020;background:#fff0f0;padding:16px;border-radius:8px;margin:16px 0">
<strong style="font-size:1.25em">OK TO DOWNLOAD AND SUBMIT? NO — DO NOT SUBMIT THIS FILE.</strong>
<p style="margin:8px 0 0">The validator and the uniqueness gate both fail. Nothing on this page authorizes an upload or a weekly slot.</p></div>"""


def site_page(site: str, reg: dict, aud: dict, base: dict) -> str:
    r, a, b = reg[site], aud[site], base[site]
    hr, sg = b["holdout_dti_hide_and_recover"], b["holdout_dti_sgmc_off_catalogue"]
    fmt = b["format_checks"]
    pair = a["worst_focus_comparator"]
    flags = []
    if site in ("GEMSDOE25", "GEMSDOE30"):
        flags.append("Positive support is identical to the other of GEMSDOE25 / GEMSDOE30 "
                     "(audit lineage flag <code>g25_g30_identical_positive_support</code>), yet both are reported as 0.2600.")
    if site == "GEMSDOE32":
        flags.append("This is the highest reported value (0.2778). The local static holdout ranks it near the bottom "
                     "(HR ≈ %.4f), so the local proxy does not reproduce the portal ranking." % hr["pooled_dti"])
    if site == "GEMSDOE28":
        flags.append("Four GEMSDOE28 files are reported (0.2708, 0.2649, 0.2710, 0.2707). Only the 0.2710 file "
                     "(<code>h36-1-rung30-blind-r1</code>) is audited here.")
    if site == "GEMSDOE33":
        flags.append("Reported value 0.2632 and file are unverified; the audit places it at 99.71% overlap with GEMSDOE27.")
    flags.append("Reported score has no organizer receipt; the portal value is USER-REPORTED / UNVERIFIED.")
    flag_html = "".join(f"<li>{f}</li>" for f in flags)
    body = f"""<h1>{esc(site)} — executive summary</h1>
{BANNER}
<h2>At a glance</h2>
<table>
<tr><th>Item</th><th>Value</th></tr>
<tr><td>Historical file source (research only; not a submission download)</td><td><a href="{esc(r['source_url'])}">{esc(r['path'].split('/')[-1])}</a></td></tr>
<tr><td>Pinned commit</td><td><code>{esc(r['ref'])}</code></td></tr>
<tr><td>SHA-256</td><td><code>{esc(r['sha256'])}</code></td></tr>
<tr><td>Site</td><td><a href="{esc(r['site_url'])}">{esc(r['site_url'])}</a></td></tr>
<tr><td>Reported portal score</td><td>{esc(r['historical_claim'])} — <strong>USER-REPORTED / UNVERIFIED</strong></td></tr>
<tr><td>Estimated leaderboard score</td><td><strong>Not estimable.</strong> No organizer receipt, and the static local holdout does not reproduce portal ordering.</td></tr>
<tr><td>Unique submission?</td><td><strong>NO</strong> — {pct(a['worst_focus_fraction'])} of dots within 3 px of {esc(pair)}; {pct(a['lattice_fraction'])} within 3 px of the calibration lattice.</td></tr>
<tr><td>Withheld positives (holdout)</td><td>{hr['n_withheld_positives']} (hide-and-recover); {sg['n_withheld_positives']} (off-catalogue SGMC)</td></tr>
<tr><td>OK to submit?</td><td><strong>NO</strong></td></tr>
</table>
<h2>Local HOLDOUT-DTI (static binary diagnostic)</h2>
<p>Label: <strong>HOLDOUT-DTI</strong>. Evaluator <code>{esc(hr['evaluator_version'])}</code>, {hr['n_withheld_positives']} withheld positives, {hr['n_spatial_clusters']} spatial clusters, 95% cluster-bootstrap CI.</p>
<ul>
<li>Hide-and-recover pooled DTI: <strong>{hr['pooled_dti']:.4f}</strong> {ci(hr['ci95_cluster_bootstrap'])}</li>
<li>Off-catalogue SGMC HOLDOUT-DTI, prevalence-calibrated: <strong>{sg['prevalence_calibrated_dti']:.4f}</strong> {ci(sg['calibrated_ci95'])}; raw pooled HOLDOUT-DTI: {sg['raw_pooled_dti']:.4f} {ci(sg['raw_ci95'])}</li>
</ul>
<p>Mode <code>{esc(b['evaluator_flags']['mode'])}</code>; promotion_eligible <code>{esc(b['evaluator_flags']['promotion_eligible'])}</code>. The evaluator says: <em>{esc(b['evaluator_flags']['provenance_warning'])}</em></p>
<h2>Format checks (saved bytes, local)</h2>
<ul>
<li>Single band {esc(fmt['dtype'])}; EPSG:{fmt['epsg']}; shape {fmt['shape'][0]} × {fmt['shape'][1]}; transform matches reference: {fmt['transform_matches_reference']}</li>
<li>NaN cells: {fmt['nan_cells']:,} (nodata = {esc(fmt['nodata'])}). Finite values in [0,1]: {fmt['finite_values_in_0_1']}.</li>
<li>Positive cells: {fmt['positive_cells']:,}. These pass the range check. The NaN outside-footprint convention is reported separately and is not an organizer acceptance receipt.</li>
</ul>
<h2>Why it is blocked</h2>
<p>{esc(LATTICE_NOTE)} The shared rule stops any candidate with more than 70% of dots within 3 px of a registry raster. This file is {pct(a['lattice_fraction'])} within 3 px of the lattice, and {pct(a['worst_focus_fraction'])} within 3 px of {esc(pair)}.</p>
<h2>Irregularities for review</h2>
<ul>{flag_html}</ul>
<p><small>Sources: <a href="{esc(r['source_url'])}">pinned file</a> · <a href="{esc(r['site_url'])}">site</a> · <a href="../../evidence/focus9-holdout-baseline-20261029.json">baseline evidence</a> · <a href="../../docs/data/historical-audit.json">geometry audit</a> · <a href="{LEADERBOARD}">leaderboard</a>. Scores are not ORGANIZER-CONFIRMED.</small></p>
"""
    return page(site, body)


def home(reg: dict, aud: dict, base: dict, run_card: dict) -> str:
    rows = []
    for site in EXPECTED:
        r, a, b = reg[site], aud[site], base[site]
        hr = b["holdout_dti_hide_and_recover"]
        sg = b["holdout_dti_sgmc_off_catalogue"]
        rows.append(
            f"<tr><td><a href=\"{esc(site.lower())}.html\">{esc(site)}</a></td>"
            f"<td>{esc(r['historical_claim'])} <small>(USER-REPORTED)</small></td>"
            f"<td>{hr['pooled_dti']:.4f} {ci(hr['ci95_cluster_bootstrap'])}</td>"
            f"<td>{sg['prevalence_calibrated_dti']:.4f} {ci(sg['calibrated_ci95'])}</td>"
            f"<td><a href=\"{esc(r['source_url'])}\">{esc(r['path'].split('/')[-1])}</a> <small>(research only)</small></td>"
            f"<td>NO — {pct(a['worst_focus_fraction'])} vs {esc(a['worst_focus_comparator'])}</td>"
            f"<td>Not estimable</td><td><strong>NO</strong></td></tr>")
    table = "\n".join(rows)
    body = f"""<h1>Focus-9 executive summary</h1>
{BANNER}
<h2>Answer</h2>
<ul>
<li><strong>Best reported file:</strong> GEMSDOE32 at 0.2778 (USER-REPORTED). It is not submittable.</li>
<li><strong>Best file to download and submit right now:</strong> <strong>None.</strong> All nine files fail the repo's uniqueness gate. Every one of them is 97.6% or more within 3 px of a peer.</li>
<li><strong>Estimated leaderboard score for any of the nine:</strong> not estimable. The organizer's score is not reproduced here, and the local static holdout does not reproduce portal ordering.</li>
<li><strong>Uniqueness:</strong> 0 of 9 unique. All nine overlap the calibration lattice at 99.9%.</li>
</ul>
<h2>Comparison table</h2>
<table>
<tr><th>Site</th><th>Reported score</th><th>Local HOLDOUT-DTI hide-and-recover (95% CI)</th><th>Local HOLDOUT-DTI SGMC-cal (95% CI)</th><th>Historical file source (research only)</th><th>Unique?</th><th>Estimated score</th><th>OK to submit?</th></tr>
{table}
</table>
<p><small>Static-binary diagnostics, not organizer scores: hide-and-recover HOLDOUT-DTI uses <code>{esc(base['GEMSDOE24']['holdout_dti_hide_and_recover']['evaluator_version'])}</code>, {base['GEMSDOE24']['holdout_dti_hide_and_recover']['n_withheld_positives']:,} withheld positives and 95% cluster-bootstrap CI; SGMC-cal HOLDOUT-DTI uses <code>{esc(base['GEMSDOE24']['holdout_dti_sgmc_off_catalogue']['evaluator_version'])}</code>, {base['GEMSDOE24']['holdout_dti_sgmc_off_catalogue']['n_withheld_positives']:,} withheld positives and 95% CI. See the per-site pages and JSON evidence for full values and provenance caveat.</small></p>
<h2>How to submit</h2>
<p>No file on this page is cleared. The rules and this page's gates are <a href="{RULES}">official rules</a>. Follow the decision page at <a href="../index.html">the decision home</a>.</p>
<h2>Irregularities for review</h2>
<ul>
<li>GEMSDOE25 and GEMSDOE30 have identical positive support (44,090 dots) and both report 0.2600 (audit lineage flag <code>g25_g30_identical_positive_support</code>).</li>
<li>The static local holdout does not reproduce portal ordering: GEMSDOE32 (reported 0.2778) scores HR 0.0045, and GEMSDOE28 (reported 0.2710) scores HR 0.0294. Local HR values are not leaderboard estimates.</li>
<li>Four GEMSDOE28 files are reported; only the 0.2710 file is audited here.</li>
<li>The competition data links on Dropbox and GDR (OpenEI) are not in this sandbox's allowlist. The restored rasters come from owner mirrors on GitHub codeload, not organizer downloads.</li>
<li>The public leaderboard claims conflict: 0.3195 (prompt, unverified older claim), 0.4413 (prompt, claimed current but not refreshed here), and 0.4544 (dated public-page observation saved 2026-10-28). None is a receipt for a particular file; verify the current public rank on the official page.</li>
</ul>
<h2>Source freshness</h2>
<p>Run card: <a href="run-card.json">run-card.json</a> · Leaderboard: <a href="{LEADERBOARD}">official page</a>. Public leaderboard values in the prompt disagree (0.3195, 0.4413, 0.4544). These must be checked manually. Automated access to DrivenData is prohibited by its terms.</p>
<p><small>Verdict: <strong>{esc(run_card['verdict'])}</strong>. No candidate generated.</small></p>
"""
    return page("Focus-9 summary", body)


def run_card(reg: dict, base: dict) -> dict:
    return {
        "schema_version": 1,
        "run_id": "focus9-summary-20261029",
        "hypothesis": "None tested. This session builds the nine-site executive summary and verifies the local holdout baseline; no new candidate is generated.",
        "mechanism": "Not applicable.",
        "named_non_fault_mimic": "Not applicable.",
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": base["GEMSDOE24"]["holdout_dti_hide_and_recover"]["evaluator_version"],
            "withheld_positives": base["GEMSDOE24"]["holdout_dti_hide_and_recover"]["n_withheld_positives"],
            "note": "Static binary baseline for the nine pinned files; see evidence/focus9-holdout-baseline-20261029.json. Not a candidate score.",
        },
        "correlation_overlap_vs_registry": {"status": "NOT RUN for a new candidate; the nine historical files are audited in docs/data/historical-audit.json."},
        "raster_sha256": None,
        "validator_output": {"status": "NOT RUN: no new candidate raster"},
        "submission_name": None,
        "submission_note": None,
        "experiments_run": 0,
        "weekly_slots_used": 0,
        "verdict": "negative",
        "ok_to_submit": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="Verify sources and render in memory only")
    args = ap.parse_args()
    reg, aud, base = load_sources()
    card = run_card(reg, base)
    files = {OUT / "index.html": home(reg, aud, base, card), OUT / "run-card.json": json.dumps(card, indent=1) + "\n"}
    for site in EXPECTED:
        files[OUT / f"{site.lower()}.html"] = site_page(site, reg, aud, base)
    if args.check:
        print(f"OK: {len(files)} files rendered in memory; nothing written.")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for path, text in files.items():
        path.write_text(text)
    print(f"wrote {len(files)} files to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
