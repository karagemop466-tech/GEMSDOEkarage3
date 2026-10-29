"""A dated raster receipt may not silently claim newly added TIFFs."""
from copy import deepcopy

import pytest

from scripts.audit_saved_tiffs import compare_dated_receipt


def _report(files):
    return {
        'schema_version': 1,
        'checked_utc': 'time varies',
        'classification': 'GEOMETRY AND FORMAT DIAGNOSTIC, NOT A SCORE',
        'scope': 'All checked-in docs TIFFs versus one pinned witness; not a complete registry or a surface audit.',
        'input_provenance': 'Hash-pinned public owner mirrors, not authenticated organizer inputs.',
        'template': {'source_url': 'https://example.invalid/template', 'sha256': 'template-hash'},
        'witness': {'source_url': 'https://example.invalid/witness', 'sha256': 'witness-hash',
                    'positive_pixels': 4, 'uncovered_footprint_pixels': 2},
        'footprint_pixels': 10,
        'rasters': [
            {'file': name, 'sha256': f'hash-{name}', 'duplicate_stop': True}
            for name in files
        ],
        'complete_registry_checked': False,
        'new_candidate_generated': False,
        'experiments_run': 0,
        'weekly_slots_used': 0,
        'verdict': 'negative',
        'ok_to_submit': False,
    }


def test_later_rasters_are_returned_as_unreceipted_not_a_receipt_mismatch():
    receipt = _report(['docs/old.tif'])
    fresh = _report(['docs/old.tif', 'docs/new.tif'])
    assert compare_dated_receipt(fresh, receipt) == ['docs/new.tif']


def test_modified_historical_raster_still_fails_receipt_verification():
    receipt = _report(['docs/old.tif'])
    fresh = deepcopy(receipt)
    fresh['rasters'][0]['sha256'] = 'changed'
    with pytest.raises(ValueError, match='differs from committed rows'):
        compare_dated_receipt(fresh, receipt)


def test_missing_historical_raster_still_fails_receipt_verification():
    receipt = _report(['docs/old.tif'])
    fresh = _report([])
    with pytest.raises(ValueError, match='missing from the fresh audit'):
        compare_dated_receipt(fresh, receipt)
