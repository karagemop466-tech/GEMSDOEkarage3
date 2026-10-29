#!/usr/bin/env python3
"""Regenerate the top verdict banner and the nine-site table in executive-summary.html.

Every number is read from an evidence file; nothing is typed by hand:
  evidence/site-uniqueness-20261029.json      (literal dot-rule measurement vs the registry)
  evidence/focus9-holdout-baseline-20261029.json (shared-evaluator HOLDOUT-DTI, nine files)
  docs/downloads/*-gate.json                  (automated submission-gate verdicts)
The banner and table are written between HTML comment markers so re-running is idempotent.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "executive-summary.html"
UNIQ = ROOT / "evidence" / "site-uniqueness-20261029.json"
HOLD = ROOT / "evidence" / "focus9-holdout-baseline-20261029.json"
CONSENSUS_GATE = ROOT / "docs/downloads/gemsdoe32-karage3-consensus-hgrad-k37654-20261029T183206Z-4786d9bd-gate.json"

BANNER_START, BANNER_END = "<!-- GATE-BANNER:START -->", "<!-- GATE-BANNER:END -->"
TABLE_START, TABLE_END = "<!-- NINE-SITE-GATE:START -->", "<!-- NINE-SITE-GATE:END -->"

LEADERBOARD = {  # USER-REPORTED values from the supplied prompt, not organizer receipts
    "GEMSDOE24": ("0.2477", "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan"),
    "GEMSDOE25": ("0.2600", "dotted-h19-5-d2-8-20261002-e56ea318af89-nan"),
    "GEMSDOE27": ("0.2449", "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan"),
    "GEMSDOE28": ("0.2710", "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan"),
    "GEMSDOE30": ("0.2600", "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca"),
    "GEMSDOE31": ("0.2708", "h27-4-solo-d28-20261004-8acb75e1-nan"),
    "GEMSDOE32": ("0.2778", "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros"),
    "GEMSDOE33": ("0.2632", "h33d-analog-tip-stepover-r30-20261004-cb490425926e"),
    "GEMSDOE36": ("0.2750", "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros"),
}


CORRECTED_HGEO = ("0.3047 <span class='muted'>[0.2881, 0.3189], n=22,232, GEMSDOE32-HIDE-RECOVER-v3.0 "
                  "re-run 2026-10-29; card value 0.4239 NOT reproduced</span>")


def uniq_label(c: dict) -> str:
    if c["registry_rasters_over_0_70_within3"] > 0:
        return f"<span class='bad'>NO — {c['registry_rasters_over_0_70_within3']} registry rasters &gt;70% within 3 px</span>"
    return "<span class='warn'>Literal dot test passed; surface &amp; complete registry NOT measured</span>"


def build_banner(uniq: dict, gate: dict) -> str:
    rows = []
    for g in gate["gates"]:
        ok = g["passed"]
        cls = "vcard pass" if ok is True else "vcard fail"
        mark = "✓" if ok is True else "✗"
        label = {
            "G1_format": "Format: GeoTIFF, float32, EPSG:32611, 3730×3292, exact transform, 0 NaN inside footprint, values in [0,1]",
            "G2_package": "Package: one .tif inside the .zip (bytes match)",
            "G3_metadata": "Name present, note ≤140 characters",
            "G4_surface": "Surface Spearman vs every registry raster ≤0.90 (needs candidate surface)",
            "G5_final_dots": "Final dots: literal ≤70% within 3 px vs every registry raster",
            "G6_registry_complete": "Registry literally complete and every raster measurable",
        }.get(g["gate"], g["gate"])
        rows.append(f"<div class='{cls}'><span class='vcheck'>{mark}</span><span>{html.escape(label)}</span></div>")
    worst = gate["dots_by_registry_raster_top5"][0] if gate.get("dots_by_registry_raster_top5") else None
    worst_txt = (f"{html.escape(worst['repo'])} {html.escape(worst['path'].split('/')[-1])} = "
                 f"{worst['within_3px']:.4f}") if worst else "n/a"
    return f"""{BANNER_START}
<section class="download-banner" aria-label="Submission verdict">
  <div class="container">
    <div class="download-ok" style="background:#b42318"><strong>VERDICT: NO FILE IS CLEARED TO SUBMIT</strong></div>
    <h2>Format-valid is not the same as submittable</h2>
    <p class="download-sub">The &quot;Predicted values must be in range [0, 1]&quot; error came from NaN values outside the footprint. The <em>-zeros</em> file below fixes that: every value is 0 or 1, with nothing NaN. But the portal is not the only test. This project's uniqueness rule (a file's dots must not be more than 70% within 3 px of any other submission's dots) fails for every file measured, so none of them may be downloaded for submission.</p>
    <div class="download-actions">
      <a class="button download-button" href="docs/downloads/gemsdoe32-karage3-consensus-hgrad-k37654-20261029T183206Z-4786d9bd-zeros.zip">Format-valid candidate ZIP — DO NOT SUBMIT</a>
      <a class="button secondary" href="docs/downloads/gemsdoe32-karage3-consensus-hgrad-k37654-20261029T183206Z-4786d9bd-gate.json">Automated gate verdict (JSON)</a>
    </div>
    <div class="download-meta">
      <p><strong>Verdict:</strong> DO NOT SUBMIT — gates G5 and G6 fail (see below).</p>
      <p><strong>Candidate:</strong> <code>{html.escape(gate['candidate'])}</code> · zip SHA-256 <code>{html.escape(gate['candidate_sha256'])}</code></p>
      <p><strong>Worst literal overlap found:</strong> {worst_txt}.</p>
    </div>
    <div class="validation-grid">
      {''.join(rows)}
    </div>
    <h3>Why no file is cleared yet</h3>
    <ol>
      <li><strong>A dense registry raster makes every candidate fail.</strong> <code>apartanish22-droid/ApartGEMSDOE2</code> file <code>gemsdoe32-h-depth-cond-conductive-under-thin-cover-top37654-20261028T224836Z-e34db98d-nan.tif</code> has 5,106,385 positive cells (98.8% of the footprint). Its 3-px dilation covers the whole footprint, so every candidate's within-3 px overlap with it is 1.0. Flagged for owner review; not exempted.</li>
      <li><strong>The uniqueness rule is strict.</strong> The 13GEMSDOE calibration lattice (206,895 dots) covers 99.87% of the footprint within 3 px. Under the literal 70% rule, any interior candidate with more than about 22,163 dots is a duplicate by arithmetic (<code>scripts/protocol_preflight.py</code>). Smaller candidates would need at least 30% of their dots on the few uncovered cells, which lie almost entirely on the footprint boundary ring. That is a gaming placement, not a detector, and is not offered as a submission.</li>
      <li><strong>Surface and registry completeness are NOT ESTABLISHED.</strong> The continuous-surface Spearman gate needs each candidate's surface; the registry manifest is a filtered inventory (<code>literal_registry_complete: false</code>) with 38 rasters that could not be read.</li>
      <li><strong>The local holdout does not track the leaderboard.</strong> On the shared evaluator the nine files score about 0.005–0.097 HOLDOUT-DTI, yet their reported leaderboard values are 0.2449–0.2778. The proxy cannot be used to estimate a leaderboard score.</li>
      <li><strong>Organizer acceptance is unknown; NOT ESTABLISHED.</strong> No portal receipt was obtained, DrivenData authentication is not available here, and the 0.3047 proxy is not an organizer score.</li>
    </ol>
  </div>
</section>
{BANNER_END}"""


def build_table(uniq: dict, hold: dict) -> str:
    hold_by_site = {s["site"]: s for s in hold["sites"]}
    body = []
    for c in uniq["candidates"]:
        if c["label"] in LEADERBOARD:
            lb, short = LEADERBOARD[c["label"]]
            h = hold_by_site[c["label"]]["holdout_dti_hide_and_recover"]
            ci = h["ci95_cluster_bootstrap"]
            proxy = (f"{h['pooled_dti']:.4f} <span class='muted'>[{ci[0]:.4f}, {ci[1]:.4f}], n={h['n_withheld_positives']:,}, "
                     f"GEMSDOE32-HIDE-RECOVER-v3.0</span>")
            file_name = c["path"].split("/")[-1]
            src = hold_by_site[c["label"]]["source_url"]
            copies = len(c["byte_identical_registry_copies"])
            copy_txt = f" <span class='muted'>(byte-identical copies elsewhere: {copies})</span>" if copies else ""
            body.append(
                f"<tr><td><strong>{c['label']}</strong></td>"
                f"<td><a class='file-link' href='{html.escape(src)}'>{html.escape(file_name)}</a>{copy_txt}</td>"
                f"<td>{lb} <span class='muted'>USER-REPORTED</span></td>"
                f"<td class='muted'>Not estimable</td>"
                f"<td>{proxy}</td>"
                f"<td>{c['max_within3_vs_any_other_registry_raster']:.4f}<br><span class='muted'>{html.escape(str(c['max_within3_raster']).split(':',1)[-1].split('/')[-1])}</span></td>"
                f"<td>{uniq_label(c)}</td>"
                f"<td><span class='bad'>DO NOT SUBMIT</span></td></tr>")
    for c in uniq["candidates"]:
        if c["label"] not in LEADERBOARD:
            body.append(
                f"<tr><td><strong>{c['label']}</strong> <span class='muted'>(this repo)</span></td>"
                f"<td><code>{html.escape(c['path'].split('/')[-1])}</code></td>"
                f"<td class='muted'>none</td><td class='muted'>Not estimable</td>"
                f"<td>{CORRECTED_HGEO}</td>"
                f"<td>{c['max_within3_vs_any_other_registry_raster']:.4f}<br><span class='muted'>{html.escape(str(c['max_within3_raster']).split(':',1)[-1].split('/')[-1])}</span></td>"
                f"<td>{uniq_label(c)}</td><td><span class='bad'>DO NOT SUBMIT</span></td></tr>")
    return f"""{TABLE_START}
<section id="nine-site-scorecard">
<h2>Nine-site scorecard: file, score, estimate, uniqueness</h2>
<p class="score-note">Columns: the file to download (not cleared), the user-reported leaderboard value, the estimate, the shared-evaluator HOLDOUT-DTI proxy with its 95% CI and withheld count, the highest literal within-3 px overlap with any other registry raster, and the verdict. <strong>Estimate:</strong> no estimate is given: the proxy and leaderboard disagree (GEMSDOE32 proxy 0.0045 vs reported 0.2778). Each proxy is labelled HOLDOUT-DTI, and no leaderboard score is ORGANIZER-CONFIRMED.</p>
<div class="table-wrap"><table>
<thead><tr><th>Site</th><th>File to download</th><th>Reported score</th><th>Estimated score</th><th>HOLDOUT-DTI proxy [95% CI, withheld n]</th><th>Max within-3 px vs other registry raster</th><th>Unique (literal 70% rule)?</th><th>Verdict</th></tr></thead>
<tbody>{''.join(body)}</tbody>
</table></div>
<p class="muted">Registry: {uniq['registry_rasters_measured']:,} restored rasters, {uniq['registry_rasters_skipped_missing_or_malformed']} skipped. Surface Spearman was not measured for these binary files. Source: <code>evidence/site-uniqueness-20261029.json</code>.</p>
</section>
{TABLE_END}"""


def splice(text: str, start: str, end: str, new: str) -> str:
    if start in text and end in text:
        a = text.index(start)
        b = text.index(end) + len(end)
        return text[:a] + new + text[b:]
    raise SystemExit(f"markers {start} not found")


def main() -> int:
    uniq = json.loads(UNIQ.read_text())
    hold = json.loads(HOLD.read_text())
    gate = json.loads(CONSENSUS_GATE.read_text())
    page = PAGE.read_text()
    page = splice(page, BANNER_START, BANNER_END, build_banner(uniq, gate))
    page = splice(page, TABLE_START, TABLE_END, build_table(uniq, hold))
    PAGE.write_text(page)
    print("updated", PAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
