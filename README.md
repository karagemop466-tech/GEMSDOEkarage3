# GEMS Fieldnotes

**Read this README, the [project brief](docs/PROJECT_BRIEF.md), and [current run card](docs/data/current-run.json) at the beginning of every session.**

An evidence-first workspace for the [DOE GEMS Prize Challenge](https://www.drivendata.org/competitions/306/competition-doe-gems/): map previously unidentified geological **faults** relevant to geothermal exploration. A fault prediction is not proof of a geothermal vent.

## Current decision: DO NOT SUBMIT

**There is no new candidate TIFF, no defensible estimated organizer score, and no authorized weekly slot.** The current request refers to a single assigned method paragraph, but does not provide one. Independent raster forensics also found a literal registry conflict: the registered 13GEMSDOE lattice makes any 37,654-distinct-dot candidate overlap it by at least **82.34%** within three pixels, above the requested 70% limit. This is a geometric bound, not a score; it does not prove all smaller budgets impossible. Do not optimize dots into the lattice holes to evade the test.

The best of the **user-reported, unverified** historical focus-site values is GEMSDOE32’s **0.2778**; no submission-page receipt here binds that value to the raster. It is already reported, not a new submission. All nine pinned historical files fail the focus-site proximity test. The [site](index.html) and [executive submission guide](executive-summary.html) put the decision and evidence up front. No competition submission was made.

## Mission and standing instructions

* **Maximize P(Win):** prioritize well-supported, generalizable fault discovery, responsible uncertainty, and conservation of weekly slots—not cosmetic hash changes or leaderboard guessing.
* **Own the Outcome:** make missing data, failed gates and negative results visible; independently check saved bytes and record provenance. No human inspection should be required to validate a future artifact; the protocol still requires a **separate** slot selector.
* Focus the executive comparison on GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36. Link historical files only as research references. Never recommend an already-submitted or unvalidated file as new.
* Stay in the explicitly assigned single method lane. Before placement and on final dots, stop if rank correlation exceeds 0.90 or more than 70% of dots are within 3 pixels of **any** registered raster. Missing/undefined comparisons do not pass. Do not silently exempt controls.
* Reuse the shared template feature stack, `evaluate_holdout.py` and `submission_writer.py`; do not create a private scientific fork. Hide whole segments with a buffer, derive catalogue-dependent features only from visible faults, mask visible faults pixel-exactly, and score pooled distance-weighted Tversky (α 0.2, β 0.8, 300 m triangular kernel). Run one-feature leakage canaries; AUC above 0.90 is leakage until resolved.
* Scientific values must be **HOLDOUT-DTI** with evaluator/version, withheld positives and 95% CI, or **ORGANIZER-CONFIRMED** from a submission-page receipt. Owner/user-reported historical values remain explicitly **unverified**, never mislabeled as confirmed. A projection is not a score.
* Pre-register three to five geological hypotheses, with specific layers, physical signature, why faults may be missing, non-fault mimics, distinctness and cost. Beat the same-protocol holdout best before a separate selector considers a weekly slot. Stop after three experiments or two hours; negative results are deliverables.
* End each run with a JSON card: hypothesis, mechanism, non-fault mimic, HOLDOUT-DTI and CI, surface/dot registry comparisons, TIFF SHA-256, exact-byte validator result, submission name and ≤140-character note, and promote/negative verdict. Missing evidence must be `null`, not invented.
* Run multiple passes: implementation and verification; bug/edge-case review; final requirement and reliability review. Use official, verifiable sources and flag what cannot be checked. The user requested a PR and merge onto main once work is verified.

The [project brief](docs/PROJECT_BRIEF.md) preserves the user's detailed request and unverified historical inventory, with repeated sections consolidated. The [research slate](docs/research-notes.md) includes four **unrun** proposals. The [source register](docs/data-sources.md) distinguishes official data, owner mirrors and inaccessible inputs.

## What this checkout actually contains

* A GitHub Pages dashboard, submission guide, research slate and source register. The browser checks public GitHub repository heads for changes; it does **not** scrape DrivenData, recompute scientific evidence or update organizer scores.
* An independently reproducible [nine-file/lattice forensic audit](docs/data/historical-audit.json). It uses pinned owner-repository bytes and records all 72 directional comparisons and a single-lattice witness. It is **not** a complete registry or a holdout evaluation.
* A [read-only TIFF auditor](scripts/validate_raster.py) that checks the exact bytes without clipping; it reports the conservative template-null and whole-array-finite conventions separately. Neither result proves organizer acceptance or a weekly-slot authorization.
* A wrapper that executes the **unchanged, hash-pinned shared restorer**. During this session it restored four core owner-mirrored rasters and verified their hashes; [receipt](evidence/core-data-mirror-receipt.json). The large data stay in an ignored, ephemeral cache. They are not authenticated copies from DrivenData. The shared cached derived feature stack is absent.
* No trained model, new geological experiment, new submission TIFF, feature-canary result, holdout score, complete registry, authenticated organizer receipt or personal quota.

### Shared-tool warning

At the pinned GEMSDOE32 revision, its local CLI `scripts/evaluate_holdout.py` and `scripts/submission_writer.py` silently turn continuous positive probabilities into booleans. This does not preserve the organizer's continuous metric. [Upstream issue #37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37) is already open. The separately vendored shared evaluator accepts continuous values. This account has read-only access to that repository, so the shared bug was not fixed here and no private fork was created. See [research notes](docs/research-notes.md#critical-implementation-irregularity).

## Reproduce the audit (no submission slot needed)

Python 3.11+, `gh`, and network access to GitHub are needed. Never commit large data or credentials. The restorer uses the existing GitHub authentication if configured; the files are public mirrors, not official-authenticated data.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/restore_mirror.py             # ~419 MB of ignored, hash-checked core mirrors
python scripts/audit_historical.py            # pinned historical TIFFs + lattice → JSON
python scripts/build_run_card.py              # bind the zero-experiment negative card to that audit
python scripts/preflight.py --dots 37654      # exits 1: duplicate-stop; 2 means inconclusive, never approval
python scripts/build_site.py                  # regenerate snapshot-backed pages
python scripts/build_site.py --check
python -m pytest -q
```

A real candidate can be checked independently without modifying it:

```sh
python scripts/validate_raster.py candidate.tif --template .cache/competition-mirror/sample_submission.tif
# Optional whole-file range diagnostic, NOT proof of organizer acceptance:
python scripts/validate_raster.py candidate.tif --template .cache/competition-mirror/sample_submission.tif --require whole-array
```

The organizer says one float32 GeoTIFF on the same grid, with predictions in [0,1] and null/NaN outside bounds. The mirrored template has an irregular NaN footprint. The conservative null-outside check and all-finite diagnostic answer different questions; the reported portal range error's cause is unknown. Do not silently repair input values.

## Next steps and limitations

1. Coordinate an explicit method lane and resolve the literal calibration-lattice policy without silently weakening it. The strict rule currently stands.
2. Obtain an authenticated organizer template/data and a complete, refreshed registry; verify external data licenses/coverage. Owner-mirror hashes establish consistency, not organizer provenance. Resolve the mirrored example/label discrepancy.
3. Fix the shared upstream probability-wrapper defect once, then use the shared cached stack and a fold-local evaluator with per-feature canaries, matched incumbent, pooled DTI and paired spatial-block uncertainty.
4. If all checks pass, write and re-open the **new** TIFF using the shared writer, audit surface and dots against the complete registry, and use a separate selector to check the real weekly quota. Record the exact-file organizer receipt; no estimated leaderboard score should be invented.
5. Confirm deadline details and eligibility under the [official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf), including disclosure of generative AI in the required narrative. The official page and PDF contain a time ambiguity; plan conservatively.

The [verification workflow](.github/workflows/verify.yml) checks the generated snapshots, unit tests and JavaScript syntax on pushes and pull requests. It does not download competition data, recompute the historical raster audit, run a model or authorize submissions. Its availability depends on the repository's Actions settings.

## Parallel evidence desk and retained tools

Other parallel reviews have also been merged into this repository. Their [earlier dashboard](docs/index.html), [readiness report](docs/readiness.json), [historical raster audit](docs/historical-audit.json), [run card](docs/run-card.json), and commit-pinned [shared-tool inspection](evidence/template-inspection/README.md) are retained for provenance. They are complementary historical records—not a new candidate or a second weekly-slot decision. The root site and `docs/data/current-run.json` describe **this** preflight; both prior and current cards are negative. The upstream source snapshots are for inspection, not private modified scientific tools.

Existing `scripts/check_readiness.py`, `scripts/promotion_gate.py`, `scripts/audit_historical_rasters.py`, `scripts/verify_historical_rasters.py`, and their tests remain in place. `scripts/promotion_gate.py` evaluates supplied metadata and does not authenticate a producer or grant upload permission. The earlier browser tests can be run with `npm ci --no-audit --no-fund && npm test`; the earlier Python suite with `python -m unittest discover -s tests -v`. All large datasets under `data/` are ignored except the tracked focus registry manifest.
