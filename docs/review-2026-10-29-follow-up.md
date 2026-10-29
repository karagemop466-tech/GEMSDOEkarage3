# Follow-up review — 29 October 2026 UTC

## Decision: NEGATIVE — DO NOT SUBMIT

This follow-up repaired a stale public release path, audited generated pages and tests, and wrote a three-proposal slate. It did **not** generate a new TIFF, run a geological experiment, produce a HOLDOUT-DTI result, select a slot, or upload anything. During PR review, `main` advanced with PR #46: it quarantined the previously unassessed `karage3-unique-offcat` pair and an H-GEO-CONDUIT candidate, then refreshed the saved-byte audit to include all 13 TIFFs. After integration, all 13 have a literal duplicate stop against the pinned lattice witness; none is approved. The H-GEO candidate's card-reported HOLDOUT-DTI remains NOT ESTABLISHED as a reproducible same-protocol comparison. No estimated leaderboard score is defensible.

## Three review passes

### Pass 1 — inspect and repair

- Read `AGENTS.md`, the standing README prompt, project brief, dated review, current and latest cards, release gate, site builders and their tests.
- Found an unsafe inconsistency: root `index.html` and `executive-summary.html` were stale and advertised `karage3-unique-offcat-...-zeros.tif` as “READY TO DOWNLOAD” / submission-ready; `docs/how-to-submit.html` separately offered direct links and called it unique. The two TIFFs were absent from the pinned saved-byte audit. A stale saved-byte gate in `build_k3c_site.py` and `build_release_review.py` assumed the audit must enumerate every TIFF anywhere under `docs/`; it rejected the build instead of generating the conservative current decision.
- Corrected the builders to fail closed if TIFFs are added without an audit row. After PR #46 was merged to `main`, both off-catalogue families were moved under `docs/quarantine/` and the pinned saved-byte report was refreshed to hash-bind all 13 docs TIFFs. Every row exceeds the literal 70% overlap stop against one registered lattice witness; this is a negative one-witness screen, not a complete-registry or surface-before-placement audit. The root download stays disabled and the guide is conditional; quarantined candidates remain DO NOT SUBMIT. Their TIFF bytes were not modified by this follow-up.
- Added `docs/research/candidate-slate-2026-10-29.md` with three scoped proposals, feature layers/signatures, catalogue-missing rationale, mimics, bounded local novelty checks, relative cost and explicit data-availability status. Candidate 1 is a cross-spectral gravity–magnetic phase-coherence hypothesis; it remains proposal-only.

### Pass 2 — test and correct assumptions

- Removed outdated README wording that asked the owner to decide whether the lattice could be exempted. The current user protocol is explicit: literal any-registry overlap, no exemptions. Corrected the README's overbroad sentence about *all* dot detectors so it now describes only the measured coverage and proven bound for the named 37,654-dot budget; it does not imply that every conceivable sparse raster is mathematically impossible.
- Confirmed the user-facing home/summary do not expose a quarantined TIFF as an approved submission download. The gated download button remains disabled. Public leaderboard values remain historical context, never projected as a candidate score.
- Reviewed local modules for the candidate slate: checked the `src/gems32` and `src/karage3` source for cross-spectral operators, Landsat thermal stacks and 3DHP flowline-residual code. This is only a bounded repository scan; it is not a global sibling-project novelty claim.
- Verified source availability statements at official pages: USGS says current 3DHP products are available through downloads/services; USGS says Landsat 8–9 Collection 2 Level-2 surface-temperature products are available via EarthExplorer at 30 m under the no-cost open-data policy. Neither target-area coverage nor local acquisition was established; neither external-data candidate is marked viable.

### Pass 3 — recheck against the standing request

- After merging the updated `main` snapshot, ran the full Python unittest suite: **110 tests passed**; pytest: **205 passed, 1 skipped, 81 subtests passed**; Node dashboard tests: **4 passed**.
- Reproduced the refreshed saved-byte report with `python scripts/audit_saved_tiffs.py --fetch --cache /tmp/gems-inputs --verify-receipt evidence/saved-tiffs-literal-20261028.json`; all 13 current TIFF rows match the pinned hashes and stop on >70% overlap with the witness. This does not prove full-registry or pre-placement compliance.
- Ran `python scripts/build_preflight_site.py`, `python scripts/build_review_status.py`, `python scripts/build_release_review.py`, `python scripts/build_site.py --check`, `python scripts/verify_numbers.py` (26/26 consistency checks), and Python syntax compilation. Generated pages match their builders and show no authorized download.
- Ran a direct text/link/status check of root pages and release-review. Both quarantined candidate families appear only with explicit negative / **DO NOT SUBMIT** treatment; the H-GEO score remains visibly a copied, NOT ESTABLISHED candidate-card claim.
- Rechecked prerequisites before experimentation: the `feature_stack.npy` cache is absent; the complete current registry is unavailable; the method paragraph is not unambiguously assigned in this prompt; and shared-template defects remain open. Consequently no candidate can be validated by the required evaluator in this checkout. The top slate candidate was **not tested**, and no slot was touched.

## Nine-site executive decision

The supplied focus list still has the reported GEMSDOE32 item as the highest owner-reported historical score (0.2778), not an organizer-receipt-bound score. Its pruning of a related dense prediction set is a plausible false-positive-efficiency mechanism, but does not prove causality or predict a new score. The nine-site executive comparison remains at [`docs/focus9/index.html`](focus9/index.html); historical scores are marked USER-REPORTED / UNVERIFIED and all are research-only. No local file is cleared for submission.

## Blockers / next work

1. Restore organizer-authenticated competition inputs and the cached feature stack, with verified hashes and a reproducible receipt.
2. Have the central template owners repair and pin the required buffered whole-segment hide-and-recover, visible-only feature derivation, pixel-exact masking, pooled DTI/FP handling, surface uniqueness gate, and masked-footprint writer/validator; run upstream regression tests. Do not fork locally.
3. Resolve the lane ambiguity from the prompt's missing “single method paragraph,” then preregister only that lane. Keep the three-experiment/two-hour ceiling.
4. Only after blockers 1–3 and complete current registry inventory are satisfied: run one-feature leakage canaries, the spatially blocked holdout with the named evaluator/positive count/95% CI, surface and final-dot literal uniqueness checks, then saved-byte validation. A negative result is publishable; promotion requires the separate selector.
5. Keep both quarantined candidate families DO NOT SUBMIT. The one-witness audit is enough to reject them under the literal overlap rule; format validity or a copied holdout claim cannot authorize download/upload.

## Official manual-review sources

- [DrivenData problem, metric and data access](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — login is required for the competition data download in this environment.
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — official starter-code repository.
- [USGS Landsat 8–9 Level-2 archive](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-landsat-archives-landsat-8-9-olitirs-collection-2-level-2-science-products) — surface-temperature product details and access route; target scenes not retrieved.
- [USGS 3DHP data access](https://www.usgs.gov/3d-hydrography-program/access-3dhp-data-products) — downloadable products/services; target-area coverage not checked.
- [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — submission/process rules; local validation is not organizer acceptance.

Current machine-readable negative card: [`docs/data/run-card-20261029-review.json`](data/run-card-20261029-review.json).