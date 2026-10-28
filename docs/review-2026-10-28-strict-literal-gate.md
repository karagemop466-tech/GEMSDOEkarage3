# Three-pass repository review: strict literal duplicate gate

**Decision: NEGATIVE — do not download or submit any TIFF from this repository.** This review ran no new geological experiment, emitted no new candidate TIFF, did not select a competition slot, and made no claim of an organizer-confirmed score. The existing H-K3C TIFF is retained as a historical research artifact.

## Pass 1 — inspect evidence and correct the release decision

The repository contained contradictory current-status claims. `README.md`, `docs/index.html`, `docs/executive-summary.html`, and `docs/current-gate-decision.json` described the archived H-K3C file as `PROMOTE / OK TO SUBMIT`. The root preflight content simultaneously stated that no file was ready. The H-K3C card itself recorded `literal_all_rasters_final_passed: false` and `null_calibrated_all_rasters_final_passed: true`.

The old gate allowed the null-calibrated excess-overlap metric to override a literal overlap above 70%. That conflicts with the strict parallel-run protocol in this request, which applies the literal >70%-within-3-px stop to any registry raster. The gate now rejects literal overlaps above 70% (including lattice/blanket rasters); null-calibrated values remain diagnostics only. It also requires an explicit raw `literal_overlap_3px` value for each final-dot registry comparison and checks that the recorded maximum matches those rows.

Applying the revised gate to the saved H-K3C run card produces `negative`, `ok_to_submit: false`. The historical card, TIFF and older results are not altered; they are not valid authorization under the strict rule.

## Pass 2 — identify edge cases and add regression coverage

- Added tests proving that a null-calibrated pass cannot override literal failure, that any literal overlap above 0.70 blocks promotion, and that missing final-dot literal overlap measurements fail closed.
- Kept surface rank-correlation checks and complete-inventory/hash binding requirements. The screen assesses supplied card content; it cannot authenticate a registry inventory or prove source provenance.
- Rebuilt the generated pages from the same gate so the landing page, executive summary and gate JSON no longer advertise the archived TIFF as approved.
- Updated the README and `AGENTS.md` to make the strict literal rule operative. Historical H-K3C values remain labeled as HOLDOUT-DTI; they are not projections of a future leaderboard score.

## Pass 3 — check the complete request and remaining blockers

No new raster was written because the archived H-K3C candidate already violates the specified duplicate gate; creating a variant or placing points in lattice holes would bypass the rule rather than establish uniqueness. Current `.cache/gems_work` feature arrays are absent from this checkout, as is a current complete registry snapshot sufficient for a fresh candidate scan. The readiness report also records no independently authenticated organizer data or same-session baseline. Therefore this review cannot produce a new HOLDOUT-DTI, 95% CI, score estimate, or approved downloadable TIFF.

### Historical numbers, accurately labeled

- **HOLDOUT-DTI** — `GEMSDOE32-HIDE-RECOVER-v3.1-24cell`, 66,904 withheld positives, 0.111044 [0.098990, 0.122727] for the archived H-K3C experiment. This is not an organizer score or estimate.
- **Literal registry audit** — the archived run card recorded a maximum final-dot literal overlap of 1.0 (100%) against a registry raster, exceeding the 70% limit. Its null-calibrated worst identifiable excess of 0.689103 is a diagnostic and does not change the result.
- **Raster SHA-256** — archived H-K3C bytes: `0d1461e8786d99da06182b196af0fc40cf03220dc76126e83623e218516429df`. The historical format check passed, but format validity does not override the duplicate stop.
- **Leaderboard values** — the values in the prompt are user-reported snapshots. No submission-page receipt or current authenticated leaderboard was obtained in this review; no new score is confirmed.

## Next steps

1. Restore and hash-check the canonical feature cache and an explicitly scoped, fresh registry, including continuous surfaces and dense/blanket rasters.
2. Preserve the strict literal 0.90 correlation / 70% three-pixel limits unless the user explicitly revises them. Do not use uncovered lattice cells as a loophole.
3. Before another experiment, reconcile the shared holdout evaluator's known catalogue-fragment bias and reproduce a matched incumbent with whole-segment buffered, visible-only feature construction.
4. Run no more than three preregistered experiments. Test every feature alone for leakage, report paired spatial HOLDOUT-DTI with evaluator version, withheld count and 95% CI, then check uniqueness before placement and on final dots.
5. A separate selector must verify the current weekly cap; only an exact-byte candidate passing every gate may be considered for submission. Capture an organizer receipt before labeling any result ORGANIZER-CONFIRMED.

Official references requested for review: [competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), and [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). Links identify the official sources but are not evidence that their current contents or the organizer account were authenticated in this review.

## Verification

- `pytest`: 168 passed, 1 skipped (optional cache integration unavailable), 49 subtests passed.
- `unittest`: 109 passed.
- Dashboard Node tests: 4 passed; browser-feed Node tests: 2 passed.
- Generated-site consistency check and `git diff --check`: passed.
- These are software checks, not new geological validation or organizer scores.

## Run card

The machine-readable companion is [`evidence/review-run-card-strict-literal-20261028.json`](../evidence/review-run-card-strict-literal-20261028.json). It records a negative result, no new experiment and no new submission name.
