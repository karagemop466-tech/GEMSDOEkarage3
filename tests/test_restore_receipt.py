"""Regression: a partial --group restore must never overwrite the tracked full receipt.

Offline: the network fetch (restore_entry) is replaced by a stub, so no bytes move.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.restore_data as restore_data  # noqa: E402


def _stub_restore(entry, root):
    return {"id": entry["id"], "dest": entry["dest"], "group": entry["group"],
            "status": "restored", "bytes": 0, "sha256": entry["sha256"]}


class RestoreReceiptTests(unittest.TestCase):
    def _manifest(self, tmp: Path) -> Path:
        man = tmp / "manifest.json"
        man.write_text(json.dumps({"schema_version": 1, "files": [
            {"id": "a", "dest": "a.tif", "group": "core", "sha256": "0" * 64, "path": "x", "repo": "x/y", "ref": "r"},
            {"id": "b", "dest": "b.tif", "group": "external", "sha256": "1" * 64, "path": "x", "repo": "x/y", "ref": "r"},
        ]}))
        return man

    def test_partial_group_writes_beside_data_and_leaves_tracked_receipt_untouched(self):
        tracked = ROOT / "data" / "restore_receipt.json"
        before = tracked.read_bytes()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            argv = ["restore_data.py", "--group", "core", "--target-dir", str(tmp / "data"),
                    "--manifest", str(self._manifest(tmp))]
            with patch.object(restore_data, "restore_entry", side_effect=_stub_restore), \
                    patch.object(sys, "argv", argv):
                restore_data.main()
            partial = json.loads((tmp / "data" / "restore_receipt_core.json").read_text())
            self.assertEqual(partial["verified_files_count"], 1)
        self.assertEqual(tracked.read_bytes(), before)

    def test_full_group_is_the_only_path_that_may_replace_tracked_receipt(self):
        # Source-level guard: the tracked path is written only inside the group == "all" branch.
        src = (ROOT / "scripts" / "restore_data.py").read_text()
        self.assertIn('if args.group == "all":\n        receipt_path = ROOT / "data" / "restore_receipt.json"', src)


if __name__ == "__main__":
    unittest.main()
