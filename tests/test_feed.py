import json
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import Request
from scripts.refresh_feed import SameOriginRedirect, parse_leader, refresh

GOOD = '''<html><table><tr><th>Other</th></tr><tr><td>1</td></tr></table>
<table><thead><tr><th>Rank</th><th>Participant</th><th>Best<br>public<br>DW-Tversky<br>(in descending order)</th></tr></thead>
<tbody><tr><td>#1</td><td>example<br>32 submissions</td><td>0.4544</td></tr>
<tr><td>#2</td><td>other</td><td>0.3916</td></tr></tbody></table></html>'''


class FeedTests(unittest.TestCase):
    def test_only_rank_one_metric_column_is_parsed(self):
        self.assertEqual(parse_leader(GOOD), {'rank': 1, 'score': 0.4544, 'display_score': '0.4544'})

    def test_missing_wrong_or_ambiguous_schema_fails_closed(self):
        for data in ('login page', GOOD.replace('DW-Tversky', 'Accuracy'),
                     GOOD.replace('0.4544', '1.1'), GOOD + GOOD):
            with self.subTest(data=data[:30]), self.assertRaises(ValueError):
                parse_leader(data)

    def test_refresh_retains_old_observation_but_marks_unavailable(self):
        old = {'leaderboard': {'last_observation': {'rank': 1, 'score': 0.4, 'observed_utc': 'old'}}}
        with patch('scripts.refresh_feed.get_url', side_effect=URLError('blocked')):
            report = refresh(old)
        self.assertFalse(report['leaderboard']['available'])
        self.assertEqual(report['leaderboard']['last_observation']['observed_utc'], 'old')
        self.assertFalse(report['submission_approved'])
        self.assertEqual(len(report['sources']), 9)
        self.assertTrue(all(not x['available'] for x in report['sources']))

    def test_refresh_treats_leaderboard_and_sites_independently(self):
        def get(url, *, github=False):
            if not github:
                return GOOD.encode()
            return json.dumps({'sha': 'a'*40, 'commit': {'committer': {'date': '2026-10-27T01:00:00Z'}}}).encode()
        with patch('scripts.refresh_feed.get_url', side_effect=get):
            report = refresh()
        self.assertTrue(report['leaderboard']['available'])
        self.assertTrue(all(x['available'] for x in report['sources']))
        self.assertFalse(report['submission_approved'])
        self.assertIn('not an artifact-linked receipt', report['leaderboard']['last_observation']['evidence_class'])

    def test_cross_origin_redirect_rejected_before_authorization_forward(self):
        handler = SameOriginRedirect()
        request = Request('https://api.github.com/test', headers={'Authorization': 'Bearer secret'})
        with self.assertRaises(ValueError):
            handler.redirect_request(request, None, 302, 'redirect', {}, 'https://evil.example/test')


if __name__ == '__main__':
    unittest.main()
