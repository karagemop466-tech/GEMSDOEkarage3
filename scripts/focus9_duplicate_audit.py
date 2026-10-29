#!/usr/bin/env python3
"""Byte-level uniqueness audit of the nine focus-site top files against the pinned registry manifest.

For each focus site's highest-reported file, list every registry entry whose SHA-256 is identical.
An identical SHA-256 in another site's repository means the same bytes were already submitted or
published elsewhere, so the file is NOT unique.

Scope: exact byte duplicates across the 2,444 manifest rows (registry/complete_registry_manifest.json).
This is NOT the literal 3-px / rank-correlation registry gate (scripts/audit_registry.py) and does not
certify uniqueness of the dot set. Manifest completeness is flagged as literal_registry_complete=false.

Output: evidence/focus9-duplicate-audit-20261029.json
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "complete_registry_manifest.json"
OUT = ROOT / "evidence" / "focus9-duplicate-audit-20261029.json"

# (focus site, repo, path of the highest USER-REPORTED file, USER-REPORTED value)
TOP_FILES = [
    ("GEMSDOE24", "buffedlizard55-lab/GEMSDOE24", "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477),
    ("GEMSDOE25", "buffedlizard55-lab/GEMSDOE25", "docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600),
    ("GEMSDOE27", "buffedlizard55-lab/GEMSDOE27", "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", 0.2449),
    ("GEMSDOE28", "buffedlizard55-lab/GEMSDOE28", "docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", 0.2710),
    ("GEMSDOE30", "buffedlizard55-lab/GEMSDOE30", "docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif", 0.2600),
    ("GEMSDOE31", "buffedlizard55-lab/GEMSDOE31", "docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif", 0.2708),
    ("GEMSDOE32", "buffedlizard55-lab/GEMSDOE32", "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", 0.2778),
    ("GEMSDOE33", "buffedlizard55-lab/GEMSDOE33", "docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif", 0.2632),
    ("GEMSDOE36", "buffedlizard55-lab/GEMSDOE36", "docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif", 0.2750),
]


def main() -> int:
    rows = json.loads(MANIFEST.read_text())
    manifest = json.loads(MANIFEST.read_text())
    by_sha: dict[str, list[dict]] = defaultdict(list)
    for r in rows["rasters"]:
        by_sha[r["sha256"]].append(r)
    out_rows = []
    for site, repo, path, reported in TOP_FILES:
        own = [r for r in rows["rasters"] if r["repo"] == repo and r["path"] == path]
        if len(own) != 1:
            out_rows.append({"site": site, "file": path, "status": f"manifest_match_count={len(own)}"})
            continue
        sha = own[0]["sha256"]
        dupes = [
            {"repo": r["repo"], "path": r["path"]}
            for r in by_sha[sha]
            if not (r["repo"] == repo and r["path"] == path)
        ]
        other_repos = sorted({d["repo"] for d in dupes if d["repo"] != repo})
        out_rows.append({
            "site": site,
            "reported_score_USER_REPORTED": reported,
            "file": path,
            "repo": repo,
            "ref": own[0]["ref"],
            "sha256": sha,
            "bytes": own[0]["bytes"],
            "identical_bytes_elsewhere_count": len(dupes),
            "identical_bytes_in_other_site_repos": other_repos,
            "identical_bytes_entries": dupes,
            "unique_by_bytes_vs_manifest": len(other_repos) == 0,
        })
    out = {
        "schema": "focus9-duplicate-audit-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest": "registry/complete_registry_manifest.json",
        "manifest_literal_registry_complete": manifest.get("literal_registry_complete"),
        "manifest_rows": len(rows["rasters"]),
        "scope": "exact SHA-256 duplicates only; not the literal 3-px / rank-correlation gate",
        "rows": out_rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    for r in out_rows:
        if "sha256" in r:
            print(f"{r['site']:10s} unique_by_bytes={r['unique_by_bytes_vs_manifest']!s:5s} "
                  f"other_site_repos={r['identical_bytes_in_other_site_repos']}")
        else:
            print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
