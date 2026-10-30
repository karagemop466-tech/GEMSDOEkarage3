# NOT CLEARED — `-nan.tif` variants (do NOT upload)

Moved here from `docs/downloads/` on 2026-10-30 (session 7). Each file has **7,111,787 float32 NaN
cells** outside the 5,167,373-cell footprint. The same dots exist in the matching `-zeros.tif`
(0 NaN, values only 0 or 1). A `-nan.tif` is the file pattern behind the portal error
"Predicted values must be in range [0, 1]" reported by the user. The official page allows
"null or nan" outside the bounds (docs page 967), but the portal rejected this file pattern, so the
project refuses to publish it. Upload the `-zeros.tif` version only.

| File | Matching zeros file (still in docs/downloads) | Literal-uniqueness status |
|---|---|---|
| `gemsdoe32-hk3-smgc-maxenv-axial28-37654-20261027T213000Z-c886c782-nan.tif` | `…-c886c782-zeros.tif` | **99.69%** within 3 px of lattice witness (limit 70%) — FAIL |
| `gemsdoe32-karage3-consensus-hgrad-k37654-20261029T183206Z-4786d9bd-nan.tif` | `…-4786d9bd-zeros.tif` | **99.89%** — FAIL |
| `karage3-k3-fuse-greedy-b2-20261027T212847Z-80117cd2-nan.tif` | `…-80117cd2-zeros.tif` | **99.92%** — FAIL |

Historical references to these filenames in `evidence/` and `registry/` are intentionally unchanged
(provenance). Recover bytes from git history on branch `arena/3a5348a7-gemsdoekarage3` before this move if needed.
