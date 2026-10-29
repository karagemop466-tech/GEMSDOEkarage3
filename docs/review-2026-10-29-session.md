# Repository review and next-step decision — 29 October 2026 UTC

## Executive decision

**NEGATIVE — no new TIFF was generated, no weekly slot was spent, and nothing in the repository is cleared to download and submit.** The requested parallel-run protocol has no unambiguous assigned method lane in this prompt. The current checkout also lacks organizer-authenticated competition rasters, the cached feature stack, a complete current registry, and a protocol-conforming shared holdout. Proceeding to model selection or generating an uploadable-looking file would violate the fail-closed gates rather than maximize the chance of a valid result.

- [Current run card (JSON)](data/review-run-20261029.json)
- [Current readiness snapshot](readiness.json)
- [Nine-site executive summary and historical file table](../index.html#scorecard)
- [Submission instructions](../executive-summary.html)
- [Previous four-hypothesis slate and evidence review](review-2026-10-28-session.md#ranked-research-slate--planning-only)
- [Official problem, metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)

The nine historical rows remain useful for comparison, but every score is **USER-REPORTED / UNVERIFIED** in this repository, every archived file is research-only, and a new live-score estimate is **not estimable** from the available holdout evidence. The exact historical artifacts and pairwise comparisons are already in the [nine-site table](../index.html#scorecard); this review did not re-download them or change their status.

## What the reported GEMSDOE32 result can and cannot mean

The official competition description says the prediction target is geological faults that are indicative of geothermal resources; it does not label every predicted fault as a geothermal vent. The official metric is a distance-weighted Tversky index with a 300 m triangular kernel, `alpha=0.2` for false-positive mass and `beta=0.8` for false-negative mass; the submission format requires one float32 band with scores in `[0,1]`, the training grid/CRS, and null or NaN outside its bounds ([official problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).

A plausible, **not causally proven**, explanation for the user-reported GEMSDOE32 `0.2778` is selective thinning/pruning. Under the published max-over-neighborhood scoring equations, several predictions clustered around the same target can add little marginal true-positive credit after a nearby prediction already supplies a high kernel weight, while outlying predicted mass can still contribute false-positive penalty. Removing redundant or weakly supported predictions could therefore increase DTI. In the repo's historical set audit, the GEMSDOE32 dots are reported as a pruned subset of GEMSDOE31, with 2,545 fewer dots in a near-catalogue collar. That is compatible with the metric mechanism; it does **not** prove which deleted dots were false positives or that the score change was caused by this pruning. Hidden test labels and artifact-linked DrivenData receipts are absent.

The site scores supplied in the prompt do not define a calibrated conversion from holdout DTI to leaderboard score. Therefore no projected score is entered as a score, and this review cannot substantiate that any new file would beat `0.2778`, `0.3195`, `0.4413`, or a later public leader.

## Current blocker check

`python scripts/check_readiness.py` refreshed [`readiness.json`](readiness.json) and reported `ready_for_experiment=false`, `ok_to_submit=false` (expected exit 2). Specifically, it measured:

1. **No data/cache in this checkout:** required core rasters are not present at their expected paths and `.cache/gems_work/feature_stack.npy` is absent. The checked-in prepared manifest is a record of an earlier preparation; it is not proof those bytes remain available now.
2. **No complete current registry:** 0 of 416 pinned raster paths are present locally; continuous surfaces and registry freshness are not verified by that local measurement.
3. **No assigned lane:** no lane is inferred from the earlier candidate slate.
4. **Shared-template defects remain open:** upstream issues cover holdout truth/visible buffering (#60), pooled false-positive handling (#41), leakage diagnostics (#61), surface-stage overlap enforcement (#42), and masked in-footprint pixels (#66). The pinned shared code is provenance, not proof of correctness. This checkout cannot patch the central shared template and must not substitute a private fork.
5. **No comparable incumbent rerun:** there is no current same-evaluator, same-fold baseline to beat. The user-supplied historical results are not that baseline.

A single registered calibration-lattice witness has previously triggered literal overlap failures for the archived dense submissions. That is a valid stop witness for those artifacts, not a completeness proof about every raster or a proof that every conceivable new surface is duplicate. No candidate surface or final dots exist in this review, so candidate correlation and overlap are **NOT RUN**, not zero.

## Candidate slate disposition

The preceding independent review already ranked four plausible ideas. I checked the official competition page, USGS [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [3DEP](https://www.usgs.gov/3d-elevation-program), [3DHP](https://www.usgs.gov/3d-hydrography-program/access-3dhp-data-products), and DOE GDR [submission 1391](https://gdr.openei.org/submissions/1391) pages. The pages state that GeoDAWN products have a CC0 release, 3DEP products are free without use restrictions, 3DHP products include web services and a downloadable 2025 release, and GDR 1391 is publicly accessible under CC BY 4.0 and lists 2 m temperature-probe files. Thus these are official, discoverable data sources; this review did **not** download the binary datasets, verify exact coverage/CRS against the competition footprint, or stage/check their hashes. Source availability is not experimental readiness. For all candidates below, expected improvement is qualitative only; none is a score forecast. Novelty relative to every sibling repository cannot be guaranteed from the available complete-registry evidence.

| Priority | Hypothesis / layers / signature | Why it could find an off-catalogue fault; difference from existing work | Main mimic | Data and readiness |
|---|---|---|---|---|
| 1 (qualitative; medium cost) | **Signed multi-scale potential-field offset:** competition GeoDAWN RTP/TMI, isostatic gravity and detrended elevation; measure signed, cross-strike profile change-point offsets that persist under scale continuation. | Tests the relative polarity and displacement of paired field transitions under weak relief, rather than another unsigned edge magnitude or edge coincidence. A buried discontinuity may lack a mapped surface trace. | Lithologic contacts, dikes, remanent magnetization, survey leveling/seams. | Uses supplied competition layers, but none are present locally and the shared derived stack is absent. Not runnable here. |
| 2 (qualitative; high cost) | **Replicated drainage deflection:** USGS 3DEP terrain plus USGS 3D Hydrography Program channels, with independent gravity edges as a structural check; require repeated, same-sense lateral channel offsets across separate drainages. | Replication across channels is distinct from a single scarp, curvature ridge, or drainage-density hotspot and may reveal young concealed displacement absent from the fault catalogue. | Avulsion, stream capture, lava dams, shoreline scarps, roads, lithologic boundaries. | Official portals: [3DEP](https://www.usgs.gov/3d-elevation-program) says products are free without use restrictions; [3DHP](https://www.usgs.gov/3d-hydrography-program/access-3dhp-data-products) lists services and a 2025 download. The exact tiles/coverage, study-area intersection and 3DHP license were not checked; no data were downloaded, so defer rather than call viable. |
| 3 (qualitative; medium–high cost) | **Matched shallow-temperature residual:** DOE GDR/INGENIOUS #1391 temperature observations, terrain/elevation and conductivity; cross-fit depth- and sampling-aware regional background, then test spatially coherent residuals with independent geophysics. | A residual thermal pathway may extend beyond mapped fault traces and avoids treating raw well/spring proximity as a fault predictor. | Uneven well sampling, groundwater flow, pumping, insolation, lithology. | [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391) is publicly accessible (CC BY 4.0) and lists a downloadable 2 m temperature-probe ZIP. The binary was not fetched and target-footprint coverage/CRS was not verified, so this is a discoverable source, not data validated for this run. |
| 4 (qualitative; medium–high cost) | **Acquisition-block invariant radiometric residual:** GeoDAWN K/eTh/eU plus acquisition-block/flight-line metadata and independent magnetics; require the residual signature to survive held-out acquisition blocks. | Distinguishes putative alteration structure from block-specific calibration and tests spatial generalization, rather than using a raw radiometric ratio hotspot. Similar radiometric methods exist in sibling work; fleet-wide uniqueness is unverified. | Lithology, soil moisture, vegetation, altitude correction and processing seams. | The official [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) states that grids and line data are available and CC0. Exact target products and block metadata are not staged locally; not runnable. |

**No candidate is promoted to an experiment.** The instruction to use the single assigned lane takes precedence over selecting one from a research slate. No holdout scores or feature canaries were generated.

## Leaderboard and historical-score irregularity

The request gives `0.3195` and `0.4413` as competing current highs. The repo additionally retains a dated public leaderboard observation of `0.4544` from 28 October 2026. Those are different dated claims/snapshots, not a value that can be reconciled by assumption. The live leaderboard was **not** refreshed during this review; the repo's source policy avoids automated leaderboard access. Please treat the official [live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) as the source for a contemporaneous public rank, and distinguish that from a score receipt for a particular submitted TIFF. No receipt is available here.

The official [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) is a benchmark baseline and requires competition data obtained through the challenge website. It does not validate the owner-mirror inputs or any user-reported site result.

## Three-pass review log

### Pass 1 — repo and source inspection
- Read `AGENTS.md`, README, the retained project brief, prior current-session review, current run cards, focus-site evidence, readiness logic, and official problem/metric/format/source pages.
- Confirmed the repository already has a nine-site executive summary and historical file/score/uniqueness table. It is a comparison of supplied historical artifacts, not edits to the nine sibling sites.
- Confirmed the current template and candidate TIFFs are absent from this checkout; do not mistake `data/prepared_manifest.json` for the cached stack.

### Pass 2 — regression and gate review
- Installed dependencies only in ignored local environments (`.venv/`, `node_modules/`); no source or tracked binary dependencies were added.
- `.venv/bin/python -m pytest -q`: **188 passed, 1 skipped, 78 subtests passed** (56 rasterio pending-deprecation warnings). The skipped test is the existing optional integration requiring a missing cached stack.
- `npm test`: **4 passed**; `node --test tests/test_browser_feed.js`: **2 passed**.
- `scripts/verify_numbers.py`: **22/22 consistency checks passed**. These checks establish repository consistency, not organizer score or slot eligibility.
- `scripts/build_site.py --check`: passed. `scripts/check_readiness.py`: expected **not-ready / exit 2**; see detailed blockers above.

### Pass 3 — user-request and safety recheck
- The nine-site table remains visible, lists historical filenames and reported values, marks uniqueness against peer files, and explicitly says DO NOT SUBMIT. No numerical live score estimate is claimed.
- No duplicate historical TIFF was copied, renamed, or presented as a new submission. No candidate TIFF or score was fabricated. The submission instructions and exact format requirements remain linked from the README/site.
- Updated the README/site entry points to expose this review and the live evidence state. No selector was run, and no submission slot was selected.

## Next steps, in order

1. Assign one explicit method paragraph/lane and clarify with the protocol owner whether the literal 3-pixel rule applies to the calibration lattice exactly as written; do not self-exempt it.
2. Restore authorized competition rasters and the cached feature stack, then verify hashes and metadata against the actual submission template. Owner mirrors are not organizer-authenticated.
3. Resolve or centrally verify the shared evaluator/holdout/surface/validator defects; pin and regression-test the fixed shared implementation, not a local fork.
4. Build a complete, current, hash-pinned registry; recheck both unplaced candidate surfaces and final dots against every registered raster.
5. Reproduce the incumbent on the same corrected whole-segment buffered holdout, run per-feature leakage canaries, and only then test at most three preregistered experiments within the budget. Report HOLDOUT-DTI with evaluator, withheld-positive count and 95% CI.
6. If and only if a candidate beats the matched holdout baseline and passes the complete duplicate/format gates, invoke a separate authorized selector within the then-current account cap. Preserve the submission receipt and exact TIFF hash; until then, no live score is known.

## Run card

See the machine-readable [negative review card](data/review-run-20261029.json). It records no experiment, no new raster hash, no candidate uniqueness measurement, no validator pass and no submission name.
