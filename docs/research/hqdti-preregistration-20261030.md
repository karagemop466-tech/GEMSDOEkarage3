# H-QDTI pre-registration record (2026-10-30)

**Status: WRITTEN AFTER THE RESULT.** This record was created after experiments 1–3 had already run
(`evidence/qdti-holdout-20261030.json`, `evidence/catalogue-buffer-baseline-20261030.json`). It is a
retrospective record, not a pre-run commitment. Do not describe it as pre-registered in advance.

Referenced by the header of `scripts/qdti_holdout.py`.

## 1. Method lane

One lane only: **label-trained logistic emission on the official label-free layers** (H-QDTI).
No other method is evaluated in this record. The method is fitted per withheld cell, on visible
faults only, and scored with the shared evaluator `src/gems32/holdout.py` (unmodified).

- Features: the 19 official training layers, plus a 4-px Gaussian context copy of each (38 features).
- Positives: footprint pixels within 3 px of a visible catalogue fault. Negatives: footprint pixels
  farther than 3 px from one.
- Emission: top fraction of the active domain by predicted probability, for pre-registered fractions
  0.5 %, 1 %, 2 %, 5 %, 10 % of the active area.
- Controls: a random same-area emission (same count, random placement) at every fraction.
- Leakage canary: each single feature's holdout AUC must stay at or below 0.90.

## 2. Ranked hypotheses (proposed before any new test; ranked by prior plausibility and cost)

Ranking criteria: (a) geological plausibility of the mimic, (b) whether the official layers show the
signal directly, (c) implementation cost. No expected-score figure is claimed for any hypothesis.

| Rank | Hypothesis | Mimic (non-fault explanation to rule out) | Status |
|---|---|---|---|
| 1 | H2 — Magnetic tilt-derivative contact ridges (`tc`) co-located with gravity-gradient ridges (`iso_grav_anom_hg`). Emit ridge crests. | Intrusion contacts and lithologic boundaries | **NOT TESTED** |
| 2 | H3 — Geodetic strain-rate ridges (`geod_shearrate`, `geod_dilaterate`) that coincide with detrended-elevation slope steps (`det_elev_slope`). | Landslide and erosional scarps | **NOT TESTED** |
| 3 | H4 — Basement-step ridges (`depth_to_base_surf` gradient) at contrasts in `cond_surf`. | Sedimentary-basin margins | **NOT TESTED** |
| 4 | H1 — H-QDTI logistic emission (this record's method). | Label-fitted classifier | **TESTED: NEGATIVE** (below random control) |
| 5 | H5 — Off-catalogue-only emission (>300 m from `labels.tif`), validated with SGMC off-catalogue faults. | None; it is a placement constraint, not a geology model | **NOT TESTED** (needs the SGMC evaluator, not run) |

H1 is listed as rank 4 because its result is already known. The top-ranked untested hypothesis is H2.

## 3. Results on record (HOLDOUT-DTI, shared evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives, 1,000 bootstraps)

Leakage canary (`evidence/qdti-holdout-20261030.json`): max single-feature mean AUC **0.559**
(`det_elev_slope`), below the 0.90 threshold. **PASS.**

| Area fraction | H-QDTI [95% CI] | Random same-area control [95% CI] |
|---|---|---|
| 0.5 % | 0.0117 [0.0058, 0.0188] | 0.0358 [0.0322, 0.0391] |
| 1 % | 0.0154 [0.0095, 0.0222] | 0.0514 [0.0467, 0.0555] |
| 2 % | 0.0184 [0.0129, 0.0248] | 0.0644 [0.0573, 0.0711] |
| 5 % | 0.0229 [0.0177, 0.0293] | 0.0638 [0.0562, 0.0711] |
| 10 % | 0.0233 [0.0185, 0.0287] | 0.0518 [0.0454, 0.0582] |

At every fraction, the H-QDTI interval lies entirely below the random-control interval (no overlap). At 10 %, H-QDTI [0.0185, 0.0287] vs control [0.0454, 0.0582].

**Verdict: H1 (H-QDTI) does not beat the random same-area control at any fraction. Not promotable.**
It also falls below the best local nine-site holdout value (0.0967, GEMSDOE25/30 file), so it does not
beat the holdout best either.

Caveats recorded for the verdict:
- One lbfgs ConvergenceWarning (`draw21_fold2`, 300 iterations). Its effect is not isolated.
- Confidence intervals for the H-QDTI rows are in the JSON; this record does not restate them from memory.

## 4. Consequence

- No new experiment was run for H2–H5. The 3-experiment budget is spent (experiments 1–3 above).
- **H2 is not validated on the spatially-blocked holdout. No submission slot is used.** Validating H2
  needs a fourth experiment, which requires an explicit decision to change the budget.
- The final H-QDTI raster (`scripts/build_qdti_candidate.py`) is a research artifact, not a candidate.
  It is quarantined as NOT CLEARED, because it failed the random control.

## 5. Gates applied

| Gate | Threshold | Outcome |
|---|---|---|
| Leakage canary | single-feature AUC ≤ 0.90 | PASS (max 0.559) |
| Holdout vs random control | must beat the random same-area control | **FAIL** at all fractions |
| Holdout vs holdout best | must beat 0.0967 | **FAIL** (0.0233) |
| Literal uniqueness | within-3 px ≤ 70 % and \|rho\| ≤ 0.90 vs every registry raster | **DUPLICATE-STOP** (within-3 px 1.000 vs a ~98.8 %-positive registry raster; the rho gate passes, max \|rho\| 0.152). The within-3 px rule is degenerate against that raster; a rule decision is needed (`evidence/literal-uniqueness-20261030.json`, filtered inventory, 1,979 rasters compared). |

All numbers in this record are HOLDOUT-DTI (local proxy, not organizer scores). None is ORGANIZER-CONFIRMED.
