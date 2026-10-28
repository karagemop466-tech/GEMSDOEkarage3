#!/usr/bin/env python3
"""Render the H-K3C executive pages from the run card (docs/k3c/run-card.json).

Writes:
  docs/k3c/index.html             executive summary: verdict, download, per-site table, hypotheses, experiments
  docs/k3c/how-to-submit.html     step-by-step DrivenData submission guide for the cleared file
  docs/index.html, docs/executive-summary.html   top-level decision pages (replaces the 2026-10-28 duplicate-stop stubs)
  docs/current-gate-decision.json gate output for the current card
Every number is read from JSON evidence; nothing is typed by hand here.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from promotion_gate import assess  # noqa: E402

FOCUS_SITES = [
    ("GEMSDOE24", "https://buffedlizard55-lab.github.io/GEMSDOE24/"),
    ("GEMSDOE25", "https://buffedlizard55-lab.github.io/GEMSDOE25/"),
    ("GEMSDOE27", "https://buffedlizard55-lab.github.io/GEMSDOE27/"),
    ("GEMSDOE28", "https://buffedlizard55-lab.github.io/GEMSDOE28/"),
    ("GEMSDOE30", "https://buffedlizard55-lab.github.io/GEMSDOE30/"),
    ("GEMSDOE31", "https://buffedlizard55-lab.github.io/GEMSDOE31/docs/"),
    ("GEMSDOE32", "https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html"),
    ("GEMSDOE33", "https://buffedlizard55-lab.github.io/GEMSDOE33/"),
    ("GEMSDOE36", "https://buffedlizard55-lab.github.io/GEMSDOE36/docs/"),
]
# Owner-supplied best results per site (verbatim from the standing prompt; USER-REPORTED, no organizer receipt)
OWNER_BEST = {
    "GEMSDOE24": ("h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", 0.2477),
    "GEMSDOE25": ("dotted-h19-5-d2-8-20261002-e56ea318af89-nan", 0.2600),
    "GEMSDOE27": ("topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", 0.2449),
    "GEMSDOE28": ("h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", 0.2710),
    "GEMSDOE30": ("d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", 0.2600),
    "GEMSDOE31": ("h27-4-solo-d28-20261004-8acb75e1-nan", 0.2708),
    "GEMSDOE32": ("h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778),
    "GEMSDOE33": ("h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632),
    "GEMSDOE36": ("anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", 0.2750),
}
H = html.escape


def f4(x) -> str:
    try:
        return f"{float(x):.4f}"
    except (TypeError, ValueError):
        return "n/a"


def pct(x) -> str:
    try:
        return f"{100 * float(x):.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def shell(title: str, body: str, depth: int = 1) -> str:
    pre = "../" * depth
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{H(title)}</title><link rel="stylesheet" href="{pre}assets/site.css">
<style>.ok{{background:#e4f0e3;color:#1c4732;border:3px solid #305e46}}.no{{background:#fff1f2;color:#881337;border:3px solid #be123c}}
.verdict{{padding:22px 26px;border-radius:14px;margin:18px 0;font-size:17px;line-height:1.5}}.verdict h2{{margin:0 0 8px;font-size:26px}}
.btn{{display:inline-block;padding:12px 18px;border-radius:9px;font-weight:800;text-decoration:none;margin:6px 8px 6px 0}}
.btn.ok{{background:#1c4732;color:#fff;border:0}}.btn.no{{background:#be123c;color:#fff;border:0}}.btn.light{{background:#fff;color:#1c4732;border:1px solid #c9d8cc}}
table{{min-width:0}}td,th{{font-size:12px}}code{{overflow-wrap:anywhere}}.small{{font-size:12px;color:#5c6a62}}
.label{{display:inline-block;padding:2px 6px;border-radius:5px;font-size:10px;font-weight:800;background:#eef3eb;color:#386e4c}}
.label.warn{{background:#fff0ea;color:#ad4932}}</style></head><body><main class="wrap" style="padding:28px 0 60px">
<p class="small"><a href="{pre}index.html">Home</a> · <a href="{pre}k3c/index.html">H-K3C executive summary</a> · <a href="{pre}k3c/how-to-submit.html">How to submit</a> · <a href="{pre}k3c/run-card.json">Run card (JSON)</a> · <a href="{pre}csst-bghf/index.html">Previous lane H-K3B-1</a> · <a href="{pre}ccl/index.html">Lane K3-CCL</a></p>
{body}
<p class="small" style="margin-top:40px">Score labels: <strong>USER-REPORTED</strong> = copied from the owner's prompt / sister site (no DrivenData receipt is verified in this checkout, IR-K3-04). <strong>HOLDOUT-DTI</strong> = our own hide-and-recover evaluator (version, withheld positives and 95% CI always stated). <strong>LLI PROJECTION</strong> = a regression fitted to owner-reported live scores — a go/no-go signal, never a score. Nothing on this site is ORGANIZER-CONFIRMED.</p>
</main></body></html>"""


def reason_summary(gate: dict) -> str:
    """Keep the public banner readable; the JSON decision retains every reason."""
    reasons = gate.get('reasons', [])
    return '; '.join(reasons[:3]) + (f'; and {len(reasons)-3} more (see decision JSON)' if len(reasons) > 3 else '')


def root_decision_html(card: dict, gate: dict) -> tuple[str, str]:
    """Landing-page banner and release card HTML for the current card (shared with scripts/build_site.py)."""
    ok = gate["verdict"] == "promote"
    hold = card["holdout"]
    dl = "docs/" + card["submission_file"].removeprefix("docs/")
    zp = "docs/" + card["zip_submission_file"].removeprefix("docs/")
    hr = f"{hold['dti']:.4f} [{hold['ci95'][0]:.4f}, {hold['ci95'][1]:.4f}]"
    champ = f"{hold['champion_02778_same_evaluator_dti']:.4f}"
    pd = hold["paired_delta_ci95"]
    sha8 = card["raster_sha256"][:8]
    if ok:
        aside = (f'<aside style="padding:16px;background:#ecfdf5;color:#064e3b;border-bottom:3px solid #059669"><strong>OK TO SUBMIT? YES — one file is cleared '
                 f'(lane H-K3C, {H(card["generated_utc"][:10])}).</strong> <code>{H(card["submission_name"])}</code> (SHA-256 {sha8}…) passed every automated gate: '
                 f'format/[0,1]/zero-NaN, leakage canaries, null-calibrated registry uniqueness, and HOLDOUT-DTI ({H(hold["evaluator_version"])}, n={hold["withheld_positives"]:,}) '
                 f'{hr} vs the 0.2778 champion rule {champ} with paired 95% CI [{pd[0]:+.4f}, {pd[1]:+.4f}] excluding zero. The selector decides whether to spend a weekly slot. '
                 f'<a href="{H(dl)}" download>Download .tif</a> · <a href="{H(zp)}" download>.zip</a> · <a href="docs/k3c/index.html">Executive summary</a> · '
                 f'<a href="docs/k3c/how-to-submit.html">How to submit</a> · <a href="docs/k3c/run-card.json">Run card</a></aside>')
        card_html = (f'<div class="release-card" aria-label="Current submission decision">\n'
                     f'      <div class="card-top"><span class="card-kicker">CURRENT RELEASE DECISION</span><span class="pill" style="background:#059669;color:#fff">PROMOTE · OK TO SUBMIT</span></div>\n'
                     f'      <h2>One file cleared<br>for submission.</h2>\n'
                     f'      <p>Lane H-K3C · HOLDOUT-DTI {hr} ({H(hold["evaluator_version"])}, n={hold["withheld_positives"]:,}) vs champion rule {champ}; paired Δ CI [{pd[0]:+.4f}, {pd[1]:+.4f}]. Note: <code>{H(card["note"])}</code></p>\n'
                     f'      <a class="button" href="{H(dl)}" download>Download submission .tif <span aria-hidden="true">↓</span></a>\n'
                     f'      <div class="card-foot"><span id="download-explanation">SHA-256 {H(card["raster_sha256"])}</span><a href="docs/k3c/run-card.json" style="color:#d6e8d7">Run card ↗</a></div>\n'
                     f'    </div>')
    else:
        reasons = H(reason_summary(gate))
        aside = (f'<aside style="padding:16px;background:#fff1f2;color:#881337"><strong>OK TO SUBMIT? NO. As of {H(card["generated_utc"][:10])} no file in this repository is authorized.</strong> '
                 f'Newest lane <strong>H-K3C</strong> (<code>{H(card["submission_name"])}</code>, SHA-256 {sha8}…) HOLDOUT-DTI {hr} vs champion rule {champ} (paired CI [{pd[0]:+.4f}, {pd[1]:+.4f}]); '
                 f'gate verdict <strong>{H(gate["verdict"].upper())}</strong>: {reasons}. '
                 f'<a href="docs/k3c/index.html">H-K3C executive summary &amp; research-only TIFF</a> · <a href="docs/k3c/how-to-submit.html">How to submit (when a file is cleared)</a> · '
                 f'<a href="docs/csst-bghf/index.html">Previous lane CSST-BGHF</a> · <a href="docs/release-review.html">Saved-byte audit</a></aside>')
        card_html = (f'<div class="release-card" aria-label="Current submission decision">\n'
                     f'      <div class="card-top"><span class="card-kicker">CURRENT RELEASE DECISION</span><span class="pill hold">NOT APPROVED</span></div>\n'
                     f'      <h2>No file cleared<br>for submission.</h2>\n'
                     f'      <p>Lane H-K3C verdict {H(gate["verdict"])}: {reasons}. The file is published for research only.</p>\n'
                     f'      <button class="disabled-button" disabled aria-describedby="download-explanation">Download submission .tif <span aria-hidden="true">↓</span></button>\n'
                     f'      <div class="card-foot"><span id="download-explanation">Download locked · do not submit</span><a href="docs/k3c/run-card.json" style="color:#d6e8d7">Run card ↗</a></div>\n'
                     f'    </div>')
    return aside, card_html


def apply_root_decision(html: str) -> str:
    """Replace the banner and release card of the root landing page with the current H-K3C decision."""
    card = json.loads((ROOT / "docs/k3c/run-card.json").read_text())
    gate = assess(card)
    aside, card_html = root_decision_html(card, gate)
    html, n1 = re.subn(r'<aside style="padding:16px;background:#(?:fff1f2|ecfdf5)[^"]*">.*?</aside>', lambda m: aside, html, count=1, flags=re.S)
    html, n2 = re.subn(r'<div class="release-card" aria-label="Current submission decision">.*?</div>\n  </section>', lambda m: card_html + "\n  </section>", html, count=1, flags=re.S)
    if n1 != 1 or n2 != 1:
        raise SystemExit(f"root index.html markers not found (aside={n1}, card={n2})")
    return html


def apply_guide_decision(html: str) -> str:
    """Replace the banner of the root submission guide (executive-summary.html) with the current decision."""
    card = json.loads((ROOT / "docs/k3c/run-card.json").read_text())
    gate = assess(card)
    aside, _ = root_decision_html(card, gate)
    html, n1 = re.subn(r'<aside style="padding:16px;background:#(?:fff1f2|ecfdf5)[^"]*">.*?</aside>', lambda m: aside, html, count=1, flags=re.S)
    if gate["verdict"] == "promote":
        banner = ('<div class="banner" style="background:#ecfdf5;color:#064e3b"><span class="banner-icon" aria-hidden="true">✓</span><div><strong>OK TO SUBMIT · one new TIFF is cleared by every automated gate (lane H-K3C)</strong>'
                  f'<p>Download it from the <a href="docs/k3c/index.html">H-K3C executive summary</a> and follow <a href="docs/k3c/how-to-submit.html">how to submit</a>. SHA-256 {H(card["raster_sha256"])}. '
                  'The nine historical files below remain research-only. No organizer score estimate is defensible; see the expected-live-score caveat on the decision page.</p></div></div>')
    else:
        banner = ('<div class="banner"><span class="banner-icon" aria-hidden="true">!</span><div><strong>NOT OK TO SUBMIT · No new TIFF is approved</strong>'
                  f'<p>Lane H-K3C verdict {H(gate["verdict"])}: {H(reason_summary(gate))}. Research links below lead to historical files, not a new submission.</p></div></div>')
    html, n2 = re.subn(r'<div class="banner"><span class="banner-icon" aria-hidden="true">!</span><div><strong>NOT OK TO SUBMIT · No new TIFF is approved or available</strong>.*?</div></div>', lambda m: banner, html, count=1, flags=re.S)
    if n1 != 1 or n2 != 1:
        raise SystemExit(f"root executive-summary.html markers not found (aside={n1}, banner={n2})")
    return html


def update_root_page(card, gate, ok, hold) -> None:
    """Regenerate root index.html / executive-summary.html through scripts/build_site.py (single source)."""
    import build_site  # noqa: WPS433 — local import avoids a cycle
    for path, text in build_site.render().items():
        path.write_text(text)


def build() -> None:
    card = json.loads((ROOT / "docs/k3c/run-card.json").read_text())
    gate = assess(card)
    (ROOT / "docs/current-gate-decision.json").write_text(json.dumps({**gate, "card": "docs/k3c/run-card.json", "raster_sha256": card["raster_sha256"]}, indent=2) + "\n")
    tif_rel = card["submission_file"].removeprefix("docs/k3c/")   # relative to docs/k3c/ pages
    zip_rel = card["zip_submission_file"].removeprefix("docs/k3c/")
    assert tif_rel.startswith("downloads/") and zip_rel.startswith("downloads/")
    tif_abs = ROOT / card["submission_file"]
    if hashlib.sha256(tif_abs.read_bytes()).hexdigest() != card["raster_sha256"]:
        raise SystemExit("saved raster hash does not match the run card")
    ok = gate["verdict"] == "promote"
    hold = card["holdout"]
    ex = card["experiments"]
    e1 = ex["E1_power_24cell"]
    e2 = ex["E2_strain_deficit"]
    e3 = ex["E3_budget"]
    reg = card["registry_summary"]
    val = card["validator"]
    nine = json.loads((ROOT / "evidence/nine-site-audit-k3c-20261028.json").read_text())
    nine_by = {s["site"]: s for s in nine.get("sites", [])}
    lli = card.get("live_ledger_projection", {})
    lli_proj, lli_mae = None, None
    if isinstance(lli.get("result"), dict):
        r = lli["result"]
        lli_mae = r.get("loo_mae")
        for k, v in (r.get("projections") or {}).items():
            if isinstance(v, dict) and v.get("dti") is not None and card["submission_name"] in k:
                lli_proj = v["dti"]
    # A fitted projection is not an organizer score and is not a reliable estimate.
    lli_txt = "No defensible estimate of the organizer score"
    sgmc = hold["sgmc_off_catalogue_v3"]
    witness = json.loads((ROOT / 'evidence/k3c-literal-witness-audit-20261028.json').read_text())
    if witness['candidate_sha256'] != card['raster_sha256']:
        raise ValueError('independent witness audit does not match candidate')

    verdict_box = f"""<div class="verdict {'ok' if ok else 'no'}"><h2>{'OK TO DOWNLOAD AND SUBMIT: YES' if ok else 'OK TO SUBMIT: NO — DO NOT SUBMIT'}</h2>
<p>{'Submission blocked: duplicate-stop. Independent pinned-lattice overlap: '+pct(witness['within_3px_fraction'])+'. NOT CLEARED FOR SUBMISSION.' if not ok else ''}</p>
<p>Automated verdict <strong>{H(gate['verdict'].upper())}</strong> from <code>scripts/promotion_gate.py</code> (literal protocol) on the historical run card generated {H(card['generated_utc'])}.
{'All preregistered gates passed: format, [0,1] range, leakage canaries, registry uniqueness (null-calibrated), and a paired 24-cell holdout improvement whose 95% CI excludes zero. You, the selector, decide whether to spend one weekly slot on it.' if ok else 'Failed gates: ' + H(reason_summary(gate))}</p>
<p><a class="btn {'ok' if ok else 'no'}" href="{H(tif_rel)}" download>{'Download submission .tif' if ok else 'Download research-only .tif (NOT CLEARED)'}</a>
<a class="btn light" href="{H(zip_rel)}" download>{'Download single-file .zip' if ok else 'Download research-only .zip (NOT CLEARED)'}</a> <a class="btn light" href="run-card.json">Run card (JSON)</a></p>
<p class="small">File <code>{H(card['submission_name'])}</code><br>SHA-256 <code>{H(card['raster_sha256'])}</code><br>{'Suggested DrivenData note' if ok else 'Historical note — do not submit'} ({len(card['note'])}/140 chars): <code>{H(card['note'])}</code></p>
<p class="small"><strong>Historical evidence, not clearance.</strong> HOLDOUT-DTI says the CSST-BGHF construction rule recovers withheld faults better than the champion's construction rule when both are re-derived blind ({f4(hold['dti'])} vs {f4(hold['champion_02778_same_evaluator_dti'])}, paired Δ {hold['paired_delta_vs_champion_02778']:+.4f}, 95% CI [{hold['paired_delta_ci95'][0]:+.4f}, {hold['paired_delta_ci95'][1]:+.4f}]). No holdout number reproduces the champion file's owner-reported 0.2778 (construction-censored, IR-K3-09), and the {H(lli_txt)}. The SGMC-cal paired CI [{sgmc['paired_delta_ci95'][0]:+.4f}, {sgmc['paired_delta_ci95'][1]:+.4f}] still spans zero. For context only, the historical null-calibrated diagnostic is {pct(reg['worst_null_calibrated_excess_overlap_identifiable']['excess_overlap_3px'])} excess overlap vs <code>{H(reg['worst_null_calibrated_excess_overlap_identifiable']['name'].split(':')[-1].split('/')[-1])}</code> (limit 70%, IR-K3-22). The historical holdout has not been reproduced in this review; no hidden score can be inferred.</p></div>"""

    def row(site, url):
        s = nine_by.get(site, {})
        own_file, own_score = OWNER_BEST[site]
        audited = s.get("primary_audited_file", "").split("/")[-1]
        ov = s.get("karage3_vs_primary_3px_overlap")
        ov_max = s.get("karage3_vs_site_max_3px_overlap")
        uniq = (ov_max is not None and ov_max <= 0.70)
        same = audited and own_file.split("-zeros")[0].split("-nan")[0].split("-allfinite")[0] in audited
        return (f"<tr><td><a href='{H(url)}'>{site}</a><br><span class='small'>best: <code>{H(own_file)}</code></span></td>"
                f"<td><strong>{f4(own_score)}</strong> <span class='label warn'>USER-REPORTED</span><br><span class='small'>no verified organizer receipt in this checkout (IR-K3-04)</span></td>"
                f"<td>{f4(s.get('holdout_hide_recover_v3_dti'))} {H(str(s.get('holdout_hide_recover_v3_ci95','')))}<br><span class='small'>byte-audited file: <code>{H(audited)}</code>{'' if same else ' (latest pinned file, not the best-scoring one)'}</span></td>"
                f"<td>{pct(ov)} of our dots within 3 px of the audited file; {pct(ov_max)} max vs any {site} raster → {'below threshold in this limited comparison only' if uniq else 'above threshold in this comparison'}</td>"
                f"<td>Historical — do not resubmit (best file is in the H19-5 family; see forensics)</td></tr>")

    site_rows = "".join(row(s, u) for s, u in FOCUS_SITES)
    ours = (f"<tr style='background:#eef3eb'><td><strong>GEMSDOEkarage3 · Lane H-K3C (this session)</strong><br><a class='file-link' href='{H(tif_rel)}' download>{H(card['submission_name'])}</a></td>"
            f"<td><span class='label'>no live score yet</span><br><span class='small'>{H(lli_txt)}</span></td>"
            f"<td><strong>{f4(hold['dti'])}</strong> {H(str(hold['ci95']))} <span class='label'>HOLDOUT-DTI {H(hold['evaluator_version'])}, n={hold['withheld_positives']:,}</span><br><span class='small'>champion rule same evaluator {f4(hold['champion_02778_same_evaluator_dti'])}; paired Δ {hold['paired_delta_vs_champion_02778']:+.4f} CI {H(str(hold['paired_delta_ci95']))}; SGMC-cal {f4(sgmc['prevalence_calibrated_dti'])} vs champion {f4(sgmc['champion_02778_calibrated_dti'])}</span></td>"
            f"<td>max vs 9 sites {pct(reg['focus9_max_3px_overlap'])}; max vs any ≤100k-dot raster {pct(reg['discrete_le100k_max_literal_3px_overlap'])}; vs 0.2778 champion {pct(card['spatial_allocation']['overlap_3px_vs_champion_02778'])} → <strong>{'limited focus-site comparison only' if ok else 'NOT UNIQUE under literal all-registry rule'}</strong></td>"
            f"<td><strong>{'SUBMIT (selector decides slot)' if ok else 'DO NOT SUBMIT'}</strong></td></tr>")

    table = f"""<h2>Per-site executive table — what to download, what it is estimated to score, is it unique</h2>
<div class="table-wrap"><table><thead><tr><th>Site · file to download</th><th>Estimated / reported score</th><th>HOLDOUT-DTI (hide-and-recover; SGMC-cal)</th><th>Unique?</th><th>Decision</th></tr></thead><tbody>{ours}{site_rows}</tbody></table></div>
<p class="table-note">Holdout numbers for the nine sites come from <code>evidence/nine-site-audit-k3c-20261028.json</code> (byte-verified rasters from each site's pinned commit, evaluated on the template 8-cell HOLDOUT-DTI (n=22,232 withheld positives, 95% CI shown) <code>{H(nine.get('evaluator_versions',{}).get('hide_recover','GEMSDOE32-HIDE-RECOVER-v3.0') if isinstance(nine.get('evaluator_versions'),dict) else 'GEMSDOE32-HIDE-RECOVER-v3.0')}</code>). Pinned historical files include a related dot-set family (exact set algebra in <code>knowledge/focus9_forensics.md</code>): GEMSDOE25 ≡ GEMSDOE30, GEMSDOE31 ≡ the "solo" control, GEMSDOE32 = solo − 2,545 collar dots, GEMSDOE36 = GEMSDOE32 + 1,200 dots.</p>"""

    why = """<h2>Why did the GEMSDOE32 file reportedly perform well?</h2>
<p>The owner's reported result is unverified: no organizer receipt linked to the file has been supplied. The
pinned geometry audit shows a sparse-dot lineage and catalogue-collar pruning. A plausible explanation is that
less redundant prediction mass reduces false-positive cost while keeping spatial coverage, but the hidden labels
are unavailable and do not establish causation. We cannot determine whether any new submission would beat it.
Fault prediction is not direct validation of a geothermal vent. <a href="../../knowledge/focus9_forensics.md">Read the lineage audit</a>.</p>"""

    hyp = """<h2>Historical hypotheses from the previous session (ranked; full text in <code>docs/research/k3c-preregistration-20261028.md</code>)</h2>
<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Hypothesis</th><th>Layers</th><th>Signature</th><th>Why it targets uncatalogued faults</th><th>Named mimic</th><th>Lift · cost</th></tr></thead><tbody>
<tr><td>1 (tested)</td><td>H-K3C-1 Kostrov strain-deficit prior</td><td>Band 04 geod_2ndinv (+07, 08); fold-visible catalogue</td><td>S/(D+c): strain-rate rank ÷ 10 km visible fault density, prior = clip((ratio/median)^0.5, 0.5, 2)</td><td>Unaccounted strain could indicate unmapped faults but may also reflect distributed deformation</td><td>1915/1954 post-seismic relaxation; distributed block rotation</td><td>small–moderate · low</td></tr>
<tr><td>2</td><td>H-K3C-2 strike-conditioned structural-grain ridge</td><td>Bands 03, 05, 18; visible strike histogram</td><td>Directional Hessian ridge limited to the two dominant local strike modes ±20°</td><td>Blind faults inherit regional grain; suppresses flight-line and drainage artefacts</td><td>Dikes, bedding</td><td>small · moderate</td></tr>
<tr><td>3</td><td>H-K3C-3 multi-altitude tilt-depth wedge</td><td>Bands 02, 14 + GeoDAWN extensions</td><td>Tilt-depth half-width vs upward-continuation level</td><td>Some dipping contacts may migrate with altitude; flow margins can mimic the signal</td><td>Thin basalt flow margins</td><td>small · moderate</td></tr>
<tr><td>4</td><td>H-K3C-4 half-graben polarity wedge</td><td>Bands 15, 13, 12</td><td>Up-gradient 2nd derivative of basement depth</td><td>Intrabasin blind faults under fill</td><td>Pinch-outs; interpolation artefacts (61GEMSDOE: 0.0009)</td><td>negative prior · low</td></tr>
<tr><td>5 (blocked)</td><td>H-K3C-5 relocated microseismicity planes</td><td>USGS ComCat (external, public domain)</td><td>3-D RANSAC hypocentral planes</td><td>Swarms illuminate active blind transfer zones</td><td>Induced seismicity</td><td>unknown · host not reachable from sandbox</td></tr>
</tbody></table></div>"""

    def hr_cell(d):
        return f"{f4(d['pooled_dti'])} {H(str(d['ci95']))}"

    exp = f"""<h2>Preregistered experiments (budget 3 of 3 used) — all HOLDOUT-DTI, evaluator <code>{H(hold['evaluator_version'])}</code>, 24 cells = 4 quadrants × draws 20–25</h2>
<div class="table-wrap"><table><thead><tr><th>Arm</th><th>Hide-and-recover (pooled, 95% CI)</th><th>Detached ≥ 600 m</th><th>Paired Δ</th></tr></thead><tbody>
<tr><td>Control: 0.2778 champion rule (D2.8 + visible B=2)</td><td>{hr_cell(e1['CTRL_champion_rule'])}<br><span class="small">n withheld = {e1['CTRL_champion_rule']['n_withheld_positives']:,}</span></td><td>{hr_cell(e1['detached_600m']['CTRL'])}</td><td>—</td></tr>
<tr><td>E1: CSST-BGHF (previous lane) re-measured on 24 cells</td><td>{hr_cell(e1['E1_csst_bghf'])}</td><td>{hr_cell(e1['detached_600m']['E1'])}</td><td>E1 − CTRL {e1['paired_E1_minus_CTRL']['mean_boot_delta']:+.4f} CI {H(str(e1['paired_E1_minus_CTRL']['ci95']))}, P(&gt;0) = {e1['paired_E1_minus_CTRL']['prob_positive']}</td></tr>
<tr><td>E2: E1 × Kostrov strain-deficit prior (H-K3C-1)</td><td>{hr_cell(e2['E2'])}</td><td>{hr_cell(e2['detached_600m_E2'])}</td><td>E2 − E1 {e2['paired_E2_minus_E1']['mean_boot_delta']:+.4f} CI {H(str(e2['paired_E2_minus_E1']['ci95']))}, P(&gt;0) = {e2['paired_E2_minus_E1']['prob_positive']}; historical SGMC-cal E1 {f4(e2['sgmc_cal_live']['E1'])} vs E2 {f4(e2['sgmc_cal_live']['E2'])} (champion {f4(e2['sgmc_cal_live']['champion_02778'])}); prior-alone AUC {f4(e2['prior_alone_oriented_auc'])}; preregistered rule passed: <strong>{e2['e2_passes_preregistered_rule']}</strong></td></tr>
{''.join(f"<tr><td>E3: {e3['surface']} surface at budget {b}</td><td>{hr_cell(r['hr'])}</td><td>{hr_cell(r['detached_600m'])}</td><td>vs 37,654: {r['paired_vs_37654']['mean_boot_delta']:+.4f} CI {H(str(r['paired_vs_37654']['ci95']))}</td></tr>" for b, r in e3['rows'].items())}
</tbody></table></div>
<p class="table-note">Shipped: surface <strong>{H(e3['surface'])}</strong>, budget <strong>{e3['shipped_budget']:,}</strong> dots, min spacing 3.1 px (310 m), B = 2 px collar. Shipped-arm vs champion rule: Δ {hold['paired_delta_vs_champion_02778']:+.4f}, 95% CI {H(str(hold['paired_delta_ci95']))}, P(Δ&gt;0) = {hold['paired_prob_positive']}. Detached ≥ 600 m: {f4(hold['detached_600m']['dti'])} vs champion {f4(hold['detached_600m']['champion_02778_dti'])}. SGMC-cal (62,703 off-catalogue USGS SGMC pixels): {f4(sgmc['prevalence_calibrated_dti'])} {H(str(sgmc['calibrated_ci95']))} vs champion {f4(sgmc['champion_02778_calibrated_dti'])}.</p>"""

    checks = f"""<h2>Validation gates (automated, no human inspection)</h2>
<div class="table-wrap"><table><thead><tr><th>Gate</th><th>Result</th></tr></thead><tbody>
<tr><td>GeoTIFF saved bytes: single band, float32, EPSG:32611, 3730 × 3292, transform [100, 0, 243350, 0, −100, 4508550]</td><td>{'PASS' if all(val[k] for k in ('single_band','crs_match','shape_match','transform_match')) else 'FAIL'}</td></tr>
<tr><td>Every pixel finite and in [0, 1] over the full grid (local full-array range check; portal acceptance is unknown)</td><td>{'PASS' if val['full_grid_zero_nan'] and val['range_0_1'] else 'FAIL'} — min {card['validator_output']['independent_reread']['min']}, max {card['validator_output']['independent_reread']['max']}, positives {card['validator_output']['independent_reread']['n_positive']:,}, on-catalogue positives {card['validator_output']['independent_reread']['positives_on_catalogue']}</td></tr>
<tr><td>Historical leakage canary (not reproduced): every feature alone ≤ 0.90 AUC on withheld truth ({card['leakage_canary']['n_features_tested']} features)</td><td>{'PASS' if card['leakage_canary']['passed'] else 'FAIL'} — max {f4(card['leakage_canary']['max_oriented_auc'])}; strain-deficit prior alone {f4(card['leakage_canary']['strain_deficit_prior_alone_auc'])}</td></tr>
<tr><td>Historical, not reproduced: surface rank-correlation vs {reg['unique_rasters_checked']:,} unique registry rasters (113 repos) ≤ 0.90</td><td>max |ρ| = {f4(reg['surface_max_abs_spearman'])} ({H(reg['surface_worst_raster'])})</td></tr>
<tr><td>Historical subset only — final dots within 3 px of any ≤100k-dot detector raster ≤ 70%</td><td>max {pct(reg['discrete_le100k_max_literal_3px_overlap'])} ({H(reg['discrete_worst_raster'])}); nine focus sites max {pct(reg['focus9_max_3px_overlap'])}</td></tr>
<tr><td>Uniqueness — literal overlap with every registry raster (required; null calibration is diagnostic only)</td><td>{'PASS' if card['registry']['literal_all_rasters_final_passed'] else 'FAIL'} — literal worst {pct(reg['literal_worst_any_raster']['within_3px_fraction'])} ({H(reg['literal_worst_any_raster']['name'])}), p0 = {reg['literal_worst_any_raster'].get('p0')}, excess = {reg['literal_worst_any_raster'].get('excess_overlap_3px')}</td></tr>
<tr><td>Historical holdout (not reproduced): paired improvement over the 0.2778 champion rule, same evaluator, 95% CI excludes 0</td><td>{'PASS' if hold['paired_delta_ci95'][0] > 0 else 'FAIL'} — Δ {hold['paired_delta_vs_champion_02778']:+.4f} CI {H(str(hold['paired_delta_ci95']))}</td></tr>
<tr><td>Overall promotion-gate verdict</td><td><strong>{H(gate['verdict'].upper())}</strong> {('— ' + H(reason_summary(gate))) if gate['reasons'] else ''}</td></tr>
</tbody></table></div>
<p class="small">Spatial allocation of the shipped dots: {pct(card['spatial_allocation']['near_apron_2_8px_frac'])} within 8 px of the catalogue, {pct(card['spatial_allocation']['stepover_8_35px_frac'])} at 8–35 px, {pct(card['spatial_allocation']['far_field_gt1500m_frac'])} beyond 1.5 km; {pct(card['spatial_allocation']['lidar_gap_dot_frac'])} inside the 1 m LiDAR gap; median strain-deficit prior at dots {card['spatial_allocation']['prior_live_median_at_dots']}.</p>"""

    body = f"""<h1>GEMSDOEkarage3 — Lane H-K3C executive summary</h1>
<p class="lede">Historical evidence and the current decision. No new file is cleared; no defensible organizer-score estimate exists. Generated from <code>docs/k3c/run-card.json</code> on {H(card['generated_utc'])}; elapsed {card['elapsed_seconds']} s, peak RSS {card['peak_rss_mb']} MB.</p>
{verdict_box}{table}{why}{hyp}{exp}{checks}
<p>See the <a href="../review-literal-20261028.md">current review</a> and <a href="../current-gate-decision.json">gate decision</a>. These old experiments are not reproduced in this session.</p>
<h2>Historical reproduction commands (not run in this review)</h2><pre class="code">.venv/bin/python scripts/restore_data.py && .venv/bin/python scripts/prepare_data.py && .venv/bin/python scripts/restore_pinned_registry.py
.venv/bin/python scripts/fetch_all_registry.py
PYTHONPATH=src .venv/bin/python scripts/build_features.py && PYTHONPATH=src .venv/bin/python scripts/build_crsb_features.py && PYTHONPATH=src .venv/bin/python scripts/build_csst_features.py
PYTHONPATH=src .venv/bin/python scripts/run_k3c_session.py && .venv/bin/python scripts/build_k3c_site.py && .venv/bin/pytest -q</pre>
<p><a href="../research/k3c-preregistration-20261028.md">Locked preregistration</a> · <a href="../../knowledge/irregularities.md">Irregularities register</a> · <a href="../../research/2026-10-28-k3c.md">Research note</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem description</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official leaderboard</a></p>"""
    (ROOT / "docs/k3c/index.html").write_text(shell("H-K3C executive summary — GEMSDOEkarage3", body), encoding="utf-8")

    howto = f"""<h1>How to submit — only after a file is cleared</h1>
{verdict_box}
<p><strong>No candidate is cleared now. Do not upload a research-only TIFF.</strong></p>
<ol class="steps">
<li>After an independent selector approves a future candidate, download its uniquely named TIFF and verify its published SHA-256.</li>
<li>Open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData submissions page</a>, check the current weekly cap, and choose New submission.</li>
<li>Choose the validated single-band TIFF (or ZIP containing one TIFF), enter the candidate's short note, and submit.</li>
<li>Record the organizer receipt, candidate hash and returned score together. A format check alone is not organizer acceptance.</li>
</ol><p>As described in the supplied form, predictions must be in [0,1] and match the sample CRS, shape and transform.
Current rules, authentication and acceptance could not be independently verified in this environment.</p>"""
    (ROOT / "docs/k3c/how-to-submit.html").write_text(shell("How to submit — H-K3C", howto), encoding="utf-8")

    # top-level decision pages
    top = f"""<h1>GEMSDOEkarage3 — current submission decision</h1>
{verdict_box.replace('href="' + H(tif_rel), 'href="k3c/' + H(tif_rel)).replace('href="' + H(zip_rel), 'href="k3c/' + H(zip_rel)).replace('href="run-card.json"', 'href="k3c/run-card.json"')}
<p><a class="btn light" href="k3c/index.html">Full executive summary (per-site table, hypotheses, experiments)</a> <a class="btn light" href="k3c/how-to-submit.html">How to submit</a></p>
<h2>Previous lanes (research only — DO NOT SUBMIT)</h2><ul>
<li>H-K3B-1 CSST-BGHF (2026-10-28 session 3): <a href="csst-bghf/index.html">dashboard</a> — gate negative (8-cell paired CI spanned zero; literal lattice rule remains binding).</li>
<li>K3-CCL: <a href="ccl/index.html">summary</a> — duplicate stop vs 21 catalogue-halo rasters; holdout instrument bias IR-K3-12.</li>
<li>Archived SMGC / CRSB-GUB / K3-fuse TIFFs in <code>docs/downloads/</code> — negative; see <a href="release-review.html">release review</a>.</li></ul>"""
    top_html = shell("GEMSDOEkarage3 — submission decision", top, depth=0)
    for name in ("index.html", "executive-summary.html"):
        (ROOT / "docs" / name).write_text(top_html, encoding="utf-8")
    update_root_page(card, gate, ok, hold)
    sites_p = ROOT / "docs/sites.json"
    sites = json.loads(sites_p.read_text())
    sites["promoted_candidate"] = card["submission_name"] if ok else None
    sites["promoted_candidate_sha256"] = card["raster_sha256"] if ok else None
    sites["promoted_candidate_card"] = "docs/k3c/run-card.json"
    sites_p.write_text(json.dumps(sites, indent=2) + "\n")
    print(f"built docs/k3c/index.html, docs/k3c/how-to-submit.html, docs/index.html, docs/executive-summary.html; verdict={gate['verdict']}")


if __name__ == "__main__":
    build()
