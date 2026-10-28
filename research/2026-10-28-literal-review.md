# Literal registry review and research slate — 28 October 2026

> Independent parallel-session review. Input availability and shared-tool descriptions below are dated to that session; see the [later session review](../docs/review-2026-10-28-session.md) and [latest run card](../docs/data/latest-run.json) for restored raw mirrors, the exact shared-template pin and the current decision. Neither review authorizes submission.

## Decision

**NO FILE IS APPROVED FOR SUBMISSION.** The former K3C PROMOTE verdict was based on replacing the requested literal overlap test with a null-calibrated excess metric. That substitution was not authorized. The corrected screen is negative; no new geological experiment, TIFF, leaderboard estimate, slot selection or upload was made in this review. The standalone [current JSON card](../docs/data/current-run.json) is the authoritative record for this review.

The pinned witness is a registered **calibration lattice**, not a geological model. The literal rule treats it like any other raster. A duplicate stop against it is a geometric protocol result, not proof that two methods or geology are identical. Changing the rule requires an explicit user decision; neither a filename change nor a statistical normalization supplies an exception.

## Exact bytes and the pigeonhole stop

Reopened all eight TIFFs under `docs/`, recomputed hashes, grid/range/mask diagnostics, and compared their in-footprint positive pixels with the hash-pinned 13GEMSDOE lattice. [Machine-readable saved-byte report](../evidence/saved-tiffs-literal-20261028.json); reproduce with `.venv/bin/python scripts/audit_saved_tiffs.py --fetch`. The reference template and lattice are owner-published mirrors, hash pinned but not independently authenticated by the organizer. This is a one-witness disproof, **not** a complete registry or pre-placement surface audit.

| Retained file group | Directed share of candidate dots ≤3 px from witness | Decision |
|---|---:|---|
| K3-CCL | 99.9097% | DO NOT SUBMIT |
| H-K3B-1 CSST-BGHF | 99.3626% | DO NOT SUBMIT |
| H-K3-SMGC, NaN and zero twins | 99.6866% each | DO NOT SUBMIT |
| H-K3-1 CRSB-GUB | 99.3387% | DO NOT SUBMIT |
| K3-FUSE, NaN and zero twins | 99.9225% each | DO NOT SUBMIT |
| H-K3C | 99.3520% | DO NOT SUBMIT |

The eight include multiple encodings of the same dot support; a distinct hash alone is not distinct geometry. The historical K3C card also reports worst **literal** final overlap of 100% in its older scan, while some fields labeled `overlap_3px` instead hold calibrated excess. Its surface-stage overlap is not demonstrated by a measured preregistered support mask. The 99.3520% lattice figure above is freshly recomputed from K3C saved bytes and is sufficient to reject it.

K3C SHA-256: `0d1461e8786d99da06182b196af0fc40cf03220dc76126e83623e218516429df`. Its raw band is finite and within [0,1], with the pinned 3730 × 3292 grid, EPSG:32611 and 100 m transform. It does **not** encode outside-footprint cells as null in our conservative mask-based interpretation, so `scripts/check_format.py`'s combined local check fails. Conversely, the NaN-outside twins satisfy the conservative null interpretation but fail the separate all-cell-finite diagnostic. No encoding has been verified by a DrivenData receipt; the cause of the user's prior range error is unknown. An internal TIFF mask can represent null outside with finite raw values in a synthetic local test, but that is not evidence of portal acceptance. Historical writer phrases claiming a permanent fix or `validator_range_0_1_guaranteed` are not organizer guarantees.

The pinned lattice has 206,895 positive pixels and covers 5,160,724 of the 5,167,373 mirror-footprint pixels within 3 pixels, leaving 6,649 uncovered. Any set of N distinct in-footprint dots must overlap by at least `max(0, N − 6,649) / N`. For N=37,654, this is 31,005/37,654 = **82.3418%**, above 70%. The first budget proved to fail is **22,164**. Budgets at or below 22,163 are merely *not ruled out by this bound*; they need the full literal registry and scientific tests. Do not optimize artificial geometry solely to hide in lattice gaps.

## Nine-site analysis

The [executive comparison](../executive-summary.html#site-details) lists each exact pinned historical file, provenance/hash, claimed value, format diagnostics and directional overlaps. In the historical snapshot, all 72 directional comparisons among those nine files exceed 70%; none is a new authorized submission. No hidden-score estimate is justified, and the rankings below are **USER-REPORTED / UNVERIFIED**, not organizer receipts.

| Site | Historical claim | Current published page reviewed (not independently replayed) |
|---|---:|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | 0.2477 | S3DEP1 is a research-only point-best; page flags the lattice, domain-shift checks and unreproduced results. |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | 0.2600 | H80's reported screen is negative against its same-run H35 comparator; page notes mismatched registry transform and no TIFF. |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | 0.2449 | H28-6 says duplicate stop and no new file; H33 is research-only and its uniqueness claim covers a limited set, not the full registry. |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | 0.2710 | S27 says no candidate; archived S25 is reported below a matched random control. Stale sections use inconsistent local input-availability snapshots. |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | 0.2600 | CSR-1 and newer artifacts are lattice-stopped; an older screen omitted the witness. Some reported holdouts lack fold-local construction. |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | 0.2708 | H31-CC is research-only, with a negative paired comparison and a literal lattice stop; a format claim is not a portal receipt. |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | 0.2778 | Highest supplied claim, not hash-linked to a receipt. Newer H51-1 is withheld because of 99.45% lattice overlap and other gates. |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | 0.2632 | R7's reported surface overlap exceeds 70%; a later final-dot pass cannot erase that pre-placement stop. Prior full-catalogue threshold fits are exploratory. |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | 0.2750 | No candidate authorized; the page explicitly distinguishes lattice degeneracy from geological identity. |

These are dated page observations, not replays or cross-evaluator comparisons. Main-branch metadata was refreshed for all nine; a changing head does not audit new bytes. The official public leaderboard directly displayed **0.4544 at rank 1 on 2026-10-28 around 22:34 UTC**. This is a public-board snapshot only, not the private result or a score for our file; [check the current board](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). An earlier automated attempt could not fetch DrivenData; the current metadata feed is GitHub-only because DrivenData's terms prohibit automated monitoring. The displayed board observation is dated and must be checked directly on the official page.

### Why might 0.2778 be higher?

The pinned pixel audit finds GEMSDOE25 and GEMSDOE30 have identical in-footprint supports. GEMSDOE32 is GEMSDOE31 with 2,545 near-catalogue dots removed; GEMSDOE36 contains GEMSDOE32's dots plus 1,200. Under the [official metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), for each truth pixel the best nearby confidence is multiplied by `max(1 − d/300 m, 0)`, and prediction mass far from truth contributes weighted false positives. At 100 m spacing, single-pixel offsets of 0, 1, 2, 3 pixels have kernel weights 1, 2/3, 1/3, 0—not full credit throughout a 3-pixel disk. Pruning or thinning can improve coverage per unit false-positive mass, but removing true positives can hurt. Hidden expert labels, causal attribution, and a receipt are absent; we cannot prove why 0.2778 happened or promise an improvement.

Prior K3C reports **HOLDOUT-DTI 0.111044** (95% CI [0.098990, 0.122727], `GEMSDOE32-HIDE-RECOVER-v3.1-24cell`, 66,904 withheld-positive occurrences) versus same-card champion-rule 0.100798, paired delta CI [+0.003019, +0.017272]. These are historical source claims, not rerun, not a live score, not proof of a compliant whole-segment buffered split, and not proof against the current same-protocol best. In particular the shared template's [issue #60](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/60) documents that its collar is not a truth-to-visible buffer.

## Ranked hypotheses — proposals only

Order is qualitative expected fault-recovery potential, not a score projection. The exact operators were not identified in the reviewed local implementations; exhaustive novelty across all siblings is not established. The experiment is blocked until one method paragraph is explicitly assigned and the central template and inputs are ready.

| Rank / estimated implementation cost | Layers and measurable signature; why it might reach off-catalogue faults | Distinction, named mimic and access |
|---|---|---|
| 1 / medium–high | **Paired texture displacement:** supplied RTP/TMI and detrended elevation; phase-correlate corresponding texture windows across a candidate line and require a consistent signed displacement along strike and across scales. A fault hidden beneath cover could offset a marker without a surface scarp. | Unlike pointwise gravity–magnetic edge coincidence, this estimates a shared-pattern shift. Volcanic facies, remanence and survey striping can mimic it; require shifted-null and texture-only controls. The shared derived feature cache is absent; its source authenticity is unverified. |
| 2 / high | **Repeated cross-fan channel offsets:** [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) DEM and derived channels; compare signed displacements of multiple independent channels crossing an independently defined break in slope. A subdued fan-crossing fault may lack a mapped scarp. | Tests paired-channel offset rather than a single curvature or drainage veto. Avulsion, stream capture, roads and ancient shorelines mimic it; actual tiles and coverage not verified. |
| 3 / medium–high | **Cross-fitted shallow-temperature residuals:** [INGENIOUS GDR](https://gdr.openei.org/submissions/1391) 2 m probe observations, terrain and conductivity; remove spatial/terrain sampling background out of fold, then test coherent residuals against independent structural edges. A covered fluid pathway could be missed by a surface catalogue. | Models measurement/sampling confounders rather than simply distance to a spring; sun, groundwater and uneven surveys mimic anomalies. Source declares CC BY 4.0; specific bytes and coverage are unverified. |
| 4 / medium–high | **Acquisition-block radiometric residual:** [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) K/eTh/eU, flightline metadata and independent magnetic edges; seek alteration residuals stable in held-out survey blocks. Concealed mineral alteration might support a hidden structure. | Tests cross-acquisition invariance, not raw radioelement ratio hotspots. Rock type, soil moisture and leveling seams mimic it; survey grids/coverage have not been obtained. |

Potential-field texture alone does not prove a fault; thermal/alteration signals do not establish a vent or economic resource. Conductance at 2–200 km depths from the [USGS ScienceBase model](https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b) is too coarse to assume 100 m trace localization. All external data require exact coverage, licensing, provenance and binary verification before use.

## Blockers and next steps

1. Obtain the single method paragraph; do not silently adopt this slate as an assignment.
2. The authenticated account has **read-only** access to the shared GEMSDOE32 template. Central issues [#42](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/42) (surface gate), [#60](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/60) (buffer), [#37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37) (soft-input wrappers), and [#63](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/63) (registry completeness) remain open. Pin and regression-test fixes in the template, not a private fork. Local experimental entry points stop until then.
3. Restore organizer-authenticated features, labels and the shared cache; freeze a complete current registry including every applicable raster and define a measurable preregistered surface support. A missing/undefined comparison is a stop.
4. Freeze buffered whole-segment folds and the matched current best. Compute each catalogue feature from visible faults only; mask visible faults pixel-exactly; run per-feature leakage canaries (oriented AUC >0.90 stops); calculate pooled DTI and paired spatial 95% CI. Run no more than three experiments or two hours.
5. Check literal correlation and overlap both before placement and on final saved dots, then independently validate exact TIFF bytes. Only an independent selector can authorize a slot, after checking the live account quota. The [official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) specify three feedback submissions per week subject to current site limits and require disclosure of generative-AI use; the account's remaining quota is unknown.

## Engineering review passes

1. **Implement and verify.** Independently reopened the eight retained TIFFs and recomputed their SHA-256, lattice overlaps and local format diagnostics. Replaced the null-calibrated promotion logic with a literal, fail-closed card screen, stopped the known-bad budget in the experiment entry points, and rebuilt the public decision pages. Initial browser test setup lacked `jsdom`; installed the lockfile dependencies and reran it.
2. **Review and fix.** Found that direct `python scripts/...` invocations could fail on an import rather than reach the safety preflight; corrected their module path and added direct-CLI regression tests. Also strengthened the screen to require defined surface support, per-feature canary coverage, the known witness, fold-local buffered holdout claims, budget limits and a separate selector; rejected ambiguous calibrated primary rules. Verification after fixes: 130 Python tests passed, one optional-cache test skipped and 66 subtests passed; browser-feed tests 2/2 and dashboard tests 4/4 passed. These are engineering checks, not science results.
3. **Prompt and integration recheck.** Reconciled the independent parallel main-branch review without changing the central template or suppressing the user’s literal rule. Its K3C witness calculation exactly agrees with the eight-file audit; unrelated 5-pixel diagnostics are not treated as the 3-pixel rule. Replaced a stale historical numbers verifier with a current hash-bound, fail-closed consistency check. Post-integration verification: 133 pytest tests passed, 66 subtests passed, and one SMGC feature-cache integration test was skipped because the cache is absent; `unittest` passed 66; dashboard tests passed 4/4; browser-feed tests passed 2/2; 17/17 evidence consistency checks and deterministic site builds passed. Remaining blockers are listed above; no scientific experiment or competition slot was used. See the final PR checks for deployment status.
