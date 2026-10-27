from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = (
    Path("index.html"),
    Path("executive-summary.html"),
    Path("research/repository-review.html"),
    Path("research/hypotheses.html"),
)
EXPECTED_SITES = {
    "GEMSDOE24",
    "GEMSDOE25",
    "GEMSDOE27",
    "GEMSDOE28",
    "GEMSDOE30",
    "GEMSDOE31",
    "GEMSDOE32",
    "GEMSDOE33",
    "GEMSDOE36",
}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for attribute in ("href", "src"):
            value = values.get(attribute)
            if value:
                self.targets.append(value)


class StaticSiteTests(unittest.TestCase):
    def test_all_local_html_links_resolve(self) -> None:
        for page in PAGES:
            with self.subTest(page=str(page)):
                parser = LinkParser()
                parser.feed((ROOT / page).read_text(encoding="utf-8"))
                for target in parser.targets:
                    parsed = urlsplit(target)
                    if parsed.scheme or parsed.netloc or not parsed.path:
                        continue
                    destination = (ROOT / page.parent / parsed.path).resolve()
                    self.assertTrue(destination.exists(), f"{page}: missing {target}")

    def test_local_markdown_links_resolve(self) -> None:
        markdown_files = (
            Path("README.md"),
            Path("research/repository-review-2026-10-27.md"),
            Path("research/hypotheses-2026-10-27.md"),
        )
        for page in markdown_files:
            text = (ROOT / page).read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)", text):
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                destination = (ROOT / page.parent / parsed.path).resolve()
                self.assertTrue(destination.exists(), f"{page}: missing {target}")

    def test_current_run_card_is_explicitly_negative_and_fail_closed(self) -> None:
        card = json.loads((ROOT / "data/current-run-card.json").read_text(encoding="utf-8"))
        self.assertEqual(card["verdict"], "negative")
        self.assertFalse(card["download_authorized"])
        self.assertFalse(card["submit_authorized"])
        self.assertIsNone(card["raster_sha256"])
        self.assertIsNone(card["holdout_dti"]["value"])
        self.assertIsNone(card["holdout_dti"]["confidence_interval_95"])
        self.assertIsNone(card["correlation_overlap_vs_registry"]["surface_rank_correlation"])
        self.assertIsNone(card["correlation_overlap_vs_registry"]["maximum_dot_overlap_within_3px"])
        self.assertEqual(card["validator_output"]["status"], "NOT RUN")

    def test_executive_summary_covers_all_requested_sites_and_blocks_upload(self) -> None:
        page = (ROOT / "executive-summary.html").read_text(encoding="utf-8")
        for site in EXPECTED_SITES:
            with self.subTest(site=site):
                self.assertIn(site, page)
        self.assertIn("OK TO DOWNLOAD A NEW TIFF: NO", page)
        self.assertIn("OK TO SUBMIT: NO", page)
        self.assertIn("Not estimable", page)
        self.assertIn("USER-PROVIDED / UNVERIFIED", page)

    def test_readme_preserves_session_contract(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for required in (
            "Maximize P(Win)",
            "Own the Outcome",
            "evaluate_holdout.py",
            "submission_writer.py",
            "HOLDOUT-DTI",
            "0.90",
            "70%",
            "three experiments or two hours",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readme)


if __name__ == "__main__":
    unittest.main()
