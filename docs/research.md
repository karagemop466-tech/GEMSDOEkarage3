# Research preregistration — 2026-10-27

## Scope and limits
No model experiment has been run. The initial project began as an evidence desk; this follow-up recovered core data mirrors and pinned canonical source, then ran historical saved-byte forensics. No method lane was supplied. Three experiments or two hours is the hard experiment budget; this audit used zero experiments and zero submission slots. Do not infer novelty across the parallel projects from novelty in this empty checkout.

The following are **untested geological hypotheses**, ranked qualitatively by plausible benefit/cost, not numerical DTI projections. All differ from the geological methods implemented in this checkout (none); the historical audit is not a new detector. Cross-project novelty and cached-band availability must be checked before implementation. The 19-band owner-mirrored feature raster is now restored and its metadata inspected: TMI is band 14, RTP band 2, isostatic gravity anomaly band 13, detrended elevation band 12, and its slope band 19. These descriptions come from the mirrored file, not independent official-host authentication. The radiometric hypothesis needs additional USGS GeoDAWN K/U/Th grids (DOI 10.5066/P93LGLVQ); an upstream owner-mirror manifest is obtainable on GitHub, but direct official-host availability and provenance were not verified, so it is not presently viable. None is eligible for promotion.

| Priority | Hypothesis / specific layers | Transform and missing-fault rationale | Non-fault mimic | Expected benefit / cost |
|---|---|---|---|---|
| 1 | Magnetic-edge migration: TMI and RTP | Compare normal displacement of gradient maxima under multiple upward-continuation heights, rejecting broad contacts. A consistent displaced edge may indicate a buried dipping discontinuity without a mapped surface trace. Unlike catalogue-flank pruning, this predicts from potential fields independently of catalogue distance. | Dipping lithologic contact or remanence | Medium / medium |
| 2 | Radiometric compositional discontinuity: potassium, equivalent uranium, equivalent thorium | Detect oriented change points in log K/Th and U/Th, require magnetic-edge corroboration and reject total-count-only changes. Alteration along buried permeability could remain unmapped. Unlike generic radiometric fusion, test compositional residuals rather than raw amplitudes. | Sediment provenance, soil moisture and survey seams | Low–medium / low |
| 3 | Cross-field edge offset: gravity and RTP | Test persistent parallel but spatially offset signed gradients, rather than coincident edge strength. A concealed basin-bounding fault may displace density and magnetic boundaries differently. | Unfaulted intrusive contact | Medium / medium–high |
| 4 | Asymmetric piedmont curvature: elevation plus magnetic edge | Compare signed profile curvature on opposing sides of long linear edges, veto drainage-aligned concavities using DEM-derived flow direction. A buried scarp could be muted by sediment cover. Unlike generic ridge detection, demand cross-edge asymmetry and drainage rejection. | Lake shorelines and terrace risers | Low / medium |

The top candidate is a preregistration only: verify lane assignment and feature cache, test each feature alone (AUC >0.90 is a leakage stop), compare surfaces against the complete registry before dot placement, then run whole-segment buffered hide-and-recover with all catalogue features recomputed from visible faults. Use the shared template evaluator and writer at a pinned revision, never a private substitute. Compare against the current best using identical folds and paired spatial bootstrap CI; then test final dots against every registry raster. Do not exempt calibration lattices without an explicit protocol change.

## Why the cited GEMSDOE32 artifact might perform well
The [historical upstream audit](https://github.com/karagemop466-tech/GEMSDOEkarage3/blob/main/evidence/upstream/h33-historical-audit.json) describes deleting base dots within two pixels of the catalogue, leaving 37,654 positive pixels. On its stated 100 m grid, that is catalogue-flank pruning. Sparse separated predictions can cover more distinct neighborhoods with fewer redundant predictions; this is a metric-placement hypothesis, not proof of physical discovery. A causal attribution needs a controlled ablation under the same evaluator. Its historical report mixes surrogate/drift-adjusted quantities and a projected leaderboard value; those are not accepted as scores here.

The pinned GEMSDOE32 current-status snapshot reports no upload authorization. It also reports, without a rerun here, that a later holdout-improving candidate fails an independent SGMC criterion and literal overlap with a calibration lattice. These upstream claims have not been rerun in this checkout. A different TIFF hash alone cannot establish geological uniqueness; changing metadata, padding, compression, or adding random dots is not an acceptable new method.

## Evidence and irregularities
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution): fetched README saved under evidence/upstream. It explicitly supports CPU-only training; the prompt's GPU-required claim is too strong.
- [Official competition description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/): not fetched here because this environment only permits GitHub and package hosts. No current leaderboard or weekly cap is verified.
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [INGENIOUS](https://gbcge.org/current-projects/ingenious/), [NLR guidelines PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf): supplied source leads, not verified literature evidence in this run. No physical mechanism above is presented as established by these unread pages.
- Conflicting leaderboard claims in the request (0.3195 and 0.4413) remain unresolved; neither is treated as current fact.
- No organizer submission-page receipt linking the cited TIFF hash and 0.2778 was found in the inspected GEMSDOE32 status file. All nine requested score claims remain OWNER-REPORT, not ORGANIZER-CONFIRMED or HOLDOUT-DTI.
- GEMSDOE28's best owner-reported item in the supplied list is the rung30 artifact, not the earlier solo item. Equal reported values across sites do not prove identical rasters.
- Cannot edit the nine external sites from this checkout. This site provides a centralized executive summary for each, with pinned upstream evidence.

## Next session
Obtain the assigned method lane; restore the canonical cached stack with provenance/checksums (canonical source and four core data mirrors have now been recovered); restore the full fresh registry including continuous surfaces; audit fold-local leakage and evaluator semantics; run at most three preregistered experiments; publish a unique TIFF only after saved-byte format checks and performance/novelty gates. Slot selection remains separate. No training, new-candidate TIFF, holdout measurement, or upload has been fabricated here. Core inputs and historical TIFFs were restored for learning with checksum receipts.


## Follow-up: measured historical audit, not a geological experiment

See [historical-review.html](historical-review.html), [saved-byte evidence](historical-audit.json), [core data/grid receipt](core-data-receipt.json), and [readiness](readiness.json).

We verified actual bytes and pixels, not just README assertions. The 40,199-dot GEMSDOE28 solo base pruned within two catalogue pixels equals the 37,654-dot GEMSDOE32 artifact exactly: 2,545 deletions and no additions. GEMSDOE25/30 are positive-pixel duplicates; GEMSDOE31/earlier GEMSDOE28 solo are duplicates. All nine cited leaders exceed the literal overlap threshold against another audited pattern, and all pass the unchanged canonical saved-byte validator against the mirrored template. These are RASTER-AUDIT measurements, not scores or causal scoring attribution.

No numerical DTI benefit is assigned to the four hypotheses. Their ranking is qualitative and conditional, with magnetic-edge migration first because its required TMI/RTP bands are locally available and its mechanism does not require catalogue-distance features. Its overlap, canaries, and fold-local behavior are unknown. No distinct lane was invented merely to bypass the protocol.

The pinned official reference notebook source verifies alpha=0.2/beta=0.8 for its **training loss**, not this project's full DTI evaluator. Exact excerpts and the notebook digest are preserved in `evidence/official-reference-metric-extract.json` in the repository. This source does not establish current organizer rules, weekly cap or leaderboard. The organizer's evaluation target is fault detection; fault candidates are not confirmed geothermal vents.

### Inspection irregularities / actionable constraints
- Path-based canonical evaluator and writer both binarize positive inputs; do not use these APIs as if they preserve continuous probabilities. No probability model was run and no private fork was made.
- Raw training rasters contain real-valued features and a nodata sentinel, so they are never submission files. The prior rejected file was not available; its actual range-error cause remains unknown.
- A partial historical registry can prove a duplicate failure but never a uniqueness pass. Neither the pinned 416-raster manifest nor the inspected ten artifacts establishes fresh surface completeness.
- Restoring the core data removes a real preparation blocker, but does not restore the canonical feature cache or establish a scientifically valid baseline.


## Reconciled parallel audit

A parallel session merged an earlier [nine-file local audit](historical-raster-audit.json) during this session. It independently found all 72 directed historical winner comparisons exceed the 70% overlap cutoff (minimum 86.72%). Its selected GEMSDOE30/33 variants differ from the all-finite variants inspected in the present ten-artifact audit. That earlier audit did not have the template or dependency modules; its availability statements describe that earlier run, not current preparation status. Its source snapshots, scripts and regression tests are preserved. The current source of truth for saved-byte format checks is [historical-audit.json](historical-audit.json), explicitly against an owner-mirrored template, not organizer authentication.
