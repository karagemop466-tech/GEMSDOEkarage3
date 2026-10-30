# Repository review — 2026-10-30

## Executive result

**Negative submission decision: do not download or submit any retained TIFF.** This checkout has no authenticated competition data/cache, no complete current registry, and no assigned single-method lane. The existing samples are historical/research artifacts, not eligible candidates. The automated readiness report is the authoritative blocker list (`scripts/check_readiness.py`); it records `ready_for_experiment: false` and `ok_to_submit: false`.

No new geological experiment, TIFF, organizer submission, selector action, or weekly-slot use was performed in this review. Producing a file without the required method lane and complete evidence would violate the run protocol and falsely suggest readiness.

## What was reviewed and repaired

A full repository inventory, project landing docs, submission/release gates, TIFF audit artifacts, and test suites were reviewed. Newly retained consensus-hgrad TIFFs had not been included in two saved-byte inventories. This made the release-page builder refuse to run and caused its downstream consistency tests to fail. The audit receipts were refreshed against the pinned local template and lattice witness; the fresh run found both TIFF variants are duplicate-stops (within-3-pixel overlap 99.8897%), while the zeros variant also fails the outside-footprint convention. The refreshed report was linked by SHA-256 from the current run card, mirrored to `docs/data`, and included in the retained-submission inventory.

The audit is explicitly limited: the pinned template and witness are owner-supplied mirrors, not organizer-authenticated; the lattice is one witness, not the complete registry; and overlap alone can reject, never approve. No claim of geological novelty or full-registry uniqueness follows from this update.

## Readiness and known blockers

`python scripts/check_readiness.py` currently reports:

- no organizer-authenticated copies of training features, labels, existing faults, or sample submission;
- cached `.cache/gems_work/feature_stack.npy` absent;
- 0/416 pinned registry paths present in the required complete local registry;
- no current same-evaluator baseline rerun;
- unresolved shared evaluator defects/issues around buffering, false-positive pooling, leakage validation, and surface-stage overlap;
- no unambiguous lane assigned for this parallel run.

Therefore no valid holdout-DTI estimate can be made here, and no leaderboard-score projection is reported. Historical numbers in site pages are user-reported unless tied to an organizer receipt. The exact available number audit is in `evidence/` and labels the method/evaluator where applicable.

## Verification performed

- `.venv/bin/pytest -q`: **225 passed, 1 skipped** (56 upstream/deprecation warnings; 92 subtests).
- `npm test`: **4 passed**.
- `.venv/bin/python scripts/verify_numbers.py`: **33/33 consistency checks passed**.
- Fresh pinned-witness saved-byte audit: 20 TIFFs under `docs/` inventoried; all are negative/refused by duplicate or boundary-gaming rule. This is not a complete-registry uniqueness test.
- `scripts/check_readiness.py`: negative as expected; it is an advisory availability gate, not an approval.

## Next work, ordered by impact

1. Obtain competition data through an authorized DrivenData session (or exact organizer-provided files) and verify hashes against organizer downloads. Do not substitute a peer's mirror as official provenance.
2. Restore the *full* pinned registry and cached feature stack; confirm completeness, freshness, grid, and provenance before opening a candidate workflow.
3. Assign this session one exact method lane and use the shared template's evaluator/writer. Repair or obtain upstream fixes for the evaluator issues recorded by readiness; do not fork a private evaluator.
4. Run a frozen whole-segment spatial holdout with buffers, visible-only fold-local features, pooled DTI (alpha .2, beta .8, 300 m triangular kernel), and feature-alone leakage canaries. Compare against the same-evaluator baseline and publish withheld-positive count, evaluator version, and 95% CI.
5. Apply surface-stage and final-dot rank-correlation/overlap gates against the complete registry. Stop immediately at the protocol's duplicate threshold. Only after all gates pass may the separate selector consider a weekly slot; retain the exact organizer receipt.

## Core values

Maximize P(Win) by refusing unverified gains and preserving the ability to test a genuinely distinct candidate. Own the Outcome by keeping every blocker machine-readable, correcting stale evidence, and making a negative result visible rather than presenting a speculative TIF as a submission-ready artifact.
