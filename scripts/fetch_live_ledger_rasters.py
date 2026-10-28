#!/usr/bin/env python3
# Vendored from buffedlizard55-lab/GEMSDOE32@8a733107 (karage3 edits: multi-owner sites; reads registry/owner_score_ledger.csv).
"""Locate and download the GeoTIFF bytes behind every OWNER-REPORT live score in docs/score-ledger.csv.

Why: the live leaderboard is the only measurement of the hidden scoring population.  To study it
(ledger decomposition, random-equivalent lift, projection of new candidates) we need the exact
bytes that were scored.  This script searches each GEMSDOE repository tree on GitHub for a .tif whose
file name contains the ledger submission name (exact stem match first, then a hash-token match),
downloads it into ``.cache/ledger/<repo>/<path>`` and records sha256 + match method.

Matching is conservative: a ledger row is marked ``matched`` only when exactly one candidate file
name contains the full submission stem (or, failing that, the unique 8+ hex-char hash token that
appears in the submission name).  Ambiguous or missing rows are reported, never guessed.

Output: ``evidence/live_ledger_rasters.json`` (cache itself is git-ignored).
Usage:  python scripts/fetch_live_ledger_rasters.py [--jobs 6]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "buffedlizard55-lab"
MAX_BYTES = 8_000_000

# Ledger "site" labels -> GitHub repository names (verified against `gh api users/<owner>/repos`).
SITE_TO_REPO = {
    "21GEMSDOE": "GEMSDOE21",
}
# Sites hosted by other owners (owner names taken verbatim from the GitHub Pages URLs in the 2026-10-28 brief).
SITE_TO_OWNER = {
    "KANLERGEMSDOE1": "kanlerxz87-cyber", "KANLERGEMSDOE2": "kanlerxz87-cyber", "KANLERGEMSDOE3": "kanlerxz87-cyber",
    "WBGGEMSDOE1": "wingbangboozle1-lang", "WBGGEMSDOE2": "wingbangboozle1-lang", "WBGGEMSDOE3": "wingbangboozle1-lang",
    "ApartGEMSDOE1": "apartanish22-droid", "ApartGEMSDOE2": "apartanish22-droid", "ApartGEMSDOE3": "apartanish22-droid",
    "GEMSDOESASS1": "sassnarep3-star", "GEMSDOESASS2": "sassnarep3-star", "GEMSDOESASS3": "sassnarep3-star",
    "GEMSDOEkarage1": "karagemop466-tech", "GEMSDOEkarage2": "karagemop466-tech", "GEMSDOEkarage3": "karagemop466-tech",
}


def owner_of(repo: str) -> str:
    return SITE_TO_OWNER.get(repo, OWNER)

# Rows supplied in the 2026-10-26 standing prompt that were not yet in docs/score-ledger.csv.
EXTRA_ROWS = [
    ("GEMSDOE24", "gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros", "0.0859"),
    ("GEMSDOE25", "gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros", "0.0742"),
    ("GEMSDOE27", "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite", "0.2190"),
    ("GEMSDOE28", "gems28-s18-mxtp-20261025-3e95505c011a-allfinite", "0.0217"),
    ("GEMSDOE30", "gems30-MSDB1-edge44090-20261025-e7856ec3f14a", "0.1462"),
]


def gh_json(path: str):
    out = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ledger_rows() -> list[dict]:
    rows = []
    with (ROOT / "registry" / "owner_score_ledger.csv").open() as fh:
        for r in csv.DictReader(fh):
            try:
                score = float(r["score"])
            except ValueError:
                continue
            if r["site"].startswith("DrivenData"):
                continue
            rows.append({"site": r["site"], "submission": r["submission"].strip(), "score": score, "owner": owner_of(SITE_TO_REPO.get(r["site"], r["site"]))})
    have = {(r["site"], r["submission"]) for r in rows}
    for site, sub, sc in EXTRA_ROWS:
        if (site, sub) not in have:
            rows.append({"site": site, "submission": sub, "score": float(sc), "added_from": "standing prompt 2026-10-26"})
    return rows


def repo_tifs(repo: str) -> tuple[str | None, list[dict]]:
    try:
        ref = gh_json(f"repos/{owner_of(repo)}/{repo}/commits/HEAD")["sha"]
        tree = gh_json(f"repos/{owner_of(repo)}/{repo}/git/trees/{ref}?recursive=1")
    except subprocess.CalledProcessError:
        return None, []
    tifs = [t for t in tree.get("tree", []) if t["type"] == "blob"
            and t["path"].lower().endswith((".tif", ".tiff")) and int(t.get("size", 0)) <= MAX_BYTES]
    return ref, tifs


def strip_variant(name: str) -> str:
    s = re.sub(r"\.(tif|tiff|zip)$", "", name, flags=re.I)
    for suf in ("-zeros-zeros", "-zeros", "-nan", "-allfinite", "_allfinite", "-nanoutside", "-zero", "-hard", "-candidate"):
        if s.lower().endswith(suf):
            s = s[: -len(suf)]
    return s


def match(sub: str, tifs: list[dict]) -> tuple[dict | None, str, list[str]]:
    stem = strip_variant(sub).lower()
    full = sub.lower()
    exact = [t for t in tifs if Path(t["path"]).stem.lower() == full]
    if len(exact) >= 1:
        return exact[0], "exact_filename", [t["path"] for t in exact]
    cont = [t for t in tifs if full in Path(t["path"]).name.lower()]
    if len(cont) == 1:
        return cont[0], "full_name_substring", [cont[0]["path"]]
    cont = [t for t in tifs if stem and stem in Path(t["path"]).name.lower()]
    if cont:
        # prefer a zeros/allfinite variant, then nan; record all candidates
        pref = sorted(cont, key=lambda t: (0 if "zeros" in t["path"].lower() else 1 if "allfinite" in t["path"].lower() else 2, len(t["path"])))
        # all candidates must be variants of the same stem for an unambiguous match
        stems = {strip_variant(Path(t["path"]).name).lower() for t in cont}
        if len(stems) == 1:
            return pref[0], "stem_variant", [t["path"] for t in cont]
        return None, "ambiguous_stem", [t["path"] for t in cont]
    toks = [t for t in re.findall(r"[0-9a-f]{8,}", sub.lower()) if not t.isdigit()]
    for tok in toks:
        hits = [t for t in tifs if tok in Path(t["path"]).name.lower()]
        stems = {strip_variant(Path(t["path"]).name).lower() for t in hits}
        if hits and len(stems) == 1:
            pref = sorted(hits, key=lambda t: (0 if "zeros" in t["path"].lower() else 1, len(t["path"])))
            return pref[0], f"hash_token:{tok}", [t["path"] for t in hits]
        if hits:
            return None, f"ambiguous_hash_token:{tok}", [t["path"] for t in hits]
    return None, "not_found", []


def fetch(repo: str, ref: str, path: str, size: int, cache: Path) -> Path | None:
    dest = cache / repo / path
    if dest.exists() and dest.stat().st_size == size:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    for attempt in range(3):
        try:
            with tmp.open("wb") as fh:
                subprocess.run(["gh", "api", f"repos/{owner_of(repo)}/{repo}/contents/{path}?ref={ref}",
                                "-H", "Accept: application/vnd.github.raw"], stdout=fh, check=True,
                               stderr=subprocess.PIPE)
            tmp.replace(dest)
            return dest
        except subprocess.CalledProcessError:
            time.sleep(2 * (attempt + 1))
    tmp.unlink(missing_ok=True)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--cache", default=str(ROOT / ".cache" / "ledger"))
    ap.add_argument("--out", default=str(ROOT / "evidence" / "live_ledger_rasters.json"))
    a = ap.parse_args()
    cache = Path(a.cache)
    rows = ledger_rows()
    repos = sorted({SITE_TO_REPO.get(r["site"], r["site"]) for r in rows})
    trees = {}
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for repo, res in zip(repos, ex.map(repo_tifs, repos)):
            trees[repo] = res
            print(f"{repo}: {len(res[1])} tifs @ {str(res[0])[:12]}", flush=True)
    out = []
    jobs = []
    for r in rows:
        repo = SITE_TO_REPO.get(r["site"], r["site"])
        ref, tifs = trees.get(repo, (None, []))
        hit, how, cands = match(r["submission"], tifs) if ref else (None, "repo_unavailable", [])
        rec = dict(r, repo=repo, owner=owner_of(repo), ref=ref, match=how, candidates=cands[:6])
        if hit:
            rec.update(path=hit["path"], git_size=int(hit["size"]))
            jobs.append((len(out), repo, ref, hit["path"], int(hit["size"])))
        out.append(rec)
    # Several ledger rows can resolve to the same blob (e.g. a re-upload under a second name):
    # download each (repo, path) exactly once, then fan the result back out to every row.
    uniq: dict[tuple[str, str], list] = {}
    for i, repo, ref, path, size in jobs:
        uniq.setdefault((repo, path), [ref, size, []])[2].append(i)
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(fetch, repo, v[0], path, v[1], cache): (repo, path) for (repo, path), v in uniq.items()}
        for f in cf.as_completed(futs):
            key = futs[f]
            p = f.result()
            for i in uniq[key][2]:
                if p is None:
                    out[i]["status"] = "download_failed"
                else:
                    out[i].update(status="ok", local=str(p.relative_to(ROOT)), sha256=sha256(p), bytes=p.stat().st_size)
    for rec in out:
        rec.setdefault("status", "unmatched")
    n_ok = sum(r["status"] == "ok" for r in out)
    doc = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence_class_of_scores": "OWNER-REPORT (user-supplied submission log; no organizer receipts)",
        "n_rows": len(out), "n_matched_downloaded": n_ok,
        "rows": out,
    }
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"matched+downloaded {n_ok}/{len(out)} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
