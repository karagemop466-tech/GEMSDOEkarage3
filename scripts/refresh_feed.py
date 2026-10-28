#!/usr/bin/env python3
"""Refresh public source metadata; never changes submission authorization.

Only public GitHub repository metadata is refreshed. DrivenData's published
terms prohibit automated access; its leaderboard is linked, never fetched by
this script. Any retained observation is explicitly stale. No portal
credentials, predictions, or uploads are used.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
SITES = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")
MAX_BYTES = 2_000_000


class TableParser(HTMLParser):
    """Extract cell text without interpreting any script or guessed field."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.depth = 0
        self.suppressed = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.suppressed += 1
        if tag == "table":
            if self.depth == 0:
                self.table = []
            self.depth += 1
        elif self.depth == 1 and tag == "tr":
            self.row = []
        elif self.depth == 1 and tag in ("th", "td") and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.suppressed:
            self.suppressed -= 1
        if self.depth == 1 and tag in ("th", "td") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif self.depth == 1 and tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.depth:
            self.depth -= 1
            if self.depth == 0 and self.table is not None:
                self.tables.append(self.table)
                self.table = None

    def handle_data(self, data):
        if self.cell is not None and not self.suppressed:
            self.cell.append(data)


def parse_leader(html: str) -> dict:
    parser = TableParser()
    parser.feed(html)
    found = []
    for table in parser.tables:
        for head_index, row in enumerate(table):
            headers = [re.sub(r"\s+", "", c).lower() for c in row]
            rank_ix = next((i for i, x in enumerate(headers) if x == "rank"), None)
            metric_ix = next((i for i, x in enumerate(headers) if "tversky" in x), None)
            if rank_ix is None or metric_ix is None:
                continue
            for data in table[head_index + 1:]:
                if max(rank_ix, metric_ix) >= len(data):
                    continue
                if not re.fullmatch(r"#?\s*1", data[rank_ix].strip()):
                    continue
                raw = data[metric_ix].strip()
                if not re.fullmatch(r"(?:0(?:\.\d+)?|1(?:\.0+)?)", raw):
                    raise ValueError("Rank-one score is not a finite [0,1] decimal")
                found.append({"rank": 1, "score": float(raw), "display_score": raw})
    if len(found) != 1:
        raise ValueError(f"Expected exactly one rank-one row in a Tversky leaderboard, found {len(found)}")
    return found[0]


class SameOriginRedirect(HTTPRedirectHandler):
    """Reject cross-origin redirects *before* forwarding an Authorization header."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        source, target = urlsplit(req.full_url), urlsplit(newurl)
        if (source.scheme, source.netloc) != (target.scheme, target.netloc):
            raise ValueError("Cross-origin redirect rejected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get_url(url: str, *, github: bool = False) -> bytes:
    parsed = urlsplit(url)
    if not github or parsed.scheme != 'https' or parsed.netloc != 'api.github.com':
        raise ValueError('Automated access is restricted to the public GitHub API')
    headers = {"User-Agent": "GEMS-research-source-monitor/1.0", "Accept": "application/json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    with build_opener(SameOriginRedirect()).open(Request(url, headers=headers), timeout=12) as response:
        # Never use the GitHub token on a non-GitHub redirect destination.
        if not response.geturl().startswith("https://api.github.com/"):
            raise ValueError("Unexpected GitHub API redirect")
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Response exceeds size limit")
        return data


def refresh(previous: dict | None = None, baseline: dict | None = None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    baseline_sites = (baseline or {}).get("sites", {})
    previous_lb = ((previous or {}).get("leaderboard") or {}).get("last_observation")
    leaderboard = {"url": LEADERBOARD, "checked_utc": None, "available": False,
                   "last_observation": previous_lb,
                   "error": "Not fetched: DrivenData terms prohibit automated access; follow the official link."}
    sources = []
    for site in SITES:
        api = f"https://api.github.com/repos/buffedlizard55-lab/{site}/commits/main"
        entry = {"site": site, "url": f"https://github.com/buffedlizard55-lab/{site}",
                 "available": False, "checked_utc": now, "commit": None, "commit_utc": None,
                 "snapshot_commit": baseline_sites.get(site), "changed_since_snapshot": None, "error": None}
        try:
            payload = json.loads(get_url(api, github=True))
            commit = payload["sha"]
            date = payload["commit"]["committer"]["date"]
            if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
                raise ValueError("Invalid commit hash")
            if not isinstance(date, str) or not date.endswith("Z"):
                raise ValueError("Invalid commit time")
            entry.update(available=True, commit=commit, commit_utc=date,
                         changed_since_snapshot=(commit != baseline_sites[site]) if site in baseline_sites else None)
        except (OSError, URLError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
            entry["error"] = f"{type(e).__name__}: {str(e)[:180]}"
        sources.append(entry)
    return {"schema_version": 1, "checked_utc": now, "leaderboard": leaderboard, "sources": sources,
            "scope": "Metadata freshness only. No automated source refresh changes scientific evidence or submission approval.",
            "submission_approved": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "data" / "feed.json")
    args = parser.parse_args()
    try:
        prev = json.loads(args.out.read_text()) if args.out.exists() else None
    except (OSError, json.JSONDecodeError):
        prev = None
    baseline_path = ROOT / "registry" / "site_commits_at_snapshot.json"
    try:
        baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else None
    except (OSError, json.JSONDecodeError):
        baseline = None
    feed = refresh(prev, baseline)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(feed, indent=2, allow_nan=False) + "\n")
    available = sum(s["available"] for s in feed["sources"])
    print(f"Leaderboard available: {feed['leaderboard']['available']}; site metadata: {available}/{len(SITES)}; "
          f"submission approved: {feed['submission_approved']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
