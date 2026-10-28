"""Deterministic public correction from saved-byte audit; does not approve uploads."""
import json
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def build():
    audit = json.loads((ROOT / 'evidence/release-audit-20261028.json').read_text())
    for src, dest in [('evidence/release-audit-20261028.json', 'release-audit-20261028.json'), ('evidence/run-card-20261028.json', 'run-card-20261028.json'), ('research/2026-10-28-review.md', 'review-20261028.md')]:
        (ROOT / 'docs/data' / dest).write_bytes((ROOT / src).read_bytes())
    rows = []
    for r in audit['rows']:
        name = Path(r['file']).name
        rows.append(f'<tr><td><a download href="downloads/{escape(name)}">{escape(name)}</a><br><small>Archive only · SHA256 {r["sha256"]}</small></td>'
                    f'<td>Not estimable</td><td>{100*r["within_3px_fraction"]:.4f}% · FAIL</td>'
                    f'<td>{"PASS" if r["validator"]["whole_array_finite_range_pass"] else "FAIL"}</td><td>DO NOT SUBMIT</td></tr>')
    body = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Submission decision · GEMS</title><link rel="stylesheet" href="assets/site.css"></head><body>
<main class="wrap"><p><a href="../index.html">Home</a> · <a href="preflight-executive.html">Nine-site executive summary</a></p>
<h1>No submission is authorized</h1><p><strong>2026-10-28 · NEGATIVE · Automated saved-byte review</strong></p>
<p>Earlier PROMOTE / OK TO SUBMIT claims on archived pages are withdrawn. All five saved TIFFs fail your literal any-registry overlap rule. No new TIFF, performance estimate, weekly selection or organizer submission was made.</p>
<h2>Existing downloads — research only</h2><p>Different file hashes do not prove geological uniqueness. The overlap below is measured against one hash-pinned registered lattice, sufficient to reject but not a complete registry scan. Format PASS is only a local all-finite [0,1] diagnostic against a mirrored template; it does not prove portal acceptance.</p>
<div style="overflow-x:auto"><table><thead><tr><th>Archive file (not a new submission)</th><th>Leaderboard estimate</th><th>Dots within 3 px of witness</th><th>Whole-array finite/range</th><th>Decision</th></tr></thead><tbody>''' + '\n'.join(rows) + '''</tbody></table></div>
<h2>Best historical result is not a new candidate</h2><p>The largest owner-reported value in the focus list is GEMSDOE32's 0.2778. It is USER-REPORTED / UNVERIFIED without a hash-linked organizer receipt. Its geometry is a pruned subset of GEMSDOE31; that supports an emission-efficiency hypothesis, not causal proof or a forecast of improvement.</p>
<p><a href="comparison.html">Interactive nine-site executive summaries</a> · <a href="preflight-executive.html">Compare all nine requested sites, filenames, historical claims and duplicate decisions</a>.</p>
<h2>How a future valid submission will be released</h2><ol><li>Use one assigned lane, the canonical cache, evaluator and writer. Test features alone for leakage and freeze buffered whole-segment visible-only folds.</li><li>Beat the frozen same-evaluator best on paired spatial HOLDOUT-DTI with a 95% CI. Report evaluator version and withheld positives. Never convert this into a leaderboard estimate.</li><li>Check surface rank correlation and final directional dot overlap against every registry raster, with no calibration/density exceptions.</li><li>Validate exact saved bytes: single band, finite footprint, [0,1], CRS/shape/transform; diagnose outside-footprint encoding separately. Publish SHA256, unique name and note of at most 140 characters.</li><li>A separate selector checks the live weekly cap and eligibility. Only after authorization should the single TIFF or ZIP containing one TIFF be uploaded to the organizer's form.</li></ol>
<p>No human visual inspection is substituted for these automated checks. Missing evidence is a failed gate, not permission to upload.</p>
<p><a href="data/release-audit-20261028.json">Saved-byte audit JSON</a> · <a href="data/run-card-20261028.json">Current run card</a> · <a href="data/review-20261028.md">Research slate, review passes and limitations</a> · <a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official task</a></p></main></body></html>'''
    (ROOT / 'docs/release-review.html').write_text(body + '\n')
    (ROOT / 'docs/comparison.html').write_text("""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nine-site historical comparison</title><link rel="stylesheet" href="assets/site.css"><script defer src="dashboard.js"></script></head><body><main class="wrap"><h1>Nine-site executive comparison</h1><p><strong>DO NOT SUBMIT: no new candidate approved.</strong> Historical owner values are unverified, not organizer receipts. No leaderboard estimate is available.</p><p><a href="release-review.html">Current automated release review</a> · <a href="preflight-executive.html">Pinned nine-site audit</a></p><button disabled>No submission available</button><p id="updated" role="status">Loading historical evidence; no submission authorized.</p><div style="overflow-x:auto"><table><thead><tr><th>Site / owner claim</th><th>Historical artifact</th><th>Leaderboard estimate</th><th>Local format</th><th>Uniqueness</th><th>Submission</th></tr></thead><tbody id="rows"></tbody></table></div><section id="site-details"></section></main></body></html>
""")
    for rel in ('docs/index.html' , 'docs/executive-summary.html', 'docs/crsb-gub/index.html', 'docs/crsb-gub/executive-summary.html'):
        p = ROOT / rel
        text = p.read_text()
        text = re.sub(r'<!-- RELEASE-REVIEW -->.*?<!-- /RELEASE-REVIEW -->\s*', '', text, flags=re.S)
        link = '../release-review.html' if 'crsb-gub/' in rel else 'release-review.html'
        banner = f'<!-- RELEASE-REVIEW --><aside role="note" style="background:#fff1f2;color:#881337;padding:24px;border:3px solid #be123c;font:18px/1.5 sans-serif"><strong>2026-10-28: DO NOT SUBMIT. Earlier approval below is withdrawn.</strong> All saved candidates fail the literal registry overlap gate. <a href="{link}">Current automated release review</a> · <a href="{"../" if "crsb-gub/" in rel else ""}preflight.html">Preflight evidence</a>. This page is historical, not authorization. Portal acceptance and outside-null wording remain unresolved.</aside><!-- /RELEASE-REVIEW -->'
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
