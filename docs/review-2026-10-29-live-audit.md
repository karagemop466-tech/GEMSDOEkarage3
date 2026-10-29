# Repository review follow-up — live checkout audit (2026-10-29 UTC)

## Decision: **NEGATIVE — DO NOT SUBMIT any retained TIFF**

This follow-up re-ran the repository's negative-only saved-byte audit against every TIFF currently under `docs/`. It generated no candidate and ran no model experiment. The report is [`evidence/saved-tiffs-literal-20261029.json`](../evidence/saved-tiffs-literal-20261029.json), SHA-256 `a157006d513ac7a56fd95166f8fa304a3232b5efe80a372e2217f55ae1143a99`.

### What the audit establishes

- **13 TIFFs** are checked in under `docs/` at this checkout. Every one has `duplicate_stop: true` against the one hash-pinned lattice witness: 3-pixel overlaps range from **99.3387% to 99.9225%**. The user's literal threshold is greater than 70%, so every saved artifact is stopped by this witness alone. This is a sufficient negative result, not a complete registry scan; it does not claim the candidates are geologically identical.
- The newly present H-GEO-CONDUIT zero and NaN variants each have **99.8287%** overlap with the witness. The `karage3-unique-offcat` zero and NaN variants each have **99.8893%**. Their names do not establish uniqueness.
- All 13 entries report `strict_format_gate_pass: false`. This local format gate combines template/grid, footprint, and outside-footprint rules. The output is **not** an organizer validation receipt, and this report does not independently attribute the earlier portal's [0,1] error. A failed strict-format gate and a duplicate stop are independent reasons not to submit.
- This single-witness audit does not check rank correlation for continuous candidate surfaces before placement, a complete registry, a valid holdout, a current leaderboard, or account submission quota.

The report's template and lattice are hash-pinned owner mirrors, not organizer-authenticated competition inputs. The audit can reject against that supplied witness, but it cannot establish competition acceptance or support any score claim.

## Test and build verification — current environment

The first test attempt could not run because the base Python had no `pytest` or geospatial/scientific dependencies. I created the ignored project virtual environment and installed the declared `requirements.txt` dependencies. Then:

- `.venv/bin/python -m pytest -q`: **12 failed, 185 passed, 1 skipped, 80 subtests passed**.
- `.venv/bin/python scripts/verify_numbers.py`: **21/22** evidence consistency checks passed; it fails because its retained-TIFF inventory is stale and does not include the four newly present files (two H-GEO-CONDUIT variants and two `karage3-unique-offcat` variants).
- `.venv/bin/python scripts/build_site.py --check`: **fails closed** because `scripts/build_k3c_site.py` rejects the stale saved-byte receipt when the current `docs/**/*.tif` set differs from that receipt.

These failures are real and must not be hidden as passing checks. Several of the test failures are related to contradictory/stale artifacts: `tests/test_karage3_deliverables.py` still asserts the historical CSST-BGHF lane card as a deliverable while the current README and current decision cards supersede it; other tests and generators expect an earlier TIFF inventory. One accessibility test also finds a site table wrapper lacking `role="region"` and `tabindex="0"`. This follow-up does not rewrite historical source receipts or revise the shared evaluator as a shortcut.

## Required engineering work before this repo is release-ready

1. Make a single authoritative, dated artifact inventory (including every TIFF and ZIP) and bind the public decision pages to that receipt. Preserve old audit files as historical records rather than silently rewriting their date/scope.
2. Reconcile and quarantine superseded candidate artifacts or clearly mark them research-only; add regression tests that fail if any TIFF link can be misread as approved for upload.
3. Migrate or remove stale CSST-BGHF-era test expectations only after preserving provenance and accurately testing today's fail-closed status. Fix the table-wrapper accessibility failure.
4. Run the full unit, browser, feed, evidence, and deterministic site-build suites sequentially after the reconciliation. Do not claim a clean release before all checks pass.
5. Keep the required central-template, authenticated input/cache, complete registry, surface-stage literal uniqueness, and corrected holdout blockers from [`review-2026-10-29.md`](review-2026-10-29.md). A local cleanup does not clear them or authorize a submission slot.

## Scope and limitations

No competition data, public leaderboard, submission portal, account quota, or organizer receipt was accessed in this follow-up. No new HOLDOUT-DTI or score estimate was produced. The supplied scores remain user-reported/unverified. The negative audit is about saved TIFF bytes versus one registry witness only.

## Run card

```json
{
  "hypothesis": "No new geological hypothesis was tested; this was a saved-artifact integrity review.",
  "mechanism": "The negative-only audit compares each retained TIFF's positive support with a pinned calibration-lattice witness using the literal 3-pixel overlap rule.",
  "named_non_fault_process": "A calibration lattice is a non-geological placement pattern and can trigger the protocol's geometric duplicate stop without implying geological similarity.",
  "holdout_dti": {
    "label": "HOLDOUT-DTI",
    "evaluator_version": null,
    "withheld_positives": null,
    "value": null,
    "ci_95": null,
    "status": "NOT RUN; no experiment"
  },
  "correlation_overlap_vs_registry": {
    "surface_spearman": null,
    "surface_dot_overlap": null,
    "final_spearman": null,
    "final_dot_overlap": {
      "min": 0.9933871567429755,
      "max": 0.9992249174680637,
      "threshold_exceeded": true,
      "witness_scope": "One pinned lattice witness only"
    }
  },
  "raster_sha256": null,
  "validator_output": {
    "no_nan_inside_footprint": "per-file details in saved-tiffs-literal-20261029.json",
    "values_in_0_1": "per-file details in saved-tiffs-literal-20261029.json",
    "crs_shape_transform_match": "per-file details in saved-tiffs-literal-20261029.json",
    "strict_format_gate_pass": false,
    "organizer_receipt": false
  },
  "submission_name": null,
  "note": "No TIFF approved; all retained TIFFs are research-only and must not be submitted.",
  "verdict": "negative"
}
```
