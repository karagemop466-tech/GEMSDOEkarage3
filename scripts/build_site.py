#!/usr/bin/env python3
"""Build the static decision pages from the pinned forensic snapshot."""
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
EXPECTED = {f"GEMSDOE{x}" for x in (24, 25, 27, 28, 30, 31, 32, 33, 36)}


def esc(value) -> str:
    return escape(str(value), quote=True)


def render() -> dict[Path, str]:
    audit_path = ROOT / "docs/data/historical-audit.json"
    manifest_path = ROOT / "data/focus_registry.json"
    audit = json.loads(audit_path.read_text())
    heads = json.loads((ROOT / "docs/data/repo-heads.json").read_text())
    manifest = json.loads(manifest_path.read_text())
    run_card = json.loads((ROOT / "docs/data/current-run.json").read_text())
    if audit.get("kind") != "GEOMETRY-AUDIT, NOT A SCORE" or len(audit["sites"]) != 9 or {x["site"] for x in audit["sites"]} != EXPECTED:
        raise ValueError("The historical evidence is incomplete or wrong")
    if audit.get("manifest_sha256") != hashlib.sha256(manifest_path.read_bytes()).hexdigest():
        raise ValueError("Evidence was not produced from the current manifest")
    if run_card.get("geometry_audit_sha256") != hashlib.sha256(audit_path.read_bytes()).hexdigest():
        raise ValueError("Run card is not bound to this audit; rebuild the preflight card")
    if not (run_card.get("verdict") == "negative" and run_card.get("raster_sha256") is None
            and run_card.get("experiments_run") == 0 and run_card.get("weekly_slots_used") == 0):
        raise ValueError("The static negative-decision copy requires an explicit update for a new run")
    actual_pairs = {(x["candidate"], x["reference"]) for x in audit["pairwise"]}
    expected_pairs = {(a, b) for a in EXPECTED for b in EXPECTED if a != b}
    if len(audit["pairwise"]) != 72 or actual_pairs != expected_pairs or not all(x["fraction"] > 0.7 for x in audit["pairwise"]):
        raise ValueError("The static 72-comparison statement no longer matches evidence")
    if any(x.get("new_submission_authorized") is not False for x in audit["sites"]):
        raise ValueError("This historical-only page cannot render an authorized candidate")
    records = {r["site"]: r for r in manifest["sites"]}
    if len(manifest["sites"]) != 9 or set(records) != EXPECTED or set(heads["sites"]) != EXPECTED:
        raise ValueError("Manifest or freshness baseline does not contain exactly the focus sites")
    # Guard the prose that describes this exact frozen historical snapshot.
    l, g, lineage = audit["lattice"], audit["grid"], audit["lineage"]
    if not (l["source"]["sha256"] == manifest["inputs"]["lattice"]["sha256"] and
            g["footprint_pixels"] == 5167373 and l["covered_within_3px"] == 5160724 and
            l["uncovered_beyond_3px"] == 6649 and l["budget_example"] == 37654 and
            l["budget_lower_bound_numerator"] == 31005 and l["budget_lower_bound_denominator"] == 37654 and
            lineage["g31_not_g32"] == lineage["removed_within_2px_of_labels"] == 2545 and
            lineage["g32_not_g31"] == lineage["g32_not_g36"] == 0 and lineage["g36_not_g32"] == 1200 and
            g["template_positives_equal_labels"] and g["label_positive_pixels"] == 60988):
        raise ValueError("Update static geometry/lineage prose for the changed snapshot")
    champion = next(row for row in audit["sites"] if row["site"] == "GEMSDOE32")
    if (champion["historical_claim"] != "0.2778" or champion["dots"] != 37654 or
            any(float(row["historical_claim"]) > 0.2778 for row in audit["sites"]) or
            round(100 * min(x["fraction"] for x in audit["pairwise"]), 2) != 86.72 or
            not all(row["lattice_fraction"] > .999 for row in audit["sites"])):
        raise ValueError("Update static historical-best and overlap prose for the changed snapshot")
    table_rows, details, head_rows = [], [], []
    for row in audit["sites"]:
        site = row["site"]
        record = records[site]
        head = heads["sites"][site]
        if not re.fullmatch(r"[0-9a-f]{40}", head["head"]) or record["repo"] != head["repo"]:
            raise ValueError(f"Invalid recorded head for {site}")
        if (row["format"]["sha256"] != record["sha256"] or row["file"] != Path(record["path"]).name or
                row["historical_claim"] != record["historical_claim"] or row["source_url"] != record["source_url"] or
                row["site_url"] != record["site_url"]):
            raise ValueError(f"Historical row differs from pinned manifest for {site}")
        source = esc(row["source_url"])
        site_url = esc(row["site_url"])
        filename = esc(row["file"])
        pct = f"{100 * row['worst_focus_fraction']:.2f}%"
        lattice = f"{100 * row['lattice_fraction']:.2f}%"
        fmt = row["format"]["checks"]
        if not all(fmt.get(key) is True for key in ("single_band", "float32", "shape_matches_mirror",
                   "crs_matches_mirror", "transform_matches_mirror", "inside_all_finite",
                   "inside_range_0_1", "inside_not_nodata_or_masked")):
            raise ValueError(f"Static inside/grid pass statement is unsupported for {site}")
        null_status = "matches" if fmt["outside_footprint_null_conservative"] else "does not match"
        finite_status = "passes" if fmt["whole_array_finite_range_diagnostic"] else "does not pass"
        table_rows.append(f'''<tr><td><strong>{esc(site)}</strong><a class="file-link" href="{source}">{filename}</a><span class="micro">Historical source · not a new download</span></td>
<td><span class="value">{esc(row['historical_claim'])}</span><span class="micro">USER-REPORTED / UNVERIFIED</span></td><td>Not estimable<span class="micro">No validated transfer to hidden truth</span></td>
<td><span class="warning-text">NO · {pct}</span><span class="micro">within 3 px of {esc(row['worst_focus_comparator'])}</span></td><td><span class="tag">DO NOT SUBMIT</span><span class="micro">Already-reported historical file</span></td></tr>''')
        details.append(f'''<details id="site-{esc(site)}"><summary>{esc(site)} · <span class="tag">DO NOT SUBMIT</span></summary>
<p><a href="{source}">{filename}</a><br><span class="micro">Historical source for research only · <a href="{site_url}">open site</a></span></p>
<div class="data-pair"><span>User-reported / unverified</span><strong>{esc(row['historical_claim'])}</strong></div>
<div class="data-pair"><span>Hidden-score estimate</span><strong>Unavailable</strong></div>
<div class="data-pair"><span>Most-overlapping focus site</span><strong>{pct} vs {esc(row['worst_focus_comparator'])}</strong></div>
<div class="data-pair"><span>Within 3 px of lattice</span><strong>{lattice}</strong></div>
<p>Format on pinned mirror: inside range / grid checks pass; {null_status} conservative null-outside; {finite_status} whole-array-finite diagnostic. Organizer acceptance is unknown.</p>
<p class="code">SHA-256 {esc(row['format']['sha256'])}</p></details>''')
        head_rows.append(f'''<tr><td><strong>{esc(site)}</strong></td><td><span class="repo-head" data-repo="{esc(head['repo'])}" data-baseline="{esc(head['head'])}">Not checked yet</span></td><td><a class="code" href="https://github.com/{esc(head['repo'])}/commit/{esc(head['head'])}">{esc(head['head'][:12])}</a></td></tr>''')
    time = heads["observed_utc"].split(".")[0].replace("T", " ")
    main = (ROOT / "site/index.template.html").read_text().replace("{{TABLE_ROWS}}", "\n".join(table_rows))
    guide = ((ROOT / "site/executive.template.html").read_text()
             .replace("{{SITE_DETAILS}}", "\n".join(details))
             .replace("{{HEAD_ROWS}}", "\n".join(head_rows))
             .replace("{{HEAD_TIME}}", esc(time)))
    if "{{" in main or "{{" in guide:
        raise ValueError("Unexpanded site template token")
    from build_k3c_site import apply_root_decision, apply_guide_decision  # current lane decision (docs/k3c/run-card.json)
    main = apply_root_decision(main)
    guide = apply_guide_decision(guide)
    # Submission desk: the top-of-site executive summary (generated from evidence JSON).
    from build_submission_desk import desk_banner, render as render_desk  # noqa: E402
    banner = desk_banner()
    main = main.replace('<main id="main"', banner + '\n<main id="main"', 1)
    guide = guide.replace('<main id="main"', banner + '\n<main id="main"', 1)
    return {ROOT / "index.html": main, ROOT / "executive-summary.html": guide,
            ROOT / "submission-desk.html": render_desk()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if checked-in pages are stale")
    args = parser.parse_args()
    for path, text in render().items():
        if args.check:
            if not path.exists() or path.read_text() != text:
                raise SystemExit(f"Stale generated page: {path}")
        else:
            path.write_text(text)
            print(f"Built {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
