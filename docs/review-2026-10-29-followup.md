# 29 October 2026 follow-up — stale audit scope and release status

## Decision

**NEGATIVE — DO NOT SUBMIT.** This follow-up changed repository documentation, release-page generation, and tests only. It ran no geological/model experiment, generated no TIFF, selected no weekly slot, and made no organizer upload. There is still no submission file approved for download.

The repository contains research-only TIFFs from earlier work. Do not confuse a saved artifact or a format check with release eligibility.

## Findings

1. The frozen `evidence/saved-tiffs-literal-20261028.json` review covers nine TIFFs that existed at the time of that dated audit. Four later TIFFs are now in the repo: `karage3-unique-offcat` (zeros/nan) and `gemsdoe32-karage3-h-geoconduit-hybrid` (zeros/nan). The old audit did not cover those four. A previous publisher and verifier incorrectly required that dated receipt to cover every file currently present, making the deterministic rebuild fail. It would have been unsafe to expand the audit's claims without the lattice bytes and a new complete audit.
2. The 12,000-pixel `karage3-unique-offcat` sidecar said “0%” versus focus-site dots and gave a theoretical lattice minimum. That is not full-registry uniqueness or surface-before-placement evidence. Its metadata is now explicitly marked negative / not established; its historical overlap note is not represented as a validated uniqueness pass.
3. The H-GEO-CONDUIT artifact has 35,615 positive pixels in its saved-byte sidecar. **GEOMETRY-AUDIT (not a score):** the pinned lattice witness has 6,649 footprint pixels outside its 3-pixel neighborhood. Thus at least 28,966/35,615 = 81.33% of any distinct in-footprint dots at that budget must be within 3 pixels of that witness, above the literal 70% stop. This is a necessary bound, not a complete registry audit.
4. The H-GEO-CONDUIT card's historical result remains only a claim: **HOLDOUT-DTI (run-card claim; not independently reproduced in this review) 0.423855**, 95% CI `[0.405253, 0.442747]`, evaluator `GEMSDOE32-HOLDOUT-v3-visible-gated`, 22,232 withheld positives. It is not organizer-confirmed, not a leaderboard estimate, and not established as comparable to the focus site's **0.2778 USER-REPORTED / UNVERIFIED** claim.
5. The current nine-site executive summary and dedicated pages already exist for GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, and 36. Their historical owner values are not backed by artifact-linked organizer receipts here; new leaderboard score estimates are not defensible.

## Changes made

- Rewrote README's current executive decision to remove assertive, unsupported causal claims; retained the standing reference prompt and added the focus-nine table, four ranked research hypotheses, verified limitations, and links to each site's executive summary.
- Updated the main public site and generated decision pages to put **NO APPROVED TIFF / DO NOT SUBMIT** first, keep the download button disabled, link to the current negative card and nine-site summary, and describe the archived H-GEO result with evaluator/count/CI and clear provenance.
- Updated saved-byte publishing so the 28 Oct receipt stays scoped to its nine actually audited files. The four newer files are explicitly listed as **not audited / NOT ESTABLISHED / DO NOT SUBMIT**, with file hashes; they are not linked as approved downloads. No fabricated re-audit was created.
- Updated the off-catalogue sidecar to withdraw its ambiguous uniqueness wording and record no estimate, no eligibility, and no submission approval.
- Updated regression tests and `scripts/verify_numbers.py` to catch future inventory/audit scope drift and to prove that newer artifacts remain unreviewed instead of being silently counted as uniqueness passes.
- The first GitHub CI run exposed one more date-scope bug: `audit_saved_tiffs.py --verify-receipt` compared the 28 Oct receipt to the entire current TIFF inventory and failed after the four later files appeared. Fixed receipt verification to compare all metadata and each frozen row exactly while separately reporting later rows as outside the receipt. Added regression tests so new files are surfaced as unreceipted and changed/missing historical rows still fail closed.

## Three-pass review

### Pass 1 — inspect

Read the project instructions, README, current and parallel run cards, current gate, focus-nine pages, dated saved-byte receipts, build scripts, and tests. Found four later TIFFs not covered by the dated 28 Oct receipt; the generated-site publisher failed closed on this mismatch. The original public page also pointed at stale lane-specific information and did not surface the most recent candidate card consistently.

### Pass 2 — correct

Kept the dated raster receipt immutable and narrowed claims to its actual nine files. Added an inventory for later files that labels them unreviewed and blocks submission. Reconciled the README and public decision pages with `docs/data/candidate-review-20261029.json`, surfaced the lattice lower bound, and corrected the off-catalogue metadata to negative status. No model code, evaluator, or candidate raster was changed.

### Pass 3 — verify

- `.venv/bin/python -m pytest -q --tb=short`: **200 passed, 1 skipped, 80 subtests passed**; rasterio emitted 56 pending-deprecation warnings.
- `.venv/bin/python -m unittest discover -s tests -q`: **105 passed**.
- `npm test`: **4 passed**; `node --test tests/test_browser_feed.js`: **2 passed**.
- `python scripts/build_site.py --check`: passed after deterministic rebuild.
- `.venv/bin/python scripts/verify_numbers.py`: **22/22 consistency checks passed**. This is a consistency check, not a score or slot decision.
- `git diff --check`: passed.

## Remaining blockers

1. No unambiguous method lane is assigned, and inherited experiment budget is already recorded as 3/3 used. No further run was started.
2. Competition inputs and the canonical feature cache are absent/authentication is unavailable in this checkout. Owner mirrors do not establish organizer provenance.
3. The shared whole-segment buffered holdout, visible-only catalogue feature derivation, surface uniqueness gate, and masked-footprint validator remain unresolved upstream. Do not implement private substitutes.
4. A complete current registry and its rasters are needed to test every candidate surface before placement and final dots. The four newer TIFFs must stay blocked until this is available.
5. An independent selector must verify eligibility and current weekly quota. There is no organizer receipt in this review.

## Run card — this follow-up

```json
{
  "hypothesis": "No geological hypothesis was newly tested. The planning slate remains the signed multiscale gravity–magnetic edge-displacement hypothesis, pending lane assignment and data/protocol access.",
  "mechanism": "No new model mechanism was executed; this turn corrected dated evidence scope and release controls only.",
  "named_non_fault_mimic": "Unfaulted lithologic contacts, dikes, remanent magnetization, and survey artifacts can mimic potential-field edge displacement.",
  "holdout_dti": {
    "evidence_class": "HOLDOUT-DTI",
    "value": null,
    "ci_95": null,
    "evaluator_version": null,
    "withheld_positives": null,
    "status": "NOT RUN — no new experiment; inherited cap is 3/3 and the shared evaluator protocol is blocked"
  },
  "correlation_overlap_vs_registry": {
    "candidate_surface_spearman": null,
    "candidate_surface_dot_overlap_3px": null,
    "candidate_final_spearman": null,
    "candidate_final_dot_overlap_3px": null,
    "status": "NOT RUN for a new candidate. Existing H-GEO-CONDUIT 35,615-dot budget has a GEOMETRY-AUDIT necessary lower bound of 81.33% overlap with one pinned lattice witness; the later 12,000-dot artifact lacks complete registry evidence."
  },
  "raster_sha256": null,
  "validator_output": {
    "no_nan_inside_footprint": null,
    "values_in_0_1": null,
    "crs_shape_transform_match": null,
    "status": "No new raster produced or validated in this follow-up; prior sidecar claims are not a current release validation."
  },
  "submission_name": null,
  "note": "No candidate is cleared; do not submit archived TIFFs.",
  "verdict": "negative"
}
```
