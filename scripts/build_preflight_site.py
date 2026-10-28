#!/usr/bin/env python3
"""Build the static evidence site from the frozen manifest and audit, no network."""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
manifest = json.loads((ROOT / "registry" / "historical.json").read_text())
audit = json.loads((ROOT / "evidence" / "geometry_audit.json").read_text())


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def shell(title: str, active: str, body: str) -> str:
    nav = [("preflight.html", "Overview", "home"), ("preflight-executive.html", "Executive summary", "executive"),
           ("preflight-research.html", "Research & sources", "research")]
    links = "".join('<a href="{}"{}>{}</a>'.format(
        href, ' aria-current="page"' if active == key else '', label)
        for href, label, key in nav)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · GEMS Research Desk</title><meta name="description" content="An evidence-led research and submission-readiness review for the DOE GEMS Prize.">
<link rel="stylesheet" href="assets/site.css"><script defer src="assets/site.js"></script></head>
<body><header class="topbar"><div class="wrap"><a class="brand" href="preflight.html" aria-label="GEMS Research Desk home"><span class="brand-mark">G</span><span class="brand-name">GEMS <br>RESEARCH DESK<small>GEOLOGIC MAPPING / DOE</small></span></a>
<nav class="nav" aria-label="Main navigation">{links}</nav><span class="nav-pill"><span class="nav-dot"></span>Evidence first</span></div></header>
<main>{body}</main>
<footer class="footer"><div class="wrap footer-inner"><p><strong>GEMS Research Desk</strong> &nbsp; / &nbsp; Independent research, not affiliated with the organizers.<br>Evidence snapshots may become stale. No slot has been selected.</p><div class="footer-links"><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem ↗</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard ↗</a><a href="https://github.com/karagemop466-tech/GEMSDOEkarage3">Repository ↗</a></div></div></footer></body></html>'''


def archive_url(url: str) -> str:
    return url.replace("/blob/", "/raw/", 1)


rows = []
for item in manifest["historical"]:
    name = item["site"]
    peer = max((p for p in audit["pairs"] if p["candidate"] == name),
               key=lambda p: p["fraction_candidate_dots_within_3px"])
    frac = peer["fraction_candidate_dots_within_3px"] * 100
    rows.append(f'''<tr><td class="site"><a href="{esc(item['site_url'])}">{esc(name)} ↗</a></td>
<td class="file"><a href="{esc(archive_url(item['source_url']))}">{esc(item['historical_file'])}</a><span class="fine">Historical archive · research only</span></td>
<td><span class="score">{esc(item['quoted_owner_claim'])}</span><span class="fine">USER-REPORTED / unverified</span></td>
<td>Unavailable<span class="fine">No validated transfer to hidden score</span></td>
<td><span class="no">No</span><span class="fine">{frac:.2f}% within 3 px of {esc(peer['reference'])}</span></td>
<td><span class="no">DO NOT SUBMIT</span><span class="fine">Already reported; not a new candidate</span></td></tr>''')
rows_html = "\n".join(rows)

home = '''
<section class="hero"><div class="wrap hero-grid"><div><div class="eyebrow">DOE GEMS PRIZE &nbsp; / &nbsp; RESEARCH INTELLIGENCE</div>
<h1>Find the faults.<br><em>Keep the evidence.</em></h1><p>Turning geologic signals into defensible fault predictions. The goal: test each candidate for scientific value, uniqueness, and submission readiness before a slot is spent.</p>
<div class="actions"><a class="btn" href="preflight-executive.html">View executive summary <span class="arrow">↗</span></a><a class="btn ghost" href="preflight-research.html">Explore the research <span class="arrow">→</span></a></div></div>
<aside class="status-card" aria-label="Current submission readiness"><div class="card-head"><span>SUBMISSION CHECKPOINT</span><span class="tag red">Not ready</span></div><h2 class="card-title">No file is ready<br>to submit.</h2><p>There is no new, validated TIFF or authorized weekly slot. Historical files below are research references—not new submissions.</p>
<div class="status-checks"><div class="status-check"><b>×</b> Assigned method lane not supplied</div><div class="status-check"><b>×</b> Literal registry rule blocks the usual dot budget</div><div class="status-check"><b>×</b> No new holdout or candidate file</div></div>
<a class="card-link" href="preflight-executive.html">See the full decision &nbsp; →</a></aside></div></section>
<section class="ticker"><div class="wrap ticker-grid"><div class="stat"><span class="stat-icon">↗</span><div><small>Public leaderboard leader</small><strong id="public-score">0.4544</strong><span class="evidence" id="public-score-detail">PUBLIC snapshot · 27 Oct 2026 · may be stale</span></div></div>
<div class="stat"><span class="stat-icon">◈</span><div><small>Best historical claim · 9 sites</small><strong>0.2778</strong><span class="evidence">USER-REPORTED / not receipt-verified</span></div></div>
<div class="stat"><span class="stat-icon">⌁</span><div><small>New validated candidate</small><strong>None</strong><span class="evidence">No HOLDOUT-DTI run this session</span></div></div></div></section>
<section class="section" id="evidence"><div class="wrap"><div class="section-head"><div><div class="section-label">THE EVIDENCE PIPELINE</div><h2>A better score starts with a better test.</h2></div><p>Format is necessary, but it is not evidence that a prediction is unique or will generalize to hidden faults.</p></div>
<div class="cards"><article class="step-card"><div class="step-top"><span class="step-icon">⌁</span><span>01 / GEOLOGY</span></div><h3>Propose a physical signal</h3><p>Start with a testable mechanism, the layers it uses, and the non-fault processes that could imitate it.</p></article>
<article class="step-card"><div class="step-top"><span class="step-icon">◫</span><span>02 / VALIDATION</span></div><h3>Recover withheld segments</h3><p>Build catalogue features from visible faults only, check each feature for leakage, and compare matched spatial holdouts.</p></article>
<article class="step-card"><div class="step-top"><span class="step-icon">◇</span><span>03 / RELEASE</span></div><h3>Protect the submission</h3><p>Check the complete registry before and after placement, validate saved bytes, then use a separate slot selector.</p></article></div></div></section>
<section class="section tight" style="padding-top:0"><div class="wrap"><div class="insight"><div class="insight-visual"><span>THE NINE-SITE REVIEW</span></div><div class="insight-body"><div class="section-label">WHAT THE EVIDENCE SAYS</div><h2>A higher claim is not a new discovery.</h2><p>The reported GEMSDOE32 leader is a catalogue-adjacent deletion of an earlier dot pattern. That geometry is verified on mirrored rasters; the reason for its reported score is not. All nine historical files fail the requested proximity rule against another focus-site file.</p><a class="text-link" href="preflight-executive.html#nine-sites">Review all nine historical files &nbsp; →</a></div></div></div></section>
<section class="section tight" style="padding-top:0"><div class="wrap"><div class="watch"><div><strong><span class="status-dot"></span>Source watch</strong><p id="watch-detail">Loading source metadata; the checked-in snapshot may be stale. Refresh never approves a submission.</p></div><a class="text-link" href="data/feed.json">View feed JSON &nbsp; →</a></div></div></section>'''

executive = '''
<section class="page-hero"><div class="wrap"><div class="eyebrow">DECISION BRIEF &nbsp; / &nbsp; 28 OCT 2026</div><h1>Submission executive summary.</h1><p>The strongest defensible recommendation is to protect the next slot. A downloadable archive is not the same as a new, unique, validated submission.</p></div></section>
<section class="section tight"><div class="wrap"><div class="alert"><span class="alert-icon">!</span><div><strong>NO FILE IS APPROVED FOR SUBMISSION</strong><p>No new TIFF was generated in this run. Do not upload, rename, or resubmit the historical research files listed below.</p></div></div>
<div class="two-col"><div class="panel"><div class="section-label">CURRENT DECISION</div><h2>Download is locked for now.</h2><p>There is no new file, defensible leaderboard estimate, artifact-linked organizer receipt, or selected weekly slot. The method lane is missing, and the literal registry rule blocks the customary dot budget.</p><div class="actions"><span class="btn" aria-disabled="true">No submission file available &nbsp; ⊘</span><a class="text-link" href="preflight-research.html">Understand the blockers →</a></div></div>
<div class="panel"><div class="section-label">WHEN A CANDIDATE EXISTS</div><h2>Required evidence</h2><div class="mini-grid"><div class="mini"><small>Format</small><strong>Saved-byte checks</strong></div><div class="mini"><small>Uniqueness</small><strong>Complete registry</strong></div><div class="mini"><small>Performance</small><strong>Paired holdout win</strong></div><div class="mini"><small>Decision</small><strong>Separate selector</strong></div></div></div></div>
<div class="section-head" id="nine-sites" style="margin-top:42px"><div><div class="section-label">HISTORICAL BASELINES</div><h2>The nine-site scorecard.</h2></div><p>Values below are unverified owner/user reports, not ORGANIZER-CONFIRMED receipts or estimates for a new file.</p></div>
<div class="table-wrap"><table class="score-table"><thead><tr><th>Site</th><th>Historical file · research only</th><th>Reported result</th><th>Estimated score</th><th>Unique vs peers?</th><th>Submit?</th></tr></thead><tbody>''' + rows_html + '''</tbody></table></div>
<p class="caption">GEOMETRY-AUDIT: each “No” cites the largest directional three-pixel overlap among the other eight pinned historical files, not the complete registry. All 72 directional comparisons exceed 70%. Files and hashes: <a href="data/historical.json">manifest</a> · <a href="data/geometry_audit.json">audit</a>. Public GitHub mirrors are not organizer-authenticated; historical score-to-hash receipts were unavailable.</p>
<div class="two-col" style="margin-top:35px"><div class="panel"><div class="section-label">FUTURE SUBMISSION GUIDE</div><h2>Exactly how to submit—when cleared.</h2><ol class="list"><li><strong>Wait for an eligible file.</strong> The automated checks must pass and the separate selector must authorize a slot. No file is eligible today.</li><li><strong>Download the new TIFF</strong> from the approved card, and verify that its SHA-256 matches the saved-byte receipt. Do not use a historical archive.</li><li>Open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition</a>, enroll or sign in, and open its submission flow.</li><li>Select the single-band GeoTIFF, enter its unique name and short note as required, and check the remaining weekly allowance before submitting. The logged-in interface was not accessible during this review.</li><li>Save the organizer receipt with the exact file hash. Select one final submission for both prize rounds; the public leaderboard is not the private score.</li></ol><p>The official rules state three submissions per week, subject to current website limits; this project cannot see the account’s remaining allowance. The rules also require a narrative disclosure of generative-AI use and reproducible code and documentation for finalists.</p><p>Do not submit any file shown in the table above. Official requirements: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format">submission format</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules, §§3.2–3.5</a>.</p></div>
<div class="panel"><div class="section-label">THE PREVIOUS RANGE ERROR</div><h2>Inspect values, not just the extension.</h2><p>Automated diagnostics inspect the saved file for one float32 band, exact grid/CRS/transform, finite in-footprint values, and range [0, 1]. They also distinguish whole-array finiteness from null-outside encoding.</p><p>The official null-outside wording and the reported portal range error can conflict with naive NaN or zero encoding. Local checks do not prove the portal will accept a file; no current candidate has been tested there.</p><a class="text-link" href="https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/scripts/check_format.py">View the format diagnostic →</a></div></div></div></section>'''

research = '''
<section class="page-hero"><div class="wrap"><div class="eyebrow">SCIENCE &amp; SOURCES</div><h1>Reason from the geology.</h1><p>Four prospective mechanisms, a precise account of what the raster evidence can—and cannot—say, and links to the official data.</p></div></section>
<section class="section tight"><div class="wrap research-body"><div class="alert"><span class="alert-icon">!</span><div><strong>PROPOSALS ONLY · NO METHOD LANE ASSIGNED</strong><p>No hypothesis below has been fit or validated in this checkout. Expected impact is qualitative, not a score forecast.</p></div></div>
<div class="panel"><div class="section-label">PHYSICAL HYPOTHESES / QUALITATIVE ORDER</div><h2>Ideas worth a controlled test.</h2><p>All four differ from code in this initially empty checkout; global novelty across sibling sites has not been established.</p>
<h3>01 &nbsp; Paired signed gravity–magnetic profiles <span class="tag green">Medium cost</span></h3><p>Orient cross-sections through gravity, TMI/RTP and detrended terrain; compare signed multiscale changes and offsets to seek a concealed discontinuity. Lithologic contacts, remanence and survey leveling can mimic it. Related edge approaches exist in sibling sites. The provided feature stack is currently absent.</p>
<h3>02 &nbsp; Cross-fan drainage-offset consistency <span class="tag grey">High cost</span></h3><p>Use USGS 3DEP terrain to match multiple channels across a persistent break in slope. A coherent offset may indicate a subdued fault; fan avulsion, stream capture and roads can imitate it. Tile coverage and actual binary access remain unverified.</p>
<h3>03 &nbsp; Depth-differential conductance reversal <span class="tag grey">Medium / high cost</span></h3><p>Compare gradients in USGS MT conductance layers at different depths with gravity margins. Clay, saline fluids and inversion resolution are alternatives. The official source lists files, but their local bytes and suitability for trace-scale mapping remain unverified.</p>
<h3>04 &nbsp; Cross-line residual thermal gradient <span class="tag grey">High cost</span></h3><p>Correct well/spring temperatures for depth and sampling density before testing a residual contrast across independent lineaments. Uneven sampling, lithology and anthropogenic wells are serious confounders. The public source lists a downloadable archive; binary access and full provenance remain unchecked.</p>
<a class="text-link" href="https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/research/2026-10-27-review.md">Read the full scientific review &amp; prerequisites →</a></div>
<div class="panel"><div class="section-label">B2 FORENSICS</div><h2>Why might the historical file have scored well?</h2><p>On hash-checked public mirrors, GEMSDOE32 is exactly GEMSDOE31 after removing 2,545 dots near mapped faults. Under a distance-weighted Tversky metric, such a deletion can help if the reduction in false-positive cost outweighs lost truth coverage. Hidden truth and score-to-file receipts are unavailable, so causation and any improvement beyond the USER-REPORTED 0.2778 remain unknown.</p><p>The competition asks for faults indicative of geothermal resources—not confirmed vents. A lineament, a model probability, and a geothermal discovery are different claims.</p><a class="text-link" href="data/geometry_audit.json">Inspect the independent geometry audit →</a></div>
<div class="panel" id="sources"><div class="section-label">OFFICIAL &amp; TRUSTED SOURCES</div><h2>Follow the evidence.</h2><p>These are source pages reviewed during this session. Availability of a source page does not prove that all binary data or usage rights have been verified locally.</p>
<ul class="source-list"><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"><strong>DrivenData · problem and metric ↗</strong><span>Official targets, distance-weighted Tversky and format.</span></a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf"><strong>NLR · official rules PDF ↗</strong><span>Eligibility, submission and prize process.</span></a></li>
<li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and"><strong>USGS · GeoDAWN release ↗</strong><span>Magnetic and radiometric survey metadata.</span></a></li>
<li><a href="https://www.usgs.gov/3d-elevation-program"><strong>USGS · 3DEP ↗</strong><span>Free topographic data; tile coverage must be checked.</span></a></li>
<li><a href="https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b"><strong>USGS · Great Basin conductance ↗</strong><span>Five modeled depth ranges and downloadable layers.</span></a></li>
<li><a href="https://gdr.openei.org/submissions/1391"><strong>DOE GDR · INGENIOUS ↗</strong><span>Regional datasets, attribution and license information.</span></a></li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution"><strong>DrivenData · reference solution ↗</strong><span>Official starting code and environment.</span></a></li>
<li><a href="https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37"><strong>Shared-tool defect · issue #37 ↗</strong><span>Probabilistic inputs are silently binarized; upstream repair required.</span></a></li></ul></div></div></section>'''

DOCS.mkdir(exist_ok=True)
(DOCS / 'data').mkdir(exist_ok=True)
home_page = shell('Overview', 'home', home)
executive_page = shell('Executive summary', 'executive', executive)
(DOCS / 'preflight.html').write_text(home_page, encoding='utf-8')
(DOCS / 'preflight-executive.html').write_text(executive_page, encoding='utf-8')
(DOCS / 'preflight-research.html').write_text(shell('Research & sources', 'research', research), encoding='utf-8')
# The conventional docs/index.html and docs/executive-summary.html pages are
# generated by build_review_status.py; do not let this legacy preflight builder
# replace those authoritative review pages.
shutil.copyfile(ROOT / 'registry' / 'historical.json', DOCS / 'data' / 'historical.json')
shutil.copyfile(ROOT / 'evidence' / 'geometry_audit.json', DOCS / 'data' / 'geometry_audit.json')
current_run_card = ROOT / 'evidence' / 'run_card.json'
shutil.copyfile(current_run_card, DOCS / 'data' / 'run_card.json')
# This is the latest current-session card. Keep the historical candidate card at
# docs/run-card.json intact for build_review_status.py's forensic evidence page.
shutil.copyfile(current_run_card, DOCS / 'data' / 'latest-run-card.json')
shutil.copyfile(ROOT / 'research' / '2026-10-27-review.md', DOCS / 'data' / 'review.md')
print('Built overview, executive summary and research pages from pinned evidence.')
