"""Publish the literal duplicate-stop decision; never create a submission."""
import hashlib
import html
import json
from pathlib import Path
from promotion_gate import assess

ROOT = Path(__file__).resolve().parents[1]

def main():
    card = json.loads((ROOT / 'docs/run-card.json').read_text())
    decision = assess(card)
    if decision['verdict'] != 'negative' or card.get('ok_to_submit') is not False:
        raise ValueError('This duplicate-stop page requires a negative card')
    tif = ROOT / card['submission_file']
    if hashlib.sha256(tif.read_bytes()).hexdigest() != card['raster_sha256']:
        raise ValueError('Saved raster hash mismatch')
    historical = json.loads((ROOT / 'registry/historical.json').read_text())['historical']
    rows = ''.join('<tr><td>{site}</td><td><code>{file}</code></td><td>{score}<br>USER-REPORTED / UNVERIFIED</td><td>Unavailable</td><td>No — historical lineage overlap</td><td>DO NOT SUBMIT</td></tr>'.format(site=html.escape(r['site']),file=html.escape(r['historical_file']),score=html.escape(str(r['quoted_owner_claim']))) for r in historical)
    body = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GEMS — submission blocked by duplicate gate</title><link rel="stylesheet" href="assets/site.css"></head><body><main class="wrap">
<h1>Submission blocked: duplicate-stop</h1><p><strong>DO NOT SUBMIT the existing SMGC TIFF. No new submission is cleared.</strong> Review date: 2026-10-28.</p>
<p>The former “OK TO SUBMIT” decision is retracted. Its own saved evidence records 99.6866% of dots within 3 px of the registered calibration lattice, above the literal 70% limit. Excluding dense rasters was not authorized. Different bytes do not establish a new method.</p>
<p><a href="preflight-executive.html">Nine-site detailed executive summary and sources</a> · <a href="preflight.html">Historical forensic review</a> · <a href="review-2026-10-28.md">Review, hypotheses and next steps</a> · <a href="run-card.json">Candidate evidence card</a> · <a href="current-gate-decision.json">Automated decision</a></p>
<p><a href="../research/2026-10-28-review.md">Independent saved-byte follow-up and ranked hypotheses</a> · <a href="../evidence/retained-submissions-audit-20261028.json">Five-TIFF literal overlap audit</a> · <a href="review-run-card.json">Follow-up run card</a></p><h2>Current candidate — retained for research only</h2><p><a href="{tif}" download>Download existing TIFF — NOT CLEARED FOR SUBMISSION</a><br><code>{sha}</code></p>
<p>Saved HOLDOUT-DTI (not reproduced in this review): GEMSDOE32-HIDE-RECOVER-v3.0, 22,232 withheld positives, 0.107297, 95% CI [0.093004, 0.120923]. This is not an organizer score or a leaderboard prediction. The cached feature stack is absent locally; the follow-up restored the hash-pinned mirrored grid, labels and historical rasters, not organizer-authenticated data. No new experiments or competition slots used.</p>
<h2>Nine-site decision table</h2><p>These are the highest results in the supplied historical snapshot, not a live leaderboard. Exact archive links and geometry are in the detailed summary. No organizer receipt authenticates these reported scores.</p><div style="overflow:auto"><table><thead><tr><th>Site</th><th>Historical filename (research only)</th><th>Reported historical result</th><th>Estimated hidden score</th><th>Unique under protocol?</th><th>Decision</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>How submission works — only after all gates and selector approval</h2><ol><li>Generate a genuinely new lane surface; check the complete registry before placement and after emission. Stop at any duplicate.</li><li>Run feature-only leakage canaries and buffered whole-segment visible-only holdout; beat the frozen incumbent using the same evaluator and paired spatial confidence interval.</li><li>Validate saved single-band TIFF bytes: all finite values in [0,1], exact sample CRS, shape and transform. Do not use a NaN companion on the portal. Legacy outside-null wording is a format irregularity, not permission to upload nonfinite values.</li><li>The independent selector must check the actual submission page weekly cap and authorize the slot. This project has not selected a slot.</li><li>On DrivenData, select the cleared TIFF in “New submission”, paste its unique name and note (at most 140 characters), and preserve the resulting receipt with file hash.</li></ol>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem and format</a> · <a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference code</a>. Official web pages and Dropbox are outside this runtime's network allowlist; their current contents were not reverified here.</p></main></body></html>'''
    output = body.format(tif=html.escape(card['submission_file'].removeprefix('docs/')),sha=card['raster_sha256'],rows=rows)
    for name in ('index.html','executive-summary.html'):
        (ROOT/'docs'/name).write_text(output)
    (ROOT/'docs/current-gate-decision.json').write_text(json.dumps(decision,indent=2)+'\n')

if __name__ == '__main__':
    main()
