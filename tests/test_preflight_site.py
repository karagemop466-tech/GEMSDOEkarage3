import json
import re
import subprocess
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('a', 'link') and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag == 'script' and 'src' in attrs:
            self.links.append(attrs['src'])


class SiteTests(unittest.TestCase):
    def test_legacy_pages_root_and_nojekyll(self):
        root = (ROOT / 'index.html').read_text()
        self.assertIn('docs/preflight.html', root)
        self.assertTrue((ROOT / '.nojekyll').is_file())
        self.assertTrue((DOCS / 'index.html').is_file())
        home = (DOCS / 'index.html').read_text()
        self.assertIn('current submission decision', home.lower())
        self.assertIn('promotion_gate.py', home)
        decision = json.loads((DOCS / 'current-gate-decision.json').read_text())
        summary = (DOCS / 'executive-summary.html').read_text()
        expected = 'OK TO DOWNLOAD AND SUBMIT: YES' if decision['ok_to_submit'] else 'DO NOT SUBMIT'
        self.assertIn(expected, summary)
        self.assertIn(decision['raster_sha256'], summary)
        for card_path in ('run-card.json', 'data/latest-run-card.json', 'data/run_card.json'):
            card = json.loads((DOCS / card_path).read_text())
            self.assertEqual(card['verdict'], 'negative')
            self.assertFalse(card['ok_to_submit'])

    def test_internal_links_exist(self):
        for page in ('preflight.html', 'preflight-executive.html', 'preflight-research.html'):
            parser = Links()
            parser.feed((DOCS / page).read_text())
            for url in parser.links:
                parsed = urlsplit(url)
                if not parsed.scheme and not parsed.netloc and parsed.path:
                    with self.subTest(page=page, url=url):
                        self.assertTrue((DOCS / parsed.path).is_file())

    def test_all_nine_historical_rows_labeled_and_upload_blocked(self):
        page = (DOCS / 'preflight-executive.html').read_text()
        manifest = json.loads((ROOT / 'registry/historical.json').read_text())
        self.assertEqual(page.count('USER-REPORTED / unverified'), 9)
        for row in manifest['historical']:
            self.assertIn(row['historical_file'], page)
            self.assertIn(row['quoted_owner_claim'], page)
        self.assertIn('NO FILE IS APPROVED FOR SUBMISSION', page)
        self.assertIn('No submission file available', page)

    def test_older_research_slate_is_labeled_and_current_review_is_linked(self):
        research = (DOCS / 'preflight-research.html').read_text()
        home = (ROOT / 'index.html').read_text()
        self.assertIn('ARCHIVED 27 OCTOBER HYPOTHESIS SLATE', research)
        self.assertIn('href="../research.html"', research)
        self.assertIn('href="docs/release-review.html">Latest safety review', home)
        self.assertNotIn('initially empty checkout', research)

    def test_no_stale_feed_can_approve_a_slot(self):
        feed = json.loads((DOCS / 'data/feed.json').read_text())
        card = json.loads((DOCS / 'data/latest-run.json').read_text())
        self.assertEqual(card, json.loads((DOCS / 'data/latest-run-card.json').read_text()))
        self.assertFalse(feed['submission_approved'])
        self.assertFalse(card['ok_to_submit'])
        self.assertFalse(card['slot_selected'])
        self.assertEqual(card['verdict'], 'negative')
        self.assertIsNone(card['raster_sha256'])
        self.assertLessEqual(len(card['note']), 140)

    def test_deterministic_build(self):
        files = [DOCS / p for p in ('preflight.html', 'preflight-executive.html', 'preflight-research.html',
                                    'data/latest-run-card.json', 'data/historical.json', 'data/geometry_audit.json', 'data/run_card.json', 'data/review.md')]
        before = {p: p.read_bytes() for p in files}
        subprocess.run([sys.executable, str(ROOT / 'scripts/build_preflight_site.py')], cwd=ROOT, check=True, capture_output=True)
        self.assertEqual(before, {p: p.read_bytes() for p in files})

    def test_status_not_tied_to_page_metadata(self):
        javascript = (DOCS / 'assets/site.js').read_text()
        self.assertNotRegex(javascript, r'submission_approved\s*=\s*true')
        self.assertIn('Refresh never approves a submission', javascript)
        self.assertIn('stale', javascript)


if __name__ == '__main__':
    unittest.main()
