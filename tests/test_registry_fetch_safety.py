import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.fetch_all_registry import fetch_repo_rasters

ROOT = Path(__file__).resolve().parents[1]


def tar_stream():
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as tar:
        info = tarfile.TarInfo('repo/docs/test.tif')
        info.size = 4
        tar.addfile(info, io.BytesIO(b'good'))
    return data.getvalue()


class RegistryFetchSafety(unittest.TestCase):
    def test_failed_head_is_reported(self):
        with patch('scripts.fetch_all_registry.resolve_head', return_value=None):
            _, ref, rows, error = fetch_repo_rasters('owner', 'repo', 'test', ROOT / '.cache/test-registry')
        self.assertIsNone(ref)
        self.assertEqual(rows, [])
        self.assertIsNotNone(error)

    def test_bad_cached_file_same_size_is_replaced(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            cache = Path(tmp)
            target = cache / 'owner/repo/docs/test.tif'
            target.parent.mkdir(parents=True)
            target.write_bytes(b'evil')
            with patch('scripts.fetch_all_registry.resolve_head', return_value='a' * 40), \
                 patch('urllib.request.urlopen', return_value=io.BytesIO(tar_stream())):
                _, _, rows, error = fetch_repo_rasters('owner', 'repo', 'test', cache)
            self.assertIsNone(error)
            self.assertEqual(target.read_bytes(), b'good')
            self.assertEqual(len(rows), 1)

    def test_failed_stream_does_not_claim_success(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp, \
             patch('scripts.fetch_all_registry.resolve_head', return_value='a' * 40), \
             patch('urllib.request.urlopen', side_effect=OSError('broken')), \
             patch('scripts.fetch_all_registry.time.sleep'):
            _, _, rows, error = fetch_repo_rasters('owner', 'repo', 'test', Path(tmp))
            self.assertEqual(rows, [])
            self.assertIn('broken', error)
