# Follow-up repository review — 29 October 2026 UTC

## Decision: NEGATIVE — DO NOT SUBMIT

This follow-up did not generate a TIFF, run model experiments, claim a score, use a competition slot, or upload anything. It reconciles a contradictory README analysis and re-runs available checks against the checkout as it exists now.

## Correction made

The README previously asserted that GEMSDOE32's reported 0.2778 was caused by a specific pruning mechanism, that further pruning/off-catalogue targeting could beat it, and stated a candidate HOLDOUT-DTI 0.4239 as a result. Those claims overstated the available evidence. The text now labels the portal value USER-REPORTED / UNVERIFIED, treats the pruning explanation as a hypothesis only, and identifies the H-GEO-CONDUIT result as an unreproduced candidate-card claim—not a leaderboard estimate or submission approval. The current negative gate remains decisive.

## Verification performed

- `npm ci`: passed; 39 packages installed, audit reported zero vulnerabilities (npm's transitive deprecation warning noted).
- `npm test`: passed, 4 tests.
- `node --check assets/site.js`: passed.
- `python -m compileall -q scripts src tests`: passed.
- `git diff --check`: passed.
- `python -m pytest -q`: could not run because `pytest` is not installed.
- `python -m unittest discover -s tests -q`: not a valid substitute for pytest in this repository; failed imports because Python scientific packages (`numpy`, `rasterio`) and `pytest` are absent. It also encountered test expectation failures. No Python-suite pass is claimed.
- `python scripts/build_site.py --check`: failed closed with `ValueError: Saved-byte audit is stale or does not reject every retained TIFF`. The saved-byte report lists 9 TIFFs while 13 TIFFs currently exist under `docs/`; newer/extra artifacts have not been included in that evidence. This is a material publishing/release blocker; do not bypass the audit check or call the site build verified.

The earlier `docs/review-2026-10-29.md` test counts refer to the environment and files tested at that time. They do not override the current check results above.

## Findings and next actions

1. Reconcile every retained TIFF against a complete, hash-bound literal uniqueness audit, including the 4 present TIFFs not covered by `evidence/saved-tiffs-literal-20261028.json`. Re-run the audit only with a documented evaluator/protocol and current complete registry; do not infer duplicate status from missing records.
2. After updating evidence, run `python scripts/build_site.py --check` and Python tests in a provisioned environment from `requirements.txt`/`requirements-audit.txt`; retain fail-closed behavior meanwhile.
3. Maintain the negative decision. No archive TIFF is authorized for download/submission, and no score estimate is supported.
4. No new experiment is appropriate: the method lane remains unassigned, the shared methodology/data/cache gates remain unresolved, and prior experiment-budget status is not superseded by this review.

## Review run card

```json
{
  "hypothesis": "No new candidate tested; the README score-causality narrative was unsupported and corrected.",
  "mechanism": "Pruning may alter the false-positive/coverage tradeoff under a distance-weighted metric, but available historical data do not prove causality.",
  "named_non_fault_process": "Lithologic contacts and survey artifacts can mimic potential-field structures; not applicable to a new experiment because none was run.",
  "holdout_dti": {
    "evidence_class": "HOLDOUT-DTI",
    "evaluator_version": null,
    "withheld_positives": null,
    "value": null,
    "ci_95": null,
    "status": "NOT RUN"
  },
  "correlation_overlap_vs_registry": {
    "surface_spearman": null,
    "surface_dot_overlap": null,
    "final_spearman": null,
    "final_dot_overlap": null,
    "status": "No new surface or dots; stale registry audit coverage prevents release certification."
  },
  "raster_sha256": null,
  "validator_output": {
    "no_nan_inside_footprint": null,
    "values_in_0_1": null,
    "crs_shape_transform_match": null,
    "status": "No new TIFF. Existing saved-byte audit is incomplete for current docs/ TIFF inventory."
  },
  "submission_name": null,
  "note": "No approved TIFF; historical/candidate artifacts remain research-only.",
  "verdict": "negative"
}
```
