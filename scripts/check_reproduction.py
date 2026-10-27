#!/usr/bin/env python3
"""Compare independently regenerated audit content, ignoring only run time."""
import json
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: check_reproduction.py expected.json actual.json")
expected, actual = (json.loads(Path(p).read_text()) for p in sys.argv[1:])
for obj in (expected, actual):
    obj.pop("created_utc", None)
if expected != actual:
    raise SystemExit("Pinned geometry audit differs from regenerated result")
print("Pinned geometry audit reproduced (execution timestamp ignored).")
