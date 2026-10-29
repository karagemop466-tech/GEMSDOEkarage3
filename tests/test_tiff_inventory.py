import shutil
from pathlib import Path

import pytest

from scripts.tiff_inventory import inventory

ROOT = Path(__file__).resolve().parents[1]


def test_current_inventory_covers_every_tiff_with_a_negative_audit_row():
    checked = inventory(ROOT)
    current = {str(path.relative_to(ROOT)) for path in (ROOT / 'docs').rglob('*.tif')}
    assert len(checked['audited_paths']) == 13
    assert set(checked['audited_paths']) == current
    assert checked['unassessed_paths'] == []
    assert all(row['duplicate_stop'] and row['ok_to_submit'] is False
               for row in checked['audit']['rasters'])
    assert any('/quarantine/geoconduit-hybrid/' in p for p in checked['audited_paths'])
    assert any('/quarantine/karage3-unique-offcat/' in p for p in checked['audited_paths'])


def _copy_audit_tree(tmp_path):
    shutil.copy2(ROOT / 'evidence/saved-tiffs-literal-20261028.json',
                 tmp_path / 'evidence/saved-tiffs-literal-20261028.json')
    shutil.copytree(ROOT / 'docs', tmp_path / 'docs')


def test_inventory_fails_if_new_tiff_has_no_audit_classification(tmp_path):
    (tmp_path / 'evidence').mkdir(parents=True)
    _copy_audit_tree(tmp_path)
    (tmp_path / 'docs/downloads/unclassified.tif').write_bytes(b'not-a-real-raster; inventory test only')
    with pytest.raises(ValueError, match='do not match'):
        inventory(tmp_path)


def test_inventory_fails_if_audited_bytes_change(tmp_path):
    (tmp_path / 'evidence').mkdir(parents=True)
    _copy_audit_tree(tmp_path)
    checked = inventory(ROOT)
    path = tmp_path / checked['audited_paths'][0]
    path.write_bytes(path.read_bytes() + b'\0')
    with pytest.raises(ValueError, match='Invalid or changed saved-byte audit record'):
        inventory(tmp_path)
