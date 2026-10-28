#!/usr/bin/env python3
"""Build safe, clearly historical CSST-BGHF pages from retained evidence.

The older narrative made unsupported claims about portal rejection, uniqueness
and holdout wins. The source evidence and run card remain unchanged for research;
this renderer never authorizes a file or rewrites historical receipts.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs/csst-bghf'
H = html.escape


def page(title: str, body: str) -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{H(title)}</title><link rel="stylesheet" href="../assets/site.css"></head><body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header"><div class="container header-inner"><a class="brand" href="../../index.html"><span class="brand-mark">G</span><span class="brand-name">GEMS Fieldnotes<small>Historical CSST-BGHF</small></span></a>
<nav class="nav" aria-label="Primary"><a href="../../index.html">Overview</a><a href="index.html">Archive</a><a href="executive-summary.html">Submission guide</a><a href="../../research.html">Research</a></nav></div></header>
<main id="main" class="container"><div class="page-hero"><div class="eyebrow">Historical research · not a release</div><h1 class="page-title">{H(title)}</h1></div>
<div class="banner"><span class="banner-icon" aria-hidden="true">!</span><div><strong>DO NOT SUBMIT · DUPLICATE STOP</strong><p>This archive is not a new candidate. Old holdout results are exploratory: the shared instrument has unresolved protocol defects, and no selector approved a slot. <a href="../review-2026-10-28-session.md">Read the current review ↗</a></p></div></div>
{body}
</main><footer class="footer"><div class="container footer-inner"><span>GEMS Fieldnotes · evidence before submission</span><a href="../../sources.html">Sources &amp; limitations</a></div></footer></body></html>\n'''


def build_all() -> None:
    card = json.loads((ROOT / 'evidence/csst_bghf_run_card.json').read_text())
    retained = json.loads((DOCS / 'run-card.json').read_text())
    if card != retained or card['ok_to_submit'] is not False:
        raise ValueError('Historical run card changed or is not negative; review before publishing')
    witness = json.loads((ROOT / 'evidence/csst-bghf-literal-witness-reaudit-20261028-final.json').read_text())
    raster = ROOT / card['submission_file']
    if (hashlib.sha256(raster.read_bytes()).hexdigest() != card['raster_sha256']
            or witness['candidate_sha256'] != card['raster_sha256']
            or witness['duplicate_stop'] is not True):
        raise ValueError('Historical TIFF and witness receipt do not match')
    audit = json.loads((ROOT / 'evidence/historical-reaudit-20261028-session.json').read_text())
    if len(audit['sites']) != 9 or not all(s['duplicate_vs_focus'] for s in audit['sites']):
        raise ValueError('Expected the pinned nine-site negative geometry audit')
    rows = ''.join(
        f"<tr><th scope='row'>{H(s['site'])}</th><td><a href='{H(s['source_url'], quote=True)}'>{H(s['file'])}</a>"
        f"<br><small>Historical source only</small></td><td>{H(s['historical_claim'])} "
        f"<small>USER-REPORTED / UNVERIFIED</small></td><td>{100*s['worst_focus_fraction']:.2f}% "
        f"vs {H(s['worst_focus_comparator'])}; duplicate stop</td><td>DO NOT SUBMIT</td></tr>"
        for s in audit['sites'])
    hold = card['holdout']
    tif = H(Path(card['submission_file']).name, quote=True)
    zip_name = H(Path(card['zip_submission_file']).name, quote=True)
    sha = H(card['raster_sha256'])
    overlap = witness['within_3px_fraction'] * 100
    comparison = f"""<section><h2>Historic file, independently rechecked</h2>
<p><a href="downloads/{tif}" download>Download research-only TIFF</a> · <a href="downloads/{zip_name}" download>Research-only ZIP</a> · <a href="run-card.json">Historical run card</a></p>
<p><code>{tif}</code><br>SHA-256 <code>{sha}</code></p>
<p>The pinned lattice covers <strong>{overlap:.2f}%</strong> of this file's {witness['dots_inside_footprint']:,} dots within 3 pixels, exceeding the literal 70% threshold. This one witness is decisive for a stop, not evidence that the complete registry was checked. <a href="../../evidence/csst-bghf-literal-witness-reaudit-20261028-final.json">Saved-byte witness receipt ↗</a></p>
<p>Local saved bytes are finite and in [0,1] inside the mirrored footprint and match its CRS, shape and transform; the whole array also passes a finite/range diagnostic. Zero outside the footprint does not satisfy the separate conservative null-outside interpretation. The organizer template and portal acceptance are unverified; the reported range error's cause is unknown.</p></section>"""
    historic_holdout = f"""<section><h2>Historical report, not a qualifying win</h2>
<p>Previously reported HOLDOUT-DTI {hold['dti']:.4f}, 95% CI [{hold['ci95'][0]:.6f}, {hold['ci95'][1]:.6f}] ({H(hold['evaluator_version'])}, n={hold['withheld_positives']:,}). Its old paired interval [{hold['paired_delta_ci95'][0]:+.6f}, {hold['paired_delta_ci95'][1]:+.6f}] includes zero. These historical values were not reproduced in this review and cannot qualify a submission because shared fold-buffer and false-positive pooling defects remain open. They are not organizer scores or estimates.</p></section>"""
    table = f"""<section><h2>Nine-site research references</h2><p>Values are owner/user reports, not artifact-linked organizer receipts. Each linked file is historical and must not be resubmitted. Overlap is directional and compares only the pinned focus files.</p>
<div class="table-wrap" role="region" tabindex="0" aria-label="Historical nine-site research comparison"><table><thead><tr><th scope="col">Site</th><th scope="col">Historical file</th><th scope="col">Reported value</th><th scope="col">Strongest focus overlap</th><th scope="col">Action</th></tr></thead><tbody>{rows}</tbody></table></div></section>"""
    index = comparison + historic_holdout + table + '''<section><h2>Why the GEMSDOE32 result was reported as 0.2778</h2><p>That number is unverified. The pinned GEMSDOE32 support is GEMSDOE31 support minus 2,545 catalogue-near dots. Less redundant prediction mass could reduce false positives under the official distance-weighted Tversky metric, but hidden labels are unavailable; causation and performance of a new file are unknown.</p><p><a href="../../research.html">Ranked hypotheses and controls ↗</a> · <a href="../review-2026-10-28-session.md">Current three-pass review ↗</a></p></section>'''
    guide = comparison + '''<section><h2>Future submission checklist</h2><ol><li>Only consider a new candidate after the shared evaluator and registry gates are repaired and the matched holdout establishes a win.</li><li>An independent selector must approve the candidate and check the current weekly cap. No file is approved now.</li><li>Reopen the exact saved TIFF and verify its hash, band, dtype, grid, mask and values against an organizer-authenticated template. Check the outside-footprint convention independently.</li><li>After uploading an approved file, retain the organizer receipt and hash before labeling any score organizer-confirmed.</li></ol><p>Consult the <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official rules</a> and <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a>. A local format diagnostic is not acceptance or authorization.</p></section>'''
    notes = f'''# Historical CSST-BGHF research — DO NOT SUBMIT

This is an archive, not a new release. [{tif}](downloads/{tif}) has SHA-256 `{sha}`.
A single pinned lattice witness covers {overlap:.2f}% of its dots within 3 px, so it is a literal duplicate stop. The historical holdout was not reproduced and the shared instrument has unresolved buffer/pooling defects. Its old numerical values are in [the unchanged run card](run-card.json), not evidence of a qualifying win.

See [the current review](../review-2026-10-28-session.md), [ranked research](../../research.html), and [the literal witness receipt](../../evidence/csst-bghf-literal-witness-reaudit-20261028-final.json). The reason for the reported portal range error and organizer acceptance remain unknown.
'''
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / 'index.html').write_text(page('CSST-BGHF research archive', index), encoding='utf-8')
    (DOCS / 'executive-summary.html').write_text(page('Future submission guide', guide), encoding='utf-8')
    (DOCS / 'research.md').write_text(notes, encoding='utf-8')
    print('Built research-only CSST-BGHF archive pages; no run card or raster was changed.')


if __name__ == '__main__':
    build_all()
