# GEMSDOEkarage3 — evidence-first fault mapping

## Current decision — 2026-10-29: **NO APPROVED TIFF · DO NOT SUBMIT**

**There is no file that is OK to download and submit.** A previous H-GEO-CONDUIT GeoTIFF is retained as a research artifact, not a release. The project's current gate is negative and no submission slot has been selected or used. The artifact must not be mistaken for an approved download because a TIFF exists or its basic grid/range audit passed.

- Archived research file: `docs/quarantine/geoconduit-hybrid/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif` (SHA-256 `064348774a950f22cd677b52c8e27778066ef2947505630ff4074fc6e4eeaf43`; 35,615 positive pixels, per its saved-byte audit). The 2026-10-29 saved-byte raster audit measured **99.8287%** within 3 px of the pinned lattice witness; full-registry checks and holdout reproduction remain unestablished.
- **HOLDOUT-DTI (historical candidate run-card claim; not independently reproduced in the 2026-10-29 review): 0.423855**, 95% CI `[0.405253, 0.442747]`; evaluator `GEMSDOE32-HOLDOUT-v3-visible-gated`; 22,232 withheld positives. This is not `ORGANIZER-CONFIRMED`, not a leaderboard projection, and is not established as comparable to the user-reported 0.2778 historical portal result.
- **GEOMETRY-AUDIT (not a score):** the pinned calibration-lattice witness leaves 6,649 footprint cells outside its 3-pixel neighborhood. For 35,615 distinct in-footprint dots, at least 28,966 (81.33%) must fall inside that neighborhood, above the literal 70% stop threshold. This is a necessary bound from one witness, not a complete registry certification; it is sufficient to reject this dot budget under the stated protocol.
- The candidate's slot decision is `PENDING-REVIEW`; its full literal registry surface audit, matched protocol-compliant holdout reproduction, feature leakage canaries, and separate selector approval are not established. Therefore: **DO NOT SUBMIT**. No submission note is authorized while eligibility is NO. Do not use an old file, rename it, or adjust it to evade the overlap test.
- A later branch artifact, `karage3-h1-seismic-gravity-basin`, is also negative: its run card records HOLDOUT-DTI 0.000000 against a 0.100798 baseline and explicitly says the complete-registry scan was not performed. The run-card file is quarantined under `evidence/quarantine/h1-seismic-gravity-basin/`; its basic format checks and witness-only non-overlap are not approval or proof of registry uniqueness. This artifact was inherited from the updated base branch, not generated or validated in this review.

[Current review](docs/review-2026-10-29.md) · [Latest follow-up review](docs/review-2026-10-29-followup.md) · [Machine-readable candidate review card](docs/data/candidate-review-20261029.json) · [Release decision](docs/current-gate-decision.json) · [Nine-site executive summary](docs/preflight-executive.html) · [Step-by-step conditional submission guide](executive-summary.html)

## What the highest focus-site result does — and does not — tell us

The highest value in the supplied focus-site list is GEMSDOE32's `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, **0.2778 USER-REPORTED / UNVERIFIED**. The repository's pinned geometry audit reports that its support is a subset of GEMSDOE31's and that 2,545 pixels in the directional difference lie within 2 pixels of the mirrored known-fault labels (**GEOMETRY-AUDIT, not a score**). That is consistent with a hypothesis that removing redundant or low-yield predictions can improve an asymmetric distance-weighted metric. It does **not** prove why the organizer score changed: no artifact-linked submission receipt was verified, the hidden truth is unavailable, and the audit uses owner-supplied mirrored inputs. Accordingly, we cannot promise a score above 0.2778 or give a valid new leaderboard-score estimate.

### Focus-site scorecard

Every historical value below is copied from the user-supplied inventory and is **USER-REPORTED / UNVERIFIED**, not an organizer receipt. The file links on site pages are historical research references, not a recommended download. “Estimated score” is not available for any row.

| Site | Highest supplied historical item | Reported value | New leaderboard estimate | Unique/cleared? |
|---|---|---:|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 USER-REPORTED / UNVERIFIED | Not estimable | No — historical; fails literal proximity gate |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 USER-REPORTED / UNVERIFIED | Not estimable | No — historical; fails literal proximity gate |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 USER-REPORTED / UNVERIFIED | Not estimable | No — historical; fails literal proximity gate |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 USER-REPORTED / UNVERIFIED | Not estimable | No — historical; fails literal proximity gate |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 USER-REPORTED / UNVERIFIED | Not estimable | No — historical; fails literal proximity gate |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 USER-REPORTED / UNVERIFIED | Not estimable | No — historical; fails literal proximity gate |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | 0.2778 USER-REPORTED / UNVERIFIED | Not estimable | No — historical; fails literal proximity gate |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 USER-REPORTED / UNVERIFIED | Not estimable | No — historical; fails literal proximity gate |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 USER-REPORTED / UNVERIFIED | Not estimable | No — historical; fails literal proximity gate |

Per-site summaries: [GEMSDOE24](docs/focus9/gemsdoe24.html) · [GEMSDOE25](docs/focus9/gemsdoe25.html) · [GEMSDOE27](docs/focus9/gemsdoe27.html) · [GEMSDOE28](docs/focus9/gemsdoe28.html) · [GEMSDOE30](docs/focus9/gemsdoe30.html) · [GEMSDOE31](docs/focus9/gemsdoe31.html) · [GEMSDOE32](docs/focus9/gemsdoe32.html) · [GEMSDOE33](docs/focus9/gemsdoe33.html) · [GEMSDOE36](docs/focus9/gemsdoe36.html)

## Candidate geological hypotheses — research proposals, not score forecasts

The following candidates are a qualitative research queue, not claims of global novelty and not authorization to run. The inherited experiment cap is already recorded as 3/3 used, no unambiguous lane is assigned, and the shared evaluator defects listed in `AGENTS.md` remain blockers. No new experiment is started here.

| Priority | Layers and physical signature | Why it may reveal an unmapped fault | Main non-fault mimic | Difference, cost and data status |
|---|---|---|---|---|
| 1 | GeoDAWN isostatic gravity + RTP magnetics; signed cross-strike edge displacement persisting across continuation/smoothing scales under weak relief. | A buried basement discontinuity can juxtapose potential-field properties without a mapped surface trace. | Lithologic contacts, dikes, remanent magnetization, survey striping. | Signed paired-profile displacement and scale persistence, rather than unsigned edge magnitude. Moderate implementation cost; authenticated raster bands/cache and a centrally corrected evaluator are not staged. |
| 2 | DEM/topography + drainage and an independent gravity boundary; repeated similarly oriented cross-channel deflections. | Repeated channel response could expose a subdued structure beneath young cover. | Avulsion, stream capture, lava dams, roads, erosion. | Multi-channel replication rather than a single scarp/curvature score. High cost; exact official 3DEP/3DHP coverage/download for this AOI was not verified. |
| 3 | INGENIOUS shallow temperature + terrain/conductivity; cross-fitted thermal residual conditional on independent geophysical structure. | Thermal residuals may identify fluid pathways without using known-well proximity as the target. | Insolation, groundwater, sampling density. | Explicit terrain/survey background adjustment. Moderate-high cost; GDR #1391 is a lead, but local coverage and retrieval are not verified. |
| 4 | GeoDAWN K/eTh/eU + acquisition-block metadata and independent magnetic structure; alteration residual stable across held-out survey blocks. | Persistent multi-block alteration patterns may extend beyond mapped traces. | Lithology, soil moisture, vegetation, processing seams. | Acquisition-block invariance rather than raw ratio hotspots. Moderate-high cost; exact grids/metadata are not staged. |

Rank is research priority only; **no expected DTI improvement is numerically forecast**. Do not implement until a lane is explicitly assigned, the shared template is corrected/pinned, data provenance is resolved, and the experiment budget is reset/authorized.

## Submission readiness and what remains

The site's executive submission page deliberately offers no enabled candidate-download control. A valid future release must pass, in order: (1) authenticated competition grid/data and cached feature stack; (2) shared whole-segment buffered visible-only hide-and-recover, pooled DTI and leakage canaries; (3) continuous-surface and final-dot literal checks against the complete current registry; (4) exact saved-byte validation for finite in-footprint values in `[0,1]`, CRS, shape and transform; and (5) a separate selector that confirms eligibility and current weekly quota. Only then is a TIFF download enabled. A passing local validator is not organizer acceptance.

Known access/blocker limits:

- The DrivenData data page requires competition login; this checkout does not have that session's authenticated download permission. Owner mirrors are not organizer-authenticated.
- The template's canonical feature stack is absent; `data/` only has small manifests/receipts, not competition rasters.
- Shared holdout, preview surface gate and masked-footprint validator remain unresolved upstream; do not create a private fork. See [AGENTS.md](AGENTS.md) for issue IDs.
- Complete current registry comparison, current leaderboard refresh, organizer receipt, and live weekly quota are unavailable in this review.
- Current session has no assigned method paragraph and inherited experiment budget was used; no experiments or submission slot were spent here.

### Official sources for manual review

- [Competition overview and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Competition data page (login may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data source](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)
- [DOE GEMS rules / submission guidance PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Tversky index](https://en.wikipedia.org/wiki/Tversky_index) (secondary reference; prefer competition documentation for metric definition)

## Core values

- **Maximize P(Win)**: choose actions that increase the probability of a trustworthy competition result, including stopping when the evidence is insufficient.
- **Own the Outcome:** fix inconsistencies and broken gates end-to-end; treat negative results as useful evidence rather than hiding them.

## Start-of-session checklist

Read this README, [`AGENTS.md`](AGENTS.md), [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md), [`docs/review-2026-10-29-followup.md`](docs/review-2026-10-29-followup.md), [`docs/review-2026-10-29.md`](docs/review-2026-10-29.md), [`docs/review-2026-10-28-session.md`](docs/review-2026-10-28-session.md), and [`docs/data/latest-run.json`](docs/data/latest-run.json) before further work. Treat historical cards as evidence with limited scope, never authorization.

# STANDING REFERENCE PROMPT (verbatim)

> Maximize P(Win). No excuses. Own the outcome.
> Please review the entire repo, then build and update the project as needed. Do not fabricate anything or hallucinate. Our goal is to win the DOE GEMS competition by creating a submission that gets a higher score than the current high on the leaderboard of 0.4413; all files must be validated by the project without human intervention and the project should clearly indicate whether a file is ok to download and submit or not. Right now the submission I downloaded and submitted had an error of "Predicted values must be in range [0, 1]".
>
> Please focus on analyzing the highest scoring submissions from GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36. Then answer the following questions with PhD level analysis: why and how did h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros on https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html get a score of 0.2778 which is the highest of any of those sites? Can we generate a submission that gets a higher score? If so, how? Make sure our project has an executive summary on every one of those sites (GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36) and a table that compares them and lists what file to download and what their estimated or actual score is and whether they are unique or not.
>
> We MUST GENERATE A UNIQUE TIF SUBMISSION! Do not copy a previous submission, except for learning or comparison purposes! Whatever we generate MUST be a unique tif submission unlike any of those on the sites listed below! Also provide a unique name and a short note <= 140 characters to help distinguish the submission in the contest. Also make it easy to download at the very beginning of our site in an obvious Executive Summary and have an executive summary subpage explaining step by step how to submit into the contest.
>
> Before writing any model code, read the GEMS feature list and generate 3-5 novel candidate geological hypotheses that have not been tried yet. For each hypothesis, name: (1) the specific layer(s) involved, (2) the physical signature you are targeting, (3) why it would catch faults/geothermal vents missing from the USGS/INGENIOUS catalogue rather than ones already in it, and (4) how it differs from existing implementations. Rank them by expected DTI improvement and implementation cost, then implement and validate the top candidate on the spatially-blocked holdout set.
>
> Parallel-run protocol (keep every run short, comparable, and non-duplicative):
> 1) Lane: Stay inside your assigned method paragraph. If raster rank-correlation with any registry raster exceeds 0.90, or >70% of your dots fall within 3 px of a registry raster's dots, log as a duplicate and stop. Check both on the continuous surface before placement AND on final dots.
> 2) Reuse, don't rebuild: Use the template's cached feature stack, evaluate_holdout.py, and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive any catalogue-based features only from visible faults, mask visible faults pixel-exactly, and score pooled DTI (alpha=0.2, beta=0.8, 300 m triangular kernel). If a shared tool in the template is wrong, fix it there — no private forks.
> 3) Label every number: Every score must be labeled either HOLDOUT-DTI (with evaluator version, number of withheld positives, and 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). Never write a projection as a score.
> 4) Leakage canary: Test each feature alone on holdout before trusting results. Single-feature AUC > 0.90 indicates leakage until proven otherwise.
> 5) Run card: End with one JSON card containing: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, registry correlation + overlap, raster SHA256, validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match), submission_name + <=140-char note, and verdict: promote / negative. Negative results are valid deliverables. Do not spend a real submission slot on an idea that hasn't beaten holdout best.
> 6) Budget: Stop after 3 experiments or 2 hours.
>
> Make sure you run 3 passes:
> Pass 1: Implement and verify everything works.
> Pass 2: Review your work, find bugs, missing requirements, or edge cases, and fix them.
> Pass 3: Re-check against the user's full prompt to ensure accuracy, reliability, completeness, and code quality.
>
> Create a pull request and merge the PR onto main. Document remaining work and limitations.


---

## Three-pass review and run card

The 2026-10-29 repository review is recorded in [`docs/review-2026-10-29.md`](docs/review-2026-10-29.md). It made no new model experiment and no submission. The current candidate review is negative; see [`docs/data/candidate-review-20261029.json`](docs/data/candidate-review-20261029.json) for its run card and incomplete uniqueness/validation fields. Negative results are valid deliverables.
