#!/usr/bin/env python3
"""Refresh pinned GitHub evidence, not organizer scores or the DrivenData leaderboard."""
from __future__ import annotations

import base64
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = {
    24: ('h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan', .2477),
    25: ('dotted-h19-5-d2-8-20261002-e56ea318af89-nan', .2600),
    27: ('topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan', .2449),
    28: ('h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan', .2710),
    30: ('d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca', .2600),
    31: ('h27-4-solo-d28-20261004-8acb75e1-nan', .2708),
    32: ('h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros', .2778),
    33: ('h33d-analog-tip-stepover-r30-20261004-cb490425926e', .2632),
    36: ('anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros', .2750),
}


def gh(path):
    return subprocess.check_output(['gh', 'api', path], timeout=60, stderr=subprocess.PIPE)


def audit(number):
    repo = f'buffedlizard55-lab/GEMSDOE{number}'
    name, score = CLAIMS[number]
    result = {'site': f'GEMSDOE{number}', 'repository': f'https://github.com/{repo}',
              'owner_reported_submission': name, 'owner_reported_value': score,
              'evidence_class': 'USER/OWNER-REPORT — no organizer receipt',
              'claim_origin': 'User-supplied historical list; no file-to-score receipt verified.',
              'estimated_score': None, 'unique': None, 'ok_to_submit': False, 'sources': []}
    try:
        meta = json.loads(gh(f'repos/{repo}'))
        branch = meta['default_branch']
        commit = json.loads(gh(f'repos/{repo}/commits/{branch}'))['sha']
        result.update(commit=commit, default_branch=branch)
        for path in ['README.md', 'registry/current_status.json']:
            try:
                entry = json.loads(gh(f'repos/{repo}/contents/{path}?ref={commit}'))
                if entry.get('encoding') != 'base64' or not entry.get('content'):
                    raise ValueError(f'{path}: GitHub did not return base64 file contents')
                data = base64.b64decode(entry['content'], validate=False)
                dest = ROOT / 'evidence' / 'upstream' / f'GEMSDOE{number}' / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                result['sources'].append({'url': f'https://github.com/{repo}/blob/{commit}/{path}',
                                          'local': str(dest.relative_to(ROOT)),
                                          'sha256': hashlib.sha256(data).hexdigest()})
            except subprocess.CalledProcessError:
                if path == 'README.md':
                    raise
                # Not every site has this optional status file.
        if not result['sources']:
            raise ValueError('no pinned README returned')
        result['refresh_status'] = 'ok'
    except (subprocess.SubprocessError, OSError, KeyError, TypeError, ValueError) as exc:
        result['refresh_status'] = 'failed'
        result['error'] = str(exc)
    return result


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(audit, CLAIMS))
    complete = all(row['refresh_status'] == 'ok' for row in rows)
    target = ROOT / 'docs' / 'sites.json'
    payload = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
               'scope': 'GitHub repository heads only; historical claims are not organizer receipts.',
               'refresh_complete': complete, 'sites': rows}
    temporary = target.with_suffix('.json.partial')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    temporary.replace(target)
    print(f"GitHub source refresh: {sum(row['refresh_status'] == 'ok' for row in rows)}/{len(rows)} succeeded")
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
