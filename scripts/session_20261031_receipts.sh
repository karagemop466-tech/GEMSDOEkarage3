#!/usr/bin/env bash
# Regenerates the 2026-10-31 receipts used by docs/executive-summary-20261031.html and the run card.
# Requires .cache/gems_data (restore: evidence/template-inspection/scripts/restore_data.py --group core|external
# --target-dir .cache/gems_data) and .cache/historical/lattice.tif (hash-pinned; see scripts/audit_registry.py).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
TPL=docs/downloads/sample_submission.tif
NINE=$(ls docs/downloads/GEMSDOE{24,25,27,28,30,31,32,33,36}-*.tif)
CANDS="docs/quarantine/colocation-h1/*-nan.tif docs/quarantine/strain-signchange-h2/*-nan.tif docs/quarantine/colocation-h1-expanded/*-nan.tif"
mkdir -p evidence/session-20261031/format evidence/session-20261031/uniqueness-nine evidence/session-20261031/uniqueness-candidates
for f in $NINE $CANDS; do
  b=$(basename "$f" .tif)
  $PY scripts/check_format.py "$f" --template $TPL --out "evidence/session-20261031/format/$b.json" > /dev/null || true
done
for f in $NINE; do
  b=$(basename "$f" .tif); n=$(basename "$f" | cut -d- -f1)
  REFS=""
  for g in $NINE; do [ "$g" = "$f" ] && continue; REFS="$REFS --ref $(basename "$g" | cut -d- -f1)=$g"; done
  $PY scripts/measure_overlap.py "$f" --template $TPL $REFS --ref LATTICE_13GEMSDOE=.cache/historical/lattice.tif \
     --out "evidence/session-20261031/uniqueness-nine/$b.json" > /dev/null
done
for f in $CANDS; do
  b=$(basename "$f" .tif)
  REFS=""
  for g in $NINE; do REFS="$REFS --ref $(basename "$g" | cut -d- -f1)=$g"; done
  $PY scripts/measure_overlap.py "$f" --template $TPL $REFS --ref LATTICE_13GEMSDOE=.cache/historical/lattice.tif \
     --out "evidence/session-20261031/uniqueness-candidates/$b.json" > /dev/null
done
echo RECEIPTS_DONE
