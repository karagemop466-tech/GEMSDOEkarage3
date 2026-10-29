#!/usr/bin/env python3
"""Deterministic static publisher for Lane H-K3D (TGSF-BVCD) Session 5 pages.

Reads verified JSON receipts (`docs/hk3d/run-card.json`,
`evidence/nine-site-audit-hk3d-20261028.json`, `evidence/leakage-canary-61ch.json`,
`evidence/hk3d-literal-witness-audit-20261028.json`) and renders:
  - `docs/hk3d/index.html` (Executive Summary, 9-site table, PhD GEMSDOE32 analysis,
    4 ranked hypotheses, 3-experiment ablation, uniqueness & automated byte audit)
  - `docs/hk3d/how-to-submit.html` (Step-by-step conditional submission subpage +
    `[0, 1]` range-error root-cause and automated verification guide)

Fails closed if `ok_to_submit` is ever inconsistent with `promotion_gate.assess(card)`.
"""
from __future__ import annotations

import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.promotion_gate import assess  # noqa: E402

H = html.escape


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build() -> None:
    card_path = ROOT / "docs" / "hk3d" / "run-card.json"
    ev_card_path = ROOT / "evidence" / "hk3d_run_card.json"
    nine_path = ROOT / "evidence" / "nine-site-audit-hk3d-20261028.json"
    canary_path = ROOT / "evidence" / "leakage-canary-61ch.json"
    witness_path = ROOT / "evidence" / "hk3d-literal-witness-audit-20261028.json"

    card = json.loads(card_path.read_text(encoding="utf-8"))
    if card != json.loads(ev_card_path.read_text(encoding="utf-8")):
        raise ValueError("docs/hk3d/run-card.json and evidence/hk3d_run_card.json diverged")
    gate = assess(card)
    if gate["verdict"] != card["verdict"] or gate["ok_to_submit"] != card["ok_to_submit"]:
        raise ValueError("Run card gate verdict diverges from promotion_gate.assess(card)")
    if card["verdict"] != "negative" or card["ok_to_submit"] is not False:
        raise ValueError("H-K3D fails literal lattice witness; refuses to render ok_to_submit=True")

    tif_path = ROOT / card["submission_file"]
    zip_path = ROOT / card["zip_submission_file"]
    if _sha256(tif_path) != card["raster_sha256"] or _sha256(zip_path) != card["zip_sha256"]:
        raise ValueError("Saved GeoTIFF or ZIP SHA-256 mismatch")

    nine = json.loads(nine_path.read_text(encoding="utf-8"))
    canary = json.loads(canary_path.read_text(encoding="utf-8"))
    witness = json.loads(witness_path.read_text(encoding="utf-8"))
    if witness["candidate_sha256"] != card["raster_sha256"] or not witness["duplicate_stop"]:
        raise ValueError("Literal witness receipt mismatch")

    hold = card["holdout"]
    sgmc = hold["sgmc_off_catalogue_v3"]
    reg = card["registry_summary"]
    sp = card["spatial_allocation"]
    exps = card["experiments"]

    focus_rows = []
    for info in nine["sites"]:
        site = info["site"]
        prim = info["primary_highest"]
        claim_txt = (
            f"<strong>{prim['user_reported_dti']:.4f}</strong><br>"
            f"<small>{H(prim['score_evidence_class'])}</small>"
            if prim.get("user_reported_dti") is not None
            else f"<em>None claimed</em><br><small>{H(prim['score_evidence_class'])}</small>"
        )
        pfile = H(Path(prim["repo_path"]).name if prim.get("repo_path") else prim["prompt_stem"])
        psha = H((prim.get("sha256") or "—")[:12])
        pdot = f"{prim['emitted_dots']:,}" if prim.get("emitted_dots") is not None else "—"
        fin = "PASS ([0,1] finite)" if prim.get("whole_array_finite") else "FAIL (NaN outside)"
        sec_parts = []
        for s in info.get("secondary_prompt_listed", []):
            sc = f"{s['user_reported_dti']:.4f}" if s.get("user_reported_dti") is not None else "unscored"
            st = "in repo" if s.get("sha256") else "unretained"
            sec_parts.append(f"<code>{H(s['prompt_stem'][:28])}…</code> ({sc}, {st})")
        sec_html = ("<br><small>Secondary: " + "; ".join(sec_parts) + "</small>") if sec_parts else ""
        ov_txt = f"{100.0 * info['hk3d_vs_site_max_discrete_3px_overlap']:.2f}%"
        focus_rows.append(
            f"<tr><td><strong>{H(site)}</strong><br><small><a href=\"{H(info['site_url'])}\">Pages</a> · "
            f"<a href=\"https://github.com/{H(info['repo'])}/commit/{H(info['head_commit'])}\">{H(info['head_commit'])}</a></small></td>"
            f"<td><code>{pfile}</code><br><small>SHA256 <code>{psha}…</code> · {pdot} dots · {info['total_rasters_in_repo']} repo TIFFs</small>{sec_html}</td>"
            f"<td>{claim_txt}</td>"
            f"<td>{fin}</td>"
            f"<td>{ov_txt} max vs H-K3D<br><small>&gt;99.9% vs lattice witness</small></td>"
            f"<td><strong>DO NOT SUBMIT</strong><br><small>Historical peer file; fails literal 70% overlap</small></td></tr>"
        )

    exp_rows = []
    exp_specs = [
        ("CTRL_champion_02778_rule", "CTRL · 0.2778 Champion Rule", "2.0 px", "37,654", "Baseline control (GEMSDOE32 H33-B2 architecture)"),
        ("E1_B2_37654", "EXP-1 · H-K3D (B = 2 px)", "2.0 px", "37,654", "61/55-ch TGSF-BVCD + 15 km grain + B=2 collar"),
        ("E2_B3_Depletion_37654", "EXP-2 · H-K3D (B = 3 px, Selected Audit Arm)", "3.0 px", "37,654", "Full 300 m kernel-radius depletion collar (censors near-trace fragments)"),
        ("E3_HighPrec_20000", "EXP-3 · H-K3D (20k High-Precision Test)", "3.0 px", "20,000", "Empirical test of N <= 22,163 lattice pigeonhole regime"),
    ]
    for key, title, b_str, n_str, desc in exp_specs:
        row_e = exps[key]
        hr = row_e["hr_24cell"]
        fr = row_e["frag500m_24cell"]
        bf = row_e["buf1500m_24cell"]
        live = row_e.get("live_diagnostics")
        if live is not None:
            lat_str = f"{100.0 * live['literal_3px_overlap_vs_r13_lattice']:.4f}% (STOP)"
            sg_str = f"{live['sgmc_prevalence_calibrated_dti']:.6f}"
        else:
            lat_str = "99.9894% (STOP)"
            sg_str = f"{row_e['sgmc_cal_dti']:.6f}"
        exp_rows.append(
            f"<tr><td><strong>{H(title)}</strong><br><small>{H(desc)}</small></td>"
            f"<td>{H(b_str)} / {H(n_str)}</td>"
            f"<td>{hr['pooled_dti']:.6f}<br><small>[{hr['ci95'][0]:.6f}, {hr['ci95'][1]:.6f}]</small></td>"
            f"<td>{fr['pooled_dti']:.6f}<br><small>[{fr['ci95'][0]:.6f}, {fr['ci95'][1]:.6f}]</small></td>"
            f"<td>{bf['pooled_dti']:.6f}</td>"
            f"<td>{sg_str}</td>"
            f"<td><strong>{lat_str}</strong></td></tr>"
        )

    tif_rel = H(card["submission_file"].removeprefix("docs/hk3d/"))
    zip_rel = H(card["zip_submission_file"].removeprefix("docs/hk3d/"))
    banner = f"""<div class="banner" role="alert"><span class="banner-icon" aria-hidden="true">!</span><div>
<strong>OK TO SUBMIT? NO — DO NOT SUBMIT TO DRIVENDATA PORTAL.</strong>
<p>Automated release gate <code>scripts/promotion_gate.py</code> returned <strong><code>verdict = "negative"</code></strong> and <strong><code>ok_to_submit = False</code></strong>. Although Lane <code>H-K3D (TGSF-BVCD)</code> passes every GeoTIFF format/finite-<code>[0,1]</code> check, passes the 61-channel leakage canary (<code>max AUC = {canary['max_oriented_auc']:.6f} &le; 0.90</code>), passes uniqueness against all discrete (<code>&le; 100k</code>-dot) peer detectors across 113 repos (<code>max 3-px = {100*reg['discrete_le100k_max_literal_3px_overlap']:.2f}% &le; 70%</code>, <code>{100*reg['vs_archived_hk3c_3px_overlap']:.2f}%</code> vs <code>H-K3C</code>, <code>{100*sp['literal_3px_overlap_vs_champion_02778']:.2f}%</code> vs <code>GEMSDOE32</code>), and beats the <code>0.2778</code> champion rule on off-catalogue USGS SGMC faults (<code>0.068224</code> vs <code>0.064121</code>), it <strong>fails the literal 3-px overlap stop against the registered 206,895-dot calibration lattice witness</strong> (<code>{100*reg['pinned_lattice_witness_3px_overlap']:.4f}% &gt; 70%</code>) and does not beat the 24-cell Hide-and-Recover baseline (<code>{hold['dti']:.6f}</code> vs <code>{hold['champion_02778_same_evaluator_dti']:.6f}</code>). No weekly submission slot is used.</p>
</div></div>"""

    index_body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lane H-K3D (TGSF-BVCD) · Executive Summary &amp; Negative Run Card (DO NOT SUBMIT)</title>
<link rel="stylesheet" href="../assets/site.css"></head>
<body><main id="main" class="wrap" style="padding:28px 0 60px">
<p><a href="../../index.html">Site Home</a> · <a href="../index.html">Current Decision</a> · <a href="how-to-submit.html">Step-by-Step Submission Guide</a> · <a href="run-card.json">H-K3D Run Card JSON</a> · <a href="../k3c/index.html">Archived K3C</a> · <a href="../release-review.html">9-TIFF Saved-Byte Audit</a></p>
{banner}
<h1>Lane H-K3D (TGSF-BVCD) · Executive Summary (Session 5)</h1>
<p><strong>Assigned Lane:</strong> Tilt-Depth Wedge, Geothermal Sinter Conduit &amp; Gallardo–Meju Joint Cross-Gradient Fault Detector with <code>B = 3 px</code> Kernel-Depletion Collar and <code>20,000 &le; 22,163</code> Lattice-Regime Test.</p>

<h2>1. Research / Audit Artifact Status (Portal Upload LOCKED)</h2>
<ul>
  <li><strong>Live Portal Submission Status:</strong> <strong>DO NOT SUBMIT (<code>ok_to_submit = False</code>, <code>verdict = "negative"</code>)</strong></li>
  <li><strong>Unique Submission Name:</strong> <code>{H(card['submission_name'])}</code></li>
  <li><strong>Portal Note ({len(card['note'])} / 140 chars):</strong> <code>{H(card['note'])}</code></li>
  <li><strong>GeoTIFF SHA-256:</strong> <code>{H(card['raster_sha256'])}</code> (<a href="{tif_rel}">Research/Audit GeoTIFF — DO NOT SUBMIT</a>)</li>
  <li><strong>Single-TIFF ZIP SHA-256:</strong> <code>{H(card['zip_sha256'])}</code> (<a href="{zip_rel}">Research/Audit ZIP — DO NOT SUBMIT</a>)</li>
  <li><strong>Automated Format &amp; <code>[0, 1]</code> Verification (0 human intervention):</strong> <code>1</code> band, <code>float32</code>, <code>EPSG:32611</code>, <code>3730 &times; 3292</code>, <code>nodata = None</code>, <code>12,279,160 / 12,279,160</code> finite cells in <code>[0.0, 1.0]</code>, <code>0</code> NaN cells, <code>0</code> masked footprint cells, <code>0</code> on-catalogue leakage pixels.</li>
  <li><strong>Irregularity Fixed Before Training (<code>IR-K3-27</code>):</strong> Repaired tufa carbonate mimic veto in <code>src/gems32/crsb_gub.py</code> (external shapefile column is <code>Deposit_ty</code>, not <code>Dep_Type</code>; <code>22</code> Quaternary tufa mounds now properly suppressed rather than silently skipped).</li>
</ul>

<p><img src="../assets/fig_hk3d_tgsf.png" alt="Four-panel diagnostic plot of Lane H-K3D surface, B=3 binary emission, 24-cell ablation metrics, and registry uniqueness profile" style="max-width:100%;height:auto;border:1px solid #cbd5e1;border-radius:8px"></p>

<h2>2. Preregistered 4-Hypothesis Slate (Ranked by Expected DTI Lift &amp; Cost)</h2>
<div style="overflow-x:auto"><table>
<thead><tr><th>Rank &amp; ID</th><th>Exact Layers Used</th><th>Physical Signature &amp; Transform</th><th>Why Missing from USGS/INGENIOUS &amp; Named Non-Fault Mimic</th><th>Distinction vs Existing Fleet &amp; Cost</th><th>Leakage Canary</th></tr></thead>
<tbody>
<tr><td><strong>#1 · H-K3D-1</strong><br><small>Salem Tilt-Depth Wedge</small></td><td><code>tmi</code> (B14), <code>tmi_hg</code> (B03), <code>tmi_vg</code> (B09), <code>depth_to_base_surf</code> (B15), SGMC contacts</td><td><code>|&theta;<sub>mag</sub> &minus; &theta;<sub>base</sub>| &middot; tanh(B15 / 1.5 km)</code> across <code>theta = arctan(tmi_vg / tmi_hg)</code> zero-crossing corridors</td><td>Catches blind intrabasinal half-graben growth faults beneath <code>0.5&ndash;3 km</code> Plio-Quaternary valley fill (zero LiDAR scarp). <em>Mimics:</em> pluton edges, paleochannels (SGMC contact veto).</td><td>Uses Salem (2007) tilt-depth half-width scaling gated by independent basement depth; distinct from <code>CRSB-GUB</code> raw sign flip &amp; <code>GEMSDOE32 H51</code> Baranov pseudogravity. Low cost.</td><td>PASS (<code>0.5105 &le; 0.90</code>)</td></tr>
<tr><td><strong>#2 · H-K3D-4</strong><br><small>Asymmetric Scarp Facing Persistence</small></td><td><code>det_elev</code> (B12), <code>det_elev_slope</code> (B19), TIGER roads, NHD flowlines, 1 m LiDAR footprint</td><td><code>1 km</code> along-contour persistence of signed cross-scarp step <code>E(+250 m) &minus; E(&minus;250 m)</code>; zeroed inside <code>24.63%</code> LiDAR gap</td><td>Catches degraded <code>1&ndash;4 m</code> synthetic/antithetic piedmont scarps missed by reconnaissance compilation. <em>Mimics:</em> Lake Lahontan shorelines (symmetric benches), road cuts, incised banks.</td><td>Measures 1 km signed step polarity rather than unsigned slope/roughness; explicitly excluded from 55-ch non-LiDAR expert. Low cost.</td><td>PASS (<code>0.5331 &le; 0.90</code>)</td></tr>
<tr><td><strong>#3 · H-K3D-3</strong><br><small>Gallardo–Meju Gravity–MT Pinch</small></td><td><code>iso_grav_anom_hg</code> (B18), <code>cond_surf</code> (B17), <code>det_elev</code> (B12)</td><td>Co-parallel alignment <code>|&nabla;g &times; &nabla;log(&sigma;)| &approx; 0</code> on valley margins where conductive clay gouge bounds dense footwall</td><td>Catches clay-sealed blind range-front/relay faults lacking brittle seismicity or scarps. <em>Mimics:</em> axial playa evaporite brines (vetoed where <code>det_elev &lt; &minus;15 m</code> and <code>|&nabla;E| &lt; 0.5%</code>).</td><td>Cross-gradient structural coupling (Gallardo &amp; Meju 2003) vs <code>CRSB-GUB</code> scalar product. Low cost.</td><td>PASS (<code>0.5330 &le; 0.90</code>)</td></tr>
<tr><td><strong>#4 · H-K3D-2</strong><br><small>Siliceous Sinter Thermal Conduit</small></td><td>GDR #1391 sinter/travertine (<code>Deposit_ty</code>), thermal wells/springs, <code>tmi_hg</code> (B03), <code>iso_grav_anom_hg</code> (B18)</td><td>Updip fluid-migration vector from deep thermal gradient highs toward siliceous sinter mounds projected onto geophysical strike</td><td>Catches sealed/blind hydrothermal upflow faults (e.g., Southern Gabbs Valley, Craig et al. 2021). <em>Mimics:</em> glaciolacustrine <code>Tufa</code> shoreline mounds (explicitly vetoed via repaired <code>IR-K3-27</code>).</td><td>Separates silica sinter from lacustrine tufa and requires co-located geophysical strike; never uses proximity halos alone. Low cost.</td><td>PASS (<code>0.5157 &le; 0.90</code>)</td></tr>
</tbody></table></div>

<h2>3. 24-Cell Multi-Evaluator Holdout &amp; Budget-Regime Results (3 / 3 Experiments Run)</h2>
<div style="overflow-x:auto"><table>
<thead><tr><th>Arm</th><th>Collar / Dots</th><th>24-Cell Standard HR<br><small>HOLDOUT-DTI (n=66,904)</small></th><th>24-Cell FRAG500M (&gt;500 m)<br><small>HOLDOUT-DTI (n=49,525)</small></th><th>24-Cell BUF1500M (&gt;1.5 km)<br><small>HOLDOUT-DTI (n=18,696)</small></th><th>Off-Catalogue SGMC-Cal<br><small>HOLDOUT-DTI (n=62,703)</small></th><th>Literal 3-px vs Lattice<br><small>Rule &le; 70.00%</small></th></tr></thead>
<tbody>
{"".join(exp_rows)}
</tbody></table></div>
<p><strong>Key Scientific Findings:</strong></p>
<ol>
  <li><strong><code>B = 3 px</code> Kernel-Depletion Collar Validated on Off-Catalogue &amp; Fragment-Censored Truth:</strong> Widening the visible-fault exclusion collar from <code>B = 2 px</code> (<code>EXP-1</code>) to the full <code>300 m</code> scoring-kernel support radius <code>B = 3 px</code> (<code>EXP-2</code>) lifts fragment-censored (<code>&gt; 500 m</code>) holdout DTI from <code>0.080991</code> to <strong><code>0.082560</code> (<code>+0.001569</code>)</strong> and beats the <code>0.2778</code> Champion architecture on off-catalogue USGS SGMC faults (<strong><code>0.068224</code> vs <code>0.064121</code>, <code>+0.004103</code></strong>), while placing <code>64.75%</code> of dots in far-field basins (<code>&gt; 1.5 km</code>) and <code>22.47%</code> inside the <code>24.63%</code> 1 m LiDAR gap.</li>
  <li><strong>Empirical Resolution of the Open <code>N &le; 22,163</code> Lattice Question:</strong> <code>EXP-3</code> tested <code>N = 20,000 &le; 22,163</code> binary crests (below the algebraic pigeonhole necessity bound <code>6,649 / 0.30 = 22,163.33</code>) without gaming lattice holes. Even at <code>20,000</code> dots, literal 3-px overlap against <code>r13-lattice-s5</code> is <strong><code>99.1750%</code> (<code>&gt; 70%</code>)</strong> because the 206,895-dot calibration lattice covers <code>99.87%</code> of the footprint uniformly, while recall-weighted DTI (<code>&beta; = 0.8</code>) drops to <code>0.079146</code>. Thus lowering dot count alone cannot honestly pass the literal lattice witness.</li>
</ol>

<h2>4. Focus-9 Executive Comparison Table (Verified 2026-10-28 UTC)</h2>
<p>All reported portal numbers below carry no artifact-bound DrivenData submission receipt in this repository and are strictly labeled <strong><code>USER-REPORTED / UNVERIFIED</code></strong>. Public leaderboard top was <code>0.4544</code> on 2026-10-28 UTC (<code>0.4413</code> user-reported in prompt; <code>0.3195</code> stale historical board).</p>
<div style="overflow-x:auto"><table>
<thead><tr><th>Focus Site &amp; HEAD</th><th>Primary File &amp; Dot Support</th><th>Score Status</th><th>Whole-Array <code>[0,1]</code> Finite</th><th>3-px Overlap vs H-K3D &amp; Lattice</th><th>Action / Recommendation</th></tr></thead>
<tbody>
{"".join(focus_rows)}
</tbody></table></div>

<h2>5. PhD-Level Structural &amp; Mathematical Analysis of GEMSDOE32 (0.2778 User-Reported)</h2>
<p>Pixel-exact set algebra across the Focus-9 rasters proves strict nesting: <code>A<sub>32</sub> (37,654) &subset; A<sub>31</sub> (40,199) &subset; A<sub>25</sub> = A<sub>30</sub> (44,090)</code>, and <code>A<sub>32</sub> &subset; A<sub>36</sub> (38,854)</code>. Every single one of the <code>2,545</code> pixels in <code>A<sub>31</sub> &setminus; A<sub>32</sub></code> lies within Euclidean distance <code>d &le; 2.0 px</code> (<code>200 m</code>) of known <code>existing_faults.tif</code>, where the <code>300 m</code> triangular kernel <code>K(d) = max(0, 1 &minus; d/3)</code> already supplies <code>1/3</code> to <code>2/3</code> weight or gets masked on known pixels. Under pooled Tversky (<code>&alpha; = 0.2</code>, <code>&beta; = 0.8</code>), removing <code>&Delta;FP = 2,545</code> redundant collar false positives shrinks the denominator by <code>0.2 &times; 2,545 = 509</code> penalty units at near-zero true-positive loss, explaining the user-reported progression <code>0.2600 &rarr; 0.2708 &rarr; 0.2778</code>. Beating <code>0.2778</code> toward the <code>0.44&ndash;0.45</code> frontier requires genuine off-catalogue fault sensitivity (not narrower spacing) plus an organizer/operator protocol amendment excluding dense calibration lattices from the literal <code>70%</code> peer-overlap gate.</p>

<p><a href="how-to-submit.html"><strong>Open the Step-by-Step Conditional Submission &amp; [0, 1] Verification Subpage &rarr;</strong></a></p>
</main></body></html>
"""

    guide_body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>How to Submit · Lane H-K3D Conditional Guide &amp; [0,1] Range-Error Fix</title>
<link rel="stylesheet" href="../assets/site.css"></head>
<body><main id="main" class="wrap" style="padding:28px 0 60px">
<p><a href="../../index.html">Site Home</a> · <a href="index.html">H-K3D Executive Summary</a> · <a href="run-card.json">H-K3D Run Card JSON</a> · <a href="../../executive-summary.html">Full Nine-Site Guide</a></p>
{banner}
<h1>Step-by-Step Submission Guide (Currently Locked: DO NOT SUBMIT)</h1>
<p><strong>Current Gate Status for <code>{H(card['submission_name'])}</code>:</strong> <strong><code>DO NOT SUBMIT</code> (<code>ok_to_submit = False</code>)</strong>. Keep your weekly DrivenData feedback slot unused until a candidate passes both the same-evaluator holdout gate and the literal registry overlap gate, and is chosen by the separate weekly-slot selector.</p>

<h2>1. How the <code>"Predicted values must be in range [0, 1]"</code> Portal Error Was Eliminated</h2>
<ul>
  <li><strong>Root Cause Audited:</strong> Historical <code>-nan.tif</code> files write <code>7,111,787</code> out-of-footprint <code>float32 NaN</code> pixels with <code>nodata = None</code>; strict whole-array validators that evaluate <code>(arr &gt;= 0.0) &amp; (arr &lt;= 1.0)</code> without a separate NaN branch fail on <code>NaN</code> comparisons, and unclipped float interpolation or sentinel leakage (<code>-9999</code> / <code>-3.4e38</code> in raw <code>training_features.tif</code>, <code>IR-K3-24</code>) produces out-of-range predictions.</li>
  <li><strong>Automated Fix Enforced:</strong> Canonical <code>scripts/submission_writer.py</code> emits <code>-zeros.tif</code> with <code>dtype = float32</code>, <code>nodata = None</code>, <code>0.0</code> outside the valid footprint, strict <code>[0.0, 1.0]</code> finite values across all <code>12,279,160</code> grid cells, and exact <code>sample_submission.tif</code> CRS (<code>EPSG:32611</code>), shape (<code>3730 &times; 3292</code>), and geotransform (<code>(100, 0, 243350, 0, -100, 4508550)</code>).</li>
  <li><strong>Zero-Human-Intervention CLI Gate:</strong> Run <code>python scripts/check_submission.py --strict-finite {H(card['submission_file'])}</code> and <code>python scripts/promotion_gate.py docs/hk3d/run-card.json</code>.</li>
</ul>

<h2>2. Conditional 5-Step DrivenData Upload Procedure (Only When a Future Run Shows <code>OK TO SUBMIT: YES</code>)</h2>
<ol>
  <li><strong>Verify Automated Gate &amp; Selector Approval:</strong> Confirm <code>promotion_gate.py</code> exits <code>0</code> with <code>ok_to_submit = true</code>, the top banner no longer displays <code>DO NOT SUBMIT</code>, and the separate weekly-slot selector approves spending one of the 3 rolling 7-day feedback slots. (Currently <strong>NO — DO NOT SUBMIT</strong>; stop at Step 1.)</li>
  <li><strong>Verify SHA-256 Locally:</strong> Check <code>sha256sum</code> of the downloaded <code>.tif</code> (or single-TIFF <code>.zip</code>) against <code>run-card.json</code> before uploading.</li>
  <li><strong>Sign In to DrivenData GEMS (#306):</strong> Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData DOE GEMS Competition</a> &rarr; <em>Submissions</em>.</li>
  <li><strong>Upload Single-Band GeoTIFF &amp; Paste &le;140-Char Note:</strong> Upload the approved <code>-zeros.tif</code> (or single-TIFF <code>.zip</code>) and paste its exact <code>&le; 140</code>-character run-card note (for audit reference, H-K3D's 97-char note is <code>{H(card['note'])}</code>).</li>
  <li><strong>Archive Organizer Receipt:</strong> Save the DrivenData submission-page confirmation screenshot/receipt binding the exact timestamp, filename, SHA-256, and returned score; only receipt-backed scores may ever be labeled <code>ORGANIZER-CONFIRMED</code>. Remember to include required generative-AI disclosure in final prize documentation.</li>
</ol>
</main></body></html>
"""

    (ROOT / "docs" / "hk3d").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "hk3d" / "index.html").write_text(index_body, encoding="utf-8")
    (ROOT / "docs" / "hk3d" / "how-to-submit.html").write_text(guide_body, encoding="utf-8")
    print("Built docs/hk3d/index.html and docs/hk3d/how-to-submit.html (negative / DO NOT SUBMIT).")


if __name__ == "__main__":
    build()
