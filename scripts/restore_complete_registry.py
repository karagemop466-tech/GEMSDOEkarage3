#!/usr/bin/env python3
"""Restore the 2,444-raster complete-registry inventory via codeload tarballs.

Reuses the shared `restore_repo_group` from scripts/restore_pinned_registry.py
(no private fork). Every restored file must match the manifest's byte count and
SHA-256 at the pinned ref. Files land under .cache/registry (git-ignored).

Honest scope: registry/complete_registry_manifest.json itself says
`literal_registry_complete: false` (filtered inventory). Restoring it gives a
hash-bound, larger registry than before, NOT a proof of literal completeness.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from restore_pinned_registry import restore_repo_group  # noqa: E402  (shared, unmodified)

MANIFEST = ROOT / "registry" / "complete_registry_manifest.json"


def main() -> int:
    man = json.loads(MANIFEST.read_text())
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for r in man["rasters"]:
        owner, _, short = r["repo"].partition("/")
        groups.setdefault((owner, short, r["ref"]), []).append(r)
    print(f"complete manifest: {len(man['rasters'])} rasters in {len(groups)} pinned repo refs", flush=True)

    results: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(restore_repo_group, k, v) for k, v in groups.items()]
        for f in cf.as_completed(futs):
            results.extend(f.result())

    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary = {"total_entries": len(results), "counts": counts}
    print(json.dumps(summary, indent=2))
    bad = [r for r in results if r["status"] not in {"present", "restored"}]
    for r in bad[:20]:
        print("BAD", r)
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
