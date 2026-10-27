# GEMSDOEkarage3 — evidence-led GEMS fault research

> **Current decision (2026-10-27): BLOCKED. No new GeoTIFF was generated, there is no file approved to download or submit, no holdout was run, and no weekly submission slot was used.**
>
> **Start every project session by reading this README in full.** It is the canonical, de-duplicated version of the project brief and the fail-closed rules. Do not infer missing data, results, methods, or permissions from earlier sessions or sibling GEMSDOE sites.

The public GitHub Pages site is served from the repository root: [Executive overview](index.html) · [Executive submission summary](executive-summary.html) · [Repository review](research/repository-review-2026-10-27.md) · [Hypothesis shortlist](research/hypotheses-2026-10-27.md) · [Current run card](data/current-run-card.json).

## Project north star

Develop a scientifically defensible, reproducible system for discovering faults that may be missing from the public USGS / INGENIOUS catalogue and that are relevant to geothermal exploration. The intended product is one valid, unique, single-band GeoTIFF with predictions in `[0, 1]`, plus a transparent evidence packet. **A downloadable file is not a submission recommendation.** A file is not promoted unless the scientific, uniqueness, and format gates pass; weekly-slot selection is a separate decision.

The user's goals are to compare GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, and 36; understand the user-reported, unverified GEMSDOE32 `0.2778` claim; maintain an auditable source and experiment record; make the submission instructions obvious; and automate validation rather than rely on a human inspecting rasters. Historical scores supplied by a user or reproduced on participant-maintained pages are not treated as official receipts.

### Core values

- **Maximize P(Win).** In every decision, weigh tradeoffs and risk; prefer an experiment that improves the probability of a scientifically supported, valid result over a cosmetic or speculative submission.
- **Own the Outcome.** Track failures as carefully as successes. Correct defects and withdraw unsafe recommendations instead of hiding them.

## Session-start and experiment protocol

1. **Read this README and the current run card first.** Check the active branch, source freshness, current data/tool availability, and the complete registry before modeling.
2. **Stay in the explicitly assigned method lane.** If no single method paragraph and assignment source are present, do not select a method or run an experiment. Do not infer a lane from a neighboring site.
3. **Reuse the shared template, cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`.** Do not make a private replacement. Fix a shared tool in its shared template and document the change. If these assets or their provenance are missing, stop.
4. **Use hide-and-recover validation.** Hold out whole fault segments with a buffer; derive catalogue-based features only from visible faults; mask visible faults pixel-exactly; then score the pooled distance-weighted Tversky index (DTI) with `alpha=0.2`, `beta=0.8`, and a 300 m triangular kernel. Keep evaluator version, withheld-positive count, split, and 95% interval with every reported HOLDOUT-DTI.
5. **Run a leakage canary for every feature alone.** An AUC above `0.90` is a stop until leakage is ruled out.
6. **Check novelty twice:** compare the prediction surface before placement and final dots after placement against the complete registry. Stop and record a duplicate if absolute rank-correlation exceeds `0.90` or more than `70%` of dots fall within 3 pixels of any registered raster. Do not tune to evade the rule.
7. **Validate the exact saved TIFF bytes automatically:** one band, float32, `EPSG:32611`, reference shape/geotransform/bounds and 100 m resolution; no NaN inside the footprint; values in `[0,1]`; null/NaN outside the footprint. A local format pass is not proof of organizer acceptance.
8. **Use no more than three experiments or two hours, whichever comes first.** Do not spend or select a weekly slot based only on a projection. Slot promotion is a separate selector decision.
9. **End every experiment/review with a JSON run card.** Distinguish `HOLDOUT-DTI` from `ORGANIZER-CONFIRMED` (a value copied from a submission-page receipt). Never present a projected leaderboard score as a score. If a source value is unverified, label it as such rather than upgrading it to either evidence class.
10. **No human raster inspection is a gate.** Automated checks must decide validity and eligibility. A human/authorized account may still be needed to upload a candidate through DrivenData; this checkout does not have competition credentials and must never claim to have uploaded or received a score.

## Current checkout facts and stop conditions

At the start of this review, the active checkout contained only this README. There was no `data/` directory, feature cache, model, tests, complete comparison registry, shared holdout evaluator, or shared submission writer. The prescribed `evaluate_holdout.py` and `submission_writer.py` are absent. The assigned method paragraph is also absent from the request as received.

The official DrivenData data tab redirects to login in this environment. No credential, account session, or competition file was available. A public GDR entry is useful for auxiliary research, but it is not a verified substitute for the competition's `training_features.tif`, labels, sample submission, or DEM-link list. The official USGS 3DEP catalog and GDR sources are linked in the review; their availability does not prove that a particular tile covers the competition footprint.

**Consequences:** no responsible TIF can be generated or validated here. No score estimate for a new file is defensible. No historical TIFF should be renamed, copied, or resubmitted. Current status is negative, not an invitation to bypass the gates.

## Submission-format and score facts

The official problem description specifies a one-layer float32 GeoTIFF, the training raster's CRS and 100 m resolution, identical bounds, null/NaN outside the study footprint, and prediction values in `[0,1]`. It defines DTI with `alpha=0.2`, `beta=0.8` and a triangular distance kernel with 300 m support. These are competition-format/metric parameters, **not model scores**.

The reported “Predicted values must be in range `[0, 1]`” error cannot be diagnosed for a particular old file without inspecting its exact bytes. A future candidate must be checked across every pixel before it is linked for download. Do not assume that changing a filename or choosing a `-zeros` / `-nan` twin fixes a range or footprint defect.

## Evidence labels

- **HOLDOUT-DTI** — internal hide-and-recover result with evaluator version, withheld-positive count, and 95% interval. It is not a leaderboard forecast.
- **ORGANIZER-CONFIRMED** — a score copied from a competition submission-page receipt tied to that submission. No such receipt is present in this checkout.
- User-supplied historical numbers and participant-site claims remain **USER-PROVIDED / UNVERIFIED** unless supported by a receipt. A public leaderboard view is a dated public-page observation, not a submission receipt.

## Verified starting sources

- [Official DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) · [problem description, metric, and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [data tab (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) · [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — a separate reference repository; it is not the missing shared template or a substitute for the team's required evaluator/writer.
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [USGS DOI 10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)
- [USGS study of structural discontinuities and hydrothermal systems](https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa) · [USGS blind-geothermal integrated play-fairway study](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and)
- [GBCGE overview of two-meter temperature surveys](https://gbcge.org/explore/) · [INGENIOUS project](https://gbcge.org/current-projects/ingenious/) · [public DOE Geothermal Data Repository regional compilation (GDR submission 1391)](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP 1 m DEM product catalog](https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e) · [USGS availability and product information](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services)
- Participant-maintained comparison pages (use as leads, not organizer evidence): [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/), [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/), [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/), [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/), [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/), [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/), [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html), [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/), [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/).

## Before a future session can run a test

Restore the exact shared template and its cached feature stack, provide the authorized competition files, a frozen current-best result under the same evaluator, the explicit method-lane assignment, and a complete machine-readable registry with source hashes. Then pre-register one lane-conforming hypothesis, run its feature-only canaries and buffered whole-segment holdout, and stop at the stated budget. See the [repository review](research/repository-review-2026-10-27.md) and [hypothesis shortlist](research/hypotheses-2026-10-27.md) for today's negative review.
