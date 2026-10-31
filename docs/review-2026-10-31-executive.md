# Review — 2026-10-31 (branch `arena/86c0d3ae-gemsdoekarage3`)

Status: **no file cleared. OK to download and submit: NO. Weekly slots used: 0.**
Executive summary: `docs/executive-summary-20261031.html`. Step-by-step (blocked): `docs/submission-20261031.html`.
Run cards: `evidence/run-card-20261031.json` (session) and `evidence/run-cards-20261031/<KEY>.json` (per candidate, gate schema).

Labels: **HOLDOUT-DTI** = shared evaluator, with withheld count and 95% cluster-bootstrap CI. **USER-REPORTED** = copied from the request, no organizer receipt. **PROJECTION** = in-sample fit (N = 9), not a score. **ORGANIZER-CONFIRMED** = none exists.

## Passes

### Pass 1 — implement
- Nine-site receipts re-run: `evidence/focus9-reeval/`, format `evidence/session-20261031/format/`, pairwise uniqueness `…/uniqueness-nine/`.
- Three candidates built with pre-registered rules (`scripts/build_colocation_candidate.py`, `…_expanded_…`, `scripts/build_strain_signchange_candidate.py`). H1 needed amendment A1 (budget reduced to the NMS count) recorded before any holdout run.
- Holdout, random controls (`scripts/random_budget_control.py`), uniqueness vs nine plus lattice, summary and submission generators (`scripts/build_executive_20261031.py`), landing-page link (`site/index.template.html`, `scripts/build_k3c_site.py`).

### Pass 2 — review (what failed and was fixed)
- Pytest: 5 failures from saved-byte receipts not covering the TIFFs under `docs/`. Fixed by regenerating `evidence/saved-tiffs-literal-20261028.json` (`audit_saved_tiffs.py --fetch`) and `…-20261030.json` (`update_saved_tiffs_receipt.py`).
- **My own error in pass 2:** a cleanup `rm -f docs/quarantine/*/*-zeros.tif` matched every quarantine folder and deleted five tracked files from earlier sessions. Restored with `git checkout`. Receipts were then regenerated; the regression test `test_prior_zeros_quarantine_files_still_present` guards this.
- After restore, 4 failures remained: `build_run_card.py` rebinds the card hashes (`docs/data/current-run.json`); the release-review rebuild is deterministic after that. `verify_numbers.py` now 53/53.
- Final test status: pytest 241 passed, 1 skipped; `unittest discover` OK; `npm test` and `node --check docs/dashboard.js` OK; `docs/*.json` parse OK.

### Pass 3 — re-check against the gate
- The first run-card schema did not match `scripts/promotion_gate.py` (it reads `holdout`, `registry`, `elapsed_seconds`, a `validator` dict, and `experiments_run` 1–3). The cards were rebuilt to the gate schema, with values taken from receipts. Unmeasured items are `null` or `complete: false`, so the gate reports them as missing and does not infer them.
- Gate result for all three: **negative**, `ok_to_submit = false`. Verbatim reasons in `evidence/run-cards-20261031/<KEY>.gate.json`. The lattice duplicate is among the reasons, which is the correct stop.

### Pass 4 — claims check
- Every number on the summary and submission page comes from a receipt or from the generator's reading of one. Hand-entered values: the nine USER-REPORTED scores and the leaderboard snapshot (labelled PUBLIC-PAGE-SNAPSHOT, fetched 2026-10-31).
- Claims corrected during the pass: "0.98–1.00" pairwise → "0.976–1.000"; "GEMSDOE24/25/30 share one dot support" → 25 and 30 identical; 24 is within 3 px of 25 but not an exact subset; "binary 0/1" removed (not verified); evidence links changed to GitHub URLs, because only `docs/` is published.
- The "13 retained TIFFs" count in the root `index.html` aside is stale (receipts cover 40). Flagged, not edited.

## Answers

**Why GEMSDOE32 (0.2778, USER-REPORTED) scored highest.** Verified facts only:
- It keeps the fewest dots near the catalogue: 5.77% within 3 px, against 19.5–19.9% for GEMSDOE24/25/27/30.
- Catalogue-withheld HOLDOUT-DTI 0.0045 [0.0038, 0.0053]: below random placement (0.030–0.033 at 37,654 dots).
- Off-catalogue SGMC-cal HOLDOUT-DTI 0.0641: second highest of the nine (GEMSDOE36 0.0644).
- Across the nine, reported score vs SGMC-cal ρ = +0.950; vs catalogue-holdout DTI ρ = −0.849. N = 9, descriptive.
- Interpretation (judgement): the competition's test faults are reported to lie outside the public catalogue, so a file that avoids the catalogue while still covering off-catalogue structure should score better on the organizer's set. This matches the ordering. It is not proven.

**Can a higher score be reached?** Not with anything tested today. The bar is SGMC-cal above 0.0644. Random placement at 37,654 dots reaches 0.047–0.049. The three candidates did not clear it (H1 0.0252 at 12,177 dots; H2 0.0016 at 5,660; H1-expanded 0.0167 at 37,654).

**Leaderboard.** Public page, fetched 2026-10-31: #1 xiaofanhu 0.4544; #2 cfld__ 0.3934; #3 Batik Shirt Brothers 0.3917; #47 0.3244; #50 0.3195. 0.4413 is not in the top 50. The request's "high" conflicts with the page; confirm the figure you cite.

## Ranked hypotheses for the next session (not tested; ranked by expected DTI gain per cost)
1. **H3 — visible-catalogue annulus at 300–1,000 m** (not on the trace). Layers: `labels.tif`, visible-only inside the holdout. Target: off-catalogue faults parallel or en-echelon to mapped traces. Mimic: mapping-density bias toward populated areas. Cost low.
2. **H4 — basement-step × conductivity contrast** (`depth_to_base_surf` × `cond_surf` gradients). Mimic: sediment-thickness changes at alluvial-fan and playa margins. Cost moderate. Layers already appear in other lanes, so the novelty is the combination, and this has not been checked against the registry.
3. **H5 — dilatation sign-change without the shear weight**, as a diagnostic: does H2 fail on its weighting or on the signal? Cost low. Not a candidate.

GEODAWN radiometric layers are already used in several prior lanes (`scripts/build_novel_surface.py`, `src/gems32/crsb_gub.py`, `fbgr.py`, `smgc.py`, and others), so they are not presented as new.

Each hypothesis must be pre-registered, avoid SGMC as an input, beat the nine-site best and the budget-matched random controls on the SGMC-cal measure, and pass the canary, surface, and full-registry checks before any slot is considered.

## Irregularities
- IR-26-01 Leaderboard values in the request (0.3195 is #50; 0.4413 not in top 50).
- IR-26-02 Zeros-outside GEMSDOE30/32/33/36 fail the official NaN rule; the 0.2778 file is zeros-outside. Whether the portal accepted it is unverified.
- IR-26-03 "Predicted values must be in range [0, 1]" not reproduced; the uploaded file is unknown.
- IR-26-04 Literal uniqueness is unsatisfiable for footprint-spanning files (lattice covers 99.87% of the footprint within 3 px; `evidence/lattice-bound-20261030.json`, re-run today).
- IR-26-05 Nine files are not unique among themselves (pairwise 0.976–1.000). 25 and 30 have identical positive support; every 24 dot is within 3 px of a 25 dot.
- IR-26-06 Mirror `sample_submission.tif` has the labels' 60,988 positive cells; the official page says it predicts total absence.
- IR-26-07 Training and external rasters come from owner-supplied GitHub mirrors of login-walled files. Integrity-pinned, not organizer-authenticated; redistribution terms unconfirmed.
- IR-26-08 `src/gems32/holdout.py` and `submission.py` differ from the pinned template; `scripts/evaluate_holdout.py`'s docstring says it delegates "strictly to gems32.holdout (no private fork)". AGENTS.md prohibits private forks. Not reconciled.
- IR-26-09 H1 (12,177 dots) and H2 (5,660 dots) are much smaller than the nine-site files (37,654–61,328), so their holdout comparison is confounded; budget-matched controls address this in part.
- IR-26-10 My cleanup error (described above). Restored from git.
- Also open from earlier sessions: four `-nan.tif` files remain in `docs/downloads/` though one review says three were moved; `.cache/gems_work/feature_stack.npy` absent; `data/restore_receipt.json` storage root disagrees with `scripts/restore_core_data.py`; review cites #2/#3 scores 0.3916/0.3911, the fetch shows 0.3934/0.3917.

## Remaining work
1. Owner decisions: uniqueness scope; zeros vs NaN outside; the exact portal message and uploaded file; organizer receipts.
2. Leakage canaries (single feature, AUC > 0.90) for the three candidates and for the nine.
3. Paired holdout test against the same-evaluator best; elapsed time per candidate.
4. Surface-before-placement uniqueness and a complete registry inventory (the current check covers 10 known rasters).
5. Protocol audit of the shared evaluator; reconcile `src/gems32` with the template.
6. Hypotheses H3 and H4, pre-registered, with the gates above.

## Limitations
- The holdout is a local proxy with a catalogue-withheld design. It is not the organizer's test set, and its agreement with the leaderboard is N = 9.
- The new candidates were limited by the 3-experiment budget.
- No portal response, organizer receipt, or leaderboard score exists for any 2026-10-31 file.
- The reported-score projection is in-sample and must not be quoted as a score.
