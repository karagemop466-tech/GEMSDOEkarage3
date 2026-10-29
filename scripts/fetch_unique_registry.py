#!/usr/bin/env python3
"""Restore every unique raster in the pinned complete-registry inventory.

Reads ``registry/complete_registry_manifest.json`` (a FILTERED inventory: its
own note says it is not proof of a complete literal registry), downloads each
distinct SHA-256 once from its pinned immutable GitHub ref through the
authenticated ``gh api`` contents endpoint, verifies the bytes against the
manifest hash and size, and writes a receipt. Bytes are cached under the
git-ignored ``.cache/registry`` tree and are never committed.

Hash checks establish mirror integrity only, not organizer authenticity.
Failures are recorded and make the script exit non-zero; nothing is skipped
silently.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "complete_registry_manifest.json"
DEFAULT_CACHE = ROOT / ".cache" / "registry"
RECEIPT = ROOT / "evidence" / "unique-registry-restore-receipt.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def alternatives_by_sha(manifest: dict) -> dict[str, list[dict]]:
    """Every pinned (repo, ref, path) that carries each distinct SHA-256, in manifest order.

    Identical bytes frequently appear under several paths or repos. Restoring only
    the first path can fail on a stale or missing path, so callers fall back across
    alternatives instead of treating the first row as authoritative.
    """
    alts: dict[str, list[dict]] = {}
    for row in manifest["rasters"]:
        alts.setdefault(row["sha256"], []).append(row)
    return alts


def contents_endpoint(row: dict) -> str:
    return (f"repos/{quote(row['repo'])}/contents/{quote(row['path'], safe='/')}"
            f"?ref={row['ref']}")


def restore_one(row: dict, cache: Path, retries: int = 4) -> dict:
    dest = cache / row["repo"] / row["path"]
    result = {"repo": row["repo"], "ref": row["ref"], "path": row["path"],
              "sha256": row["sha256"], "bytes": row["bytes"], "status": None}
    if dest.is_file() and sha256(dest) == row["sha256"]:
        result["status"] = "cached"
        return result
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries + 1):
        if attempt:
            # GitHub secondary (abuse) limits return 403/429-style errors; back off, then retry.
            time.sleep(min(120, 5 * 2 ** attempt))
        ok, proc_err = _download(row, dest, result)
        if ok is not None:
            return result
        result["error"] = proc_err
    result["status"] = "download_failed"
    return result


def _download(row: dict, dest: Path, result: dict):
    """Return (True, None) on success; (None, message) on a retryable failure."""
    fd, name = tempfile.mkstemp(prefix="." + dest.name, suffix=".part", dir=dest.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as out:
            proc = subprocess.run(
                ["gh", "api", contents_endpoint(row), "-H", "Accept: application/vnd.github.raw"],
                stdout=out, stderr=subprocess.PIPE, check=False, timeout=300)
        if proc.returncode != 0:
            return None, proc.stderr.decode("utf-8", "replace")[-300:]
        got = sha256(tmp)
        if got != row["sha256"] or tmp.stat().st_size != row["bytes"]:
            # A hash mismatch is terminal, not retryable: the pinned bytes do not match.
            result["status"] = "hash_or_size_mismatch"
            result["observed_sha256"] = got
            return True, None
        os.replace(tmp, dest)
        result["status"] = "downloaded"
        return True, None
    finally:
        tmp.unlink(missing_ok=True)


def restore_via_codeload(rows: list[dict], cache: Path) -> list[dict]:
    """Stream each pinned repo/ref tarball once and extract only the listed paths.

    codeload.github.com is not subject to the REST API quota. Each extracted
    member is hash-checked against the manifest; members absent from the
    archive are reported, never assumed.
    """
    import tarfile
    import urllib.request
    from collections import defaultdict

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["repo"], row["ref"])].append(row)
    out: list[dict] = []
    for (repo, ref), group in groups.items():
        want = {row["path"]: row for row in group}
        found: set[str] = set()
        url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
        err = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=300) as resp, \
                        tarfile.open(fileobj=resp, mode="r|gz") as tf:
                    for member in tf:
                        if not member.isfile() or "/" not in member.name:
                            continue
                        rel = member.name.split("/", 1)[1]
                        if rel not in want or rel in found:
                            continue
                        row = want[rel]
                        dest = cache / row["repo"] / row["path"]
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        data = tf.extractfile(member).read()
                        result = {"repo": repo, "ref": ref, "path": rel, "sha256": row["sha256"],
                                  "bytes": row["bytes"], "via": "codeload"}
                        if hashlib.sha256(data).hexdigest() != row["sha256"] or len(data) != row["bytes"]:
                            result["status"] = "hash_or_size_mismatch"
                            result["observed_sha256"] = hashlib.sha256(data).hexdigest()
                        else:
                            tmp = dest.with_suffix(dest.suffix + ".part")
                            tmp.write_bytes(data)
                            os.replace(tmp, dest)
                            result["status"] = "downloaded"
                        found.add(rel)
                        out.append(result)
                err = None
                break
            except OSError as exc:  # network/HTTP errors: back off and retry the whole archive
                err = str(exc)[:300]
                time.sleep(5 * 2 ** attempt)
        for rel, row in want.items():
            if rel not in found:
                status = "archive_error" if err else "not_in_archive"
                out.append({"repo": repo, "ref": ref, "path": rel, "sha256": row["sha256"],
                            "bytes": row["bytes"], "status": status, "via": "codeload", "error": err})
        print(f"{repo}@{ref[:8]}: wanted={len(want)} extracted={len(found)} error={err is not None}", flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--workers", type=int, default=4, help="api mode only")
    ap.add_argument("--via", choices=["api", "codeload"], default="codeload",
                    help="codeload (default) streams one tarball per repo/ref and is not REST-quota limited")
    ap.add_argument("--limit", type=int, default=None, help="for testing only")
    ap.add_argument("--receipt", type=Path, default=RECEIPT)
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    alts = alternatives_by_sha(manifest)
    shas = list(alts)
    if args.limit:
        shas = shas[: args.limit]

    # Resolve each distinct hash: an on-disk cached copy at any alternative path wins.
    resolved: dict[str, dict] = {}
    attempts: list[dict] = []
    unresolved: list[str] = []
    for sha in shas:
        hit = None
        for row in alts[sha]:
            dest = args.cache / row["repo"] / row["path"]
            if dest.is_file() and sha256(dest) == sha:
                hit = dict(row, status="cached")
                break
        if hit:
            resolved[sha] = hit
        else:
            unresolved.append(sha)

    max_alts = max((len(alts[s]) for s in unresolved), default=0)
    for rnd in range(max_alts):
        if not unresolved:
            break
        batch = [alts[s][rnd] for s in unresolved if len(alts[s]) > rnd]
        if args.via == "codeload":
            outcomes = restore_via_codeload(batch, args.cache)
        else:
            with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
                outcomes = list(pool.map(lambda r: restore_one(r, args.cache), batch))
                time.sleep(2)
        attempts.extend(outcomes)
        by_key = {(o["repo"], o["path"]): o for o in outcomes}
        still = []
        for sha in unresolved:
            if len(alts[sha]) <= rnd:
                still.append(sha)
                continue
            row = alts[sha][rnd]
            o = by_key.get((row["repo"], row["path"]))
            if o and o["status"] in ("downloaded", "cached"):
                resolved[sha] = o
            else:
                still.append(sha)
        unresolved = still
        print(f"round {rnd + 1}: attempted={len(batch)} unresolved_after={len(unresolved)}", flush=True)

    for sha in unresolved:
        attempts.append({"sha256": sha, "status": "no_alternative_restored",
                         "tried": [f"{r['repo']}/{r['path']}" for r in alts[sha]]})
    results = list(resolved.values())
    counts: dict[str, int] = {}
    for res in attempts:
        counts[res["status"]] = counts.get(res["status"], 0) + 1
    ok = not unresolved and len(resolved) == len(shas)
    receipt = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest": "registry/complete_registry_manifest.json",
        "source_manifest_sha256": sha256(MANIFEST),
        "transport": args.via,
        "scope": "Unique SHA-256 rasters of the FILTERED inventory; not proof of a complete literal registry",
        "provenance": "Hash-pinned public GitHub mirrors, not organizer-authenticated",
        "unique_sha256_requested": len(shas),
        "unique_sha256_resolved": len(resolved),
        "attempt_status_counts": counts,
        "all_restored_and_hash_verified": ok,
        "resolved": sorted(results, key=lambda r: (r["repo"], r["path"])),
        "attempts": attempts,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "results"}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
