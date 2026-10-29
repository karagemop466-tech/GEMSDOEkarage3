import shutil
from pathlib import Path

import pytest

from scripts.tiff_inventory import inventory

ROOT = Path(__file__).resolve().parents[1]


def test_current_inventory_separates_audited_cohort_from_unassessed_files():
    checked = inventory(ROOT)
    assert len(checked['audited_paths']) == 9
    assert len(checked['unassessed_paths']) == 2
    assert all('karage3-unique-offcat' in path for path in checked['unassessed_paths'])
    assert all(row['status'] == 'UNASSESSED' and row['do_not_submit']
               for row in checked['unassessed']['files'])


def test_inventory_fails_if_new_tiff_has_no_audit_classification(tmp_path):
    for name in ('evidence/saved-tiffs-literal-20261028.json',
                 'evidence/unassessed-tiffs-inventory-20261029.json'):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    docs = tmp_path / 'docs'
    shutil.copytree(ROOT / 'docs', docs)
    (docs / 'downloads/unclassified.tif').write_bytes(b'not-a-real-raster; inventory test only')
    with pytest.raises(ValueError, match='do not match'):
        inventory(tmp_path)


def test_inventory_fails_if_unassessed_bytes_change(tmp_path):
    checked = inventory(ROOT)
    for relative in ('evidence/saved-tiffs-literal-20261028.json',
                     'evidence/unassessed-tiffs-inventory-20261029.json'):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    for relative in (*checked['audited_paths'], *checked['unassessed_paths']):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    row = checked['unassessed']['files'][0]
    path = tmp_path / row['path']
    path.write_bytes(path.read_bytes() + b'\0')
    with pytest.raises(ValueError, match='unassessed TIFF'):
        inventory(tmp_path)
