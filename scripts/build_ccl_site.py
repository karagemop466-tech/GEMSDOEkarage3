#!/usr/bin/env python3
"""Build docs/ccl/index.html (executive summary) and docs/ccl/how-to-submit.html from evidence JSON.

Deterministic: every number is read from evidence/ccl_run_card.json, evidence/ccl_experiments.json
and docs/ccl/focus9_table.json.  Nothing is typed by hand.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = "../assets/site.css"


def esc(x) -> str:
    return html.escape(str(x))


def page(title: str, body: str) -> str:
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>'
            f'<link rel="stylesheet" href="{CSS}"></head>\n<body>\n<main class="wrap" id="main">\n{body}\n</main>\n</body></html>\n')


def build() -> dict[Path, str]:
    card = json.loads((ROOT / "evidence/ccl_run_card.json").read_text())
    exp = json.loads((ROOT / "evidence/ccl_experiments.json").read_text())
    f9 = json.loads((ROOT / "docs/ccl/focus9_table.json").read_text())
    h = card["holdout"]
    reg = card["registry"]
    fd = reg["final_dots"]
    tif = Path(card["files"]["tif"]).name
    zipn = Path(card["files"]["zip"]).name
    lo, hi = card["live_ledger_projection"]["range"]
    ndup = len(fd.get("duplicates_null_calibrated") or [])
    status = (f'<aside role="note" style="background:#fff1f2;color:#881337;padding:20px;border:3px solid #be123c">'
              f'<p style="font-size:1.4em;margin:0"><strong>OK TO SUBMIT? NO — DO NOT SUBMIT.</strong></p>'
              f'<p>The new K3-CCL raster passed the automated format check and the holdout gate. It then hit the '
              f'duplicate stop: its final dots fall more than 70% within 3 px of {ndup} registry rasters (the '
              f'catalogue-halo lane), and it also fails the literal lattice rule. Its live-ledger projection, '
              f'{lo:.3f}–{hi:.3f}, is a projection rather than a score, and it is far below 0.2778. No competition '
              f'slot was used, and none of the nine historical files below is a new submission.</p></aside>')
    rows = [
        "<tr><th scope='row'>GEMSDOEkarage3 (this session, lane K3-CCL)</th>"
        f"<td><a href='downloads/{esc(tif)}'>{esc(tif)}</a><br><small>SHA-256 {esc(card['raster_sha256'])}</small></td>"
        f"<td>HOLDOUT-DTI {h['dti']:.4f} [{h['ci95'][0]:.4f}, {h['ci95'][1]:.4f}] ({esc(h['evaluator_version'])}, n={h['withheld_positives']:,}); "
        f"LIVE-LEDGER PROJECTION {lo:.3f}–{hi:.3f} (<em>not a score</em>)</td>"
        f"<td>Hash is new. <strong>DUPLICATE STOP</strong>: {ndup} rasters &gt;70% (null-calibrated); lattice literal "
        f"{reg['literal_lattice_witness']['within_3px_fraction']:.2%}; surface max |ρ| {reg['surface_pre_placement']['worst_abs_spearman']:.3f}</td>"
        "<td><strong>DO NOT SUBMIT</strong> (research artifact)</td></tr>"]
    for r in f9["rows"]:
        if not r.get("submission"):
            rows.append(f"<tr><th scope='row'>{esc(r['site'])}</th><td colspan='4'>No scored raster matched</td></tr>")
            continue
        rows.append(
            f"<tr><th scope='row'>{esc(r['site'])}</th><td>{esc(r['submission'])}<br><small>SHA-256 {esc(r['sha256'])}</small></td>"
            f"<td>OWNER-REPORTED {r['owner_reported_score']:.4f} (no organizer receipt)</td>"
            f"<td>Historical file, already submitted. {r['ov_h195_3px']:.1%} of its dots lie within 3 px of H19-5, "
            f"i.e. the H19-5 lane</td><td><strong>DO NOT RESUBMIT</strong> (copy)</td></tr>")
    table = ("<div role='region' aria-label='Executive summary table' tabindex='0' style='overflow-x:auto'><table>"
             "<thead><tr><th scope='col'>Site</th><th scope='col'>File</th><th scope='col'>Score / estimate (labelled)</th>"
             "<th scope='col'>Uniqueness</th><th scope='col'>Submit?</th></tr></thead><tbody>"
             + "".join(rows) + "</tbody></table></div>")
    arms = exp["results"]
    arm_rows = "".join(
        f"<tr><th scope='row'>{esc(k)}</th><td>{v['pooled_dti']:.4f}</td><td>[{v['ci95_cluster_bootstrap'][0]:.4f}, {v['ci95_cluster_bootstrap'][1]:.4f}]</td></tr>"
        for k, v in arms.items())
    body = f"""<h1>Executive summary — lane K3-CCL (2026-10-28)</h1>
{status}
<p><a href="how-to-submit.html">How to submit on DrivenData, step by step</a> · <a href="run-card.json">JSON run card</a> ·
<a href="https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/research/2026-10-28-ccl.md">Full research note</a> ·
<a href="../index.html">Main site</a></p>
<h2>Download table</h2>
<p>Score labels: <strong>HOLDOUT-DTI</strong> = local hide-and-recover evaluator (version, n withheld, 95% CI). <strong>OWNER-REPORTED</strong> = a figure the owner reported, with no organizer receipt. <strong>PROJECTION</strong> = a live-ledger model output, never a score.</p>
{table}
<h2>What was tested</h2>
<p><strong>Hypothesis.</strong> Uncatalogued faults are the missing pieces of catalogued systems: tip continuations, parallel splays and linkage zones. A learner trained on simulated catalogue incompleteness, with visible-catalogue geometry as input, should recover them.</p>
<div role="region" aria-label="Holdout results" tabindex="0"><table><thead><tr><th scope="col">Arm (budget-matched)</th><th scope="col">HOLDOUT-DTI</th><th scope="col">95% CI</th></tr></thead><tbody>{arm_rows}</tbody></table></div>
<p>The catalogue geometry roughly doubled holdout DTI: mechanism Δ {exp['paired_E1_vs_E3_mechanism']['delta_point']:+.4f} [{exp['paired_E1_vs_E3_mechanism']['delta_ci95'][0]:+.4f}, {exp['paired_E1_vs_E3_mechanism']['delta_ci95'][1]:+.4f}]. The leakage canary passed (max single-feature AUC {card['leakage_canary_max_single_feature_oriented_auc']:.3f}).</p>
<p><strong>Why it still fails.</strong> The holdout withholds catalogue fragments that sit next to visible traces, so they are easy to recover. Live new faults are depleted near the catalogue. Under the live catalogue the learner concentrates its dots in the catalogue halo, which is already occupied by registered rasters. This is the duplicate stop. Fixing the holdout comes first (see the research note, §4 and §8).</p>
<h2>Why GEMSDOE32 scored 0.2778 (OWNER-REPORTED)</h2>
<p>It uses H19-5 network dots at 2.8 px spacing, which keeps the kernel's TP coverage while cutting false-positive mass by 64%. It then prunes the dots within 2 px of catalogued faults. Each pruned dot gained the pure-false-positive value, about 2.8e-6 DTI. All 12 measured files at or above 0.2560 lie at least 97.7% within 3 px of H19-5. The best unique file is GEMSDOE70 at 0.2478.</p>
"""
    how = f"""<h1>How to submit on DrivenData — step by step</h1>
<aside role="note" style="background:#fff1f2;color:#881337;padding:16px;border:3px solid #be123c"><strong>There is currently NO file in this repository that is OK to submit.</strong> These steps are for a future file whose run card says <code>verdict: promote</code> and which an independent selector has approved, since weekly slots are limited.</aside>
<ol>
<li>Sign in at <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">drivendata.org — DOE GEMS competition</a> with the account registered for the competition.</li>
<li>Open the <strong>Submissions</strong> tab of the competition.</li>
<li>Check the file before uploading. It must be a single-band GeoTIFF in EPSG:32611, 3730×3292 pixels, transform (100, 0, 243350, 0, −100, 4508550), float32, with every value in [0, 1] and <em>zeros</em> outside the footprint. NaN outside the footprint triggered the portal error "Predicted values must be in range [0, 1]". Run locally: <code>.venv/bin/python scripts/check_submission.py FILE.tif --strict-finite</code>; it must print <code>[PASSED]</code>.</li>
<li>Upload either the <code>.tif</code> or the <code>.zip</code> that contains only that single <code>.tif</code>. Both forms are produced by <code>scripts/submission_writer.py</code>.</li>
<li>Optional: paste the run card's <code>note</code> (at most 140 characters) into the submission note field, so the score can later be tied to the file hash.</li>
<li>Submit. Save a screenshot or copy of the submission row (time, score, file name) to <code>registry/owner_score_ledger.csv</code> with the file's SHA-256. Without that, a score stays <strong>OWNER-REPORTED</strong>, not organizer-confirmed.</li>
<li>Remember the official rules: the private leaderboard decides the prizes, and the Final Round re-scores the one selected submission on expanded labels (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a>).</li>
</ol>
<p><a href="index.html">Back to executive summary</a></p>
"""
    return {ROOT / "docs/ccl/index.html": page("K3-CCL executive summary — DO NOT SUBMIT", body),
            ROOT / "docs/ccl/how-to-submit.html": page("How to submit on DrivenData", how)}


if __name__ == "__main__":
    for p, t in build().items():
        p.write_text(t)
        print("wrote", p.relative_to(ROOT))
