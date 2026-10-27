# Vendored shared tools — provenance

Source repo: `buffedlizard55-lab/GEMSDOE32` @ `73485f27cf230af770167397c2b72cb9ce3b3f25`
(cloned 2026-10-27; HEAD recorded in `registry/focus9_registry.json`).

| File here | Source path | SHA-256 here | SHA-256 source | Adaptation |
|---|---|---|---|---|
| `src/karage3/metric.py` | `src/gems32/metric.py` | `382de3eb…25289` | `382de3eb…25289` | none (byte-identical) |
| `src/karage3/holdout.py` | `src/gems32/holdout.py` | `c476410a…fd538` | `c476410a…fd538` | none (byte-identical); `from .metric import …` resolves inside `karage3` unchanged |
| `src/karage3/submission.py` | `src/gems32/submission.py` | `a9b63dc5…c556` | `48f1921e…a9bc` | output filename prefix `gemsdoe32-` → `karage3-` (3 lines) only |
| `scripts/restore_data.py` | `scripts/restore_data.py` | `e1d0db23…5063` | `4bbbb655…dff6` | import `gems32.paths` → `karage3.paths` (1 line) only |
| `tests/test_metric.py` | `tests/test_metric.py` | `7f057bcb…d90c` | `c18a5f39…8eccf` | import package rename (1 line) only |
| `src/karage3/registry_audit.py` | `src/gems32/registry_audit.py` | `f12b539c…530ab` | `f12b539c…530ab` | none (byte-identical) |
| `registry/owner_score_ledger.csv` | `docs/score-ledger.csv` | — | — | none; rows already carry `provenance=user brief` per line |

Full hashes are reproducible with `sha256sum`. Evaluator identifiers kept verbatim so numbers
remain comparable across repos: `GEMSDOE32-HOLDOUT-v3-visible-only`,
`GEMSDOE32-SGMC-CAL-v3.0`.

Session efficiency note (not a fork): `training_features.tif` was restored in this session by a
one-pass codeload extraction of the five pinned parts (the vendored script re-streams the
tarball per part). Acceptance criterion identical: assembled SHA-256 must equal the manifest
pin `4371c82e…23bc5` (verified). The vendored script remains the canonical restore path.

Template bug found while vendoring-adjacent code review: IR-K3-01 (LiDAR band indices in
`h33.py`/`hypotheses.py`/`h35_new.py` of the source repo). Those modules were *not* vendored;
karage3 surfaces read bands by raster description name.
