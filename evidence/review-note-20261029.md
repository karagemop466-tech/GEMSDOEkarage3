# Review note, 2026-10-29 (branch arena/ae38d14e-gemsdoekarage3)

**Decision: OK TO DOWNLOAD: NO. OK TO SUBMIT: NO.** No file is published. No weekly slot used. No score estimated.

## Pass 1: format and validity (project scripts only)
- `scripts/check_submission.py` on `karage3-lgap-scarpstep-19k-20261029-4fc40bd1.tif` (sha256 4fc40bd1…): core checks pass. Single float32 band, EPSG:32611, 3730 × 3292, geotransform equal to template, values in [0,1] inside the footprint, NaN outside (as in template).
- Failed check: outside-template null check was not satisfied by the earlier unique-offcat file. Current candidate: see its card (`docs/downloads/…-card.json`).
- Earlier root-page errors fixed: the live root `index.html` said "READY TO DOWNLOAD" and "0% overlap" for `karage3-unique-offcat`. Corrected to DO NOT SUBMIT (measured overlap vs r13 99.89%, 4,517 dots inside footprint, not 12,000). Broken leaderboard link fixed. Unverified 0.4544 snapshot replaced with the user-supplied 0.4413, labeled as unverified.

## Pass 2: uniqueness
- Nine focus files + r13 lattice: max overlap 65.00% (r13 only); focus-9 10.9–13.1%; footprint Spearman about −0.003 to −0.004 (0 failures).
- Full registry (`scripts/measure_registry_overlap.py`): 1,977 compared rasters, **106 literal fails** (overlap >70%): 59 dense (≥1M positive cells), 28 mid-density, 19 sparse (worst 94.7%). 13 not comparable, 2 missing in tarball, 7 with no dots, 1 read error. Fail-closed. The registry manifest is not a certified complete literal registry (2,444 rasters, 1,997 unique SHA-256, 107 repos; literal_registry_complete=false), so this result is a floor, not a certificate.

## Pass 3: holdout, leakage, promotion, consistency
- HOLDOUT-DTI hide-and-recover: 0.0 (22,232 withheld, by construction).
- HOLDOUT-DTI SGMC-off-catalogue (prevalence-calibrated, 62,703 withheld): 0.0316 (CI 0.0209–0.0432) vs best focus-9 0.0644 (GEMSDOE36). Negative. SGMC is the same evaluator family the candidate was not built from, but the design was previously ranked against it; treat as contaminated for claims.
- Leakage canary: max single-band AUC 0.599 (step_max 0.568), threshold 0.90 not exceeded.
- Tests: `pytest` → 11 failed, 197 passed, 1 skipped. The 11 failures also occur on a clean export of the base commit (71c5da9): test_preflight_site (3), test_release_review (2), test_review_20261028 (3), test_session_safety (1), test_site (2). New `tests/test_submit_now.py`: 12/12 pass.
- `scripts/verify_numbers.py`: 21/22. The failing check "all retained TIFFs inventoried exactly once" is pre-existing on base.
- `scripts/build_site.py --check` fails on base (saved-byte audit does not include two `docs/downloads` TIFFs from an earlier session). The root generator is therefore not used; `index.html` was corrected by hand. This means CI's `build_site --check` remains red.

## Irregularities (flagged, not fixed)
1. The root generator is stale (see above). Root `index.html` is hand-maintained and must be kept in sync with the card.
2. `-nan.tif` variant of the unique-offcat file declares NaN nodata but has zero NaN cells (zeros outside).
3. "22,232 withheld positives" is fixed across all nine sites in `scripts/focus9_holdout_baseline.py`.
4. The "0.2778 led because of pruning" narrative on the root page is user-reported and unverified; it is not a receipt.
5. Historical owner-mirror scores are user-reported only. No organizer receipt exists.
6. DrivenData leaderboard was not scraped (no automated access under DrivenData terms); the 0.4413 high is user-supplied.
7. The earlier "Predicted values must be in range [0, 1]" rejection cause is still unknown. The current candidate has values in [0,1] inside the footprint and NaN outside, matching the template; this has not been confirmed by the portal.

## Remaining work (owner decisions first)
- Owner decision: how to define "dots" for dense continuous surfaces (e.g. top-K by value). Without it, 59 dense registry rasters make the literal full-inventory rule unsatisfiable.
- Owner decision: whether to accept a registry-aware constrained selection for the 19 sparse overlaps.
- Re-run the full registry audit before any download is permitted; the manifest must be checked against the official registry.
- Fix stale saved-byte audit so `build_site.py --check` and `verify_numbers` can pass.
- Weekly slot: none used; promotion remains negative.

## Official sources
- Problem and metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Rules (up to three weekly submissions and one final selection): https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- CRS: https://epsg.io/32611
