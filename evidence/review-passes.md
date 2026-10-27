# Three-Pass Verification Log (`arena/d834dcd0-gemsdoekarage3`)

## Pass 1 — Execute the Task (Implementation & End-to-End Execution)
1. **Data & Registry Restoration (`SHA-256` Verified)**:
   - Restored and verified all `30` competition & external public data files in `.cache/gems_data/` (`scripts/restore_data.py`), prepared all `19` nearest-neighbor sentinel-inpainted bands (`scripts/prepare_data.py`), and restored `454` pinned focus + extra scored registry rasters (`scripts/restore_pinned_registry.py`) plus `100` sibling-org rasters (`WBGGEMSDOE1..3`, `KANLERGEMSDOE1..3`) = `554` manifest entries (`488` unique SHA-256 rasters).
2. **Pre-Registration of 5 Novel Geological Hypotheses (`docs/research/smgc-preregistration-20261027.md`)**:
   - Formulated and ranked `H-K3-1` (`SMGC-CT`), `H-K3-2` (`HUC-Dip`), `H-K3-3` (`RCD-KThU`), `H-K3-4` (`CFEO-GM`), and `H-K3-5` (`APC-Lahontan`) with exact layers, physical signatures, missing-fault rationale, and novelty vs existing implementations.
3. **Implementation of `src/gems32/smgc.py` & `scripts/run_hk3_smgc.py`**:
   - Built `smgc_extra_4ch.npy` (`mag_edge_migration_dip`, `rad_comp_discontinuity_kth_uth`, `cross_field_grav_rtp_offset`, `asymm_piedmont_curv_scarp`) completing the `87`-channel strictly label-free multi-physics stack.
   - Executed the 87-channel single-feature holdout leakage canary (`87 / 87` channels $\le 0.90$, max oriented AUC = `0.586868` on `curv_s2`).
   - Executed all `3` pre-registered experiments (`EXP1_K3_UNSUP_SMGC_CREST`, `EXP2_K3_MULTIPLICATIVE_DUAL87`, `EXP3_K3_SMGC_MAX_ENVELOPE_AXIAL28`) and generated `docs/downloads/gemsdoe32-hk3-smgc-maxenv-axial28-37654-20261027T213000Z-c886c782-zeros.tif` (`SHA256 = f21a0e831e6307d1d8230119c4d2f9812646fa8b092b2326b180a54feccea33f`).

## Pass 2 — Review and Refine (Bugs, Edge Cases & Fixes)
1. **Fixed Redundant Subprocess Call in `scripts/run_hk3_smgc.py`**:
   - `scripts/evaluate_holdout.py` already invokes `vendor/gems57/evaluate_holdout.py`; removed a duplicate direct CLI call with mismatched flags.
2. **Separated Ultra-Dense (`>100k` dots) Probes from Genuine Discrete (`<=100k` dots) Final-Dot Overlap Gate**:
   - In `scan_full_registry`, `top_surf_candidates` included `GEMSDOE22`'s `335,879`-dot ultra-dense probe in the `stage="final"` 3-px dot overlap check. Updated `verify_final_shas` to check `top_ov_candidates` across all `463` genuine discrete (`<=100k` dots) submissions (`max 3-px overlap = 0.634727 <= 0.70`, and `0.608780 <= 0.70` across all `397` focus-site rasters), while checking `stage="surface"` Spearman across all `488` non-lattice rasters (`max |Spearman| = 0.201012 <= 0.90`).
3. **Sanitized `NaN` JSON Token in `evidence/nine_site_refreshed_audit_20261027.json`**:
   - `GEMSDOE30`'s latest raster had `ds.nodata = float('nan')`; converted `float('nan')` to `"NaN"` so strict RFC 8259 JSON parsers parse `evidence/nine_site_refreshed_audit_20261027.json` cleanly.
4. **Synchronized `docs/assets/fig_hk3_smgc.png` Panel D Title & `pytest.ini`**:
   - Updated Panel D title in `scripts/run_hk3_smgc.py` to dynamically reflect `51.2% >1.5km, 2.1% Flat Playa` and added `pytest.ini` (`pythonpath = . src vendor`) so `.venv/bin/pytest -v` passes all `16/16` unit and integration tests cleanly.

## Pass 3 — Final Verification (Line-by-Line Audit Against Original Request)
1. **Saved-Byte GeoTIFF Validation (`check_submission.py --strict-finite` & `submission.audit_geotiff`)**:
   - `docs/downloads/gemsdoe32-hk3-smgc-maxenv-axial28-37654-20261027T213000Z-c886c782-zeros.tif` verified: `1` band, `float32`, `EPSG:32611`, `(3730, 3292)`, `nodata = None`, `12,279,160 / 12,279,160` finite pixels in `[0.0, 1.0]`, `37,654` emitted dots, `0` on-catalogue dots.
2. **Release Gate & Promotion Gate (`scripts/promotion_gate.py docs/run-card.json`)**:
   - Returns `verdict = "promote"`, `reasons = []`.
3. **Documentation & Standing Prompt Reference**:
   - Verified `README.md` (with verbatim standing prompt), `docs/research.md`, `docs/index.html`, `docs/executive-summary.html`, `docs/run-card.json`, and `docs/sites.json`.
