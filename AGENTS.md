# Project starting point and safety rules

Read `README.md`, `docs/PROJECT_BRIEF.md`, the latest dated review in `research/`, and `docs/data/current-run.json` before work. Prior run cards are historical evidence, not authorization. Do not claim organizer confirmation without an artifact-linked receipt, present a historical TIFF as a new submission, or promote on format alone.

## Literal uniqueness is mandatory

The user's rule is **no exemptions**: stop if rank correlation with any registered raster exceeds 0.90 **or** more than 70% of candidate-support pixels are within 3 pixels of that raster, both before placement and on final dots. The local screen additionally rejects strong anticorrelation conservatively. A dense or synthetic lattice still counts. Null-calibrated excess is an optional diagnostic, never a substitute. `scripts/protocol_preflight.py` stops budgets of 22,164 or more because the pinned lattice proves a violation; this is a necessary bound, not proof that lower budgets pass. A new candidate needs complete, current, hash-bound registry measurements at both stages. The historical filtered registry fetcher cannot certify completeness.

## Shared tools and experiments

Use the centrally maintained template; do not privately fork or silently change its evaluator/writer. The shared surface gate and whole-segment buffered holdout have open upstream issues [#42](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/42) and [#60](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/60), respectively. The soft wrappers are also under review in [#37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37); related issues #39, #41, #51, #61, #62 and #63 should be resolved/rechecked centrally. This account has read-only access to that upstream repository. Do not run the historical experiment entry points until the template has been corrected, pinned and regression-tested; local entry points fail closed.

Do not choose a method lane without an unambiguous user assignment. Preserve the three-experiment/two-hour limit and run a separate selector only after the literal uniqueness, matched holdout, leakage and saved-byte format checks pass. No weekly slot without that selector. A local format diagnostic is not a portal receipt.

Historical K3C HOLDOUT-DTI and other prior numbers are un-reproduced claims. `evidence/saved-tiffs-literal-20261028.json` records the independent saved-byte audit against one lattice witness; `docs/k3c/run-card.json` is its corrected, explicitly superseded public copy. `evidence/k3c_run_card.json` retains the original historical card for provenance.
