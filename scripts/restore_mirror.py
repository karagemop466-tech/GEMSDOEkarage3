#!/usr/bin/env python3
"""Run the pinned upstream data restorer; these are NOT organizer-authenticated data.

No credential is stored. Large rasters and the temporary shared tool are kept
in .cache by default and are not part of the Git patch. This is not training.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REF = "73485f27cf230af770167397c2b72cb9ce3b3f25"
REPO = "buffedlizard55-lab/GEMSDOE32"
FILES = {
    "scripts/restore_data.py": "4bbbb6552c4725558cadddc97f698393d584a5ec2a71bd1d41bb1f95c108dff6",
    "src/gems32/__init__.py": "e4a584f79eab8c0db81b5704b1525536fef2dcee5bac28da1455a39868983504",
    "src/gems32/paths.py": "ceb7c79097958beff1f618e608491c3528341b14ee8b2e9cdcfafe1406230b69",
    "registry/data_manifest.json": "463cf26c840a9338816e873a762beb8186c50952ae26ae572e73d71eb329bd34",
}


def restore_shared_tool(workdir: Path) -> None:
    for relative, expected in FILES.items():
        dest = workdir / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file() and hashlib.sha256(dest.read_bytes()).hexdigest() == expected:
            continue
        result = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github.raw+json",
                                 f"repos/{REPO}/contents/{relative}?ref={REF}"],
                                check=True, stdout=subprocess.PIPE)
        if hashlib.sha256(result.stdout).hexdigest() != expected:
            raise ValueError(f"Pinned upstream tool hash mismatch: {relative}")
        with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            try:
                tmp.write(result.stdout)
                tmp.close()
                tmp_path.replace(dest)
            finally:
                tmp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dir", type=Path, default=ROOT / ".cache" / "competition-mirror")
    parser.add_argument("--tool-dir", type=Path, default=ROOT / ".cache" / ("shared-template-" + REF[:7]))
    args = parser.parse_args()
    tool_dir = args.tool_dir.resolve()
    target_dir = args.target_dir.resolve()
    if tool_dir == target_dir:
        parser.error("tool and raster directories must be distinct")
    restore_shared_tool(tool_dir)
    print("Restoring SHA-pinned owner mirrors; NOT organizer-authenticated.", flush=True)
    subprocess.run([sys.executable, str(tool_dir / "scripts/restore_data.py"),
                    "--group", "core", "--target-dir", str(target_dir)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
