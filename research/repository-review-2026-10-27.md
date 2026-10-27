# Repository review — 2026-10-27

## Decision

**NEGATIVE / BLOCKED. No new TIFF is available to download or submit.** No modeling experiment was performed; no holdout score or leaderboard estimate was produced; no slot was selected or used; and no portal upload was made. This is an evidence-based stop, not a candidate submission.

The machine-readable record is [`data/current-run-card.json`](../data/current-run-card.json). The user-facing decision and nine-site table are in [`executive-summary.html`](../executive-summary.html).

## Pass 1 — inspect the checkout and authoritative requirements

### Repository state

At the start of this review, the active branch was `arena/cde35f94-gemsdoekarage3`, the worktree was clean, and the only tracked file was a 16-byte `README.md` containing the project title. There was no `data/` directory, package/dependency file, source code, test, training raster, label raster, sample submission, cached feature stack, experiment registry, automated source-feed refresh, or generated GeoTIFF. The shared `evaluate_holdout.py` and `submission_writer.py` specified by the run protocol were not in the checkout. The initial GitHub Pages source was the `main` branch root; the site returned only the README heading.

This finding is specific to the checked-out branch/repository. It does not claim those files are absent from every related GEMSDOE project or another user's machine.

### Source and requirement check

| Requirement / claim | Source checked | Finding and safe interpretation |
|---|---|---|
| Competition target | [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | The task is to predict geological faults indicative of geothermal resources. The public fault catalogue is incomplete; expert-identified new faults are used for test evaluation. |
| Score | Same official problem description | Distance-weighted Tversky index; `alpha=0.2`, `beta=0.8`; triangular distance kernel with 300 m support. These are metric parameters, not a score or a score projection. False negatives receive a larger coefficient than false positives; actual outcomes still depend on all metric terms and spatial placement. |
| TIFF format | Same official problem description | One band; float32; projected UTM Zone 11N / EPSG:32611; 100 m resolution; same bounds as training; null/NaN outside the valid bounds; predictions in `[0,1]`. Exact shape, transform, and footprint must be compared to the official sample raster, which is absent here. |
| Competition file access | [Official data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | The request redirected to DrivenData's login page in this environment. No competition files were obtained. No password, cookie, or credential was requested or stored. |
| Official starting implementation | [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) | A separate baseline repository exists. It is not present in this checkout and is not the shared, cached template/toolchain named in the protocol. No private evaluator or writer was substituted for it. |
| GeoDAWN source | [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | USGS describes airborne magnetic/radiometric survey products for geologic/geophysical mapping; the USGS release is a valid source reference, not proof that a particular contest feature stack has been downloaded or aligned. |
| INGENIOUS auxiliary source | [DOE Geothermal Data Repository entry 1391](https://gdr.openei.org/submissions/1391) and [INGENIOUS project page](https://gbcge.org/current-projects/ingenious/) | The GDR page is publicly accessible and lists regional temperature, seismicity, geophysical, paleogeothermal, well/spring and related resources. It is not the same as the competition's private/download-tab files; a source listing does not prove footprint coverage or license fit for a particular derived layer. |
| 1 m elevation availability | [USGS 3DEP data catalog](https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e) and [3DEP product information](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services) | An official 1 m DEM product/source exists. USGS describes 3DEP products as free of charge and without use restrictions. Coverage of every GEMS footprint tile was not tested here. |
| Current public leaderboard | [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | At the time checked on 2026-10-27, the page displayed a top public value of `0.4544`. This is an official public-page observation, not a submission-page receipt for our work, may change, and is not a prediction. The prompt's user-provided, unverified `0.4413` and later `0.3195` values are not what the public page showed at this retrieval. |

The prompt's named error, “Predicted values must be in range `[0, 1]`,” is an organizer-format requirement, but no exact TIFF that triggered it was available. It would be unjustified to diagnose a particular cause without reopening that file. A future validator must inspect every in-footprint pixel and the exact saved bytes, then compare CRS, shape, transform, bounds, NoData, and band/type to the authenticated sample submission.

### Scientific context checked

The scientific rationale is promising but does not justify a score claim. USGS's Great Basin work describes fault interactions and structural discontinuities as controls on permeability and hydrothermal circulation, with localized stress/strain around stepovers and fault terminations ([USGS publication](https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa)). A USGS-recorded blind-geothermal play-fairway project reports integration of structural setting, gravity/magnetic gradients, shallow temperature, resistivity, and geothermometry, and reports that detailed geophysical work was important for recognizing promising basin sites ([USGS project record](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and)). GBCGE describes two-meter temperature surveys as a method that has identified thermal anomalies without other surface geothermal indicators ([GBCGE method overview](https://gbcge.org/explore/)).

These sources support the physical plausibility of testing cross-domain corroboration and shallow thermal observations. They also document substantial prior art, so they do not establish that any proposal below is new across the sibling GEMSDOE sites or will outperform a baseline. The GDR's public compilation is a potential data source, not a verified contest-footprint raster.

## Pass 2 — review claims, provenance, and hidden assumptions

### Nine-site historical comparison

The executive summary transcribes the nine values and file-name stems exactly as supplied in the user prompt. Each historical value is explicitly labeled **USER-PROVIDED / UNVERIFIED**. The participant-maintained GitHub Pages were opened as research leads, but none of their downloadable TIFFs, checksums, or submission-page receipts were fetched and verified in this checkout. Site-authored holdout results use different evaluators, folds, label proxies, buffers, denominators, and registry snapshots; they cannot be pooled into one score ranking.

The current participant pages also contain changing audit states and sometimes different scope/registry claims. A complete byte-pinned cross-site raster registry is absent here. Accordingly, this review does **not** certify that any of the nine historical files are exact duplicates or unique. More importantly, no uniqueness result exists for a new candidate, because no candidate surface or final dot set exists.

### What can and cannot be inferred from the GEMSDOE32 result

The prompt's `0.2778` is **USER-PROVIDED / UNVERIFIED**, not a HOLDOUT-DTI result from this checkout and not ORGANIZER-CONFIRMED without a submission-page receipt. The GEMSDOE32 participant page describes the H33-2-B2 pattern as related to the GEMSDOE25 d=2.8 dotted pattern and as removing dots near the known fault catalogue. That is a plausible provenance/mechanism claim to investigate, not proof of the score's cause.

A scientifically plausible explanation is **better allocation of a finite prediction budget**: spacing reduces redundant nearby predictions, while a catalogue collar can shift some prediction mass away from already mapped traces and toward candidate unmapped structures. Under the official 300 m triangular DTI kernel, predictions close to a true new fault contribute more than distant ones; false negatives have a larger coefficient than false positives. Thus a sparse/dotted pattern can be better if it keeps useful proximity to more hidden traces without spending too much prediction mass on low-yield areas. Conversely, catalogue removal can reduce recall and hurt score. The hidden expert labels and a score-bound receipt are needed to separate these possibilities.

**Causal conclusion:** the value alone cannot establish whether catalogue removal, spacing, a feature stack, model fitting, fortuitous spatial overlap, or another factor drove the reported result. The exact participant-site reproduction is not in this checkout, and the claimed `0.2778` is not linked here to a receipt and raster hash. Therefore this review cannot honestly claim to have explained “why” it scored that value as a verified causal finding.

**Can a new approach beat it?** In principle, but there is no evidence in this repository to say that it will. No new score estimate is supplied. The live public leaderboard page was observed above the prompt's historical targets, so even beating the old `0.2778` claim would not imply leaderboard leadership.

### Protocol blockers and leakage / uniqueness checks

- No single assigned method paragraph or assignment source was present in the prompt/repository. The parallel-run lane rule therefore prevents us from selecting an approach.
- There are no training labels, no cached feature stack, no shared evaluator/writer, no frozen current-best under the required same evaluator, and no full, pinned registry.
- No feature-only AUC canary, spatially blocked hide-and-recover, pixel-exact visible-fault mask, or surface/final-dot novelty comparison can run without those assets.
- No predicted surface exists, so neither pre-placement rank correlation nor final-dot overlap can be measured. Returning `0`, claiming uniqueness, or generating arbitrary dots would be fabricated evidence.
- No exact GeoTIFF bytes exist to hash or validate. The validator fields in the run card are `NOT RUN`, not pass.
- Budget used: zero experiments and zero submission slots. Stopping before an untestable experiment is consistent with, and stricter than, the maximum experiment/time budget.

## Pass 3 — full requirement re-check and closeout

- **Executive summary for every requested site:** present in [`executive-summary.html`](../executive-summary.html), with the supplied historical stem/value, explicit evidence class, no score estimate for a new submission, uniqueness status, and a fail-closed download/submit decision.
- **Why the H33-2-B2 result may have been stronger:** a mechanism-level explanation is included, with uncertainty and no causal overclaim.
- **Unique TIFF:** not generated. The repo has no authenticated input data or shared generation pipeline. We do not copy a prior submission or manufacture a TIFF-shaped placeholder.
- **Automatic validation:** this checkout cannot run it without the exact sample/reference rasters, candidate, and shared validator. The future required checks are enumerated in the README and executive page.
- **Official source links:** competition description, data tab/login, leaderboard, rules PDF, reference solution, USGS GeoDAWN, INGENIOUS/GDR, and 3DEP are provided.
- **Novel hypotheses:** three conditional proposals are documented separately. They are not claimed to be globally untried, are not selected for implementation, and were not tested.
- **Run card:** one negative JSON card records the null / not-run evidence and the blockers. No score has been projected.
- **Submission action:** no submission, no selector choice, no account access, and no slot use occurred.

## What remains before the first valid experiment

1. Restore and pin the shared template, cached feature stack plus metadata, `evaluate_holdout.py`, `submission_writer.py`, and tests. Do not reimplement these privately.
2. Provide the authorized DrivenData competition files (`training_features.tif`, labels, sample submission, DEM-link metadata) to a local `data/` path. Do not publish private competition data in Git.
3. Restore the complete machine-readable registry (all relevant source rasters, checksums, masks, and provenance) and freeze the current best under the same evaluator/split.
4. Record the explicitly assigned lane paragraph and assignment source. If it is still absent, stop rather than choose a method.
5. Pre-register one lane-conforming hypothesis, its named non-fault mimics, preprocessing, leakage tests, holdout split and stop thresholds before fitting.
6. Run the shared evaluator on at most three experiments or two hours, compare with the frozen incumbent, and report HOLDOUT-DTI with evaluator version, withheld positives, and 95% CI. Run the feature-only leakage canary for each feature.
7. Only if the holdout gate passes, evaluate surface and final-dot novelty against the complete registry, write via the shared submission writer, reopen the exact TIFF, validate format/range/footprint, and record the SHA-256.
8. Keep `download_authorized` and `submit_authorized` false until every automated release gate passes. A selector must separately decide whether to spend a real slot; only a submission-page receipt can produce an ORGANIZER-CONFIRMED score.
9. Implement a provenance-aware scheduled feed only after the source schema is pinned: record fetch time, URL, HTTP outcome, and content hash; keep official leaderboard observations distinct from receipts and participant-reported claims. The current site is a static snapshot and does not remove the need to refresh sources.

## Sources for manual review

- [Competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official problem description: task, metric, datasets, submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (login required in this environment)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project page](https://gbcge.org/current-projects/ingenious/) · [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP 1 m DEM catalog](https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e)
