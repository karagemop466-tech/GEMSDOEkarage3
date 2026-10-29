"""Deterministic public correction from saved-byte audit; does not approve uploads."""
import hashlib
import json
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def build():
    audit = json.loads((ROOT / 'evidence/saved-tiffs-literal-20261028.json').read_text())
    rasters = audit['rasters']
    expected = {str(p.relative_to(ROOT)) for p in (ROOT / 'docs').rglob('*.tif')}
    audited = {r['file'] for r in rasters}
    if (len(rasters) < 8 or not audited.issubset(expected)
            or any(hashlib.sha256((ROOT / r['file']).read_bytes()).hexdigest() != r['sha256']
                   or not r['duplicate_stop'] for r in rasters)):
        raise ValueError('Refusing to publish stale or changed saved-byte audit entries')
    unreviewed = sorted(expected - audited)
    for src, dest in [('evidence/saved-tiffs-literal-20261028.json', 'saved-tiffs-literal-20261028.json'), ('evidence/run-card-20261028.json', 'run-card-20261028.json'), ('research/2026-10-28-review.md', 'review-20261028.md')]:
        (ROOT / 'docs/data' / dest).write_bytes((ROOT / src).read_bytes())
    rows = []
    for r in audit['rasters']:
        name = Path(r['file']).name
        rows.append(f'<tr><td><a download href="{escape(r["file"].removeprefix("docs/"))}">{escape(name)}</a><br><small>Archive only · SHA256 {r["sha256"]}</small></td>'
                    f'<td>Not estimable</td><td>{100*r["within_3px_fraction"]:.4f}% · FAIL</td>'
                    f'<td>{"PASS" if r["format_diagnostic"]["all_cell_finite_range"] else "FAIL"}</td><td>DO NOT SUBMIT</td></tr>')
    for rel in unreviewed:
        path = ROOT / rel
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f'<tr><td><code>{escape(path.name)}</code><br><small>Present in repository; not included in the dated saved-byte audit · SHA256 {digest}</small></td>'
                    '<td>Not estimable</td><td>NOT ESTABLISHED · not measured</td><td>Not established</td><td>DO NOT SUBMIT</td></tr>')
    n_tiffs = len(rasters)
    n_unreviewed = len(unreviewed)
    body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Submission decision · GEMS</title><link rel="stylesheet" href="assets/site.css"></head><body>
<main class="wrap"><p><a href="../index.html">Home</a> · <a href="focus9/index.html">Focus-9 executive summary</a> · <a href="preflight-executive.html">Nine-site executive summary</a> · <a href="review-2026-10-29.md">29 Oct review</a></p>
<h1>No submission is authorized</h1><p><strong>2026-10-29 · NEGATIVE · Dated saved-byte audit covers {n_tiffs} TIFFs; {n_unreviewed} newer files are not covered.</strong></p>
<p>The {n_tiffs} files covered by the 28 Oct saved-byte audit fail its literal any-registry overlap rule against the registered 206,895-dot calibration lattice witness. This is a scoped, dated result, not a claim about every file now in the repository. The {n_unreviewed} newer TIFFs below have no complete uniqueness determination here and are also <strong>DO NOT SUBMIT</strong>. No weekly slot or organizer submission was used.</p>
<h2>Repository TIFF inventory — research only</h2><p>Different file hashes do not prove geological uniqueness. For dated audited files, the overlap is measured against the hash-pinned registered lattice, sufficient to reject. Newer TIFFs are listed as not audited rather than implicitly passing or failing the uniqueness measurement. Format diagnostics do not establish organizer acceptance.</p>
<div style="overflow-x:auto"><table><thead><tr><th>Repository artifact (not a live portal submission)</th><th>Leaderboard estimate</th><th>Literal 3-px uniqueness</th><th>Format status</th><th>Decision</th></tr></thead><tbody>''' + '\n'.join(rows) + '''</tbody></table></div>
<h2>Best historical result is not a new candidate</h2><p>The largest owner-reported value in the focus list is GEMSDOE32's 0.2778 USER-REPORTED / UNVERIFIED without a hash-linked organizer receipt. Its geometry is a pruned subset of GEMSDOE31; that supports an emission-efficiency hypothesis, not causal proof or a forecast of improvement.</p>
<h2>Archived H-GEO-CONDUIT candidate — blocked</h2><p>The retained research TIFF has 35,615 positive pixels. Its earlier card contains <strong>HOLDOUT-DTI (not independently reproduced; run-card claim) 0.423855 (95% CI [0.405253, 0.442747]), evaluator <code>GEMSDOE32-HOLDOUT-v3-visible-gated</code>, 22,232 withheld positives</strong>. This is not organizer-confirmed and not a leaderboard estimate. The lattice-witness budget bound requires at least 81.33% of any 35,615 distinct in-footprint dots to be within 3 pixels, above the literal 70% threshold. Full surface/final registry checks and the required holdout protocol are not established. <a href="data/candidate-review-20261029.json">Negative review card</a> · <a href="review-2026-10-29.md">Detailed review</a>. No TIFF download is authorized.</p>
<p><a href="focus9/index.html">Nine per-site executive summaries</a> · <a href="comparison.html">Interactive nine-site executive summaries</a> · <a href="preflight-executive.html">Compare all nine requested sites, filenames, historical claims and duplicate decisions</a>.</p>
<h2>How a future valid submission will be released</h2><ol><li>Use one assigned lane, the canonical cache, evaluator and writer. Test features alone for leakage and freeze buffered whole-segment visible-only folds.</li><li>Beat the frozen same-evaluator best on paired spatial HOLDOUT-DTI with a 95% CI. Report evaluator version and withheld positives. Never convert this into a leaderboard estimate.</li><li>Check both surface and final support rank correlation and literal directional overlap against every registry raster, with no calibration/density exceptions.</li><li>Validate exact saved bytes: single band, finite footprint, [0,1], CRS/shape/transform; diagnose outside-footprint encoding separately. Publish SHA256, unique name and note of at most 140 characters.</li><li>A separate selector checks the live weekly cap and eligibility. Only after authorization should the single TIFF or ZIP containing one TIFF be uploaded to the organizer's form.</li></ol>
<p>No human visual inspection is substituted for these automated checks. Missing evidence is a failed gate, not permission to upload.</p>
<p><a href="data/saved-tiffs-literal-20261028.json">Saved-byte audit JSON</a> · <a href="data/latest-run.json">Current run card</a> · <a href="../research/2026-10-28-literal-review.md">Research slate, review passes and limitations</a> · <a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official task</a></p></main></body></html>'''
    (ROOT / 'docs/release-review.html').write_text(body + '\n')
    (ROOT / 'docs/comparison.html').write_text("""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nine-site historical comparison</title><link rel="stylesheet" href="assets/site.css"><script defer src="dashboard.js"></script></head><body><main class="wrap"><h1>Nine-site executive comparison</h1><p><strong>DO NOT SUBMIT: no new candidate approved.</strong> Historical owner values are unverified, not organizer receipts. No leaderboard estimate is available.</p><p><a href="release-review.html">Current automated release review</a> · <a href="preflight-executive.html">Pinned nine-site audit</a></p><button disabled>No submission available</button><p id="updated" role="status">Loading historical evidence; no submission authorized.</p><div style="overflow-x:auto"><table><thead><tr><th>Site / owner claim</th><th>Historical artifact</th><th>Leaderboard estimate</th><th>Local format</th><th>Uniqueness</th><th>Submission</th></tr></thead><tbody id="rows"></tbody></table></div><section id="site-details"></section></main></body></html>
""")
    for rel in ('docs/crsb-gub/index.html', 'docs/crsb-gub/executive-summary.html'):
        p = ROOT / rel
        text = p.read_text()
        text = re.sub(r'<!-- RELEASE-REVIEW -->.*?<!-- /RELEASE-REVIEW -->\s*', '', text, flags=re.S)
        link = '../release-review.html' if 'crsb-gub/' in rel else 'release-review.html'
        prefix = '../' if 'crsb-gub/' in rel else ''
        banner = f'<!-- RELEASE-REVIEW --><aside role="note" style="background:#fff1f2;color:#881337;padding:24px;border:3px solid #be123c;font:18px/1.5 sans-serif"><strong>2026-10-28: this CRSB-GUB page is historical — DO NOT SUBMIT its file.</strong> The current decision lives at <a href="{prefix}index.html">the home decision page</a> / <a href="{prefix}k3c/index.html">Lane H-K3C executive summary</a>. Earlier lanes: <strong>H-K3B-1 CSST-BGHF</strong> (<a href="{prefix}csst-bghf/index.html">dashboard</a>, negative) and <strong>K3-CCL</strong> (<a href="{prefix}ccl/index.html">summary</a>, duplicate stop). <a href="{link}">Saved-byte release review</a> · <a href="{prefix}preflight.html">Preflight evidence</a>.</aside><!-- /RELEASE-REVIEW -->'
        text = text.replace('<!-- ARCHIVED-BODY --><details><summary>Superseded narrative — not current submission instructions</summary>', '').replace('</details><!-- /ARCHIVED-BODY -->', '')
        text = re.sub(r'(<body\b[^>]*>)\s*', r'\1\n', text, count=1, flags=re.I)
        text = re.sub(r'\s*</body>', '\n</body>', text, flags=re.I)
        if 'PROMOTE — OK TO DOWNLOAD' in text:
            text = text.replace('</body>', '</details><!-- /ARCHIVED-BODY -->\n</body>')
            banner += '<!-- ARCHIVED-BODY --><details><summary>Superseded narrative — not current submission instructions</summary>'
        text = re.sub(r'(<body\b[^>]*>)', lambda m: m[1] + '\n' + banner, text, count=1, flags=re.I)
        p.write_text(text)


if __name__ == '__main__':
    build()
