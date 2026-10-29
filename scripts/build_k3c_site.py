#!/usr/bin/env python3
"""Render the current negative decision and the superseded K3C research archive.

The historical card is preserved in evidence/; this publisher recomputes the
local screen and binds the public correction to independently re-read TIFF
bytes. It cannot select a slot or authorize an archive file.
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from promotion_gate import assess  # noqa: E402

H = html.escape


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shell(title, body, depth=0):
    pre = '../' * depth
    feed_script = '<script defer src="assets/site.js"></script>' if depth == 0 else ''
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{H(title)}</title><link rel="stylesheet" href="{pre}assets/site.css">{feed_script}</head>
<body><main id="main" class="wrap" style="padding:28px 0 60px">
<p><a href="{pre}index.html">Decision home</a> · <a href="{pre}hk3d/index.html">Session 5 H-K3D</a> · <a href="{pre}hk3d/how-to-submit.html">H-K3D submission guide</a> · <a href="{pre}k3c/index.html">K3C archive</a> · <a href="{pre}k3c/how-to-submit.html">Submission guide</a> · <a href="{pre}data/latest-run.json">Latest JSON card</a> · <a href="{pre}data/current-run.json">Parallel preflight card</a></p>
{body}<p><small>USER-REPORTED values have no artifact-linked organizer receipt here. Historical HOLDOUT-DTI values are cited, not reproduced, and are not leaderboard scores. Nothing on this page selects a weekly slot.</small></p>
</main></body></html>\n'''


def _archive():
    original = json.loads((ROOT / 'evidence/k3c_run_card.json').read_text())
    report = json.loads((ROOT / 'evidence/saved-tiffs-literal-20261029.json').read_text())
    rasters = report['rasters']
    expected = {str(p.relative_to(ROOT)) for p in (ROOT / 'docs').rglob('*.tif')}
    if (len(rasters) != len(expected) or len(rasters) < 8 or {r['file'] for r in rasters} != expected
            or any(sha256(ROOT / r['file']) != r['sha256'] or not r['duplicate_stop'] for r in rasters)):
        raise ValueError('Saved-byte audit is stale or does not reject every retained TIFF')
    matched = [r for r in rasters if r['file'] == original['submission_file']]
    if len(matched) != 1:
        raise ValueError('K3C is absent from the independent saved-byte audit')
    row = matched[0]
    tif = ROOT / row['file']
    if (sha256(tif) != row['sha256'] or row['sha256'] != original['raster_sha256']
            or not row['duplicate_stop'] or row['within_3px_fraction'] <= .70):
        raise ValueError('K3C audit is stale or does not prove a literal duplicate stop')
    return original, row, report


def root_decision_html():
    _, _, report = _archive()  # Never render the retained-TIFF claim from stale saved-byte evidence.
    n_tiffs = len(report['rasters'])
    aside = ('<aside style="padding:16px;background:#fff1f2;color:#881337"><strong>OK TO SUBMIT? NO — DO NOT SUBMIT.</strong> '
             f'Session 5 Lane H-K3D (TGSF-BVCD) and all {n_tiffs} retained research TIFFs fail the literal registry-overlap rule against the registered 206,895-dot lattice witness; '
             'the former K3C PROMOTE verdict is withdrawn. Format checks cannot approve a file or guarantee portal acceptance. '
             '<a href="docs/hk3d/index.html">Session 5 H-K3D executive summary</a> · '
             '<a href="docs/hk3d/how-to-submit.html">Step-by-step guide</a> · '
             '<a href="docs/release-review.html">Saved-byte audit</a> · <a href="docs/k3c/index.html">K3C research archive</a> · '
             '<a href="docs/data/latest-run.json">Current run card</a></aside>')
    card = ('<div class="release-card" aria-label="Current submission decision">\n'
            '      <div class="card-top"><span class="card-kicker">CURRENT RELEASE DECISION</span><span class="pill hold">NOT APPROVED</span></div>\n'
            '      <h2>No file cleared<br>for live submission.</h2>\n'
            '      <p>Session 5 H-K3D (99.3547% vs lattice witness; 24c HR 0.0942 vs 0.1008; SGMC-cal 0.0682 vs 0.0641) and all older TIFFs are stopped by <code>promotion_gate.py</code>. No weekly slot used.</p>\n'
            '      <button class="disabled-button" disabled aria-describedby="download-explanation">Download submission .tif <span aria-hidden="true">↓</span></button>\n'
            '      <div class="card-foot"><span id="download-explanation">Live slot locked · do not submit · see <a href="docs/hk3d/index.html" style="color:#d6e8d7">H-K3D audit</a></span><a href="docs/data/latest-run.json" style="color:#d6e8d7">Run card ↗</a></div>\n'
            '    </div>')
    return aside, card


def apply_root_decision(text):
    aside, card = root_decision_html()
    text, n1 = re.subn(r'<aside style="padding:16px;background:#(?:fff1f2|ecfdf5)[^"]*">.*?</aside>', lambda _: aside, text, count=1, flags=re.S)
    text, n2 = re.subn(r'<div class="release-card" aria-label="Current submission decision">.*?</div>\n  </section>', lambda _: card + '\n  </section>', text, count=1, flags=re.S)
    if (n1, n2) != (1, 1):
        raise ValueError('Root landing-page decision markers missing')
    return text


def apply_guide_decision(text):
    aside, _ = root_decision_html()
    text, n1 = re.subn(r'<aside style="padding:16px;background:#(?:fff1f2|ecfdf5)[^"]*">.*?</aside>', lambda _: aside, text, count=1, flags=re.S)
    banner = ('<div class="banner"><span class="banner-icon" aria-hidden="true">!</span><div><strong>NOT OK TO SUBMIT · No new TIFF is approved</strong>'
              '<p>The K3C archive and the other retained TIFFs fail the literal duplicate rule. Research links below are not new submissions; no leaderboard estimate or slot decision exists.</p></div></div>')
    text, n2 = re.subn(r'<div class="banner"><span class="banner-icon" aria-hidden="true">!</span><div><strong>NOT OK TO SUBMIT · No new TIFF is approved or available</strong>.*?</div></div>', lambda _: banner, text, count=1, flags=re.S)
    if (n1, n2) != (1, 1):
        raise ValueError('Root submission-guide decision markers missing')
    return text


def build():
    original, row, report = _archive()
    card = copy.deepcopy(original)
    card['historical_verdict'] = card['verdict']
    card['historical_promotion_gate'] = card['promotion_gate']
    card['validator']['dtype_float32'] = row['format_diagnostic']['checks']['float32']
    card['validator']['outside_null_or_nan'] = row['format_diagnostic']['outside_null_or_nan']
    card['reassessment'] = {
        'checked_utc': report['checked_utc'],
        'status': 'SUPERSEDED: historical promote withdrawn; literal duplicate stop and conservative outside-null failure.',
        'evidence': 'docs/data/saved-tiffs-literal-20261029.json',
        'witness_sha256': report['witness']['sha256'],
        'measured_witness_overlap_fraction': row['within_3px_fraction'],
        'full_registry_checked_in_this_reassessment': False,
        'scientific_holdout_reproduced_in_this_reassessment': False,
        'organizer_acceptance': 'unknown',
    }
    card['verdict'] = 'negative'
    card['ok_to_submit'] = False
    card['promotion_gate'] = assess(card)
    gate = assess(card)
    if gate['verdict'] != 'negative':
        raise ValueError('Historical K3C archive must not be promoted')
    (ROOT / 'docs/k3c/run-card.json').write_text(json.dumps(card, indent=2, allow_nan=False) + '\n')
    decision = {**gate, 'card': 'docs/k3c/run-card.json', 'raster_sha256': card['raster_sha256'],
                'status': 'historical K3C reassessment, not the new-run card',
                'current_run_card': 'docs/data/latest-run.json',
                'parallel_preflight_card': 'docs/data/current-run.json'}
    (ROOT / 'docs/current-gate-decision.json').write_text(json.dumps(decision, indent=2, allow_nan=False) + '\n')
    (ROOT / 'docs/data/saved-tiffs-literal-20261029.json').write_bytes((ROOT / 'evidence/saved-tiffs-literal-20261029.json').read_bytes())
    sites_path = ROOT / 'docs/sites.json'
    sites = json.loads(sites_path.read_text())
    sites['promoted_candidate'] = None
    sites['promoted_candidate_sha256'] = None
    sites['promoted_candidate_card'] = None
    sites_path.write_text(json.dumps(sites, indent=2, allow_nan=False) + '\n')

    file = H(original['submission_name']); sha = H(original['raster_sha256'])
    overlap = f"{100 * row['within_3px_fraction']:.4f}%"
    tif_rel = H(original['submission_file'].removeprefix('docs/k3c/'))
    hold = original['holdout']; ci = hold['ci95']; delta = hold['paired_delta_ci95']
    common = f'''<div class="banner"><span class="banner-icon" aria-hidden="true">!</span><div><strong>OK TO SUBMIT? NO — DO NOT SUBMIT.</strong>
<p>The previous K3C PROMOTE recommendation is withdrawn. No new TIFF or slot was generated in this audit.</p></div></div>
<p>K3C's saved dots overlap the registered lattice by <strong>{overlap}</strong> (limit 70%; 3-pixel radius). The historical card also reports a worst literal overlap of 100% against its broader set. One witness is enough to stop; neither statistic proves geological identity.</p>
<p><strong>Format:</strong> independently read bytes have one float32 band, EPSG:32611, 3730 × 3292, the mirrored transform and finite values in [0,1]. They have no null mask outside the mirrored footprint; our conservative outside-null check fails. These are local checks, not a DrivenData receipt or proof the old portal error cannot occur.</p>'''
    archive = common + f'''<h1>K3C · superseded research archive</h1>
<p>Historical file: <code>{file}</code><br>SHA-256 <code>{sha}</code><br><a href="{tif_rel}" download>Download historical TIFF for research only — DO NOT SUBMIT</a></p>
<h2>Scientific record, not re-run here</h2><p>The prior card reports <strong>HOLDOUT-DTI {hold['dti']:.6f}</strong> (95% CI [{ci[0]:.6f}, {ci[1]:.6f}], evaluator <code>{H(hold['evaluator_version'])}</code>, {hold['withheld_positives']:,} withheld-positive occurrences). The same-card champion-rule comparator is {hold['champion_02778_same_evaluator_dti']:.6f}; paired delta CI [{delta[0]:+.6f}, {delta[1]:+.6f}]. This was not reproduced here and does not establish a compliant buffered whole-segment split, a win against the current same-protocol best, an organizer score or an estimate.</p>
<p>The user-reported 0.2778 for GEMSDOE32 has no artifact-linked organizer receipt in this checkout. Its dot set is a near-catalogue-pruned subset of GEMSDOE31; reduced redundant prediction mass is plausible, but hidden labels and causality are unknown.</p>
<p><a href="run-card.json">Corrected historical card</a> · <a href="../data/saved-tiffs-literal-20261029.json">Independent saved-byte audit</a> · <a href="../../executive-summary.html#site-details">Nine-site file table</a> · <a href="../../research.html">Hypotheses</a></p>'''
    (ROOT / 'docs/k3c/index.html').write_text(shell('K3C archive · do not submit', archive, 1))
    guide = common + f'''<h1>Submission guide · not yet actionable</h1><p><strong>Do not upload <code>{file}</code></strong> (SHA-256 <code>{sha}</code>) or any other retained TIFF.</p>
<ol><li>Obtain an explicit single-method assignment. Resolve and pin the shared-template issues; restore authenticated inputs and a complete registry.</li>
<li>Test features individually for leakage, recompute catalogue-derived features from visible faults only, and validate whole buffered segments. Use the official 300 m triangular DTI and a paired CI against the current same-protocol best.</li>
<li>Before placement and again on final dots, require absolute rank correlation at most 0.90 and literal directional overlap at most 70% against every registry raster. Missing evidence stops the run.</li>
<li>Validate exact saved bytes, including internal masks, range and matching grid; publish the hash, unique name and a note of at most 140 characters. Local validation cannot guarantee portal acceptance.</li>
<li>Only after an independent selector checks eligibility and current quota, sign in at <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData GEMS</a>, upload the selected single TIFF or permitted single-TIFF ZIP, and retain the artifact-linked receipt. Include the required AI disclosure. No slot is selected now.</li></ol>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official format and metric</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules</a> · <a href="../../executive-summary.html">Full nine-site guide</a></p>'''
    (ROOT / 'docs/k3c/how-to-submit.html').write_text(shell('Submission guide · do not submit', guide, 1))
    decision_text = f'''<h1>Current submission decision</h1>{common}
<p><strong>Session 5 Lane H-K3D (TGSF-BVCD) negative run:</strong> <a href="hk3d/index.html">Executive summary &amp; 9-site table</a> · <a href="hk3d/how-to-submit.html">Step-by-step guide</a> · <a href="hk3d/run-card.json">H-K3D run card JSON</a> (99.3547% vs lattice witness; DO NOT SUBMIT).</p>
<p><strong>Latest negative card:</strong> <a href="data/latest-run.json">JSON</a> · <a href="review-2026-10-28-session.md">Session review</a> · <a href="../research/2026-10-28-literal-review.md">Parallel review</a>. Historical K3C SHA-256 <code>{sha}</code>.</p>
<p><a href="../executive-summary.html#site-details">Compare the nine historical files</a> · <a href="release-review.html">Nine-file exact-byte audit</a> · <a href="k3c/how-to-submit.html">How to submit when eligible</a></p>
<h2>Source watch</h2><p id="public-score">Unavailable</p><p id="public-score-detail">Public leaderboard snapshot; check the official page for current data.</p><p id="watch-detail">Source metadata not checked yet.</p><p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official live leaderboard</a>; a public board value is not a score for this file.</p>
<p>Release screen: <code>scripts/promotion_gate.py</code>. It cannot allocate a slot or establish the truth of unverified evidence.</p>'''
    (ROOT / 'docs/index.html').write_text(shell('Current decision · GEMS', decision_text))
    summary = f'''<h1>Executive submission decision</h1>{common}<p><strong>DO NOT SUBMIT</strong> Session 5 H-K3D (<code>docs/hk3d/run-card.json</code>, <code>ok_to_submit = False</code>) or historical K3C <code>{file}</code>; SHA-256 <code>{sha}</code>.</p>
<p>The pinned nine-file comparison contains no approved new submission or defensible leaderboard estimate. The historical best in the focus list is 0.2778 USER-REPORTED / UNVERIFIED for GEMSDOE32.</p>
<p><a href="hk3d/index.html">Session 5 H-K3D executive summary</a> · <a href="hk3d/how-to-submit.html">H-K3D step-by-step guide</a> · <a href="../executive-summary.html">Full nine-site table and conditional step-by-step guide</a> · <a href="k3c/index.html">K3C research archive</a> · <a href="data/latest-run.json">Latest run card</a></p>'''
    (ROOT / 'docs/executive-summary.html').write_text(shell('Executive summary · GEMS', summary))
    # Build root pages from their templates after the negative public card exists.
    import build_site
    for path, text in build_site.render().items():
        path.write_text(text)
    print('Published negative decision; K3C and all older files are research-only.')


if __name__ == '__main__':
    build()
