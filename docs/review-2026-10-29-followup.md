# Follow-up repository review — 29 October 2026 UTC

## Decision: NEGATIVE — DO NOT SUBMIT

This follow-up made no model experiment, did not generate a TIFF, did not evaluate a holdout, and did not use a competition slot. It corrected an unsafe user-facing inconsistency found during review.

## Critical finding and correction

The root `index.html` and `executive-summary.html` previously advertised a bundled `karage3-unique-offcat` raster as “READY TO DOWNLOAD” and “submission-ready,” with a target score claim. That claim was not supported by the current gate: `docs/current-gate-decision.json` says `verdict: negative`, `ok_to_submit: false`, and `selector_approval: false`. The root-page claims also relied on comparison with the nine focus-site files, which does not establish uniqueness against the complete registered raster set required by the project protocol. The artifact had no validated same-protocol HOLDOUT-DTI score; “Target > 0.2778” was not an estimate.

Correction made:

- Replaced both root pages with an explicit no-submit decision, no candidate download links, accurate distinction between historical reports and confirmed scores, and a safe checklist for any future authorized submission.
- Removed the unapproved `karage3-unique-offcat` TIFF/ZIP/metadata bundle from `docs/downloads/` so the previously advertised artifact cannot be downloaded from the repository.
- Added standard-library regression tests asserting the public pages do not relist that candidate or claim readiness and that the release decision remains negative.

The candidate was not independently proven to be unique, format-valid, or performant in this follow-up. Its removal is a conservative safety action, not a claim about the exact raster's scientific properties.

## Validation and limitations

- `python -m unittest tests.test_submission_safety -v`: expected to run independently with the standard library (record final execution result in the session summary).
- `.venv/bin/python -m unittest discover -s tests -q`: 107 passed.
- `.venv/bin/python -m pytest -q`: 199 passed, 1 skipped, 78 subtests passed; 56 rasterio pending-deprecation warnings. The skip depends on an optional absent evidence/cache path.
- `npm ci --no-audit --no-fund && npm test`: 4 passed. `node_modules/` is ignored and not committed.
- `python scripts/build_site.py --check`: passed after the root templates were replaced with the safe no-submit pages and the builder was changed to fail closed if a template lacks the negative status or links to the removed candidate. The build still validates its pinned historical evidence; this does not validate a TIFF for organizer submission.
- `python tests/test_submission_safety.py -v`: 3 passed.
- `node --check assets/site.js` and `git diff --check`: passed. No current holdout or new candidate is claimed.

## Follow-up actions

1. Keep the root templates and builder fail-closed checks in sync; preserve regression coverage against stale approval claims.
2. Establish authenticated competition data and the canonical feature cache; fix shared holdout/writer issues centrally and freeze a same-evaluator baseline.
3. Obtain a complete current registry and run surface and final-dots literal overlap/correlation gates.
4. Only after all scientific, uniqueness and byte-level gates pass, use a separate selector against the live weekly limit. Bind any organizer-reported score to the receipt and exact raster hash.

## Run card

```json
{
  "hypothesis": "No candidate tested in this follow-up; review found an unsafe stale approval claim in the public pages.",
  "mechanism": "Not applicable; no geological candidate was produced.",
  "named_non_fault_process": "Not applicable; no new raster or fault detector was tested.",
  "holdout_dti": {"label": "HOLDOUT-DTI", "evaluator_version": null, "withheld_positives": null, "value": null, "ci_95": null, "status": "NOT RUN"},
  "correlation_overlap_vs_registry": {"surface": null, "final_dots": null, "status": "NOT RUN; no candidate"},
  "raster_sha256": null,
  "validator_output": {"no_nan_inside_footprint": null, "values_in_0_1": null, "crs_shape_transform_match": null, "status": "NOT RUN; no candidate"},
  "submission_name": null,
  "note": "No candidate. Do not submit any repository TIFF without current explicit approval.",
  "verdict": "negative"
}
```
