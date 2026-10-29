from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
from urllib.parse import unquote, urlsplit

import pytest

from scripts import build_run_card, build_site

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["index.html", "executive-summary.html", "submission-desk.html", "research.html", "sources.html"]


class Inspect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.duplicates = []
        self.links = []
        self.title = 0
        self.main = 0
        self.lang = None
        self.table_regions = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self.title += 1
        if tag == "main":
            self.main += 1
        if "id" in a:
            if a["id"] in self.ids:
                self.duplicates.append(a["id"])
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag in {"script", "link"}:
            self.links += [a[x] for x in ("src", "href") if x in a]
        if tag == "div" and "table-wrap" in a.get("class", "").split():
            self.table_regions.append(a)


def inspect(path):
    parser = Inspect()
    parser.feed(path.read_text())
    return parser


def test_site_links_fragments_and_semantics():
    parsed = {ROOT / page: inspect(ROOT / page) for page in PAGES}
    for path, page in parsed.items():
        assert page.lang == "en" and page.title == 1 and page.main == 1
        assert not page.duplicates
        assert "main" in page.ids
        for region in page.table_regions:
            assert region.get("role") == "region" and region.get("tabindex") == "0"
            assert region.get("aria-label")
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            assert target.is_file(), f"{path.name}: broken link to {link}"
            if url.fragment and target.suffix == ".html":
                target_parsed = parsed.get(target) or inspect(target)
                assert unquote(url.fragment) in target_parsed.ids, f"{path.name}: broken fragment {link}"


def snapshot_copy(tmp_path):
    files = ["docs/data/historical-audit.json", "docs/data/repo-heads.json", "docs/data/current-run.json",
             "data/focus_registry.json", "site/index.template.html", "site/executive.template.html"]
    for relative in files:
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, dest)
    return tmp_path


def test_generated_pages_match_evidence(tmp_path, monkeypatch):
    root = snapshot_copy(tmp_path)
    monkeypatch.setattr(build_site, "ROOT", root)
    result = build_site.render()
    assert result[root / "index.html"] == (ROOT / "index.html").read_text()
    assert result[root / "executive-summary.html"] == (ROOT / "executive-summary.html").read_text()
    decision = json.loads((ROOT / "docs/current-gate-decision.json").read_text())
    if decision["ok_to_submit"]:
        assert "OK TO SUBMIT? YES" in result[root / "index.html"]
        assert decision["raster_sha256"] in result[root / "index.html"]
    else:
        public_page = result[root / "index.html"]
        assert "DO NOT SUBMIT" in public_page
        parser = Inspect()
        parser.feed(public_page)
        assert not any("karage3-unique-offcat" in link.lower() or
                       (not urlsplit(link).scheme and (".tif" in link.lower() or ".zip" in link.lower()))
                       for link in parser.links)


def test_site_builder_rejects_stale_and_tampered_evidence(tmp_path, monkeypatch):
    root = snapshot_copy(tmp_path)
    monkeypatch.setattr(build_site, "ROOT", root)
    audit_path = root / "docs/data/historical-audit.json"
    audit = json.loads(audit_path.read_text())
    audit["lattice"]["uncovered_beyond_3px"] += 1
    audit_path.write_text(json.dumps(audit))
    with pytest.raises(ValueError, match="Run card"):
        build_site.render()


def test_negative_card_builder_refuses_to_overwrite_real_run(tmp_path, monkeypatch):
    root = snapshot_copy(tmp_path)
    monkeypatch.setattr(build_run_card, "ROOT", root)
    path = root / "docs/data/current-run.json"
    card = json.loads(path.read_text())
    card["experiments_run"] = 1
    path.write_text(json.dumps(card))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="Refusing"):
        build_run_card.main()
    assert path.read_bytes() == before
