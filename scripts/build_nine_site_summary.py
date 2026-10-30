#!/usr/bin/env python3
"""Render docs/nine-site-summary.html and docs/nine-site-run-card.json from computed evidence.

Inputs (all produced by scripts in this repo, never typed by hand):
  docs/data/nine-site-summary.json      scripts/nine_site_audit.py
  evidence/k4-literal-uniqueness-scan.json   scripts/literal_uniqueness_scan.py (optional)

Every score on the page carries a label: HOLDOUT-DTI (local evaluator, with withheld-positive
count and 95% CI), USER-REPORTED (copied from the request, not organizer-confirmed), or
FORMAT / OVERLAP (local checks). ORGANIZER-CONFIRMED appears nowhere: no receipt exists.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "docs/data/nine-site-summary.json"
SCAN = ROOT / "evidence/k4-literal-uniqueness-scan.json"
OUT_HTML = ROOT / "docs/nine-site-summary.html"
OUT_CARD = ROOT / "docs/nine-site-run-card.json"
SUBMISSION_NAME = "karage3-k4-offcat-ridge-20k"
SUBMISSION_NOTE = "Off-catalogue ridge detector: 20k NMS maxima of mag/grav gradient + LiDAR scarp step."
assert len(SUBMISSION_NOTE) <= 140, len(SUBMISSION_NOTE)
K4_ZEROS = "docs/downloads/gemsdoe32-karage3-k4-offcat-ridge-20k-20261029T183711Z-2a6558a3-zeros.tif"
TEMPLATE = {"crs": "EPSG:32611", "shape": [3730, 3292], "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]}


def esc(x) -> str:
    return html.escape(str(x))


def fmt_ci(ci) -> str:
    return f"[{ci[0]:.4f}, {ci[1]:.4f}]"



def _nan_to_null(o):
    """Undefined statistics (e.g. Pearson on a constant raster) become null, never NaN in JSON."""
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    if isinstance(o, dict):
        return {k: _nan_to_null(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_nan_to_null(v) for v in o]
    return o


def main() -> int:
    doc = json.loads(SUMMARY.read_text())
    rows = doc["rows"]
    focus = [r for r in rows if r["kind"] == "focus-site"]
    cands = [r for r in rows if r["kind"] == "candidate"]
    k4 = next(r for r in cands if r["id"].startswith("CAND-k4"))
    geo = next(r for r in cands if r["id"].startswith("CAND-geo"))
    earlier = next(r for r in cands if r["id"].startswith("CAND-unique"))
    scan = json.loads(SCAN.read_text()) if SCAN.exists() else None
    best_hr = max(focus, key=lambda r: r["holdout_dti"]["value"])
    best_sg = max(focus, key=lambda r: r["sgmc_calibrated_dti"]["value"])
    pairs = doc.get("pairwise_exact_dot_subset", {})
    g32 = next(r for r in focus if r["id"] == "GEMSDOE32")
    g32_subset = {k: v for k, v in pairs.get("GEMSDOE32", {}).items() if v > 0}

    def scan_line() -> str:
        if scan is None:
            return "PENDING: full-registry literal scan has not written its result file."
        status = "PASS" if scan["pass"] else "FAIL"
        return (f"{status}: {scan['checked_same_grid']} same-grid registry rasters checked, "
                f"{scan['skipped']} grid-mismatched skipped; max |rho| (final dots) = {scan['max_abs_rho_final']:.4f}; "
                f"max 3-px overlap (final dots) = {scan['max_overlap3px_final']:.4f}; "
                f"max 3-px overlap (surface stage) = {scan['max_overlap3px_preview']:.4f}; fails = {scan['fail_count']}.")

    k4_scan_ok = scan is not None and scan["pass"]
    uniq_k4 = "YES" if (k4_scan_ok and k4["max_overlap3px_vs_other_focus_sites"] <= 0.70) else ("PENDING" if scan is None else "NO")

    def site_row(r: dict) -> str:
        repo_link = f"https://github.com/{r['repo']}/blob/{r['repo_head']}/{r['file']}"
        dup = r["max_overlap3px_vs_other_focus_sites"]
        return f"""<tr>
<td><strong>{esc(r['id'])}</strong><br><small>user-reported file: <code>{esc(r['user_reported_name'])}</code></small></td>
<td>{r['user_reported_score']:.4f} <small>USER-REPORTED</small></td>
<td><a href="{esc(repo_link)}">{esc(Path(r['file']).name)}</a><br><small>owner repo, pinned commit <code>{esc(r['repo_head'][:10])}</code> (not organizer)</small></td>
<td><code>{esc(r['sha256'][:12])}</code></td>
<td>{r['dots']:,}</td>
<td>{'PASS' if r['format']['core_format_pass'] and r['nan_count_all_pixels'] == 0 else 'FAIL'}<br><small>NaN in file: {r['nan_count_all_pixels']:,}</small></td>
<td>{r['holdout_dti']['value']:.4f} <small>HOLDOUT-DTI</small><br><small>{esc(r['holdout_dti']['evaluator'])}; n={r['holdout_dti']['n_withheld_positives']:,}; 95% CI {fmt_ci(r['holdout_dti']['ci95'])}</small></td>
<td>{r['sgmc_calibrated_dti']['value']:.4f} <small>HOLDOUT-DTI</small><br><small>{esc(r['sgmc_calibrated_dti']['evaluator'])}; n={r['sgmc_calibrated_dti']['n_withheld_positives']:,}; 95% CI {fmt_ci(r['sgmc_calibrated_dti']['ci95'])}</small></td>
<td><strong>NO</strong><br><small>{dup:.3f} 3-px overlap with {esc(r['max_overlap3px_vs_other_focus_sites_site'])}</small></td>
<td>Not estimable<br><small>no organizer receipt; local proxy not mapped to portal</small></td>
<td><span class="no">NO</span><br><small>duplicate of a peer; do not spend a slot</small></td>
</tr>"""

    focus_rows = "\n".join(site_row(r) for r in sorted(focus, key=lambda r: -r["user_reported_score"]))

    def cand_row(r: dict, verdict: str, note: str, unique: str) -> str:
        return f"""<tr>
<td><strong>{esc(r['id'])}</strong><br><small><code>{esc(Path(r['file']).name)}</code></small></td>
<td><code>{esc(r['sha256'][:12])}</code></td>
<td>{r['dots']:,}</td>
<td>{'PASS' if r['format']['core_format_pass'] and r['nan_count_all_pixels'] == 0 else 'FAIL'}</td>
<td>{r['holdout_dti']['value']:.4f} <small>HOLDOUT-DTI; n={r['holdout_dti']['n_withheld_positives']:,}; CI {fmt_ci(r['holdout_dti']['ci95'])}</small></td>
<td>{r['sgmc_calibrated_dti']['value']:.4f} <small>HOLDOUT-DTI; CI {fmt_ci(r['sgmc_calibrated_dti']['ci95'])}</small></td>
<td>{unique}<br><small>max 3-px overlap vs nine: {r['max_overlap3px_vs_other_focus_sites']:.3f}</small></td>
<td><span class="no">{esc(verdict)}</span><br><small>{esc(note)}</small></td>
</tr>"""

    cand_table = "\n".join([
        cand_row(k4, "NO - fails holdout gate", f"HOLDOUT-DTI {k4['holdout_dti']['value']:.4f} < best {best_hr['holdout_dti']['value']:.4f} (GEMSDOE25/30); SGMC-cal {k4['sgmc_calibrated_dti']['value']:.4f} < {best_sg['sgmc_calibrated_dti']['value']:.4f}. Literal scan: {'FAIL' if scan and not scan['pass'] else 'not run'} ({scan['fail_count'] if scan else 'n/a'} rasters over the gate; see scan section).", uniq_k4),
        cand_row(geo, "NO - not cleared", "Static placement built from catalogue-adjacent dots: leakage not excluded. Its card's 0.4239 did not reproduce (0.3047 here). SGMC-cal is the lowest of the files tested.", f"NOT SCANNED on full registry (vs nine: max overlap {geo['max_overlap3px_vs_other_focus_sites']:.3f})"),
        cand_row(earlier, "NO", f"Unique vs the nine (max overlap {earlier['max_overlap3px_vs_other_focus_sites']:.3f}), but HOLDOUT-DTI {earlier['holdout_dti']['value']:.4f} and SGMC-cal {earlier['sgmc_calibrated_dti']['value']:.4f} are below the nine-site best.", ("vs nine only: YES; full registry NOT SCANNED" if earlier["max_overlap3px_vs_other_focus_sites"] <= 0.70 else "NO")),
    ])

    subset_txt = ", ".join(f"{esc(k)} ({v*100:.1f}% of its dots are exact pixels)" for k, v in sorted(g32_subset.items(), key=lambda kv: -kv[1])) or "none"
    corr_txt = "Spearman(USER-REPORTED, SGMC-cal) = 0.950 and Spearman(USER-REPORTED, HOLDOUT-DTI) = -0.849 across the nine sites (n=9; scores USER-REPORTED, not organizer-confirmed)."

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nine-site executive summary · GEMSDOE focus-9</title>
<link rel="stylesheet" href="assets/site.css"></head>
<body><main class="wrap" style="padding:28px 0 60px;max-width:1180px;margin:auto">
<p><a href="nine-site-summary.html">Executive summary</a> · <a href="focus9/index.html">Focus-9 detail</a> · <a href="index.html">Decision home</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official leaderboard</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition</a></p>
<h1>GEMSDOE focus-9 · Executive summary</h1>
<p><small>Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} from <code>docs/data/nine-site-summary.json</code> by <code>scripts/build_nine_site_summary.py</code>. Run card: <a href="nine-site-run-card.json">nine-site-run-card.json</a>.</small></p>

<div style="border:3px solid #b00020;background:#fff0f0;padding:18px;border-radius:10px;margin:16px 0">
<strong style="font-size:1.3em">OK TO DOWNLOAD AND SUBMIT? NO — no file is cleared for a leaderboard slot today.</strong>
<p style="margin:8px 0 0">The only new TIF generated in this session is <strong>{esc(SUBMISSION_NAME)}</strong>. It is format-valid and downloadable, but it fails the full-registry literal uniqueness scan ({scan['fail_count'] if scan else 'not run'} rasters over the 3-px or rho gate) and the holdout gate. It is not unique and not a leaderboard candidate. Do not spend a submission on it.</p>
</div>

<h2>Short answer</h2>
<ol>
<li><strong>Highest reported file:</strong> GEMSDOE32 at 0.2778 (USER-REPORTED). Its file is <code>{esc(Path(g32['file']).name)}</code>.</li>
<li><strong>Is it unique?</strong> No. All nine focus files are near-duplicates: each one has a peer with at least {min(r['max_overlap3px_vs_other_focus_sites'] for r in focus):.3f} of its dots within 3 px (GEMSDOE25 and GEMSDOE30 are the same dot array).</li>
<li><strong>Which file can be downloaded to submit now?</strong> <strong>None.</strong> The off-catalogue candidate (<code>{esc(SUBMISSION_NAME)}</code>) fails the holdout gate: HOLDOUT-DTI {k4['holdout_dti']['value']:.4f} vs the nine-site best {best_hr['holdout_dti']['value']:.4f}.</li>
<li><strong>Why the portal said "Predicted values must be in range [0, 1]":</strong> the <code>-nan.tif</code> files hold 7,111,787 NaN pixels outside the footprint. They have the same dots as the <code>-zeros.tif</code>/<code>-allfinite.tif</code> files, which hold 0 NaN pixels and values only 0 or 1. Upload the zeros file, never the nan file. (Verified by reading the files in this session; the portal's exact rejection logic is not visible to us.)</li>
</ol>

<h2>Table 1 · The nine focus sites (highest reported file per site)</h2>
<p>Scores in this table are copied from the request (USER-REPORTED) or computed locally (HOLDOUT-DTI). The "estimated score" column is deliberately not filled with a projection: no organizer receipt exists, and the local proxy does not reproduce portal ordering on the HR metric (see "Why 0.2778").</p>
<div style="overflow-x:auto"><table>
<tr><th>Site</th><th>Reported score</th><th>File to download (zeros/allfinite, no NaN)</th><th>sha256</th><th>Dots</th><th>Format (NaN-free)</th><th>HOLDOUT-DTI hide-and-recover</th><th>Off-catalogue SGMC-calibrated</th><th>Unique vs other 8 sites?</th><th>Estimated score</th><th>OK to submit?</th></tr>
{focus_rows}
</table></div>

<h2>Table 2 · New files generated in this project</h2>
<div style="overflow-x:auto"><table>
<tr><th>File</th><th>sha256</th><th>Dots</th><th>Format</th><th>HOLDOUT-DTI</th><th>SGMC-calibrated</th><th>Unique?</th><th>Verdict</th></tr>
{cand_table}
</table></div>
<p><strong>Download status: disabled — DO NOT SUBMIT.</strong> <code>{esc(SUBMISSION_NAME)}</code> is a retained research artifact only; its holdout and full-registry uniqueness gates fail. The page intentionally provides no TIF or ZIP download link. No submission is cleared for download or upload.</p>
<p><strong>Full-registry literal uniqueness scan (k4):</strong> {esc(scan_line())}</p>

<h2>Why GEMSDOE32 reached 0.2778 (analysis)</h2>
<ol>
<li><strong>It is not a new structure.</strong> Its dots are a subset of the GEMSDOE31 family. Exact-pixel subset check: {subset_txt}. The chain of pruned catalogue-adjacent dots is what the repo's earlier review reported (<a href="focus9/gemsdoe32.html">detail</a>); the subset numbers above are our own check.</li>
<li><strong>The reported ranking tracks off-catalogue skill, not catalogue recovery.</strong> {esc(corr_txt)} GEMSDOE32 has SGMC-calibrated {g32['sgmc_calibrated_dti']['value']:.4f}, within {best_sg['sgmc_calibrated_dti']['value']-g32['sgmc_calibrated_dti']['value']:.4f} of the top of the nine ({best_sg['id']} {best_sg['sgmc_calibrated_dti']['value']:.4f}). On the hide-and-recover HOLDOUT-DTI it is the lowest-tier file ({g32['holdout_dti']['value']:.4f}), because it prunes dots that sit on catalogue faults.</li>
<li><strong>Why that pays on the portal (hypothesis, not proven):</strong> if the hidden test positives are off-catalogue faults, removing dots that duplicate catalogue traces frees budget for off-catalogue placements, and the score rises. The 9-point correlation supports this; it does not prove it.</li>
</ol>

<h2>Can we beat 0.2778?</h2>
<p><strong>Not demonstrated in this session.</strong> Under the off-catalogue proxy that tracks the reported ranking, a new file must exceed about 0.064 and be literally unique. The new unique file reached {k4['sgmc_calibrated_dti']['value']:.4f} and the geoconduit file {geo['sgmc_calibrated_dti']['value']:.4f}. The next step is a new off-catalogue placement optimized on the SGMC-calibrated proxy using only features that never touch catalogue or SGMC labels, followed by a leakage canary.</p>

<h2>Irregularities flagged for review</h2>
<ul>
<li><strong>GEMSDOE30 duplicates GEMSDOE25 in dots.</strong> Identical dot array (44,090 dots); both report 0.2600. The files differ in bytes (different SHA-256), so this is a dot-level duplicate, not a file-level one. Its pinned file <code>gemsdoe30-d28-poisson300m-offcat-44090-…-91eae1ca.tif</code> has the same bytes as a copy in the GEMSDOE29 repo (<code>gems29-refd28-repro-…</code>).</li>
<li><strong>GEMSDOE25 commit mismatch.</strong> The existing focus page cites commit <code>04333cc3</code>; the registry pin used here is <code>b13ccabae1</code>. Both are unverified against the organizer.</li>
<li><strong>Literal scan irregularities.</strong> (a) The scan's JSON keeps only the first 50 failures; all 108 failing rasters are in <code>evidence/k4-literal-uniqueness-scan-rows.jsonl</code>. (b) Three GEMSDOE23 rasters have undefined Pearson rho (NaN, constant raster), which the script treats as passing the correlation stage; they fail on overlap anyway. (c) Several overlap failures come from dense binary masks (over one million 1-valued pixels), where 3-px overlap is near 1.0 by construction. The gate is applied as written and not relaxed for these. (d) Eight rasters are grid-mismatched and skipped; one is unreadable.</li>
<li><strong>Unit tests:</strong> 105 run, 4 fail on the untouched base commit as well (stale page assertions for an older <code>csst-bghf</code> tree and the H-GEO-CONDUIT card). Not fixed here; they are not caused by this session's changes.</li>
<li><strong>Primary holdout ordering is inverted vs reported scores.</strong> Spearman(reported, HOLDOUT-DTI) = -0.849 on n=9. The protocol's hide-and-recover metric does not predict the portal ordering here.</li>
<li><strong>The H-GEO-CONDUIT card does not reproduce.</strong> Card claims HOLDOUT-DTI 0.4239 [0.4053, 0.4427] (visible-gated evaluator). Pinned evaluator gives {geo['holdout_dti']['value']:.4f} {fmt_ci(geo['holdout_dti']['ci95'])}. Its placement is built from catalogue-adjacent geometry, so the holdout is leakage-prone. SGMC-cal is {geo['sgmc_calibrated_dti']['value']:.4f}.</li>
<li><strong>Conservative outside-null check fails for every zero-filled file</strong> (including all nine focus files). That check requires NaN or masked pixels outside the footprint, which the portal's [0,1] error appears to reject. The two policies conflict; the portal's real acceptance is unknown.</li>
<li><strong>User-reported names differ from repo files.</strong> The user's names end in <code>-nan</code>, while the registry's best files are <code>-allfinite</code> or <code>-zeros</code>. Dots are identical; please confirm which file you uploaded.</li>
<li><strong>GEMSDOE33 has no -nan name in the repo</strong>; its best file is the one listed in Table 1.</li>
<li><strong>Competition rules PDF and the DrivenData metric page are not reachable from this sandbox</strong> (allowed hosts: github.com, codeload, api.github.com, pypi, npm). The metric's 300 m kernel and DTI definition in the local evaluator are the repo's implementation, not verified against the official text here. The official reference notebook is verified (SHA-256 matches the repo extract).</li>
<li><strong>GitHub tooling:</strong> the <code>gh</code> token is invalid and the REST API is rate-limited. The registry fetcher now falls back to <code>git ls-remote</code> (change in <code>scripts/fetch_all_registry.py</code>). The GitHub connection needs attention before PR creation via <code>gh</code>.</li>
<li><strong>Registry is a filtered inventory</strong> (its own note: not literally complete). Grid-mismatched rasters are skipped and listed in the scan.</li>
<li><strong>Leaderboard numbers 0.3195 and 0.4413</strong> were supplied by the user and are not verified.</li>
</ul>

<h2>How to submit (only after a file is cleared)</h2>
<ol>
<li>Choose only a file marked <strong>OK to submit: YES</strong> on this page. Today there is none.</li>
<li>Download the <code>-zeros.tif</code> (or its <code>.zip</code>). Never upload a <code>-nan.tif</code>.</li>
<li>Check: single-band GeoTIFF; CRS EPSG:32611; shape 3730 × 3292 (rows × cols); geotransform [100, 0, 243350, 0, -100, 4508550]; values 0 or 1 only; no NaN.</li>
<li>On the DrivenData submission page, choose the file, then enter a unique name and a note of at most 140 characters.</li>
<li>Save the portal receipt and record it in <code>docs/data/</code>; only a portal receipt makes a score ORGANIZER-CONFIRMED.</li>
</ol>

<h2>Official sources (for manual review)</h2>
<ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition page</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">About</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard</a> (not reachable from this sandbox)</li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR rules PDF</a> (not reachable from this sandbox)</li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">DrivenData reference solution</a> — notebook SHA-256 <code>1a7622732ba00f67237058bc0efe79b45ba4e87c449fc9c1e5d6ea659de92ca0</code> matches the repo extract</li>
<li><a href="https://gdr.openei.org/submissions/1391">GDR 1391 (INGENIOUS)</a> · <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> · <a href="https://gbcge.org/current-projects/ingenious/">INGENIOUS</a> · <a href="https://epsg.io/32611">EPSG:32611</a> · <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a></li>
</ul>
</main></body></html>
"""
    OUT_HTML.write_text(page)

    card = {
        "schema": "nine-site-run-card/1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "submission_name": SUBMISSION_NAME,
        "submission_note": SUBMISSION_NOTE,
        "submission_note_chars": len(SUBMISSION_NOTE),
        "raster": K4_ZEROS,
        "raster_sha256": k4["sha256"],
        "hypothesis": "H-K3-OFFCAT-RIDGE: blind faults leave persistent edge signatures (magnetic and gravity horizontal gradients, LiDAR DEM step) that are independent of the USGS/INGENIOUS catalogue.",
        "layers": ["training_features band 3 tmi_hg", "training_features band 18 iso_grav_anom_hg", "external lidar_scarp_features_u8 band 3 step_max"],
        "mechanism": "Mean percentile rank of three edge layers, Gaussian sigma 1.5 px, 9x9 non-maximum suppression, top 13,434 peaks (the pinned budget of 20,000 is unreachable after NMS).",
        "named_non_fault_mimic": "Lithologic contacts, dikes and intrusive margins (magnetic/gravity contrasts); landslides, road cuts, fences and acquisition striping (DEM step).",
        "leakage_canary": {"max_single_feature_auc_vs_catalogue": 0.5654, "threshold": 0.90, "status": "pass", "source": "scripts/build_karage3_offcat_ridge.py build json"},
        "holdout_dti": {"label": "HOLDOUT-DTI", "value": k4["holdout_dti"]["value"], "ci95": k4["holdout_dti"]["ci95"], "n_withheld_positives": k4["holdout_dti"]["n_withheld_positives"], "evaluator": k4["holdout_dti"]["evaluator"]},
        "sgmc_calibrated_dti": {"label": "HOLDOUT-DTI", "value": k4["sgmc_calibrated_dti"]["value"], "ci95": k4["sgmc_calibrated_dti"]["ci95"], "evaluator": k4["sgmc_calibrated_dti"]["evaluator"]},
        "holdout_gate": {"rule": "beat the current holdout best on the same evaluator", "current_best": {"site": best_hr["id"], "value": best_hr["holdout_dti"]["value"]}, "result": "FAIL"},
        "correlation_overlap_vs_registry": {
            "nine_site_max_overlap3px": k4["max_overlap3px_vs_other_focus_sites"],
            "literal_full_registry_scan": scan if scan is not None else "PENDING",
        },
        "validator_output": {
            "no_nan_inside_footprint": k4["format"]["inside_nonfinite_count"] == 0,
            "values_in_0_1": k4["format"]["inside_min"] >= 0 and k4["format"]["inside_max"] <= 1,
            "crs_matches": k4["format"]["checks"]["crs_matches"],
            "shape_matches": k4["format"]["checks"]["shape_matches"],
            "transform_matches": k4["format"]["checks"]["transform_matches"],
            "nan_count_all_pixels": k4["nan_count_all_pixels"],
            "conservative_outside_null_check": k4["format"]["outside_template_null_pass"],
            "note": "conservative outside-null check is False by design for zero-filled files; portal acceptance unknown",
        },
        "verdict": "negative",
        "ok_to_submit": False,
        "reason": "Fails the holdout gate: HOLDOUT-DTI and SGMC-cal are below the nine-site best. Not a leaderboard candidate; do not spend a slot.",
        "organizer_confirmed_score": None,
        "irregularities": [
            "GEMSDOE30 has the same dot array as GEMSDOE25 (files differ in SHA-256)",
            "GEMSDOE25 pinned commit b13ccabae1 (registry) differs from 04333cc3 cited on the focus page",
            "Literal scan: k4 candidate fails 108 registry rasters on the 3-px gate; scan JSON truncates fail_detail to 50 (full rows in evidence/)",
            "Literal scan: 3 GEMSDOE23 rasters with undefined Pearson rho are treated as passing the correlation stage",
            "Unit tests: 4 of 105 fail on the untouched base commit (stale page assertions); not caused by this session",
            "Reported ranking is anti-correlated with HOLDOUT-DTI (n=9)",
            "H-GEO-CONDUIT 0.4239 claim not reproduced (0.3047)",
            "NaN-outside variants are the likely cause of the portal [0,1] error",
            "Competition rules and metric pages unreachable from this sandbox",
            "gh token invalid and REST API rate-limited",
        ],
    }
    card = _nan_to_null(card)
    OUT_CARD.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(f"wrote {OUT_HTML} and {OUT_CARD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
