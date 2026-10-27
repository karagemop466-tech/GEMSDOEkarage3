#!/usr/bin/env bash
# Restore the immutable shared template and its hash-pinned owner mirrors into ignored cache.
# This does not run a model experiment, validate a candidate, or spend a submission slot.
set -euo pipefail
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != '--core' && "$1" != '--build-stack' ) ]]; then
  echo 'Usage: restore_shared_template.sh [--core|--build-stack]' >&2
  exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${GEMS_CACHE_DIR:-$ROOT/.cache}"
PYTHON="${PYTHON:-python3}"
REF=73485f27cf230af770167397c2b72cb9ce3b3f25
ARCHIVE_SHA=c3c72cd5d9be1aea6d449ea95df6c3137b27b03c94cbfc740934b9c6cfd5002d
ARCHIVE="$CACHE/gems32-$REF.tar.gz"
mkdir -p "$CACHE"
# Extract into a new directory each time: overlaying an old tree can retain stray
# Python modules and would not prove that the restored template is unmodified.
TEMPLATE="$(mktemp -d "$CACHE/shared-template-$REF.XXXXXXXX")"
if ! test -f "$ARCHIVE" || ! echo "$ARCHIVE_SHA  $ARCHIVE" | sha256sum -c --status; then
  curl -fsSL "https://codeload.github.com/buffedlizard55-lab/GEMSDOE32/tar.gz/$REF" -o "$ARCHIVE.partial"
  if ! echo "$ARCHIVE_SHA  $ARCHIVE.partial" | sha256sum -c --status; then
    rm -f "$ARCHIVE.partial"
    echo 'Pinned template archive digest mismatch; stopped.' >&2
    exit 1
  fi
  mv "$ARCHIVE.partial" "$ARCHIVE"
fi
tar -xzf "$ARCHIVE" -C "$TEMPLATE" --strip-components=1
(
  cd "$TEMPLATE"
  echo 'd786273021c86b62af2504060309554218ca1442ed84d717f13334dddeea892c  scripts/evaluate_holdout.py' | sha256sum -c --status
  echo 'cf7eb9948cfe5032e1db2362ddd5a075c2c744bb33ebbcfb2ba2b5ebd1b1de9b  scripts/submission_writer.py' | sha256sum -c --status
  echo '8232b42e06c42d00942b1b2bc3bff2a3dba3d16c171be0a47d2435ee92e39087  scripts/build_features.py' | sha256sum -c --status
  echo '58cff8551ba2f2eb5bbc5656306d8e19243c38721368ddd3d5e393c8e889e316  src/gems32/features.py' | sha256sum -c --status
  echo '463cf26c840a9338816e873a762beb8186c50952ae26ae572e73d71eb329bd34  registry/data_manifest.json' | sha256sum -c --status
)
echo "Shared template restored at $TEMPLATE (no edits or private fork)."
if [[ "${1:-}" == '--core' || "${1:-}" == '--build-stack' ]]; then
  "$PYTHON" "$TEMPLATE/scripts/restore_data.py" --group core --target-dir "$CACHE/shared-data"
fi
if [[ "${1:-}" == '--build-stack' ]]; then
  "$PYTHON" "$TEMPLATE/scripts/build_features.py" --features "$CACHE/shared-data/training_features.tif" \
    --out "$CACHE/shared-feature-stack.npy" --receipt "$CACHE/shared-feature-receipt.json"
fi
