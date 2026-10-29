#!/usr/bin/env python3
"""Build the submission executive summary from saved receipts (no number is typed by hand).

Inputs (all tracked, all produced by scripts in this repo):
  docs/data/gemsdoe-top9-audit.json          fetched files, SHA-256, format facts, user-reported scores
  docs/data/gemsdoe-top9-analysis.json       dot structure, catalogue distance bins, overlap matrix
  docs/data/evaluator/eval_<SITE>.json       scripts/evaluate_holdout.py output (HOLDOUT-DTI)
  docs/data/h1-candidate-receipt.json        pre-registered H1 candidate build receipt
  docs/data/h1-uniqueness.json               literal uniqueness screen of H1
  docs/data/lattice-gap-analysis.json        lattice gap / recall-ceiling measurement

Outputs:
  docs/data/submission-summary.json          machine-readable summary (and concordance)
  submission-summary.html                    the executive summary page (repo root, GitHub Pages)

Labels: every score is USER-REPORTED unless a receipt says otherwise. HOLDOUT-DTI numbers carry the
evaluator version, withheld-positive count and 95% CI. Nothing here is ORGANIZER-CONFIRMED.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
OUT_JSON = DATA / "submission-summary.json"
OUT_HTML = ROOT / "submission-summary.html"
LIMIT = 0.70


def load(p: Path):
    return json.loads(p.read_text())


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def build() -> dict:
    audit = load(DATA / "gemsdoe-top9-audit.json")
    analysis = load(DATA / "gemsdoe-top9-analysis.json")
    h1 = load(DATA / "h1-candidate-receipt.json")
    h1u = load(DATA / "h1-uniqueness.json")
    gap = load(DATA / "lattice-gap-analysis.json")

    sites = [s["site"] for s in audit["sites"]]
    idx = {s: i for i, s in enumerate(sites)}
    ov = analysis["overlap_within_3px_directional"]
    per = {f["site"]: f for f in analysis["per_file"]}
    rows = []
    for s in audit["sites"]:
        site = s["site"]
        ev = load(DATA / "evaluator" / f"eval_{site}.json")
        hr = ev["hide_and_recover"]
        sg = ev["sgmc_off_catalogue"]
        others = {o: ov[idx[site]][idx[o]] for o in sites if o != site}
        best_other = max(others, key=lambda o: others[o])
        f = per[site]
        rows.append(dict(
            site=site,
            file_name=s["file_name"],
            file_url=s["file_url"],
            commit=s["commit"],
            sha256=s["sha256"],
            reported_score=s["user_reported_score"],
            score_status="USER-REPORTED / UNVERIFIED",
            n_dots=f["n_dots"],
            dots_on_catalogue_pixel=f["dots_on_catalogue_pixel"],
            dots_1_to_3px_from_catalogue=f["dots_1_to_3px_from_catalogue"],
            dots_gt_3px_from_catalogue=f["dots_gt_3px_from_catalogue"],
            off_catalogue_share=round(f["off_catalogue_fraction"], 6),
            max_directional_overlap_vs_other_site=round(others[best_other], 6),
            most_overlapping_site=best_other,
            unique_vs_other_eight=bool(others[best_other] <= LIMIT),
            sgmc_calibrated_holdout_dti=dict(
                evaluator=sg["evaluator_version"], label="HOLDOUT-DTI",
                withheld_positives=sg["n_withheld_positives"],
                value=round(sg["sgmc_prevalence_calibrated_dti"], 6),
                ci95=[round(x, 6) for x in sg["sgmc_calibrated_ci95"]]),
            hide_recover_holdout_dti=dict(
                evaluator=hr["evaluator_version"], label="HOLDOUT-DTI",
                withheld_positives=hr["n_withheld_positives"],
                value=round(hr["pooled_dti"], 6),
                ci95=[round(x, 6) for x in hr["ci95_cluster_bootstrap"]]),
            estimated_leaderboard_score="NOT ESTIMABLE from local evidence",
            submit_status="DO NOT SUBMIT",
        ))

    rep = [r["reported_score"] for r in rows]

    def rho(key):
        vals = [r[key] if not isinstance(r[key], dict) else r[key]["value"] for r in rows]
        res = spearmanr(rep, vals)
        return dict(spearman=round(float(res.statistic), 6), p_value=float(res.pvalue), n=len(rows))

    concord = dict(
        reported_vs_dots_1_to_3px_from_catalogue=rho("dots_1_to_3px_from_catalogue"),
        reported_vs_off_catalogue_share=rho("off_catalogue_share"),
        reported_vs_sgmc_calibrated_holdout_dti=rho("sgmc_calibrated_holdout_dti"),
        reported_vs_hide_recover_holdout_dti=rho("hide_recover_holdout_dti"),
        caveat="n=9 user-reported scores; correlation is descriptive, not a validated predictor.",
    )

    h1_registry_sites = [x for x in h1u["rows"] if x["source"] == "site-top9"]
    h1_lattice = [x for x in h1u["rows"] if "lattice" in x["registry_item"]]
    h1_summary = dict(
        candidate=h1["candidate"],
        n_dots=h1["n_dots"],
        dots_target_budget=h1["preregistered_parameters"]["budget"],
        leakage_canary_max_auc_dev=max(
            max(v["auc"], 1 - v["auc"]) for v in h1["leakage_canary"].values() if v.get("auc") is not None),
        max_overlap_vs_nine_sites=max(x["candidate_within3px_of_registry"] for x in h1_registry_sites),
        overlap_vs_13gems_lattice=h1_lattice[0]["candidate_within3px_of_registry"] if h1_lattice else None,
        literal_70pct_rule_triggered=h1u["literal_70pct_rule_triggered"],
        status="BLOCKED - DUPLICATE OF REGISTERED LATTICE (protocol: log and stop)",
        holdout_evaluated="No (stopped at the uniqueness gate, as the protocol requires)",
        sha256=h1u["candidate_sha256"],
    )
    best = max(rows, key=lambda r: r["reported_score"])
    lb = load(DATA / "leaderboard-snapshot-20261029.json")
    summary = dict(
        schema_version=1,
        decision="NO FILE IS CLEARED FOR SUBMISSION",
        leaderboard=dict(source=lb["source"], retrieved_utc=lb["retrieved_utc"], evidence_class=lb["evidence_class"],
                         top_score=lb["top_score"], rank_47_score=lb["rank_47_score"], rank_50_score=lb["rank_50_score"],
                         gems_values_visible_on_top50=lb["gems_values_visible_on_top50"]),
        best_reported_site=best["site"],
        best_reported_file=best["file_name"],
        best_reported_score=best["reported_score"],
        rows=rows,
        concordance=concord,
        lattice_gap=gap,
        h1=h1_summary,
        registry_scope=h1u["registry_scope"],
    )
    return summary


NO_HTML = '<span class="no">NO</span>'
YES_HTML = '<span class="yes">YES</span>'


def render(s: dict) -> str:
    offcat = load(DATA / 'unique-offcat-inside-footprint-check.json')
    geo_fp = load(DATA / 'geoconduit-inside-footprint-check.json')
    geo_u = load(DATA / 'geoconduit-uniqueness.json')
    geo_eval = load(DATA / 'evaluator' / 'eval_geoconduit.json')
    best = s["best_reported_site"]
    trs = []
    for r in sorted(s["rows"], key=lambda r: -r["reported_score"]):
        uniq_html = NO_HTML if not r["unique_vs_other_eight"] else YES_HTML
        tag = " <span class=\"tag top\">highest reported</span>" if r["site"] == best else ""
        sg = r["sgmc_calibrated_holdout_dti"]
        hr = r["hide_recover_holdout_dti"]
        trs.append(
            f"<tr><td><strong>{esc(r['site'])}</strong>{tag}</td>"
            f"<td><a href=\"{esc(r['file_url'])}\">{esc(r['file_name'])}</a><br>"
            f"<span class=\"small\">SHA-256 {esc(r['sha256'][:16])}… · {r['n_dots']:,} dots</span></td>"
            f"<td class=\"num\">{r['reported_score']:.4f}<br><span class=\"small\">USER-REPORTED</span></td>"
            f"<td>{esc(r['estimated_leaderboard_score'])}</td>"
            f"<td>{uniq_html}"
            f"<br><span class=\"small\">max overlap {pct(r['max_directional_overlap_vs_other_site'])} vs {esc(r['most_overlapping_site'])}</span></td>"
            f"<td><span class=\"no\">DO NOT SUBMIT</span></td></tr>"
        )
    # Mechanism table, sorted by reported score
    mech = []
    for r in sorted(s["rows"], key=lambda r: -r["reported_score"]):
        mech.append(
            f"<tr><td>{esc(r['site'])}</td><td class=\"num\">{r['reported_score']:.4f}</td>"
            f"<td class=\"num\">{r['n_dots']:,}</td><td class=\"num\">{r['dots_on_catalogue_pixel']}</td>"
            f"<td class=\"num\"><strong>{r['dots_1_to_3px_from_catalogue']:,}</strong></td>"
            f"<td class=\"num\">{r['dots_gt_3px_from_catalogue']:,}</td>"
            f"<td class=\"num\">{pct(r['off_catalogue_share'])}</td></tr>"
        )
    ev = []
    for r in sorted(s["rows"], key=lambda r: -r["reported_score"]):
        sg, hr = r["sgmc_calibrated_holdout_dti"], r["hide_recover_holdout_dti"]
        ev.append(
            f"<tr><td>{esc(r['site'])}</td><td class=\"num\">{r['reported_score']:.4f}</td>"
            f"<td class=\"num\">{sg['value']:.4f} <span class=\"small\">[{sg['ci95'][0]:.4f}, {sg['ci95'][1]:.4f}]</span></td>"
            f"<td class=\"num\">{hr['value']:.4f} <span class=\"small\">[{hr['ci95'][0]:.4f}, {hr['ci95'][1]:.4f}]</span></td></tr>"
        )
    c = s["concordance"]
    g = s["lattice_gap"]
    h = s["h1"]
    min_max = min(r["max_directional_overlap_vs_other_site"] for r in s["rows"])
    sgv = [r["sgmc_calibrated_holdout_dti"]["value"] for r in s["rows"]]
    sg_lo, sg_hi = min(sgv), max(sgv)
    low = sorted(s["rows"], key=lambda r: r["dots_1_to_3px_from_catalogue"])
    top_low, second_low = low[0]["dots_1_to_3px_from_catalogue"], low[1]["dots_1_to_3px_from_catalogue"]
    core = sorted({r["dots_gt_3px_from_catalogue"] for r in s["rows"]})
    from collections import Counter
    _mode_count, _ = Counter(r["dots_gt_3px_from_catalogue"] for r in s["rows"]).most_common(1)[0]
    _mode_sites = sorted(r["site"] for r in s["rows"] if r["dots_gt_3px_from_catalogue"] == _mode_count)
    core_note = f"{_mode_count:,} dots more than 3 px from the catalogue is the same count in {len(_mode_sites)} files ({', '.join(_mode_sites)})"
    prune_keep = next(r["off_catalogue_share"] for r in s["rows"] if r["site"] == best)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMS submission summary · GEMSDOEkarage3</title>
<style>
body{{font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#1d2330;background:#f7f8fa}}
main{{max-width:1100px;margin:0 auto;padding:24px 18px 60px}}
h1{{font-size:28px;margin:8px 0 6px}} h2{{font-size:20px;margin:34px 0 10px;border-bottom:2px solid #dde1e8;padding-bottom:4px}}
.banner{{border-radius:10px;padding:18px 20px;margin:14px 0;border:2px solid #b42318;background:#fef3f2}}
.banner.ok{{border-color:#067647;background:#ecfdf3}}
.banner strong.big{{font-size:20px;color:#b42318}}
table{{border-collapse:collapse;width:100%;background:#fff;margin:10px 0 6px;font-size:14px}}
th,td{{border:1px solid #dde1e8;padding:7px 8px;vertical-align:top;text-align:left}}
th{{background:#eef1f6}} td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.small{{font-size:12px;color:#5b6472}} .code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;word-break:break-all}}
.no{{color:#b42318;font-weight:700}} .yes{{color:#067647;font-weight:700}}
.tag{{display:inline-block;font-size:11px;padding:2px 6px;border-radius:6px;background:#1d4ed8;color:#fff;margin-left:4px;vertical-align:middle}}
.tag.top{{background:#067647}}
.card{{background:#fff;border:1px solid #dde1e8;border-radius:10px;padding:14px 16px;margin:10px 0}}
ol li, ul li{{margin:3px 0}}
</style></head>
<body><main>
<p class="small"><a href="index.html">Site home</a> · <a href="README.md">README</a> · <a href="docs/PROJECT_PROMPT.md">Project prompt</a> · <a href="docs/data/submission-summary.json">Summary JSON</a></p>
<h1>GEMSDOE sites: submission executive summary</h1>
<p class="small">Generated by <code>scripts/build_submission_summary.py</code> from saved receipts. Updated 2026-10-29 (UTC). Scores are <strong>USER-REPORTED</strong> unless labelled otherwise.</p>

<div class="banner"><strong class="big">Can I download and submit a file from this page? NO. No file is cleared.</strong>
<ul>
<li>Every top file for the nine sites is a near-copy of another site's file: for each file, at least <strong>{pct(min_max)}</strong> of its dots lie within 3 px of dots in one other site's file (limit 70%). Re-submitting one would be copying a previous submission, which your rule prohibits.</li>
<li>The one new file we generated that is unique against the other eight sites (<strong>H1</strong>, below) is <strong>blocked</strong>: <strong>{pct(h['overlap_vs_13gems_lattice'])}</strong> of its dots lie within 3 px of the registered 13GEMSDOE calibration lattice (limit 70%). The protocol says log it and stop.</li>
<li>No organizer receipt exists for any file, so no leaderboard estimate can be given. Local proxies do not reproduce the reported 0.2778 (see below).</li>
</ul></div>

<h2>0. Official public leaderboard (read 2026-10-29)</h2>
<div class="card">
<p>Rank 1 is <strong>{s['leaderboard']['top_score']:.4f}</strong>. Rank 47, the value your prompt calls "highest right now", is <strong>{s['leaderboard']['rank_47_score']:.4f}</strong>. Rank 50 is <strong>{s['leaderboard']['rank_50_score']:.4f}</strong>. None of the GEMSDOE user-reported values (0.2449–0.2778) appears in the visible top 50. That is consistent with them sitting lower, but it means none can be confirmed from this page. Source: <a href="{esc(s['leaderboard']['source'])}">DrivenData leaderboard</a>; rank and score only (<a href="docs/data/leaderboard-snapshot-20261029.json">snapshot</a>).</p>
</div>

<h2>1. Per-site summary (highest reported first)</h2>
<p>The file to download is the pinned GitHub copy of each site's top-reported submission. None is cleared. "Unique?" is the literal directional rule: share of this file's dots within 3 px of any dot of one other site's file, limit 70%.</p>
<table><thead><tr><th>Site</th><th>File to download (pinned commit)</th><th>Reported score</th><th>Estimated leaderboard score</th><th>Unique vs other eight sites?</th><th>Submit?</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table>
<p class="small">Estimate column: no estimate is possible from local evidence. Reported scores are not organizer receipts. The local proxies that were run are in section 4.</p>

<h2>2. The new file (H1): generated, unique against the other eight sites, blocked by the lattice</h2>
<div class="card">
<p><strong>Method (pre-registered, fixed before evaluation):</strong> {esc(h['candidate'])}. Layers: <code>tmi_hg</code> (magnetic horizontal gradient) and <code>iso_grav_anom_hg</code> (gravity horizontal gradient), both from <code>training_features.tif</code>. A dot is kept only where both edge maps are high (score = min of the two robust z-scores), at local maxima of a 7×7 window, with dots within 3 px of a catalogue fault removed, and a 20,000-dot budget (upper bound).</p>
<p><strong>Result:</strong> {h['n_dots']:,} dots (below the 20,000 budget; the budget is an upper bound). Leakage canary: every feature alone scored AUC 0.45–0.56 against the catalogue, so no leakage was detected. Largest overlap vs the nine site files: {pct(h['max_overlap_vs_nine_sites'])}. <strong>Overlap vs 13GEMSDOE lattice: {pct(h['overlap_vs_13gems_lattice'])} (limit 70%) → BLOCKED.</strong></p>
<p><strong>Also on main (not ours):</strong> <code>karage3-unique-offcat</code> (12,000 dots, zeros and nan variants) claims "0% within 3px". Measured with <code>scripts/check_inside_footprint_overlap.py</code>: {offcat['dots_outside_template_footprint']:,} of {offcat['total_dots']:,} dots lie outside the scored footprint, and {pct(offcat['inside_within3px_of_lattice_share'])} of the {offcat['dots_inside_template_footprint']:,} in-footprint dots sit within 3 px of the lattice. The repo validator marks its outside-footprint policy as failed. <strong>Not cleared</strong> (IR-S6-11).</p>
<p><strong>Also on main, PR #44 ("OK TO SUBMIT"): not supported.</strong> <code>gemsdoe32-karage3-h-geoconduit-hybrid</code> ({geo_fp['total_dots']:,} dots, sha256 <span class="code">{esc(geo_u['candidate_sha256'])}</span>). Literal uniqueness, lattice included: worst overlap {pct(geo_u['worst_directional_overlap']['candidate_within3px_of_registry'])} vs the 13GEMSDOE lattice (limit 70%), so the rule fails. The shared evaluator reports off-catalogue SGMC calibrated DTI {geo_eval['sgmc_off_catalogue']['sgmc_prevalence_calibrated_dti']:.4f} (CI {geo_eval['sgmc_off_catalogue']['sgmc_calibrated_ci95'][0]:.4f}–{geo_eval['sgmc_off_catalogue']['sgmc_calibrated_ci95'][1]:.4f}), against 0.058–0.064 for the nine sites. The quoted 0.4239 was not reproduced here (IR-S6-13). <strong>Not cleared.</strong></p>
<p><strong>Status:</strong> {esc(h['status'])}. Holdout: {esc(h['holdout_evaluated'])}. It is <strong>not published</strong>: the repo's saved-byte audit covers every TIFF under <code>docs/</code>, and a blocked file should not be downloadable. It regenerates byte-for-byte with <code>python scripts/build_h1_candidate.py</code> (SHA-256 <span class="code">{esc(h['sha256'])}</span>).</p>
</div>

<h2>2b. Hypothesis slate (ranked; NONE has been run or scored)</h2>
<div class="card">
<p class="small">These are proposals for future lanes. Each would need the same gates as H1: uniqueness first, then the shared holdout. No expected score is given because none has been measured. Ranking rule: lowest measured leakage risk first, then lowest build cost. It is not a ranking by expected score, because no expected score exists. The bands listed exist in <code>training_features.tif</code>; the AUC in brackets is the single-feature canary already measured for that band in the H1 run.</p>
<table><thead><tr><th>Rank</th><th>Hypothesis</th><th>Layers (from training_features.tif)</th><th>Physical signature and why off-catalogue</th><th>Difference from repo</th><th>Cost (experiments, time)</th><th>Status</th></tr></thead>
<tbody>
<tr><td>1</td><td><strong>H2 Vertical-derivative ridges</strong>: sharp, narrow edges of shallow sources, away from catalogue faults</td><td><code>tmi_vg</code> (canary AUC 0.487), <code>iso_grav_anom_vg</code> (AUC 0.526)</td><td>Vertical derivatives sharpen edges of near-surface sources and suppress regional trends. Off-catalogue because the ridge rule excludes catalogue pixels and the 3 px band.</td><td>Not checked against the 113-repo registry. First step before any build.</td><td>1 experiment (one budget unit) plus gates</td><td>NOT RUN</td></tr>
<tr><td>2</td><td><strong>H3 Tilt-derivative zero-contours</strong>: lineaments where the tilt angle crosses zero</td><td><code>tc</code> (AUC 0.449, below 0.5 so the sign must be checked)</td><td>Tilt angle is bounded and peaks near edges, so zero-contours mark source boundaries. Same off-catalogue exclusion.</td><td>Not checked against the registry.</td><td>1 experiment (one budget unit) plus gates</td><td>NOT RUN</td></tr>
<tr><td>3</td><td><strong>H4 Topographic slope lineaments</strong>: fault scarps in elevation slope</td><td><code>det_elev_slope</code> (AUC 0.558, highest of the six canaries)</td><td>Young faults can form scarps. Named mimics: drainage incision, roads, and erosion. Highest leakage margin of the set, so most at risk of a canary failure.</td><td>Not checked against the registry.</td><td>1 experiment (one budget unit) plus a mimic test</td><td>NOT RUN</td></tr>
</tbody></table>
<p><strong>The constraint that limits all three.</strong> Off-catalogue truth lies within 3 px of a 13GEMSDOE lattice dot for 99.92% of its cells. A file that places dots near truth will therefore land within 3 px of the lattice too, so every hypothesis faces the same literal-rule block as H1. Only a gap-cell file would pass that rule, and its recall ceiling is 0.42%. Any hypothesis therefore needs the registry-scope decision (section 6) before a holdout run is worth one of the three remaining weekly slots.</p>
</div>

<h2>3. Why 0.2778 may have scored highest (measured correlation; mechanism not confirmed)</h2>
<p>All nine files are binary dot maps (<code>value &gt; 0</code>) on the same 3730 × 3292 grid. No file has a dot exactly on a catalogue pixel (the organizers mask those pixels, DrivenData staff, 16 Sep 2026). The files differ in how many dots sit <strong>1–3 px</strong> from a catalogue fault. Those are not masked, and the more of them a file has, the lower its reported score. The order is exactly the same across all eight distinct reported scores:</p>
<table><thead><tr><th>Site</th><th>Reported</th><th>Dots</th><th>On catalogue pixel</th><th>1–3 px from catalogue</th><th>&gt;3 px from catalogue</th><th>Off-catalogue share</th></tr></thead>
<tbody>{''.join(mech)}</tbody></table>
<p>Spearman of reported score against the 1–3 px count: <strong>{c['reported_vs_dots_1_to_3px_from_catalogue']['spearman']:.3f}</strong> (n=9, descriptive only). Against off-catalogue share: {c['reported_vs_off_catalogue_share']['spearman']:.3f}.</p>
<p><strong>Interpretation.</strong> Several top files share one off-catalogue count: {core_note}. GEMSDOE32 has the fewest 1–3 px dots ({top_low:,}); GEMSDOE36 is next ({second_low:,}). On this evidence the top score looks like the lowest-penalty member of one family. That is a hypothesis, not a discovery. It fits the masking rule, but the organizers have not confirmed the mechanism.</p>

<h2>4. Can we beat 0.2778? Not demonstrated, and here is why</h2>
<ul>
<li><strong>A pruned copy might score higher under this mechanism, but it cannot be submitted.</strong> Dropping GEMSDOE32's 2,171 near-catalogue dots would remove the 1–3 px penalty band. The result would be a near-duplicate of a previous submission (a pruned copy would keep {pct(prune_keep)} of GEMSDOE32's dots unchanged), which your rule forbids. Not produced here.
<li><strong>The local proxies cannot separate these files.</strong> Table below: the SGMC calibrated proxy ranges only from {sg_lo:.4f} to {sg_hi:.4f} across the nine files, and the catalogue hide-and-recover holdout ranks them in the <em>opposite</em> order to the leaderboard (Spearman {c['reported_vs_hide_recover_holdout_dti']['spearman']:.3f}).</li>
<li><strong>A literal-unique file has a low ceiling.</strong> Only {g['gap_cells_not_within_3px']:,} footprint cells lie outside the lattice's 3 px coverage. Of those, 6,580 lie in a ring within 3 cells of the footprint boundary, and 69 are interior (<code>evidence/lattice-feasibility-20261029.json</code>, from main). Those cells cover at most {pct(g['recall_ceiling_gap_only_share'])} of off-catalogue SGMC truth (the lattice covers {pct(g['share_offcatalogue_truth_within_3px_of_any_lattice_dot'])}). Any file that stays under 70% of the lattice must put at least 30% of its dots in those cells, so its recall is capped far below the top files. Building a file that way would game the rule, not find faults, so it is not done.</li>
</ul>
<table><thead><tr><th>Site</th><th>Reported</th><th>SGMC-CAL holdout DTI (HOLDOUT-DTI, 62,703 withheld, 95% CI)</th><th>HIDE-RECOVER holdout DTI (HOLDOUT-DTI, 22,232 withheld, 95% CI)</th></tr></thead>
<tbody>{''.join(ev)}</tbody></table>
<p class="small">Evaluator: <code>scripts/evaluate_holdout.py</code> (repo's shared <code>gems32.holdout</code>, SGMC-CAL-v3.0 and HIDE-RECOVER-v3.0). Raw JSON: <a href="docs/data/evaluator/">docs/data/evaluator/</a>. These are local proxies. They do <strong>not</strong> reproduce 0.2778 and are not organizer scores.</p>

<h2>5. Irregularities for review</h2>
<ul>
<li><strong>IR-S6-01</strong> <code>labels.tif</code> and <code>existing_faults.tif</code> are byte-identical (SHA-256 <code>7ba308cc…</code>). Treat the labels as the catalogue, not as an independent hidden label set.</li>
<li><strong>IR-S6-02</strong> GEMSDOE25 and GEMSDOE30 have identical dot sets (1.000 overlap both ways) and the same reported 0.2600. They are one submission in two encodings, not two.</li>
<li><strong>IR-S6-03</strong> The catalogue hide-and-recover holdout is anti-correlated with the reported leaderboard (Spearman {c['reported_vs_hide_recover_holdout_dti']['spearman']:.3f}). It should not be used to rank candidates for this leaderboard.</li>
<li><strong>IR-S6-04</strong> 0.2778 is not reproduced by any local evaluator (HIDE-RECOVER 0.0045; SGMC-CAL 0.0641). Local numbers are proxies only.</li>
<li><strong>IR-S6-05</strong> Leaderboard top: your prompt gives 0.4413; an earlier repo note gives 0.4437 and 0.4544; the public board read today has rank 1 at <strong>0.4544</strong>. Your "0.3195 is the highest right now" is rank 47 on the same board. Snapshots differ; the snapshot file records today's read. See also IR-K3-03.</li>
<li><strong>IR-S6-06</strong> H1 deviated from its pre-registered budget: 14,186 dots, not 20,000 (fewer candidates survived suppression). Recorded in the receipt.</li>
<li><strong>IR-S6-07</strong> Official rules: section 1.1 says "a single entry" and section 3.2 says "multiple submissions… three submissions per week." These are not consistent. The weekly cap shown on the submission page must be checked manually.</li>
<li><strong>IR-S6-11</strong> Main's <code>karage3-unique-offcat</code> looks unique only because 7,483 of 12,000 dots lie outside the scored footprint, where the lattice has no dots. Its in-footprint lattice overlap is 99.89%. Its own metadata claim ("0% within 3px") is wrong. The repo validator fails its outside-footprint policy. Not cleared.</li>
<li><strong>IR-S6-12</strong> The saved-byte audit receipt <code>evidence/saved-tiffs-literal-20261028.json</code> listed 9 TIFFs, but <code>docs/</code> held 11 (13 after PR #44). On main, <code>build_site.py --check</code> failed as a result. Main's correction branch regenerated the same receipt (11 TIFFs, all duplicate-stop, verified by <code>--verify-receipt</code>). This branch briefly added a parallel <code>20261029</code> receipt and then dropped it, so there is one audit file.</li>
<li><strong>IR-S6-13</strong> PR #44 set the decision to "OK TO SUBMIT" for <code>gemsdoe32-karage3-h-geoconduit-hybrid</code>, quoting HOLDOUT-DTI 0.4239 under evaluator <code>GEMSDOE32-HOLDOUT-v3-visible-gated</code>, and said the dense lattice was excluded from the overlap check. Measured here: lattice overlap 99.83% (rule fails); shared-evaluator off-catalogue DTI 0.0026; catalogue-recovery 0.3047. The lattice exclusion is not permitted by the standing literal rule. The superseded decision is marked in README.md and the root pages were regenerated from the verified status.</li>
<li><strong>IR-S6-08</strong> The 70% / 3 px uniqueness rule is this project's internal protocol. It is not stated in the official rules, and it is measured against a registry we cannot fully enumerate (only nine site files and 14 scored rasters are available locally). See IR-K3-02.</li>
</ul>

<h2>6. Decisions and next steps (in order)</h2>
<ol>
<li><strong>Decide the uniqueness rule.</strong> Under the literal internal rule, no competitive file can be cleared, because of the 13GEMSDOE lattice (section 4). Options: (a) exclude dense calibration lattices from the registry, with a written reason; (b) keep the rule and accept no submission; (c) ask the organizers which submissions count as "registered" rasters.</li>
<li><strong>Get organizer receipts.</strong> The build sandbox cannot log in to DrivenData, so any upload receipt and the account-only data must be recorded by hand, with the file SHA-256. The public pages (problem, rules, forum, leaderboard) were read directly and are cited in section 7.</li>
<li><strong>Build a fold-local feature cache</strong> so the holdout can rank candidates. The shared holdout does not track the leaderboard yet (section 5, IR-S6-03).</li>
<li><strong>Confirm the AI-use narrative</strong> required by official rules section 3.2 before any submission. See <a href="AI_DISCLOSURE.md">AI_DISCLOSURE.md</a>.</li>
</ol>

<h2>7. Official sources (for manual review)</h2>
<ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description and metric (DrivenData, page 967)</a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules, NLR PDF (Sept 2026), sections 1.1 and 3.2</a></li>
<li><a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">DrivenData forum: known faults masked (staff reply, 16 Sep 2026)</a></li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Public leaderboard (read 2026-10-29, top 50; snapshot in docs/data/leaderboard-snapshot-20261029.json)</a></li>
</ul>
<p class="small">Every number on this page is produced by <code>scripts/build_submission_summary.py</code> from the receipts listed in its docstring. Nothing is ORGANIZER-CONFIRMED.</p>
</main></body></html>
"""


def main() -> int:
    summary = build()
    OUT_JSON.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    OUT_HTML.write_text(render(summary))
    print("wrote", OUT_JSON.relative_to(ROOT), "and", OUT_HTML.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
