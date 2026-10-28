# Follow-up: literal two-stage registry guard

**Verdict: negative; no new TIFF, holdout experiment, or competition submission.**

## Pass 1: review and implement
This checkout inherited mutually inconsistent release claims. The older SMGC
[evidence card](../evidence/hk3_smgc_run_card.json) records literal final-registry
failure, even though a filtered subset was called a pass. The prior local gate
only checked dot overlap at the final stage, although the parallel-run protocol
requires both checks at both stages. The local screen now requires per-reference
three-pixel overlap as well as rank correlation at the surface and final stages,
consistent maxima, a complete nonempty inventory and a registry manifest digest.
It still cannot independently verify a self-reported inventory or selection.

## Pass 2: edge cases and integration
A parallel session merged [its review](review-2026-10-28.md) into main during this
work. It retired the inconsistent public pages and disabled the unsafe legacy
runner. Integrated that work on this branch; retained the historical rasters and
original evidence. Added tests for a missing or above-threshold surface overlap,
missing manifest digest, and threshold boundaries in both stages. Added
`node_modules/` to the ignore file so dependency installation cannot accidentally
enter the patch. No template evaluator or writer was privately forked.

## Pass 3: verification and remaining work
The independent [nine-site review](../research/2026-10-27-review.md) includes
four research ideas and a historical B2 lineage analysis. Claims of higher
scores or organizer acceptance remain unproven. This session did not establish
an assigned method paragraph, official input provenance, a current complete
registry, a matched holdout baseline, or a candidate. A registered lattice
also blocks the illustrated historical dot budget under the literal rule.
The [upstream evaluator issue](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37)
remains open; the main evaluator CLI still binarizes positive values.

Local results after integration: `pytest`: 96 passed, 1 skipped (missing optional
SMGC cache), 49 subtests passed; `npm test`: 3 passed; browser feed: 2 passed;
root site build check passed. These are engineering checks, not scientific
validation. Restore allowed data, resolve the lane and literal registry policy,
fix the shared template, then rerun feature canaries, matched hide-and-recover,
complete two-stage registry audits and saved-byte checks. Use a separate selector
before any weekly slot; no such selector ran here.

A second concurrent integration advanced main while the pull request was open.
After incorporating it, re-ran the suite: 100 pytest passed, one optional-cache
skip, 49 subtests passed; 57 unittest cases passed; four dashboard and two feed
Node tests passed. The review-status generator was rerun to reflect the stronger
gate; these remain software checks, not a new geological result.
