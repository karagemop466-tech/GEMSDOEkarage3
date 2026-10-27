# Pinned upstream inspection snapshot

`manifest.json` records immutable GitHub URLs and SHA256 for every recovered file. These files are unchanged copies from GEMSDOE32, not authored or privately patched here. They are **third-party tools**, not official organizer code. Core data provenance remains owner-mirrored, not organizer-authenticated.

- `scripts/evaluate_holdout.py` delegates to `src/gems32/holdout.py`.
- `scripts/submission_writer.py` delegates to `src/gems32/submission.py`.
- `scripts/restore_data.py` supplies the actual core restoration used by our wrapper.
- `src/gems32/submission.py::audit_geotiff` is the unchanged validator used to reopen all historical artifacts and the synthetic test fixture.
- `registry/feature_receipt.json` describes an upstream 35-channel cached stack; it is **not the cached array**.
- `registry/focus_registry_manifest.json` is a historical 416-raster inventory; it is not proof of current completeness or surface coverage.
- The `vendor/` files were inspected as an alternate upstream shared-template implementation; they are not used to evaluate anything in this session.

## Important API constraints discovered

The path-based `evaluate_path` converts input to `isfinite(arr) & (arr > 0)`. The writer's `write_validated_submission` also passes a positive-input binary mask to `write_submission_pair`. They are suitable for binary dot patterns, **not probability-preserving evaluation or writing**. Passing a mostly positive calibrated probability raster would turn most of it into dots. No continuous model was run here, and these behaviors were not privately changed.

The canonical writer sanitizes/clips inputs. A future model must validate raw predictions separately rather than use sanitization to hide bugs. The validator's historical constants require the 3730×3292 competition grid and 5,167,373-pixel footprint, even with a supplied template; it is not a generic arbitrary-grid validator.

No shared-tool defect affecting the binary historical audit was found, so no upstream fix/private fork was introduced. Any change needed for a future continuous-probability lane belongs in the shared template, with tests and explicit provenance.
