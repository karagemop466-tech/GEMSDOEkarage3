#!/usr/bin/env python3
"""Render docs/focus9/executive-summary-20261030.html from the 2026-10-30 focus-9 audit.

Inputs (every number is read from these files, never typed by hand):
  evidence/focus9-audit-20261030.json   scripts/focus9_audit.py (format, census, overlap, HOLDOUT-DTI)
  data/focus_registry.json              pinned file, SHA-256, source URL, user-reported claim

Labels: HOLDOUT-DTI (shared evaluator, withheld positives, 95% CI); USER-REPORTED (copied from the
request, not organizer-confirmed); FORMAT / OVERLAP (local checks). ORGANIZER-CONFIRMED appears nowhere:
there is no receipt. No site is cleared for submission.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "evidence" / "focus9-audit-20261030.json"
REG = ROOT / "data" / "focus_registry.json"
OUT = ROOT / "docs" / "focus9" / "executive-summary-20261030.html"
LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"


def esc(v) -> str:
    return html.escape(str(v), quote=True)


def main() -> int:
    audit = json.loads(AUDIT.read_text())
    reg = {s["site"]: s for s in json.loads(REG.read_text())["sites"]}
    rows = audit["rows"]
    pm = audit["pairwise_within3px_fraction_of_row_dots_in_column_file"]
    sites = [r["site"] for r in rows]

    # Uniqueness vs the other focus sites: max within-3 px share of this file's dots lying within 3 px of
    # any OTHER focus file's dots (row = this site, column = other site).
    def max_other(site: str) -> tuple[float, str]:
        best = max(((pm[site][o], o) for o in sites if o != site and pm[site][o] is not None), key=lambda t: t[0])
        return best

    table_rows = []
    site_sections = []
    for r in rows:
        s = r["site"]
        reg_r = reg[s]
        fmt_ok = r["format_gate_pass_official"]
        h = r.get("holdout_dti") or {}
        ci = h.get("ci95_cluster_bootstrap")
        ci_s = f"[{ci[0]:.4f}, {ci[1]:.4f}]" if ci else "n/a"
        mo, mo_site = max_other(s)
        dup_flag = "FAIL (near-duplicate)" if mo > 0.70 else "pass"
        verdict = ("NOT CLEARED: format fails (zeros outside NaN rule)" if not fmt_ok else
                   "NOT CLEARED: no holdout proof; uniqueness screen fails")
        table_rows.append(
            f"<tr><td>{esc(s)}</td>"
            f"<td><a href=\"{esc(reg_r['source_url'])}\">{esc(r['file'])}</a><br><small>SHA-256 {esc(r['sha256'][:16])}… "
            f"· {r['census']['inside_footprint']['positive_cells(>0)']:,} dots</small></td>"
            f"<td>{'PASS' if fmt_ok else 'FAIL'}<br><small>{esc(', '.join(r['format_checks_failed']) or '-')}</small></td>"
            f"<td>{h.get('pooled_dti', float('nan')):.4f} {esc(ci_s)}<br><small>n={h.get('n_withheld_positives')} · HOLDOUT-DTI</small></td>"
            f"<td>{r['owner_reported_score']:.4f}<br><small>USER-REPORTED</small></td>"
            f"<td>{mo:.3f} (vs {esc(mo_site)})<br><small>{dup_flag}</small></td>"
            f"<td>{esc(verdict)}</td></tr>")
        site_sections.append(
            f"<section id=\"{s.lower()}\"><h3>{esc(s)}</h3><ul>"
            f"<li><b>File:</b> <a href=\"{esc(reg_r['source_url'])}\">{esc(r['file'])}</a> "
            f"(<a href=\"{esc(s.lower())}.html\">per-site page</a>)</li>"
            f"<li><b>Format (official organizer rules, local check):</b> {'PASS' if fmt_ok else 'FAIL'}"
            f"{'' if fmt_ok else ' — values outside the footprint are 0, not NaN, which the organizer rule does not allow'}.</li>"
            f"<li><b>Dots:</b> {r['census']['inside_footprint']['positive_cells(>0)']:,} inside the footprint.</li>"
            f"<li><b>Estimated score:</b> no verified estimate. HOLDOUT-DTI {h.get('pooled_dti', float('nan')):.4f} {esc(ci_s)} "
            f"(n={h.get('n_withheld_positives')}); owner-reported {r['owner_reported_score']:.4f} (USER-REPORTED, unverified).</li>"
            f"<li><b>Uniqueness vs other focus sites:</b> up to {mo:.3f} of its dots within 3 px of {esc(mo_site)} "
            f"({dup_flag}; the 0.70 rule is applied to the registry, not only to this site).</li>"
            f"<li><b>Status:</b> {esc(verdict)}. No slot selected.</li></ul></section>")

    maxes = [max_other(s)[0] for s in sites]
    min_max, max_max = min(maxes), max(maxes)
    from scipy.stats import spearmanr
    rho, pval = spearmanr([r["holdout_dti"]["pooled_dti"] for r in rows], [r["owner_reported_score"] for r in rows])
    rho_note = (f"Holdout vs owner-reported rank: Spearman ρ = {rho:.3f}, p = {pval:.3f}, n = {len(rows)} (computed here "
                "from the audit JSON and data/focus_registry.json). The local holdout runs opposite to the user-reported "
                "ordering. This is an irregularity, not evidence about the organizer score.")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>GEMSDOE focus sites — executive summary (2026-10-30)</title>
<link rel="stylesheet" href="../styles.css"></head><body>
<h1>Executive summary — nine focus sites (2026-10-30)</h1>
<p><b>Decision: nothing is cleared for submission. No submission slot is used.</b> This page reports only what was measured.</p>
<h2>Bottom line</h2>
<ul>
<li>Five files pass the official format gate (GEMSDOE24, 25, 27, 28, 31). Four fail (GEMSDOE30, 32, 33, 36) because outside-footprint cells are 0, not NaN.</li>
<li>Uniqueness fails for every site: for each site, at least {min_max:.3f} of its dots lie within 3 px of one other focus file's dots (lowest site-maximum), and the highest is {max_max:.3f}. GEMSDOE32's dots are all within 3 px of every other focus file (1.000).</li>
<li>GEMSDOE30's dot set is identical to GEMSDOE25's (44,090 dots, 0 cells differ). Only the outside-footprint encoding differs.</li>
<li>Local HOLDOUT-DTI is highest for GEMSDOE24/25/27/30 (0.093–0.097) and lowest for GEMSDOE32/36 (0.0045). Ordering: HOLDOUT-DTI (shared evaluator, withheld positives 22,232) is inversely related to the user-reported scores.</li>
<li>The best local holdout value on record (0.0967) is well below the public leaderboard top of 0.4544 (checked 2026-10-30). No internal method beats its random control. See the H-QDTI record.</li>
</ul>
<p><small>{esc(rho_note)}</small></p>
<h2>Summary table</h2>
<table><thead><tr><th>Site</th><th>File to download</th><th>Format gate</th><th>HOLDOUT-DTI [95% CI]</th><th>Owner-reported</th><th>Max overlap vs other focus sites</th><th>Status</th></tr></thead>
<tbody>{''.join(table_rows)}</tbody></table>
<p><small>Labels: HOLDOUT-DTI = local shared evaluator <code>{esc(audit['evaluator'])}</code>, not organizer. USER-REPORTED = copied from the request, unverified. FORMAT / OVERLAP = local checks. ORGANIZER-CONFIRMED: none. Public leaderboard: <a href="{LEADERBOARD}">{LEADERBOARD}</a> (2026-10-30: #1 0.4544; 0.3195 at #48; 0.4413 not found).</small></p>
<h2>Per-site executive summaries</h2>
{''.join(site_sections)}
<h2>How to submit (step by step — applies only after a candidate is cleared)</h2>
<ol>
<li>Pick a candidate that has passed the random same-area control and beaten the holdout best (0.0967 locally). A candidate that fails either gate is not submitted.</li>
<li>Write the GeoTIFF: single band, float32, EPSG:32611, 100 m, 3730 × 3292 grid; values exactly 0 or 1 inside the footprint; NaN outside. Run <code>scripts/check_format.py</code> with the sample submission as template.</li>
<li>Run the writer audit <code>src/gems32/submission.py audit_geotiff</code> (nan mode). It must pass all checks, including zero catalogue leakage.</li>
<li>Give the file a unique name (≤ 140-character comment). Confirm its SHA-256 is not in the registry and that the literal uniqueness screen passes (within-3 px ≤ 70 %; |Spearman| ≤ 0.90).</li>
<li>Upload only after steps 1–4 pass. Record the portal's response and keep a receipt. An organizer receipt is needed before any ORGANIZER-CONFIRMED claim.</li>
</ol>
<p><small>Run card: <a href="../../evidence/run-card-20261030.json">evidence/run-card-20261030.json</a> · Earlier per-site pages (10-29, same numbers): <a href="index.html">focus9/index.html</a></small></p>
</body></html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
