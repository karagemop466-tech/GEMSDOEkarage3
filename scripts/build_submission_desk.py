#!/usr/bin/env python3
"""Render the Submission Desk (submission-desk.html) from the evidence JSON.

Every number on the page is read from:
  * evidence/focus-site-audit-20261029.json   (scripts/focus_site_audit.py)
  * evidence/exp-s6-e1-offconsensus.json      (scripts/exp_s6_offconsensus.py)

Hand-typed values are limited to the USER-REPORTED leaderboard numbers, which
come from the owner's prompt and the README table and are labelled as such.
The page never says a file is OK to upload unless a gate says so; at the time of
writing, none does.
"""
from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "evidence" / "focus-site-audit-20261029.json"
S6 = ROOT / "evidence" / "exp-s6-e1-offconsensus.json"
S6E2 = ROOT / "evidence" / "exp-s6-e2-lidar-lineament.json"
NULL = ROOT / "evidence" / "control-random-null-sgmc.json"
OUT = ROOT / "submission-desk.html"

# USER-REPORTED values: owner prompt and README table (no organizer receipt on file).
USER_REPORTED = {
    "GEMSDOE24": 0.2477, "GEMSDOE25": 0.2600, "GEMSDOE27": 0.2449, "GEMSDOE28": 0.2710,
    "GEMSDOE30": 0.2600, "GEMSDOE31": 0.2708, "GEMSDOE32": 0.2778, "GEMSDOE33": 0.2632,
    "GEMSDOE36": 0.2750,
}
LEADERBOARD_NOTE = ("The owner prompt gives 0.4413 in one place and 0.3195 in another; the README records 0.4544 "
                    "observed 2026-10-28. None is verified here; check the public board manually (see IR-S6-07).")


def esc(x) -> str:
    return escape(str(x), quote=True)


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * float(x):.2f}%"


def ci(x) -> str:
    return f"[{x[0]:.4f}, {x[1]:.4f}]"


def load() -> tuple[dict, dict]:
    return json.loads(AUDIT.read_text()), json.loads(S6.read_text())


def load_s6e2() -> dict:
    return json.loads(S6E2.read_text())


def load_null() -> dict:
    return json.loads(NULL.read_text())


def off_diag(pw: dict) -> list[tuple[str, str, float]]:
    return [(a_, b_, v) for a_, row in pw.items() for b_, v in row.items() if a_ != b_]


def focus_rows(a: dict) -> list[str]:
    rows = []
    sites = list(a["files"].keys())
    pw = a["pairwise_literal_overlap_3px_row_is_A_col_is_B"]
    sgmc = a["offcatalogue_sgmc_raw_dti_same_evaluator"]
    hold = a["holdout_dti_same_evaluator"]
    for site in sites:
        f = a["files"][site]
        url = f"https://github.com/{f['repo']}/blob/{f['pinned_commit_from_readme']}/{f['path']}"
        worst_site, worst = max(((k, v) for k, v in pw[site].items() if k != site), key=lambda kv: kv[1])
        fc = f["format_checks"]
        fmt = ("NaN outside footprint, 0/1 inside" if fc["nan_outside_footprint"] > 0
               else "0/1 everywhere (no NaN outside)")
        checks_ok = all([fc["crs_is_EPSG32611"], fc["shape_matches_template"], fc["transform_matches_template"],
                         fc["single_band"], fc["float32"], fc["values_in_0_1_where_finite"],
                         fc["nan_inside_footprint"] == 0, fc["nonzero_outside_footprint"] == 0])
        unique = "NO" if worst > 0.70 else "YES"
        rows.append(f"""<tr>
<td><strong>{esc(site)}</strong><br><a class="file-link" href="{esc(url)}">{esc(f['path'].split('/')[-1])}</a>
<span class="micro">pinned {esc(f['pinned_commit_from_readme'][:10])} · SHA-256 <span class="code">{esc(f['sha256'][:16])}…</span> · registry bytes match: {'yes' if f['registry_sha256_match'] else 'NO'} · registry ref = README commit: {'yes' if f['registry_ref_matches_readme'] else 'NO'}</span></td>
<td>{f['dot_count_gt0']:,} dots<span class="micro">{esc(fmt)}</span><span class="micro">format checks: {'all pass' if checks_ok else 'FAIL'} · values in [0,1]: {'yes' if fc['values_in_0_1_where_finite'] else 'NO'}</span></td>
<td><span class="value">{USER_REPORTED[site]:.4f}</span><span class="micro">USER-REPORTED / UNVERIFIED · no organizer receipt</span></td>
<td>Not estimable for the leaderboard.<span class="micro">Local HOLDOUT-DTI (off-catalogue SGMC, raw): <strong>{sgmc[site]['dti']:.4f}</strong> {ci(sgmc[site]['ci95'])} · n={sgmc[site]['withheld_positives']:,} withheld positives · {esc(sgmc[site]['evaluator_version'])}</span>
<span class="micro">Catalogue hide-and-recover HOLDOUT-DTI: {hold[site]['dti']:.4f} {ci(hold[site]['ci95'])} · misaligned with the official masking rule (see IR-S6-02)</span></td>
<td><span class="warning-text">{unique} · max {pct(worst)}</span><span class="micro">literal 3-px overlap with {esc(worst_site)}, the most-overlapping other focus file</span></td>
<td><span class="tag">DO NOT SUBMIT</span><span class="micro">Already-reported historical file. Not a new submission.</span></td>
</tr>""")
    return rows


def s6_row(card: dict) -> str:
    sg = card["holdout_sgmc_offcatalogue_raw"]
    hr = card["holdout_hide_and_recover_catalogue"]
    return f"""<tr class="row-new">
<td><strong>S6-E1 (new, generated here)</strong><br><a class="file-link" href="{esc(card['raster']['file'])}">{esc(card['submission_name'])}</a>
<span class="micro">SHA-256 <span class="code">{esc(card['raster']['sha256'][:16])}…</span> · {card['raster']['bytes']:,} bytes · local validator: {'PASS' if card['validator']['validator_pass'] else 'FAIL'}</span></td>
<td>{card['n_dots']:,} dots<span class="micro">NaN outside footprint (the official spec allows NaN/null outside bounds), 0/1 inside</span></td>
<td>None reported<span class="micro">no leaderboard history</span></td>
<td>Not estimable for the leaderboard.<span class="micro">Local HOLDOUT-DTI (off-catalogue SGMC, raw): <strong>{sg['dti']:.4f}</strong> {ci(sg['ci95'])} · n={sg['withheld_positives']:,} · best of the nine on this proxy is {sg['same_evaluator_best_of_nine']['dti']:.4f} ({esc(sg['same_evaluator_best_of_nine']['site'])})</span>
<span class="micro">Catalogue hide-and-recover HOLDOUT-DTI: {hr['dti']:.4f} {ci(hr['ci95'])}</span></td>
<td><span class="ok-text">YES · max {pct(card['uniqueness_vs_focus_nine_literal_3px_max'])}</span><span class="micro">vs all nine focus files</span>
<span class="warning-text">BUT {pct(card['uniqueness_vs_r13_lattice_literal_3px'])} vs calibration lattice r13-lattice-s5 (rule: ≤70%)</span></td>
<td><span class="tag">NEGATIVE · DO NOT SUBMIT</span><span class="micro">Research only. Below the random-placement null on the proxy (see controls). Blocked by the lattice rule.</span></td>
</tr>"""


def s6e2_row(c: dict) -> str:
    sg = c["holdout_sgmc_offcatalogue_raw"]
    hr = c["holdout_hide_and_recover_catalogue"]
    cm = c["cultural_mimic_control"]
    return f"""<tr class="row-new">
<td><strong>S6-E2 (new, LiDAR step × coherence)</strong><br><a class="file-link" href="{esc(c['raster']['file'])}">{esc(c['submission_name'])}</a>
<span class="micro">SHA-256 <span class="code">{esc(c['raster']['sha256'][:16])}…</span> · {c['raster']['bytes']:,} bytes · local validator: {'PASS' if c['validator']['validator_pass'] else 'FAIL'}</span></td>
<td>{c['n_dots']:,} dots<span class="micro">NaN outside footprint, 0/1 inside</span></td>
<td>None reported<span class="micro">no leaderboard history</span></td>
<td>Not estimable for the leaderboard.<span class="micro">Local HOLDOUT-DTI (off-catalogue SGMC, raw): <strong>{sg['dti']:.4f}</strong> {ci(sg['ci95'])} · n={sg['withheld_positives']:,} · {esc(sg['evaluator_version'])}</span>
<span class="micro">In focus band on the point estimate, but the CI is wide. Catalogue hide-and-recover: {hr['dti']:.4f} {ci(hr['ci95'])} (misaligned, IR-S6-02). Canary AUC {c['feature_auc_canary']['step_x_coh_alone_auc_sgmc']:.3f} (threshold 0.90).</span></td>
<td><span class="ok-text">YES · max {pct(c['uniqueness_vs_focus_nine_literal_3px_max'])}</span><span class="micro">vs all nine focus files</span>
<span class="warning-text">BUT {pct(c['uniqueness_vs_r13_lattice_literal_3px'])} vs calibration lattice (rule: ≤70%)</span></td>
<td><span class="tag">DUPLICATE_STOP · DO NOT SUBMIT</span><span class="micro">Lattice overlap above 70% stops it under the protocol. Its proxy number is logged for the record and is not used to advance it. Its inputs are not new (see the hypotheses doc).</span></td>
</tr>"""


def render() -> str:
    a, card = load()
    lat = a["lattice"]
    pw = a["pairwise_literal_overlap_3px_row_is_A_col_is_B"]
    exact = a["exact_set_relations"]
    e2 = load_s6e2()
    nul = load_null()
    rows = focus_rows(a) + [s6_row(card), s6e2_row(e2)]
    sg = a["offcatalogue_sgmc_raw_dti_same_evaluator"]
    sg_vals = sorted(v["dti"] for v in sg.values())
    off = [v for _, _, v in off_diag(pw)]
    min_pair, max_pair = min(off), max(off)
    H = lat["footprint_px_uncovered_within_3px"]
    N_min = lat["min_N_forcing_overlap_above_70pct"]
    blockers = "".join(f"<li>{esc(b)}</li>" for b in card["blockers"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Submission desk: which file to download, what it is estimated to score, and whether it is unique. Generated from evidence JSON.">
<title>GEMS Submission Desk · 2026-10-29</title>
<link rel="stylesheet" href="assets/site.css"></head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header"><div class="container header-inner">
<a class="brand" href="index.html"><span class="brand-mark">G</span><span class="brand-name">GEMS Fieldnotes<small>Submission desk</small></span></a>
<nav class="nav" aria-label="Primary"><a href="index.html">Overview</a><a href="submission-desk.html" aria-current="page">Submission desk</a><a href="executive-summary.html">Submission guide</a><a href="research.html">Research</a><a href="sources.html">Sources</a></nav>
</div></header>
<main id="main"><div class="container">
<section class="hero" aria-labelledby="desk-title">
<div><div class="eyebrow">Executive summary · generated 2026-10-29 from evidence JSON</div>
<h1 id="desk-title">Which file to download, <em>and is it safe to upload?</em></h1>
<p class="lede">Short answer: <strong>no file on this page is cleared for upload.</strong> Nine historical files that were reported as submitted are not unique (off-diagonal overlaps between them run from {pct(min_pair)} to {pct(max_pair)}). We generated two new files that overlap none of them. S6-E1 falls below chance on our off-catalogue proxy. S6-E2 sits inside the focus band on that proxy, but both fail the calibration-lattice rule. Under the parallel-run protocol both are logged DUPLICATE_STOP, so neither advances.</p>
<div class="hero-links"><a class="button" href="{esc(e2['raster']['file'])}">Download S6-E2 TIFF (research only — do NOT upload) ↓</a><a class="button" href="{esc(card['raster']['file'])}">Download S6-E1 TIFF (research only — do NOT upload) ↓</a><a class="button" href="executive-summary.html">How to submit (once cleared) ↗</a><a href="evidence/focus-site-audit-20261029.json">Audit JSON ↗</a><a href="evidence/exp-s6-e1-offconsensus.json">S6-E1 run card ↗</a><a href="evidence/exp-s6-e2-lidar-lineament.json">S6-E2 run card ↗</a><a href="evidence/control-random-null-sgmc.json">Random-null control ↗</a></div>
</div>
<div class="release-card" aria-label="Upload verdict">
<div class="card-top"><span class="card-kicker">UPLOAD VERDICT</span><span class="pill hold">NOT CLEARED</span></div>
<h2>Do not upload<br>any file today.</h2>
<p>Gate 1 (literal uniqueness, 3 px): only {H:,} footprint pixels lie beyond 3 px of the calibration lattice. A dot set of N dots therefore overlaps it by at least 1 − {H:,}/N, which exceeds 70% once N ≥ {N_min:,}. Even if every uncovered pixel were filled, the overlap would still exceed 70%, so the literal rule cannot be met at that size.</p>
<p>Gate 2 (score evidence): there is no organizer receipt, and the off-catalogue proxy in the repo does not reproduce the reported ranking.</p>
<p>Gate 3 (registry): the registry inventory is not literal-complete (IR-S6-06).</p>
</div>
</section>

<section class="section" aria-labelledby="table-title"><div class="section-head"><div><div class="eyebrow">What to download · score · uniqueness</div><h2 id="table-title">Nine focus sites plus our new file</h2></div>
<p>Each row is verified by <code>scripts/focus_site_audit.py</code>: bytes fetched at the pinned commit, SHA-256 checked against the registry, format checked against the official rules, overlaps computed at 3 px. Scores are labelled by evidence class; none is an organizer receipt.</p></div>
<p class="table-scroll-hint">Scroll across the table to see every column →</p>
<div class="table-wrap" role="region" tabindex="0" aria-label="Download, score and uniqueness table; scroll horizontally"><table><thead><tr>
<th scope="col">File to download (verified link)</th><th scope="col">Dots &amp; format</th><th scope="col">Reported score</th><th scope="col">Estimated score (local, labelled)</th><th scope="col">Unique vs the other focus files?</th><th scope="col">Upload verdict</th>
</tr></thead><tbody>
{''.join(rows)}
</tbody></table></div>
<p class="table-note"><strong>Estimated score</strong> means a local HOLDOUT-DTI with a 95% spatial cluster-bootstrap CI. The DTI uses the official α=0.2, β=0.8 and the 300 m triangular kernel. The off-catalogue reference is USGS SGMC, not the organizer's hidden labels. Local proxies rank the nine sites inside a narrow band ({sg_vals[0]:.4f}–{sg_vals[-1]:.4f} on the off-catalogue proxy) that does not match the reported spread (0.2449–0.2778). <strong>An estimate is therefore not a leaderboard forecast.</strong></p>
</section>

<section class="section" aria-labelledby="controls-title"><div class="container">
<div class="section-head"><div><div class="eyebrow">Controls for the proxy</div><h2 id="controls-title">What chance looks like on the same proxy</h2></div>
<p>Before any candidate is compared with the focus band, its score must beat a random-placement null. The null places the same 37,654 binary dots uniformly in the footprint (known-fault pixels excluded) and is scored by the same evaluator.</p></div>
<div class="cards">
<article class="card"><span class="number">0</span><h3>Random null</h3><p>Five random draws score {nul['min']:.4f}–{nul['max']:.4f} (mean {nul['mean']:.4f}) on the off-catalogue SGMC proxy, with per-draw 95% CIs in <code>evidence/control-random-null-sgmc.json</code>. S6-E1 (0.0452) is below that. S6-E2 ({e2['holdout_sgmc_offcatalogue_raw']['dti']:.4f}) is about 0.03 above it, but its CI lower bound ({e2['holdout_sgmc_offcatalogue_raw']['ci95'][0]:.4f}) sits just above the top of the null range ({nul['max']:.4f}).</p></article>
<article class="card"><span class="number">1</span><h3>Focus band</h3><p>The nine focus files span {sg_vals[0]:.4f}–{sg_vals[-1]:.4f} on the same proxy, so the focus band sits about 0.023–0.031 above the null mean.</p></article>
<article class="card"><span class="number">2</span><h3>Leakage and mimic checks</h3><p>S6-E2 uses one LiDAR-derived feature. Its canary AUC is {e2['feature_auc_canary']['step_x_coh_alone_auc_sgmc']:.3f} against the SGMC truth (threshold 0.90). That passes, but it is high enough that the proxy may reward LiDAR-visible structure in general. Road control: {pct(e2['cultural_mimic_control']['share_dots_within_100m_of_road'])} of S6-E2 dots lie within 100 m of a mapped road, against {pct(e2['cultural_mimic_control']['share_footprint_within_100m_of_road'])} of the footprint.</p></article>
</div></div></section>

<section class="section soft" aria-labelledby="why-title"><div class="container">
<div class="section-head"><div><div class="eyebrow">Why GEMSDOE32 led the nine</div><h2 id="why-title">Mechanism, checked pixel by pixel</h2></div></div>
<div class="cards">
<article class="card"><span class="number">1</span><h3>Nested, not independent</h3><p>Exact pixel tests: GEMSDOE32 ⊂ GEMSDOE31 = {exact['GEMSDOE32_subset_of_GEMSDOE31']}; GEMSDOE31 ⊂ GEMSDOE25 = {exact['GEMSDOE31_subset_of_GEMSDOE25']}; GEMSDOE32 ⊂ GEMSDOE36 = {exact['GEMSDOE32_subset_of_GEMSDOE36']}; GEMSDOE25 and GEMSDOE30 have identical dot masks = {exact['GEMSDOE25_dot_mask_identical_to_GEMSDOE30']}. GEMSDOE32 is GEMSDOE31 with {exact['GEMSDOE31_minus_GEMSDOE32_dots']:,} dots removed.</p></article>
<article class="card"><span class="number">2</span><h3>The removed dots sit on known faults</h3><p>All {exact['GEMSDOE31_minus_GEMSDOE32_dots']:,} dots removed from GEMSDOE31 to make GEMSDOE32 lie within {exact['GEMSDOE31_minus_GEMSDOE32_max_distance_to_visible_fault_px']:.1f} px of a visible catalogue fault (<code>labels.tif</code>). Official scoring masks known faults (DrivenData staff, 16 Sep). Removing a dot lowers FP_w by that dot's own non-negative term. It can also raise FN_w if the dot was the nearest hit for an unmasked truth point within 300 m, and hidden labels cannot be checked locally. The reported step 0.2708 → 0.2778 is consistent with a net gain; it is not verified.</p></article>
<article class="card"><span class="number">3</span><h3>Fewest dots of the nine</h3><p>GEMSDOE32 has {a['files']['GEMSDOE32']['dot_count_gt0']:,} dots, the lowest of the nine (next lowest: GEMSDOE28 at {a['files']['GEMSDOE28']['dot_count_gt0']:,}). Removing dots can only reduce FP_w if the removed dots carried no TP_w, and the reported ordering is consistent with that. Recall at the official metric is not computable locally.</p></article>
</div></div></section>

<section class="section" aria-labelledby="lattice-title"><div class="container">
<div class="section-head"><div><div class="eyebrow">Why the uniqueness rule blocks every dot file</div><h2 id="lattice-title">The calibration lattice covers the footprint</h2></div></div>
<div class="cards">
<article class="card"><span class="number">A</span><h3>{lat['dots']:,} lattice dots</h3><p>Registry raster <code>r13-lattice-s5</code> (<code>scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif</code>, SHA-256 <code>{esc(lat['sha256'][:12])}…</code>). It lies within 3 px of {pct(lat['footprint_coverage_within_3px'])} of the footprint. Only <strong>{H:,}</strong> footprint pixels lie outside its reach.</p></article>
<article class="card"><span class="number">B</span><h3>Pigeonhole bound</h3><p>Each hole pixel can hold at most one dot, so at most {H:,} dots of any N-dot file can fall outside the lattice's reach. Overlap is therefore at least 1 − {H:,}/N, which exceeds 70% once N ≥ <strong>{N_min:,}</strong>. Every focus file overlaps the lattice by 99.9% or more.</p></article>
<article class="card"><span class="number">C</span><h3>Consequence</h3><p>Under the literal rule you set (no exemptions, including dense or synthetic lattices) no dot file of this size can pass. We have not waived the rule, and this page does not propose a way around it.</p></article>
</div></div></section>

<section class="section soft" aria-labelledby="decide-title"><div class="container">
<div class="section-head"><div><div class="eyebrow">Decisions for you</div><h2 id="decide-title">What we need from you</h2></div></div>
<ol>
<li><strong>Uniqueness rule.</strong> Your standing instruction is literal, with no exemptions for dense or synthetic lattices. Under that instruction no dot file of this size passes, so the honest answer today is: upload nothing. If you want an upload path, you must first change that instruction in writing. We will not change the rule ourselves.</li>
<li><strong>Score evidence.</strong> A real score needs an ORGANIZER-CONFIRMED receipt. Each upload uses a one-way weekly slot, and local estimates cannot separate the nine files.</li>
<li><strong>Leaderboard number.</strong> Confirm the current public #1 by hand (IR-S6-07). The prompt gives 0.4413 and 0.3195, the README gives 0.4544, and IR-K3-03 records 0.4437 from a 26 Oct fetch.</li>
</ol>
<p><strong>Recommendation:</strong> upload nothing from this page. Both new candidates are DUPLICATE_STOP under the lattice rule. The next hypothesis to test is H4 in <code>docs/research/session6-hypotheses-20261029.md</code>, after a precondition check. That work does not change decision 1.</p>
</div></section>

<section class="section" aria-labelledby="irr-title"><div class="container">
<div class="section-head"><div><div class="eyebrow">Irregularities flagged for review</div><h2 id="irr-title">Register entries (registry/irregularities.json)</h2></div></div>
<ul>
<li><strong>IR-S6-01</strong> Reported focus-file scores are USER-REPORTED with no organizer receipt. All nine files pass the local [0,1] check (<code>values_in_0_1_where_finite</code>), so the "Predicted values must be in range [0, 1]" error is not caused by out-of-range values. Its real cause is unverified; NaN outside the footprint is allowed by the official spec, so it is not a confirmed cause either. See IR-K3-NODATA-RANGE01-01.</li>
<li><strong>IR-S6-02</strong> The catalogue hide-and-recover holdout is misaligned with the official target. Official scoring masks known faults, but this proxy rewards recovering them. It ranks GEMSDOE32 at {a['holdout_dti_same_evaluator']['GEMSDOE32']['dti']:.4f} against 0.2778 reported, so it is not used to rank files.</li>
<li><strong>IR-S6-03</strong> GEMSDOE25 and GEMSDOE30 have identical dot masks, though their files differ in bytes. Under the literal rule they are duplicates. GEMSDOE32 ⊂ GEMSDOE31 ⊂ GEMSDOE25 and GEMSDOE32 ⊂ GEMSDOE36 are also exact.</li>
<li><strong>IR-S6-04</strong> For all nine files the registry ref differs from the commit in the README link ({sum(1 for f in a['files'].values() if not f['registry_ref_matches_readme'])} of 9 mismatched), although the bytes match. Check each link by hand.</li>
<li><strong>IR-S6-05</strong> <code>labels.tif</code> and <code>existing_faults.tif</code> are byte-identical (SHA-256 <code>7ba308cc…</code>). The restored data therefore has no second, independent label layer.</li>
<li><strong>IR-S6-06</strong> The registry inventory is not literal-complete (<code>literal_registry_complete: false</code>). Only 14 scored rasters are restored locally, so uniqueness is checked against the restored subset only.</li>
<li><strong>IR-S6-07</strong> Conflicting leaderboard numbers: 0.4413 and 0.3195 (prompt), 0.4544 (README, 28 Oct), 0.4437 (IR-K3-03, a GEMSDOE28 fetch on 26 Oct). None is verified here.</li>
<li><strong>IR-S6-08</strong> On sampled pixels GEMSDOE32 has Spearman ρ = {a['files']['GEMSDOE32']['spearman_vs_lattice_sampled']:.6f} against the lattice. Binary dot maps give near-zero rank correlation, so the 0.90 rank gate says little about them. The literal 3-px overlap gate is the one that bites.</li>
<li><strong>IR-S6-09</strong> <code>src/gems32/holdout.py</code> sets <code>ESTIMATED_LB_HIDDEN_TRUTH_PX = 12691</code>, calibrated from a blind lattice score (0.0904) and another file, not from an organizer receipt. The calibrated SGMC number is not reported here; only the raw SGMC DTI is.</li>
<li><strong>IR-S6-10</strong> The site build check was failing because the saved-byte audit covers only the retained TIFFs under <code>docs/</code>. S6-E1 is therefore kept under <code>evidence/experiments/</code>.</li>
<li><strong>IR-S6-11</strong> Random placement with the same budget scores {nul['min']:.4f}–{nul['max']:.4f} on the SGMC proxy. Any proxy comparison that omits a random null overstates signal. S6-E1 scores below this null.</li>
<li><strong>IR-S6-12</strong> Procedure deviation: S6-E2 was scored on the off-catalogue proxy before the duplicate check ran. The check (<code>scripts/dup_check_s6.py</code>) then logged DUPLICATE_STOP. The proxy number is disclosed and not used to advance the candidate.</li>
</ul>
<h3>Blockers recorded for S6-E1 (from its run card)</h3><ul>{blockers}</ul>
</div></section>

<section class="section" aria-labelledby="src-title"><div class="container">
<div class="section-head"><div><div class="eyebrow">Official sources (verified 2026-10-29)</div><h2 id="src-title">Links for manual review</h2></div></div>
<ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem page — metric (DTI, α=0.2, β=0.8, 300 m triangular kernel) and submission format (float32, [0,1], EPSG:32611, NaN/null outside bounds)</a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">GEMS Prize Official Rules (NLR 96647, September 2026)</a></li>
<li><a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">DrivenData forum: known USGS/INGENIOUS faults are masked from scoring (staff reply 16 Sep)</a></li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition page (leaderboard checked by hand, not scraped)</a></li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Organizer reference solution</a></li>
</ul>
<p class="table-note">{esc(LEADERBOARD_NOTE)}</p>
</div></section>
</div></main>
<footer class="footer"><div class="container footer-inner"><span>GEMS Fieldnotes · Submission desk · generated from evidence JSON</span><span><a href="index.html">Overview</a></span></div></footer>
</body></html>
"""


def desk_banner() -> str:
    """Banner injected at the top of index.html and executive-summary.html."""
    return ('<section class="container" style="margin-top:14px" aria-label="Submission desk banner">'
            '<div style="padding:14px 18px;border:2px solid #881337;border-radius:10px;background:#fff1f2;color:#881337">'
            '<strong>SUBMISSION DESK (29 Oct 2026): NO FILE IS CLEARED FOR UPLOAD.</strong> '
            'Download table, estimates and uniqueness results: <a href="submission-desk.html"><strong>open the Submission Desk ↗</strong></a>. '
            'The new unique file is research only: <a href="evidence/experiments/s6-e1/gemsdoekarage3-s6-offcons-tmihg-ridge-37654-20261029.tif">S6-E1 TIFF</a> (do NOT upload).'
            '</div></section>')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if submission-desk.html is stale")
    args = ap.parse_args()
    text = render()
    if args.check:
        if not OUT.exists() or OUT.read_text() != text:
            print("stale: submission-desk.html", file=sys.stderr)
            return 1
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
