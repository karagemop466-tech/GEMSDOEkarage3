#!/usr/bin/env python3
"""Fetch the nine pinned focus-site GeoTIFFs for local holdout evaluation.

Source: the exact commit recorded in data/focus_registry.json, downloaded from
codeload.github.com (the same host the restore script uses). Every file is
verified against the SHA-256 in the registry; a mismatch aborts the run.
These are research copies of user-reported historical files, not organizer
receipts, and nothing here authorizes a submission.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "focus_registry.json"
DEST = ROOT / ".cache" / "focus9"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_member(repo: str, ref: str, rel_path: str, dest: Path) -> None:
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    with urllib.request.urlopen(url, timeout=300) as resp, tarfile.open(fileobj=resp, mode="r|gz") as tf:
        for member in tf:
            if not member.isfile() or "/" not in member.name:
                continue
            if member.name.split("/", 1)[1] == rel_path:
                src = tf.extractfile(member)
                if src is None:
                    break
                with dest.open("wb") as out:
                    while True:
                        block = src.read(1 << 20)
                        if not block:
                            break
                        out.write(block)
                return
    raise FileNotFoundError(f"{rel_path} not found in {repo}@{ref}")


def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    DEST.mkdir(parents=True, exist_ok=True)
    results = []
    for site in registry["sites"]:
        dest = DEST / Path(site["path"]).name
        status = "present"
        if not (dest.exists() and sha256_file(dest) == site["sha256"]):
            fetch_member(site["repo"], site["ref"], site["path"], dest)
            status = "fetched"
        got = sha256_file(dest)
        ok = got == site["sha256"]
        results.append({"site": site["site"], "file": dest.name, "status": status, "sha256_ok": ok, "sha256": got})
        print(f"{site['site']}: {status} sha256_ok={ok} {dest.name}", file=sys.stderr)
        if not ok:
            print(f"SHA-256 MISMATCH for {site['site']}; refusing to use this file.", file=sys.stderr)
            return 2
    print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
