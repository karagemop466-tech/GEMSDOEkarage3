#!/usr/bin/env python3
"""Restore all pinned registry rasters (focus 9 sites + extra scored) via codeload tarballs and verify SHA-256."""

from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOCUS_MANIFEST = ROOT / "registry" / "focus_registry_manifest.json"
EXTRA_MANIFEST = ROOT / "registry" / "extra_scored_manifest.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def restore_repo_group(owner_repo_ref: tuple[str, str, str], entries: list[dict]) -> list[dict]:
    owner, repo, ref = owner_repo_ref
    missing: dict[str, dict] = {}
    out: list[dict] = []
    for e in entries:
        dest = ROOT / e["local"]
        if dest.exists() and dest.stat().st_size == e["bytes"] and sha256_file(dest) == e["sha256"]:
            out.append({"local": e["local"], "status": "present"})
        else:
            missing[e["path"]] = e

    if not missing:
        return out

    url = f"https://codeload.github.com/{owner}/{repo}/tar.gz/{ref}"
    try:
        with urllib.request.urlopen(url, timeout=180) as resp, tarfile.open(fileobj=resp, mode="r|gz") as tf:
            for member in tf:
                if not member.isfile() or "/" not in member.name:
                    continue
                rel = member.name.split("/", 1)[1]
                if rel in missing:
                    e = missing.pop(rel)
                    dest = ROOT / e["local"]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    tmp = dest.with_suffix(dest.suffix + ".partial")
                    src = tf.extractfile(member)
                    if src is not None:
                        with tmp.open("wb") as fh:
                            shutil.copyfileobj(src, fh, 1 << 20)
                        got_sha = sha256_file(tmp)
                        got_bytes = tmp.stat().st_size
                        if got_sha == e["sha256"] and got_bytes == e["bytes"]:
                            tmp.replace(dest)
                            out.append({"local": e["local"], "status": "restored"})
                        else:
                            tmp.unlink(missing_ok=True)
                            out.append({"local": e["local"], "status": "MISMATCH", "got_sha256": got_sha})
    except Exception as exc:
        print(f"[warn] codeload failed for {owner}/{repo}@{ref[:10]}: {exc}", file=sys.stderr)

    # Fallback for any remaining missing entries via gh api
    for rel, e in list(missing.items()):
        dest = ROOT / e["local"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".partial")
        api = f"repos/{owner}/{repo}/contents/{rel}?ref={ref}"
        try:
            with tmp.open("wb") as fh:
                subprocess.run(
                    ["gh", "api", api, "-H", "Accept: application/vnd.github.raw"],
                    stdout=fh,
                    check=True,
                    stderr=subprocess.PIPE,
                )
            got_sha = sha256_file(tmp)
            if got_sha == e["sha256"] and tmp.stat().st_size == e["bytes"]:
                tmp.replace(dest)
                out.append({"local": e["local"], "status": "restored"})
            else:
                tmp.unlink(missing_ok=True)
                out.append({"local": e["local"], "status": "MISMATCH", "got_sha256": got_sha})
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            out.append({"local": e["local"], "status": "fetch-error", "error": str(exc)[:160]})
    return out


def main() -> int:
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for man_path in (FOCUS_MANIFEST, EXTRA_MANIFEST):
        if not man_path.exists():
            continue
        man = json.loads(man_path.read_text())
        owner = man.get("owner", "buffedlizard55-lab")
        for r in man.get("rasters", []):
            if r.get("status") == "ok":
                key = (owner, r["repo"], r["ref"])
                groups.setdefault(key, []).append(r)

    results: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(restore_repo_group, k, v) for k, v in groups.items()]
        for f in cf.as_completed(futs):
            results.extend(f.result())

    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(json.dumps({"total_entries": len(results), "counts": counts}, indent=2))
    bad = [r for r in results if r["status"] not in {"present", "restored"}]
    for r in bad[:20]:
        print("FAIL", json.dumps(r), file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
