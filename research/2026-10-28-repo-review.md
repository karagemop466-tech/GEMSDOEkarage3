# Repository review — 2026-10-28

## Executive decision

**Current verdict: NEGATIVE / DO NOT SUBMIT.** The current session's [`evidence/run_card.json`](../evidence/run_card.json) records zero experiments, no new candidate raster/hash, no organizer receipt, and no weekly slot selection. A prior H-K3-1 raster is present in `docs/downloads/`, but it is an archived research artifact, not an approved release. Its bytes can pass local format checks; that does not establish uniqueness under the literal registry rule, scientific validation for this run, portal acceptance, or a leaderboard score.

The main blocker is protocol integrity, not a shortage of speculative model ideas: the prompt omits its assigned method paragraph, the shared cached feature stack is absent, the pinned registry is not locally complete/current, and the same-evaluator baseline has not been rerun in this checkout. The current `scripts/check_readiness.py` confirms all of these conditions and exits nonzero. No model experiment or submission slot was used.

### What the archived 0.2778 result may mean—and what it does not show

On the pinned public GitHub mirror rasters, geometry audit identifies the GEMSDOE32 37,654-positive mask as GEMSDOE31's 40,199-positive mask after removing 2,545 predictions within two pixels of the mirrored known-fault catalogue. That is a reproducible **raster geometry** observation. The quoted `0.2778` is USER/OWNER-REPORTED in the supplied material; no submission-page receipt tying that score to that exact raster hash is present here.

A plausible explanation is that the deletion reduced false-positive mass enough to outweigh any loss of buffered true-positive credit under the competition's asymmetric distance-weighted Tversky metric. That is a hypothesis, not a causal finding: the hidden target is unavailable, and these mirrored pixels cannot reveal the removed locations' hidden-label contributions. In particular, the repo cannot prove that the B2 deletion caused the reported score, nor that a similar/new model would beat it.

The official task is fault mapping indicative of geothermal resources—not direct proof of geothermal vents. A topographic/geophysical lineament is not, by itself, a fault or a geothermal discovery. See the [official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).

## Nine-site scorecard

Values below are copied from the user-supplied list and the pinned repository manifest. They are **USER-REPORTED / UNVERIFIED**, not artifact-linked ORGANIZER-CONFIRMED receipts. No new candidate score estimate is defensible, so the estimate column is deliberately `Not estimable`. The file links below are historical references only. The pairwise result is the limited nine-file pixel audit, not a fresh complete registry check.

| Site | Historical top file | Reported value | New-file score estimate | Distinct vs the other eight pinned files? | Decision |
| --- | --- | ---: | --- | --- | --- |
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 | Not estimable | No; >70% 3-px overlap with at least one peer | Historical research only |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 0.2600 | Not estimable | No; >70% overlap with at least one peer | Historical research only |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 0.2449 | Not estimable | No; >70% overlap with at least one peer | Historical research only |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 0.2710 | Not estimable | No; >70% overlap with at least one peer | Historical research only |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 | Not estimable | No; >70% overlap with at least one peer | Historical research only |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 0.2708 | Not estimable | No; >70% overlap with at least one peer | Historical research only |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 | Not estimable | No; >70% overlap with at least one peer | Learning/reference only; do not resubmit |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | Not estimable | No; >70% overlap with at least one peer | Historical research only |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 | Not estimable | No; >70% overlap with at least one peer | Historical research only |

Exact pinned files, hashes, and geometry results: [`registry/historical.json`](../registry/historical.json), [`docs/historical-raster-audit.json`](../docs/historical-raster-audit.json), [`evidence/geometry_audit.json`](../evidence/geometry_audit.json). The nine pairwise raster comparisons show all 72 directional overlaps exceed 70%; this is not proof about every other registry artifact or candidate surface.

## Current candidate audit and irregularities

The archived `H-K3-1 SMGC-CT` file SHA-256 is `f21a0e831e6307d1d8230119c4d2f9812646fa8b092b2326b180a54feccea33f`. Directly reading the stored bytes with Rasterio confirmed one float32 band, shape `3730 × 3292`, CRS `EPSG:32611`, transform `[100, 0, 243350, 0, -100, 4508550]`, `nodata=None`, all finite values, min/max `[0, 1]`, and 37,654 nonzero cells. This is **format-only** confirmation against the file's metadata. The owner-mirrored reference template is not present in this checkout for an independent byte-to-template comparison, and local metadata/range validity does not satisfy the scientific or release gates.

The previous archived candidate report asserted a full registry maximum 3-pixel overlap of 63.47%. The newer literal-rule preflight separately identifies a registered spacing-five calibration lattice: only 6,649 of 5,167,373 footprint pixels lie beyond three pixels of that lattice. For 37,654 distinct in-footprint dots, at least `(37,654 - 6,649) / 37,654 = 82.34%` must therefore lie within three pixels of the lattice. Under the user's instruction to include **any** registered raster, that lower bound exceeds the 70% stop threshold. These two historical uniqueness claims use different registry scope/control treatment and cannot both establish uniqueness under the literal rule. We do not silently exempt the lattice or exploit its gaps. This is why the archived H-K3 file is **not approved** despite its format and prior report.

Other issues found:

1. Several checked-in pages and the first README section advertised the old candidate as “PROMOTE — OK TO DOWNLOAD AND SUBMIT,” while the current preflight/run card said no current candidate and the literal uniqueness witness stopped the customary dot budget.
2. `docs/sites.json` and old H-K3/CRSB pages contain stale status and/or score-estimate fields that should not supersede the current preflight evidence. The current user-facing table instead labels historical values as unverified and the new-score estimate unavailable.
3. The current local readiness check reports the canonical source snapshot present, but `registry/lane.json`, the cached feature stack, all 416 pinned registry raster files, and a same-evaluator rerun are absent. Core data mirrors are also absent from this checkout; prior restore receipts are provenance records, not the current files.
4. The template inspection records a known shared CLI issue: upstream holdout/writer wrappers can binarize positive probability values. The required fix belongs upstream; this repo must not silently maintain a private fork. See the upstream [issue #37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37).
5. Competition-data login and account quota/receipt access are not available here. No current public leaderboard refresh or organizer score was acquired in this review.

## Hypothesis slate — planning only; no experiments run

The repository already records candidate mechanisms in the prior research review. The request does not provide an assigned “single method paragraph”; therefore these are **not accepted as this session's lane** and none was implemented or scored. Relative ranking is qualitative, not a numerical score projection.

| Rank | Hypothesis / layers | Target and rationale | Main mimic | Cost, source availability, and difference |
| --- | --- | --- | --- | --- |
| 1 | Paired signed gravity–magnetic profiles: isostatic gravity, TMI/RTP, detrended elevation | Compare oriented, signed multiscale changes and cross-field offsets to reveal a buried discontinuity under weak relief, instead of favoring only known surface traces | Unfaulted lithologic contacts, dikes/remanence, survey leveling | Medium. Competition-provided bands are described on the [official feature page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), but the feature stack/cache is absent locally. Related edge-offset work exists in sibling repositories; novelty is not global. |
| 2 | Repeated cross-fan drainage deflections: DEM/elevation plus official USGS 3DEP terrain and hydrography | Seek coherent repeated channel offsets across an independent structure to detect subdued or covered faults absent from surface compilations | Avulsion, capture, erosion, roads, shorelines | High. [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) is an official free source page, but local tile coverage/bytes have not been verified. Not viable until data and coverage are confirmed. |
| 3 | Depth-differential conductance reversal: USGS MT conductance at multiple depths plus gravity basement margin | Test whether a deep conductance boundary reverses or shifts with depth, suggesting a covered structure instead of a shallow conductive blob | Saline water, clays, inversion resolution/coverage | Medium/high. [USGS ScienceBase](https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b) lists official map downloads; the local files and trace-scale suitability were not verified. |
| 4 | Cross-line thermal residual: INGENIOUS shallow temperature points, terrain and conductivity | Correct for depth and sampling density, then test residual temperature contrast across independent lineaments to avoid a simple hot-well proximity map | Sun exposure, groundwater, lithology, anthropogenic wells, uneven sampling | High. [DOE GDR #1391](https://gdr.openei.org/submissions/1391) provides the official project/archive landing page, but local binary access, coverage and contribution-level license provenance were not rechecked. |

Before any future test: resolve the lane with the parallel-run coordinator; restore exact cached features and the shared evaluator/writer; freeze a comparable incumbent; rebuild all catalogue-derived features inside whole-segment buffered folds; mask visible faults pixel-exactly; run single-feature leakage canaries; check complete registry surface and final-dot uniqueness; stop immediately above either threshold. Do not use a weekly slot before a positive paired holdout result and separate selector decision.

## Three review passes

### Pass 1 — inspect and execute the requested repository review
- Read the standing README, current run card, readiness inventory, research review, nine-site registry, and the two landing-page systems.
- Identified contradictory current-vs-historical release status and verified the archived TIFF's actual file bytes/metadata without treating format validity as promotion.
- Confirmed the exact focus set is all nine requested GEMSDOE repositories and distinguished historical claims from estimates.

### Pass 2 — repair user-facing inconsistencies and regression coverage
- Replaced the README's initial “ready to submit” card with the current negative decision and marked the previous H-K3 report as historical/superseded.
- Reconciled both page generators: `build_preflight_site.py` owns the preflight subpages and current-session data aliases; `build_review_status.py` owns the canonical `/docs/` landing and executive summary. The canonical entry pages now retract the former approval, show the duplicate stop, and label all nine reported scores unverified.
- Preserved the historical negative candidate card at `docs/run-card.json`, while the current-session zero-experiment card is exposed at `docs/data/latest-run-card.json`; neither path authorizes submission.
- Integrated the newer fail-closed gate and review changes from `main` without leaving the assigned branch. They retain the full historical candidate audit and fix the previously disabled runner/gate behavior.
- Replaced old H-K3-deliverable tests that asserted a now-conflicted uniqueness pass with checks for the current fail-closed decision, archived raster byte format, and the literal lattice overlap stop.
- Added `node_modules/` to `.gitignore`; local Python environment and installed test dependencies are ignored.

### Pass 3 — final verification against the request
- `.venv/bin/python -m pytest -q`: PASS, 97 passed and 1 ignored-cache integration skipped.
- `.venv/bin/python -m unittest discover -s tests -q`: PASS, 54 tests.
- `npm test`: PASS, 4/4 dashboard tests; browser-feed tests PASS, 2/2.
- `python scripts/build_preflight_site.py` and `python scripts/build_review_status.py`: PASS; `python scripts/build_site.py --check`: PASS.
- JSON parsing, JavaScript syntax checks, and `git diff --check`: PASS.
- `.venv/bin/python scripts/check_readiness.py`: intentionally returns `2` / not ready, listing absent lane, data, cache, registry rasters, and same-evaluator baseline.
- No hypothesis experiment, new TIFF creation, leaderboard upload, slot selection, or organizer-score confirmation occurred.

## Next actions and limitations

1. Obtain a written lane assignment that resolves the ambiguity in the supplied parallel-run prompt; keep this session on its assigned method only.
2. Restore the organizer data through authorized access and the cached template feature stack. Confirm dataset provenance; this checkout cannot access the DrivenData data tab anonymously.
3. Decide with the coordinator whether the literal uniqueness rule includes calibration/control rasters. Until resolved, the 37,654-dot budget is a duplicate stop; never manufacture “uniqueness” by targeting uncovered lattice gaps.
4. Verify/fix the evaluator/writer upstream and run one frozen same-evaluator baseline plus only preregistered experiments within the stated 3-run / 2-hour budget.
5. Make a candidate eligible only after leakage, paired holdout, pre/post uniqueness, raster validation, provenance, and separate slot-selector checks all pass. Obtain and store the actual submission-page receipt after any future upload.
6. Refresh official-source snapshots and confirm current leaderboard/account quota; the public leaderboard is not evidence tying a score to a file hash.

Official links for manual review: [problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [official competition rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) · [USGS conductance data](https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b) · [DOE GDR / INGENIOUS](https://gdr.openei.org/submissions/1391) · [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).

## Run card (current review)

```json
{
  "hypothesis": "No assigned method was tested; four research hypotheses are listed above for coordinator review.",
  "mechanism": "No new mechanism implemented or evaluated in this review.",
  "named_non_fault_process_that_could_mimic_it": "Not applicable to an untested candidate; leading proposed mimics include lithologic contacts, drainage capture, saline conductance, and uneven thermal sampling.",
  "holdout_dti": {
    "label": "HOLDOUT-DTI",
    "evaluator_version": null,
    "withheld_positives": null,
    "ci95": null,
    "status": "NOT RUN; no current experiment."
  },
  "correlation_overlap_vs_registry": {
    "preplacement_surface_spearman": null,
    "final_dot_overlap_3px": null,
    "status": "No new candidate. Archived 37,654-dot candidate has a literal-rule lower-bound overlap of 0.823418 against the registered lattice control; duplicate stop."
  },
  "raster_sha256": null,
  "validator_output": {
    "new_candidate": false,
    "archived_hk3_file_format_only": "single-band float32; 3730x3292; EPSG:32611; finite; min=0; max=1; no-data metadata null",
    "template_crs_shape_transform_comparison": "NOT RUN: local organizer/template raster is absent"
  },
  "submission_name": null,
  "note": "No new candidate; do not spend a slot.",
  "verdict": "negative"
}
```
