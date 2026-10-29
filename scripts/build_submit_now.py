#!/usr/bin/env python3
"""Build docs/submit-now/index.html: the one-page download and submission guide.

Reads ONLY committed inputs (so CI can check it without the 1.6 GB of rasters):
  * the candidate run card  docs/downloads/<NAME>-card.json
  * the nine focus-site holdout baseline  evidence/focus9-holdout-baseline-20261029.json
  * the historical geometry audit  docs/data/historical-audit.json

Every number is labelled: ORGANIZER-CONFIRMED (none exist here), HOLDOUT-DTI (with evaluator
version, withheld positives and 95% CI), USER-REPORTED (copied from the user's message), or
LOCAL-MEASUREMENT (format/overlap, not an organizer receipt).
Usage: build_submit_now.py [--check]
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "karage3-lgap-scarpstep-19k-20261029-4fc40bd1"
CARD = ROOT / "docs" / "downloads" / f"{NAME}-card.json"
FOCUS9 = ROOT / "evidence" / "focus9-holdout-baseline-20261029.json"
HIST = ROOT / "docs" / "data" / "historical-audit.json"
OUT = ROOT / "docs" / "submit-now" / "index.html"
SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31",
         "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def e(x) -> str:
    return html.escape(str(x), quote=True)


def pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def render() -> str:
    card = json.loads(CARD.read_text())
    f9 = {s["site"]: s for s in json.loads(FOCUS9.read_text())["sites"]}
    hist = {s["site"]: s for s in json.loads(HIST.read_text())["sites"]}
    if set(f9) != set(SITES) or set(hist) != set(SITES):
        raise ValueError("focus-site evidence incomplete")

    gates = card["gates"]
    cleared = gates["download_ok"] is True
    hr = card["holdout"]["hide_and_recover"]
    sg = card["holdout"]["sgmc_off_catalogue"]
    best = card["holdout"]["best_focus9_same_evaluator"]
    canary = card["holdout"]["leakage_canary"]
    up = card["uniqueness"]["final_dots_vs_measured_references"]
    full = card["uniqueness"]["full_inventory"]
    fmt = card["validator_output"]["format_checks"]
    note = card["submission_note"]
    sha = card["raster_sha256"]
    name = card["submission_name"]
    r13 = next(r for r in up["references"] if "r13" in r["name"])
    best_val = f"{best['prevalence_calibrated_dti']:.4f}"
    cand_val = f"{sg['prevalence_calibrated_dti']:.4f}"
    blocking = card["blocking_reasons"]
    status_word = "YES" if cleared else "NO"
    decision = ("DOWNLOAD OK" if cleared else "DO NOT DOWNLOAD OR SUBMIT")

    rows = []
    for site in SITES:
        h = hist[site]
        fz = f9[site]["holdout_dti_sgmc_off_catalogue"]
        fz_val = f"{fz['prevalence_calibrated_dti']:.4f}"
        rows.append(
            f'<tr><td><strong>{e(site)}</strong></td>'
            f'<td><a href="{e(h["source_url"])}">{e(h["file"])}</a><span class="micro">historical source, research only</span></td>'
            f'<td><span class="value">{e(h["historical_claim"])}</span><span class="micro">USER-REPORTED / UNVERIFIED</span></td>'
            f'<td>Not estimable<span class="micro">no validated leaderboard proxy</span></td>'
            f'<td><span class="warning-text">NO</span><span class="micro">{pct(h["worst_focus_fraction"])} within 3 px of {e(h["worst_focus_comparator"])}; lattice {pct(h["lattice_fraction"])}</span></td>'
            f'<td>{e(fz_val)}<span class="micro">HOLDOUT-DTI GEMSDOE32-SGMC-CAL-v3.0, n={fz["n_withheld_positives"]:,}, CI [{fz["calibrated_ci95"][0]:.4f}, {fz["calibrated_ci95"][1]:.4f}]</span></td>'
            f'<td><span class="tag">DO NOT SUBMIT</span></td></tr>')
    rows.append(
        f'<tr class="pick"><td><strong>NEW (this session)</strong></td>'
        f'<td>{e(name)}.tif<span class="micro">NOT PUBLISHED · SHA-256 {e(sha[:16])}…</span></td>'
        f'<td>None<span class="micro">no organizer receipt</span></td>'
        f'<td>Not estimable<span class="micro">no leaderboard estimate is made</span></td>'
        f'<td><span class="warning-text">NO</span><span class="micro">focus sites max {pct(max(r["overlap_fraction"] for r in up["references"] if "r13" not in r["name"]))}; r13 lattice {pct(r13["overlap_fraction"])}; full inventory: {full["count_literal_fails"]} of {full["rasters_compared"]:,} literal fails</span></td>'
        f'<td>{e(cand_val)}<span class="micro">HOLDOUT-DTI GEMSDOE32-SGMC-CAL-v3.0, n={sg["n_withheld_positives"]:,}, CI [{sg["calibrated_ci95"][0]:.4f}, {sg["calibrated_ci95"][1]:.4f}]; best focus-9 same evaluator {e(best_val)} ({e(best["site"])})</span></td>'
        f'<td><span class="tag">{e(decision)}</span></td></tr>')

    fmt_rows = "".join(
        f'<div class="data-pair"><span>{e(k.replace("_", " "))}</span><strong>{"PASS" if v else "FAIL"}</strong></div>'
        for k, v in fmt.items())
    ref_rows = "".join(
        f'<tr><td>{e(r["name"][:70])}</td><td>{pct(r["overlap_fraction"])}</td><td>{r["spearman_footprint"]:+.5f}</td></tr>'
        for r in up["references"])
    block_items = "".join(f"<li>{e(b)}</li>" for b in blocking)

    banner_title = ("OK TO DOWNLOAD: YES" if cleared else "OK TO DOWNLOAD: NO. OK TO SUBMIT: NO.")
    banner_body = ("All gates pass for the published file. Promotion still requires the owner's weekly-slot decision."
                   if cleared else
                   "No file is cleared. The candidate built this session fails the literal full-inventory uniqueness gate "
                   f"({full['count_literal_fails']} of {full['rasters_compared']:,} compared registry rasters exceed 70% overlap). "
                   "It is kept unpublished so it cannot be mistaken for a submission. Blocking reasons are below.")

    html_doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Submit now · GEMS unique file</title><link rel="stylesheet" href="../assets/site.css"><script defer src="../assets/site.js"></script></head>
<body><main id="main" class="wrap" style="padding:28px 0 60px">
<p><a href="../index.html">Decision home</a> · <a href="#status">Status</a> · <a href="#how">How to submit when cleared</a> · <a href="#compare">Nine-site table</a> · <a href="#review">Irregularities</a> · <a href="../downloads/{e(name)}-card.json">JSON run card</a></p>
<h1>Submit now: status, download rule and submission steps</h1>
<div class="banner" id="status"><span class="banner-icon" aria-hidden="true">{"&#10003;" if cleared else "!"}</span><div>
<strong>{e(banner_title)}</strong>
<p>{e(banner_body)}</p>
<p>Gate results: format {"PASS" if gates["format_pass"] else "FAIL"} · literal uniqueness vs the nine focus files and r13 lattice {"PASS" if gates["literal_uniqueness_measured_pass"] else "FAIL"} · full filtered inventory {"PASS" if gates["full_inventory_pass"] else "FAIL"} · promotion <strong>{e(card["verdict"].upper())}</strong>.</p>
</div></div>
<h2>Blocking reasons</h2>
<ul>{block_items if block_items else "<li>None</li>"}</ul>
<div class="data-pair"><span>Draft form note (for later use only)</span><strong>{e(note)} <span class="micro">({len(note)}/140 chars)</span></strong></div>
<div class="data-pair"><span>Estimated leaderboard score</span><strong>None (not estimable) · organizer-confirmed: none</strong></div>

<h2 id="how">What must change before anything is cleared</h2>
<ol>
<li><strong>Owner decision on dense surfaces.</strong> 59 failing rasters have at least 1,000,000 positive cells, so their "dots" cover the whole footprint and no dot file can be under 70%. The rule needs a definition for continuous surfaces, for example top-K cells by value, before those rasters can be compared fairly.</li>
<li><strong>Registry-aware dot selection for sparse sets.</strong> 19 failing rasters have fewer than 100,000 dots; this file overlaps one of them at 94.7%. A selector would need to put each candidate dot where, for every registry raster, at most 70% of dots fall within 3 px. That is a constrained selection and was not run here.</li>
<li><strong>Re-run the full inventory</strong> with <code>scripts/measure_registry_overlap.py</code> on the new file. A pass there is required before <code>scripts/make_submission_card.py</code> will publish a file.</li>
<li><strong>Owner selects a weekly slot</strong> (the cap is on the competition page). Nothing here does that.</li>
</ol>
<p><small>Format passes locally, but organizer acceptance of the outside-footprint convention is still unknown. The portal error "Predicted values must be in range [0, 1]" was not reproduced here.</small></p>

<h2>Hypothesis, mechanism and mimic (for the record)</h2>
<p><strong>Hypothesis.</strong> {e(card["hypothesis"])}</p>
<p><strong>Mechanism.</strong> {e(card["mechanism"])}</p>
<p><strong>Named non-fault mimic.</strong> {e(card["named_non_fault_mimic"])}</p>
<p><strong>Leakage canary.</strong> Single feature <code>{e(canary["feature"])}</code>: AUC vs SGMC off-catalogue truth = {canary["auc_vs_sgmc_offcatalogue"]:.3f} (threshold 0.90): {e(canary["status"])}. {e(canary["caveat"])}</p>
<p><strong>Holdout (HOLDOUT-DTI).</strong> {e(hr["evaluator_version"])}: pooled DTI {hr["pooled_dti"]:.4f}, CI [{hr["ci95"][0]:.4f}, {hr["ci95"][1]:.4f}], n={hr["n_withheld_positives"]:,}. {e(hr["interpretation"])}</p>
<p><small>All HOLDOUT-DTI values are static diagnostics on the shared evaluator. They do not reproduce portal ordering: the nine historical files score 0.0045 to 0.0967 here while the user-reported portal values run 0.2449 to 0.2778.</small></p>

<h2 id="compare">Nine-site comparison and the new file</h2>
<div class="table-wrap"><table><thead><tr><th>Site</th><th>File (download or source)</th><th>Reported score</th><th>Estimated leaderboard score</th><th>Unique vs the other focus sites?</th><th>Local HOLDOUT-DTI (labelled)</th><th>Decision</th></tr></thead><tbody>
{"".join(rows)}
</tbody></table></div>
<p><small>Historical rows are not downloads for submission. Their uniqueness numbers come from the committed historical geometry audit (docs/data/historical-audit.json). The new row is measured here. Full-inventory detail: <a href="{e(full["evidence"])}">{e(full["evidence"])}</a>.</small></p>

<h2 id="review">Validation evidence and irregularities</h2>
<div class="data-pair"><span>Footprint (template finite cells)</span><strong>{card["build"]["footprint_cells"]:,}</strong></div>
<div class="data-pair"><span>Dots placed (value 1.0)</span><strong>{card["build"]["candidate_dots"]:,}: {card["build"]["uncovered_cells_all_placed"]:,} uncovered by the lattice + {card["build"]["covered_dots_added"]:,} covered, all off-catalogue</strong></div>
{fmt_rows}
<table><thead><tr><th>Reference raster (measured here)</th><th>Dots within 3 px</th><th>Spearman (footprint)</th></tr></thead><tbody>{ref_rows}</tbody></table>
<p>Irregularities flagged for review:</p>
<ul>
<li>The earlier file <code>karage3-unique-offcat-20261029T180337Z-6a8c2368-zeros.tif</code> claims 12,000 dots, but only 4,517 fall inside the scored footprint; 7,483 positives lie outside it. It overlaps the r13 lattice by 99.89%, so it fails the literal rule. It is DO NOT SUBMIT.</li>
<li>Its sibling <code>...-nan.tif</code> has no NaN cells: it writes 0 outside the footprint, so its name is misleading.</li>
<li>Its metadata reports footprint_pixels = 12,279,160; that is the whole grid. The template footprint is 5,167,373 cells.</li>
<li>The first candidate built this session ranked dots by the SGMC trace, which the SGMC evaluator scores. Its SGMC-cal value of 0.169 is circular and was retired, not reported as a result.</li>
<li>The lattice-gap design satisfies the rule against r13 and the nine focus files, but not against the full inventory. A rule that only checks the focus files and one witness would have missed this.</li>
<li>The filtered registry manifest is not proven complete (<code>literal_registry_complete: false</code>). Full-inventory results are therefore a floor, not a certificate.</li>
<li>Eleven pre-existing unit tests fail on the base commit as well as on this branch (see the review note). They were not changed here.</li>
</ul>
<h3>Why the file is blocked (from the card)</h3>
<ul>{block_items if block_items else "<li>None</li>"}</ul>

<h2>Sources (official, for manual review)</h2>
<ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem and metric (DrivenData)</a></li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard (DrivenData)</a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Competition rules and submission format (NLR)</a></li>
<li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN data page</a></li>
<li><a href="https://epsg.io/32611">EPSG:32611 (WGS 84 / UTM zone 11N)</a></li>
</ul>
<p><small>Not checked live: DrivenData and NLR hosts were not reachable from this sandbox, so the text of these sources is unverified in this session. Verified: the candidate's bytes and hashes, the repo's pinned mirror hashes, and the GitHub-hosted evidence.</small></p>
</main></body></html>
'''
    return html_doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="fail if the checked-in page is stale")
    args = ap.parse_args()
    text = render()
    if args.check:
        if not OUT.exists() or OUT.read_text() != text:
            print(f"Stale generated page: {OUT.relative_to(ROOT)}", file=sys.stderr)
            return 1
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"Built {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
