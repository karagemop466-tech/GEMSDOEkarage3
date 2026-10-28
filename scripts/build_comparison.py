"""Derive UI comparison rows from pinned upstream reports; never certify their claims."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://github.com/buffedlizard55-lab/GEMSDOE32/blob/73485f27cf230af770167397c2b72cb9ce3b3f25/evidence/arena48_focus9_overlap.json'

def enrich(rows, audit):
    winners = {item['site']: item for item in audit['winners']}
    for row in rows:
        # User/repository reports are not organizer receipts or a score forecast.
        row['evidence_class'] = 'USER-REPORTED / UNVERIFIED'
        row['estimated_score'] = None
        row['unique'] = None
        row['ok_to_submit'] = False
        winner = winners[row['site']]
        # Legacy rows mixed owner claims, unlabelled holdout numbers and an
        # estimated hidden score. Do not surface those as authenticated results.
        if 'other_confirmed_submissions' in row:
            row['other_user_reported_submissions'] = row.pop('other_confirmed_submissions')
        for key in ('holdout_dti_static_hide_recover', 'holdout_dti_sgmc_calibrated'):
            row.pop(key, None)  # insufficient evaluator / positive-count / CI provenance
        row['evidence_class'] = 'USER-REPORTED / UNVERIFIED'
        row['estimated_score'] = None
        row['unique'] = False
        row['ok_to_submit'] = False
        row['historical_artifact'] = {
            'url': f"{row['repository']}/blob/{winner['repo_ref']}/{winner['file']}",
            'filename': Path(winner['file']).name,
            'sha256_upstream_reported': winner['sha256'],
            'mechanism_upstream_reported': winner['what_it_is'],
            'evidence_url': SOURCE,
            'locally_validated': False,
            'uniqueness': 'NOT UNIQUE under protocol — upstream overlap audit; not rerun locally',
            'purpose': 'Historical research only; NOT OK TO SUBMIT',
        }
    local_path = ROOT / 'docs/historical-raster-audit.json'
    if local_path.exists():
        local = json.loads(local_path.read_text())
        inspected = {item['site']: item for item in local['rasters']}
        for row in rows:
            item = inspected.get(row['site'])
            if item and item['sha256'] == row['historical_artifact']['sha256_upstream_reported']:
                peers = [p for p in local['pairwise'] if p['candidate'] == row['site']]
                row['historical_artifact']['positive_mask_locally_inspected'] = True
                row['historical_artifact']['uniqueness'] = 'NOT UNIQUE — local nine-winner dot-overlap test'
                row['historical_artifact']['local_audit'] = 'historical-raster-audit.json'
                row['historical_artifact']['max_peer_overlap_3px'] = max(p['candidate_fraction_within_3px'] for p in peers)
    return rows

if __name__ == '__main__':
    target = ROOT / 'docs/sites.json'
    document = json.loads(target.read_text())
    audit = json.loads((ROOT / 'evidence/upstream/GEMSDOE32/evidence/arena48_focus9_overlap.json').read_text())
    enrich(document['sites'], audit)
    document['promoted_candidate'] = None
    target.write_text(json.dumps(document, indent=2) + '\n')
