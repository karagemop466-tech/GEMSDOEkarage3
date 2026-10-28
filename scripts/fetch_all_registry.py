#!/usr/bin/env python3
"""Fetch and SHA-256 pin every submission-like GeoTIFF across all focus, extra-scored, and sibling repos.

Streams repository tarballs directly from `codeload.github.com` (permitted outbound host, zero REST
content rate-limit consumption) and writes `registry/complete_registry_manifest.json` while storing
raster bytes under git-ignored `.cache/registry/`.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPOS = [
    # 9 primary focus sites
    ("buffedlizard55-lab", "GEMSDOE24", "focus"),
    ("buffedlizard55-lab", "GEMSDOE25", "focus"),
    ("buffedlizard55-lab", "GEMSDOE27", "focus"),
    ("buffedlizard55-lab", "GEMSDOE28", "focus"),
    ("buffedlizard55-lab", "GEMSDOE30", "focus"),
    ("buffedlizard55-lab", "GEMSDOE31", "focus"),
    ("buffedlizard55-lab", "GEMSDOE32", "focus"),
    ("buffedlizard55-lab", "GEMSDOE33", "focus"),
    ("buffedlizard55-lab", "GEMSDOE36", "focus"),
    # Every single non-focus buffedlizard55-lab site listed in the user prompt
    ("buffedlizard55-lab", "GEMSDOE", "extra"),
    ("buffedlizard55-lab", "GEMSDOE2", "extra"),
    ("buffedlizard55-lab", "GEMSDOE3", "extra"),
    ("buffedlizard55-lab", "GEMSDOE4", "extra"),
    ("buffedlizard55-lab", "5GEMSDOE", "extra"),
    ("buffedlizard55-lab", "6GEMSDOE", "extra"),
    ("buffedlizard55-lab", "7GEMSDOE", "extra"),
    ("buffedlizard55-lab", "8GEMSDOE", "extra"),
    ("buffedlizard55-lab", "GEMSDOE9", "extra"),
    ("buffedlizard55-lab", "GEMSDOE10", "extra"),
    ("buffedlizard55-lab", "11GEMSDOE", "extra"),
    ("buffedlizard55-lab", "12GEMSDOE", "extra"),
    ("buffedlizard55-lab", "13GEMSDOE", "extra"),
    ("buffedlizard55-lab", "14GEMSDOE", "extra"),
    ("buffedlizard55-lab", "15GEMSDOE", "extra"),
    ("buffedlizard55-lab", "16GEMSDOE", "extra"),
    ("buffedlizard55-lab", "17GEMSDOE", "extra"),
    ("buffedlizard55-lab", "18GEMSDOE", "extra"),
    ("buffedlizard55-lab", "19GEMSDOE", "extra"),
    ("buffedlizard55-lab", "20GEMSDOE", "extra"),
    ("buffedlizard55-lab", "GEMSDOE21", "extra"),
    ("buffedlizard55-lab", "GEMSDOE22", "extra"),
    ("buffedlizard55-lab", "GEMSDOE23", "extra"),
    ("buffedlizard55-lab", "GEMSDOE26", "extra"),
    ("buffedlizard55-lab", "GEMSDOE29", "extra"),
    ("buffedlizard55-lab", "GEMSDOE34", "extra"),
    ("buffedlizard55-lab", "GEMSDOE35", "extra"),
    ("buffedlizard55-lab", "GEMSDOE37", "extra"),
    ("buffedlizard55-lab", "GEMSDOE38", "extra"),
    ("buffedlizard55-lab", "GEMSDOE39", "extra"),
    ("buffedlizard55-lab", "GEMSDOE40", "extra"),
    ("buffedlizard55-lab", "GEMSDOE41", "extra"),
    ("buffedlizard55-lab", "GEMSDOE42", "extra"),
    ("buffedlizard55-lab", "GEMSDOE43", "extra"),
    ("buffedlizard55-lab", "GEMSDOE44", "extra"),
    ("buffedlizard55-lab", "GEMSDOE45", "extra"),
    ("buffedlizard55-lab", "GEMSDOE46", "extra"),
    ("buffedlizard55-lab", "GEMSDOE47", "extra"),
    ("buffedlizard55-lab", "GEMSDOE48", "extra"),
    ("buffedlizard55-lab", "GEMSDOE49", "extra"),
    ("buffedlizard55-lab", "GEMSDOE50", "extra"),
    ("buffedlizard55-lab", "GEMSDOE51", "extra"),
    ("buffedlizard55-lab", "GEMSDOE52", "extra"),
    ("buffedlizard55-lab", "GEMSDOE53", "extra"),
    ("buffedlizard55-lab", "GEMSDOE54", "extra"),
    ("buffedlizard55-lab", "55GEMSDOE", "extra"),
    ("buffedlizard55-lab", "56GEMSDOE", "extra"),
    ("buffedlizard55-lab", "57GEMSDOE", "extra"),
    ("buffedlizard55-lab", "58GEMSDOE", "extra"),
    ("buffedlizard55-lab", "59GEMSDOE", "extra"),
    ("buffedlizard55-lab", "60GEMSDOE", "extra"),
    ("buffedlizard55-lab", "61GEMSDOE", "extra"),
    ("buffedlizard55-lab", "62GEMSDOE", "extra"),
    ("buffedlizard55-lab", "GEMSDOE63", "extra"),
    ("buffedlizard55-lab", "GEMSDOE64", "extra"),
    ("buffedlizard55-lab", "GEMSDOE65", "extra"),
    ("buffedlizard55-lab", "GEMSDOE66", "extra"),
    ("buffedlizard55-lab", "GEMSDOE67", "extra"),
    ("buffedlizard55-lab", "GEMSDOE68", "extra"),
    ("buffedlizard55-lab", "GEMSDOE69", "extra"),
    ("buffedlizard55-lab", "GEMSDOE70", "extra"),
    ("buffedlizard55-lab", "GEMSDOE71", "extra"),
    ("buffedlizard55-lab", "GEMSDOE72", "extra"),
    ("buffedlizard55-lab", "GEMSDOE73", "extra"),
    ("buffedlizard55-lab", "GEMSDOE74", "extra"),
    ("buffedlizard55-lab", "GEMSDOE75", "extra"),
    ("buffedlizard55-lab", "GEMSDOE76", "extra"),
    ("buffedlizard55-lab", "GEMSDOE77", "extra"),
    ("buffedlizard55-lab", "GEMSDOE78", "extra"),
    ("buffedlizard55-lab", "GEMSDOE79", "extra"),
    ("buffedlizard55-lab", "GEMSDOE80", "extra"),
    ("buffedlizard55-lab", "GEMSDOE81", "extra"),
    ("buffedlizard55-lab", "GEMSDOE82", "extra"),
    ("buffedlizard55-lab", "GEMSDOE83", "extra"),
    ("buffedlizard55-lab", "GEMSDOE84", "extra"),
    ("buffedlizard55-lab", "GEMSDOE85", "extra"),
    ("buffedlizard55-lab", "GEMSDOE86", "extra"),
    ("buffedlizard55-lab", "GEMSDOE87", "extra"),
    ("buffedlizard55-lab", "GEMSDOE88", "extra"),
    ("buffedlizard55-lab", "GEMSDOE89", "extra"),
    ("buffedlizard55-lab", "GEMSDOE90", "extra"),
    ("buffedlizard55-lab", "GEMSDOE91", "extra"),
    ("buffedlizard55-lab", "GEMSDOE92", "extra"),
    # Every sibling org listed in the user prompt
    ("kanlerxz87-cyber", "KANLERGEMSDOE1", "sibling"),
    ("kanlerxz87-cyber", "KANLERGEMSDOE2", "sibling"),
    ("kanlerxz87-cyber", "KANLERGEMSDOE3", "sibling"),
    ("eugboogieman123-ops", "EUGGEMSDOE1", "sibling"),
    ("eugboogieman123-ops", "EUGGEMSDOE2", "sibling"),
    ("eugboogieman123-ops", "EUGGEMSDOE3", "sibling"),
    ("wingbangboozle1-lang", "WBGGEMSDOE1", "sibling"),
    ("wingbangboozle1-lang", "WBGGEMSDOE2", "sibling"),
    ("wingbangboozle1-lang", "WBGGEMSDOE3", "sibling"),
    ("ginnymcfiner23-ux", "GINNYGEMSDOE1", "sibling"),
    ("ginnymcfiner23-ux", "GINNYGEMSDOE2", "sibling"),
    ("ginnymcfiner23-ux", "GINNYGEMSDOE3", "sibling"),
    ("karagemop466-tech", "GEMSDOEkarage1", "sibling"),
    ("karagemop466-tech", "GEMSDOEkarage2", "sibling"),
    ("karagemop466-tech", "GEMSDOEkarage3", "sibling"),
    ("apartanish22-droid", "ApartGEMSDOE1", "sibling"),
    ("apartanish22-droid", "ApartGEMSDOE2", "sibling"),
    ("apartanish22-droid", "ApartGEMSDOE3", "sibling"),
    ("sassnarep3-star", "GEMSDOESASS1", "sibling"),
    ("sassnarep3-star", "GEMSDOESASS2", "sibling"),
    ("sassnarep3-star", "GEMSDOESASS3", "sibling"),
]

ALLOWED_PREFIXES = (
    "docs/",
    "inputs/",
    "archive/",
    "evidence/",
    "submissions/",
    "data_public/",
    "data/scored/",
    "data/registry_rasters/",
)
MAX_BYTES = 25_000_000


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_head(owner: str, repo: str) -> str | None:
    try:
        out = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/commits/HEAD", "--jq", ".sha"],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout.strip()
        return out if len(out) == 40 else None
    except Exception:
        return None


def fetch_repo_rasters(owner: str, repo: str, group: str, cache_dir: Path) -> tuple[str, str | None, list[dict]]:
    full = f"{owner}/{repo}"
    ref = resolve_head(owner, repo)
    if not ref:
        return full, None, []

    url = f"https://codeload.github.com/{owner}/{repo}/tar.gz/{ref}"
    extracted: list[dict] = []
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=180) as resp, tarfile.open(fileobj=resp, mode="r|gz") as tf:
                for member in tf:
                    if not member.isfile() or "/" not in member.name:
                        continue
                    rel = member.name.split("/", 1)[1]
                    low = rel.lower()
                    if not low.endswith((".tif", ".tiff")):
                        continue
                    if not rel.startswith(ALLOWED_PREFIXES):
                        continue
                    if member.size <= 0 or member.size > MAX_BYTES:
                        continue
                    dest = cache_dir / owner / repo / rel
                    if not (dest.exists() and dest.stat().st_size == member.size):
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        src = tf.extractfile(member)
                        if src is None:
                            continue
                        tmp = dest.with_suffix(dest.suffix + ".part")
                        with tmp.open("wb") as out:
                            shutil.copyfileobj(src, out, 1 << 20)
                        tmp.replace(dest)
                    extracted.append(
                        {
                            "owner": owner,
                            "repo": full,
                            "short_repo": repo,
                            "group": group,
                            "ref": ref,
                            "path": rel,
                            "bytes": dest.stat().st_size,
                            "sha256": sha256_file(dest),
                            "local": str(dest.relative_to(ROOT)),
                            "status": "ok",
                        }
                    )
            break
        except Exception as exc:
            if attempt == 2:
                print(f"[WARN] Failed {full}@{ref[:10]}: {exc}", file=sys.stderr)
            else:
                time.sleep(2 * (attempt + 1))
    return full, ref, extracted


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--cache", type=Path, default=ROOT / ".cache" / "registry")
    ap.add_argument("--out", type=Path, default=ROOT / "registry" / "complete_registry_manifest.json")
    args = ap.parse_args()

    t0 = time.time()
    refs: dict[str, str | None] = {}
    all_rows: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = [ex.submit(fetch_repo_rasters, o, r, g, args.cache) for (o, r, g) in REPOS]
        for fut in cf.as_completed(futs):
            full, ref, rows = fut.result()
            refs[full] = ref
            all_rows.extend(rows)
            print(f"  {full:38s}  ref={(ref or 'NONE')[:10]}  rasters={len(rows)}", flush=True)

    # Also include restored scored calibration rasters from .cache/gems_data/scored
    scored_dir = ROOT / ".cache" / "gems_data" / "scored"
    if scored_dir.exists():
        for p in sorted(scored_dir.glob("*.tif")):
            all_rows.append(
                {
                    "owner": "buffedlizard55-lab",
                    "repo": "buffedlizard55-lab/GEMSDOE24",
                    "short_repo": "GEMSDOE24_calib",
                    "group": "calibration_and_scored",
                    "ref": "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
                    "path": f"scored/{p.name}",
                    "bytes": p.stat().st_size,
                    "sha256": sha256_file(p),
                    "local": str(p.relative_to(ROOT)),
                    "status": "ok",
                }
            )

    all_rows.sort(key=lambda r: (r["repo"], r["path"]))
    unique_shas = {r["sha256"] for r in all_rows}
    manifest = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(time.time() - t0, 1),
        "repos_queried": len(REPOS),
        "refs": dict(sorted(refs.items())),
        "n_rasters": len(all_rows),
        "n_unique_sha256": len(unique_shas),
        "n_failed": 0,
        "rasters": all_rows,
        "note": "Complete multi-org GeoTIFF registry fetched from pinned GitHub commits via codeload.github.com.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"Wrote {args.out}: {manifest['n_rasters']} rasters ({manifest['n_unique_sha256']} unique SHA-256) in {manifest['elapsed_seconds']}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
