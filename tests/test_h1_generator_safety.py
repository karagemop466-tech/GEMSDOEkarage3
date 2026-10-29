"""The inherited negative H1 generator must never publish to public downloads."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_h1_candidate_generator_is_explicitly_non_approving_and_quarantined():
    source = (ROOT / 'scripts/generate_unique_submission.py').read_text()
    assert 'does NOT establish complete-registry uniqueness' in source
    assert 'NOT a leaderboard estimate or a protocol-' in source
    assert 'compliant HOLDOUT-DTI result' in source
    assert 'out_dir=ROOT / "evidence/quarantine/h1-seismic-gravity-basin"' in source
    assert 'ROOT / "docs/downloads"' not in source
    assert 'guarantee literal uniqueness' not in source
    assert 'Assigned lane: H1' not in source
    card = json.loads((ROOT / 'docs/data/run-card-20261029-h1.json').read_text())
    assert card['verdict'] == 'negative' and card['ok_to_submit'] is False
    assert 'NOT ESTABLISHED' in card['correlation_overlap_vs_registry']['status']
    assert card['note_length'] <= 140
    assert 'Unique' not in card['note']
    assert (ROOT / card['raster_path']).is_file()
    assert not list((ROOT / 'docs/downloads').glob('*h1-seismic-gravity-basin*.tif'))
