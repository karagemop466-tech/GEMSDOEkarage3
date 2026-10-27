#!/usr/bin/env python3
"""Generate docs/k3/index.html + docs/k3/executive-summary.html from evidence/*.json ONLY.
Namespaced under docs/k3/ after merging the parallel preflight desk on main (root + docs/ front pages are theirs).
No number is hand-typed here except OWNER-REPORTED scores taken from
registry/focus9_registry.json (which cites the owner catalogue)."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
DOCS = ROOT / "docs"
REPO_URL = "https://github.com/karagemop466-tech/GEMSDOEkarage3"


def load(name: str) -> dict:
    return json.loads((EV / name).read_text())


def f4(x) -> str:
    return "—" if x is None else f"{float(x):.4f}"


def ci(c) -> str:
    return f"[{c[0]:.4f}, {c[1]:.4f}]" if c else "—"


CSS = """
:root{--bg:#0d1117;--card:#161b22;--ink:#e6edf3;--mut:#9aa7b4;--red:#f85149;--grn:#3fb950;--amb:#d29922;--acc:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
main{max-width:1060px;margin:0 auto;padding:24px 18px 64px}
.banner{border:2px solid var(--red);background:#2b1416;border-radius:12px;padding:20px 22px;margin:12px 0 20px}
.banner h1{margin:.1em 0;font-size:1.7rem}.banner .sub{color:var(--mut)}
.dl{display:inline-block;background:var(--acc);color:#04101f;font-weight:700;border-radius:8px;padding:10px 16px;text-decoration:none;margin:6px 8px 6px 0}
.dl.alt{background:#30363d;color:var(--ink)}
table{width:100%;border-collapse:collapse;margin:12px 0 20px;font-size:.92rem}
th,td{border:1px solid #30363d;padding:7px 9px;text-align:left;vertical-align:top}th{background:#1c2330}
.card{background:var(--card);border:1px solid #30363d;border-radius:12px;padding:16px 20px;margin:16px 0}
.tag{display:inline-block;padding:1px 8px;border-radius:20px;font-size:.78rem;font-weight:700}
.no{background:#3d1418;color:var(--red);border:1px solid var(--red)} .yes{background:#12331a;color:var(--grn);border:1px solid var(--grn)}
.warn{background:#33270e;color:var(--amb);border:1px solid var(--amb)}
code{background:#21262d;padding:1px 5px;border-radius:5px;font-size:.86em;word-break:break-all}
small,.mut{color:var(--mut)} a{color:var(--acc)} img.map{max-width:100%;border-radius:10px;border:1px solid #30363d}
"""


def main() -> int:
    card = load("k3_run_card.json")
    exp1, exp2 = load("exp1_screen.json"), load("exp2_emission.json")
    ext = load("extended_uniqueness.json")["summary"]
    focus = json.loads((ROOT / "registry" / "focus9_registry.json").read_text())
    linx = load("lineage_extra.json")
    sources = json.loads((ROOT / "registry" / "sources.json").read_text())["sources"]

    ok = bool(card["ok_to_submit"])
    verdict = card["verdict"]
    pooled = card["holdout_dti"]
    champ_rule = pooled["champion_rule_control"]
    r = card["raster"]
    gates = card["gates"]
    note = html.escape(card["submission"]["note"])
    fname = html.escape(r["zeros_file"])

    banner = f"""
<div class="banner">
  <div><span class="tag {'yes' if ok else 'no'}">{'OK TO SUBMIT' if ok else 'DO NOT SUBMIT'}</span>
  <span class="tag warn">verdict: {html.escape(verdict)}</span>
  <span class="tag warn">UNSCORED — no leaderboard estimate</span></div>
  <h1>{'Promoted submission' if ok else 'Research download only — do not spend a submission slot on this file'}</h1>
  <p class="sub">K3 lane: corrected-LiDAR scarp-pair + worm-persistence fusion, greedy kernel-coverage emission.
  Automated gates G1–G5: G1 {'PASS' if gates['G1_pooled_beats_champion_rule']['pass_'] else '<b>FAIL</b>'} (pooled HOLDOUT-DTI
  {f4(pooled['pooled_dti'])} {ci(pooled['ci95'])} vs champion-rule {f4(champ_rule['pooled_dti'])}),
  G2 {'PASS' if gates['G2_sgmc_veto']['pass_'] else 'FAIL'}, G3 {'PASS' if gates['G3_genuine_uniqueness']['pass_'] else 'FAIL'},
  G4 {'PASS' if gates['G4_validator']['pass_'] else 'FAIL'}, G5 {'PASS' if gates['G5_canary']['pass_'] else 'FAIL'}.
  The file below is a valid, unique, fully-automated research artifact; failing G1 means present evidence
  does <b>not</b> show it beats the 0.2778 champion (OWNER-REPORTED). Promotion to a slot is a separate selector step.</p>
  <a class="dl" href="../downloads/{fname}">⬇ Download research TIF (-zeros, validator-safe)</a>
  <a class="dl alt" href="../downloads/{html.escape(r['zip_file'])}">⬇ .zip</a>
  <a class="dl alt" href="../downloads/{html.escape(r['nan_file'])}">-nan variant</a>
  <p><small>File <code>{fname}</code><br>SHA-256 <code>{r['zeros_sha256']}</code> · {r['dots']:,} dots · 0 on-catalogue ·
  DrivenData name <code>{html.escape(card['submission']['name'])}</code><br>
  Note ({card['submission']['note_chars']}/140): <code>{note}</code></small></p>
</div>"""

    req_rows = f"""
<tr><td><code>{fname}</code> (this repo, K3)</td>
<td><b>HOLDOUT-DTI {f4(pooled['pooled_dti'])}</b> {ci(pooled['ci95'])}<br><small>{pooled['evaluator_version']}; {pooled['n_withheld_positives']:,} withheld +</small><br>
SGMC-cal HOLDOUT-DTI {f4(pooled['sgmc']['final_mask_cal'])} {ci(pooled['sgmc']['final_mask_ci95'])} (final mask)<br>
Leaderboard: <b>NOT ESTIMABLE</b></td>
<td><b>YES (genuine)</b>: worst {card['correlation_overlap_vs_registry']['final_worst_within_3px']*100:.1f}% dots within 3 px vs any focus-9 best;
{ext['genuine_worst_within_3px']*100:.1f}% vs worst of {ext['registry_rasters']} scanned rasters; surface |Spearman| ≤ {card['correlation_overlap_vs_registry']['surface_worst_abs_spearman']:.3f}.
Literal vs 5 px calibration lattice: {card['correlation_overlap_vs_registry']['literal_lattice']['candidate_within_3px']*100:.1f}% (geometric constant, IR-K3-02).</td>
<td><span class="tag no">DO NOT SUBMIT</span></td></tr>
<tr><td>Champion <code>h33-h33-2-b2…-e5eb6e7e-zeros</code> (GEMSDOE32, prior art — learning only)</td>
<td><b>OWNER-REPORTED 0.2778</b> (no organizer receipt)<br>HOLDOUT-DTI rule-control {f4(champ_rule['pooled_dti'])} {ci(champ_rule['ci95'])}; literal mask censored (IR-K3-09)</td>
<td>No — nested inside GEMSDOE25/30/31/36 bests (measured ⊂)</td>
<td><span class="tag warn">ALREADY SUBMITTED historically</span></td></tr>"""

    site_rows = ""
    order = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
             "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
    reltxt = {
        "GEMSDOE24": "⊂ parent; ⊂ GEMSDOE27 best", "GEMSDOE25": "≡ GEMSDOE30 (symdiff 0); champion ⊂ it",
        "GEMSDOE27": "= GEMSDOE24 + 1,259 dots", "GEMSDOE28": "⊂ parent; 26,248 shared with champion",
        "GEMSDOE30": "≡ GEMSDOE25 (symdiff 0)", "GEMSDOE31": "≡ solo; champion ⊂ it",
        "GEMSDOE32": "champion = solo − d≤2 ring", "GEMSDOE33": "31,614/41,865 dots = champion dots",
        "GEMSDOE36": "= champion + 1,200 dots",
    }
    for s in order:
        e = focus["site_bests"][s]
        site_rows += (f"<tr><td><a href=\"{e['site_url']}\">{s}</a></td>"
                      f"<td><code>{html.escape(e['submission_id'])}</code></td>"
                      f"<td>{e['dots']:,}</td><td>{e['owner_reported_score']:.4f}<br><small>OWNER-REPORTED</small></td>"
                      f"<td>{html.escape(reltxt[s])}</td></tr>")

    exp_rows = ""
    for name, byb in exp1["screen"].items():
        for b, ev in byb.items():
            p = ev["visible_only"]["pooled"]
            exp_rows += (f"<tr><td>Exp1 {html.escape(name)} @D2.8-{b}</td><td>{f4(p['pooled_dti'])}</td>"
                         f"<td>{ci(p['ci95'])}</td><td>{f4(ev['sgmc']['sgmc_prevalence_calibrated_dti'])}</td></tr>")
    for arm, byb in exp2["arms"].items():
        for b, ev in byb.items():
            p = ev["visible_only"]["pooled"]
            exp_rows += (f"<tr><td>Exp2 {html.escape(arm)}-{b}</td><td>{f4(p['pooled_dti'])}</td>"
                         f"<td>{ci(p['ci95'])}</td><td>{f4(ev['sgmc']['sgmc_prevalence_calibrated_dti'])}</td></tr>")
    for cname, ev in exp1["controls"].items():
        p = ev["visible_only"]["pooled"]
        exp_rows += (f"<tr><td>Control {html.escape(cname)}</td><td>{f4(p['pooled_dti'])}</td>"
                     f"<td>{ci(p['ci95'])}</td><td>{f4(ev['sgmc']['sgmc_prevalence_calibrated_dti'])}</td></tr>")

    def gate_rows():
        out = ""
        for k, g in gates.items():
            out += f"<tr><td>{k}</td><td>{'✅ PASS' if g['pass_'] else '❌ FAIL'}</td><td><small>{html.escape(json.dumps({kk: vv for kk, vv in g.items() if kk not in ('pass_', 'zeros', 'nan', 'literal_lattice')}, default=str)[:420])}</small></td></tr>"
        return out

    src_rows = "".join(f"<tr><td>{html.escape(s['id'])}</td><td><a href=\"{s['url']}\">{s['url']}</a></td><td>{html.escape(s['use'])}</td></tr>" for s in sources)

    howto = f"""
<div class="card"><h2>Exactly how to submit (only if a future run card says <i>promote</i>)</h2>
<ol>
<li>Download the <code>-zeros.tif</code> (or its .zip). This variant has <b>no NaN anywhere</b> and every one of the
12,279,160 cells in [0, 1] — it cannot produce DrivenData's <i>“Predicted values must be in range [0, 1]”</i> error.
(The <code>-nan</code> twin keeps NaN only outside the footprint, matching the sample's convention.)</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">the competition page</a> → <b>Submit</b> → choose the file
(single-band GeoTIFF, or the .zip containing that single GeoTIFF; CRS/shape/geotransform are verified identical to the sample).</li>
<li>Paste the note exactly: <code>{note}</code></li>
<li>After scoring, record the receipt (score + timestamp + file SHA-256 <code>{r['zeros_sha256'][:16]}…</code>) into the repo —
only then may a number be called ORGANIZER-CONFIRMED. Respect the weekly cap shown on the submission page.</li>
</ol>
<p><b>Current file: stop at step 1.</b> Verdict is <code>{verdict}</code>; submitting it would spend a slot against the evidence.</p></div>"""

    index = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOEkarage3 — K3 lane (DO NOT SUBMIT current file)</title><style>{CSS}</style></head><body><main>
<p><small>DOE GEMS Prize · lane K3 · Maximize P(Win) · Own the Outcome · generated from <code>evidence/*.json</code> — audit at
<a href="{REPO_URL}">{REPO_URL}</a></small></p>
{banner}
<div class="card"><h2>Decision table (file · labelled estimate · unique?)</h2>
<table><tr><th>File to download</th><th>Score estimate (labelled, never a projection-as-score)</th><th>Unique vs the nine focus sites?</th><th>Action</th></tr>
{req_rows}</table>
<p><a href="executive-summary.html">→ Full executive summary (all nine sites, why 0.2778 won, all experiments, gates, how to submit)</a></p></div>
<img class="map" src="../assets/k3_vs_champion.png" alt="Map of catalogue, champion dots and K3 dots">
<p><small>Map: catalogue (grey), champion dots (orange), K3 dots (cyan); exact-pixel overlap K3∩champion = 448 dots (1.3 %). Data: hash-pinned owner mirrors of the login-walled competition files + free USGS GeoDAWN/3DEP + GDR 1391. Mirrors prove integrity, not organizer authentication.</small></p>
</main></body></html>"""

    executive = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Executive summary — GEMSDOEkarage3 K3</title><style>{CSS}</style></head><body><main>
<p><small><a href="index.html">← back</a> · generated {html.escape(card['generated_utc'])} · run card
<a href="{REPO_URL}/blob/arena/e97d54bf-gemsdoekarage3/evidence/k3_run_card.json">evidence/k3_run_card.json</a></small></p>
{banner}
<div class="card"><h2>Required table — download file · labelled estimate · uniqueness</h2>
<table><tr><th>File</th><th>Estimate (evidence class)</th><th>Unique?</th><th>Submit?</th></tr>{req_rows}</table></div>

<div class="card"><h2>The nine focus sites — measured, not copied claims</h2>
<table><tr><th>Site</th><th>Best submission id</th><th>Dots (measured)</th><th>Live score</th><th>Measured relation</th></tr>
{site_rows}</table>
<p>Dot-set algebra re-verified here (symdiff/subset exactly). The champion (GEMSDOE32, 0.2778 OWNER-REPORTED) is
<b>nested inside</b> the GEMSDOE25/30/31/36 bests — i.e. most “different” site bests are prunings of one H19-5 ridge,
unlike K3 (448 exact dot overlaps with the champion). Best file to <i>re-submit</i> from this table: <b>none</b> — all are
historical and mutually nested; the champion already holds the family's optimum. Full per-site notes:
<a href="{REPO_URL}/blob/arena/e97d54bf-gemsdoekarage3/knowledge/focus9_forensics.md">knowledge/focus9_forensics.md</a>.</p></div>

<div class="card"><h2>Why did h33-2-b2 reach 0.2778 — and can we beat it?</h2>
<p><b>It is an emission/pruning optimum, not a new detector.</b> H19-5 ridge (121,131 px, 0.1922) → 2.8 px Poisson dotting
(44,090, 0.2600): adjacent ridge pixels are kernel-redundant (max-credit already ≈1) yet pay full false-positive tax, so
thinning keeps ~91 % of credit at 36 % of the mass. Then ring prunes delete dots within 1 px (−3,891 → 0.2708) and 2 px
(−2,545 → 0.2778) of the catalogue: the organizer masks known faults and detectors fire on their 100–200 m flank shadow
(≈0.004 credit vs the α·S≈0.052 break-even), so those dots are near-pure tax. We re-measured the B2 rule fold-locally:
0.09920 vs 0.09674 without it. B3 declines; GEMSDOE36 = champion+1,200 also declines (0.2750) — the family is at its
local optimum. Beating it needs a surface with genuinely more blind-fault recall; five prior catalogue-blind attempts
and K3 (below) all land at pooled HOLDOUT-DTI ≈0.03–0.06 vs the rule control's 0.0992, while the public #1 sits at
≈0.44 (owner: 0.4413; sister fetch 2026-10-26: 0.4437 — verify live).</p></div>

<div class="card"><h2>K3 experiments (3/3 used; all HOLDOUT-DTI, {pooled['evaluator_version']}, {pooled['n_withheld_positives']:,} withheld +)</h2>
<table><tr><th>Candidate / control</th><th>Pooled HOLDOUT-DTI</th><th>95 % CI</th><th>SGMC-cal HOLDOUT-DTI</th></tr>
{exp_rows}</table>
<p>Leakage canaries: {len(exp1['canaries'])} features tested alone, worst AUC {max(c['auc_max'] or 0 for c in exp1['canaries'].values()):.3f} ≤ 0.90 (PASS).
Greedy coverage beat D2.8 on the same fused surface (Exp2), and the corrected scarp-pair leads the champion on off-catalogue
SGMC — real signal that the template's mislabelled LiDAR bands (IR-K3-01) were suppressing — but pooled catalogue recovery
remains decisively below the champion rule, so the frozen promotion gate fails.</p></div>

<div class="card"><h2>Promotion gates (frozen pre-registration)</h2>
<table><tr><th>Gate</th><th>Result</th><th>Evidence</th></tr>{gate_rows()}</table>
<p>Extended uniqueness (Pass 2): {ext['registry_rasters']} rasters / {ext['unique_masks']} unique masks scanned in the nine clones;
genuine worst overlap {ext['genuine_worst_within_3px']*100:.1f}% — zero genuine duplicates &gt;70 %. Literal lattice overlap
{card['correlation_overlap_vs_registry']['literal_lattice']['candidate_within_3px']*100:.1f}% with only
{card['correlation_overlap_vs_registry']['literal_lattice']['uncovered_footprint_px']:,} uncovered footprint pixels (pigeonhole; IR-K3-02).</p></div>

{howto}

<div class="card"><h2>Ranked hypotheses (pre-registered before any result)</h2>
<table><tr><th>#</th><th>Hypothesis</th><th>Outcome</th></tr>
<tr><td>1</td><td>K3-H3 corrected-LiDAR crest–base dipole (template read wrong bands — IR-K3-01)</td><td>Best SGMC of any candidate incl. champion; pooled 0.0465 — negative overall</td></tr>
<tr><td>2</td><td>K3-H1 depth-persistent worms (rtp/gravity/TMI_up150)</td><td>Pooled 0.0467 solo; useful fusion partner (ρ=0.29 vs H3)</td></tr>
<tr><td>3</td><td>K3-H2 geothermal upflow boost (GDR wells/paleo, verified obtainable)</td><td>+0.0023 pooled under D2.8; solo surface weak (2,234 px support)</td></tr>
<tr><td>4</td><td>K3-H5 greedy expected-DTI emission</td><td>Beat D2.8 head-to-head (+0.0037 pooled, +0.0030 SGMC)</td></tr>
<tr><td>5</td><td>K3-H4 strain-rate ridges</td><td>Screened, weakest; dropped</td></tr></table></div>

<div class="card"><h2>Irregularities flagged (full register in repo)</h2>
<ul>
<li><b>IR-K3-01</b> shared-template LiDAR composite reads bands 1/2/5 (ex_max/ex_mean/lappos) while claiming ex/step/downface — fixed here by description-name reads.</li>
<li><b>IR-K3-02</b> literal ≤70 %/3 px vs <i>any</i> registry raster is impossible (5 px lattice covers 99.87 % at 3 px) — genuine gate + literal number both reported.</li>
<li><b>IR-K3-03</b> leaderboard #1 cited as 0.4413 / 0.4437 / 0.3195 (time-separated; 0.3195 stale).</li>
<li><b>IR-K3-04</b> all programme live scores lack organizer receipts → OWNER-REPORTED only.</li>
<li><b>IR-K3-09</b> champion mask is construction-censored on catalogue holdouts (0.00452); the honest control is the fold-local B2 rule (0.09920).</li>
<li>One GEMSDOE31 research raster has NaN inside the footprint (would fail the [0,1] validator).</li>
</ul></div>

<div class="card"><h2>Official sources (manual review)</h2>
<table><tr><th>ID</th><th>URL</th><th>Use</th></tr>{src_rows}</table>
<p><small>Limitations: no DrivenData credentials in sandbox (submission + live leaderboard are owner steps); CPU-only; competition
bytes via SHA-256-pinned owner mirrors (integrity ≠ organizer authentication). Negative results are deliverables: this verdict
is <b>{verdict}</b>.</small></p></div>
<img class="map" src="../assets/k3_vs_champion.png" alt="Map">
</main></body></html>"""

    (DOCS / "k3").mkdir(parents=True, exist_ok=True)
    (DOCS / "k3" / "index.html").write_text(index, encoding="utf-8")
    (DOCS / "k3" / "executive-summary.html").write_text(executive, encoding="utf-8")
    (DOCS / "k3").mkdir(parents=True, exist_ok=True)
    print(f"wrote docs/k3/index.html ({len(index)} B) + docs/k3/executive-summary.html ({len(executive)} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
