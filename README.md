# GEMSDOEkarage3 — evidence-first submission desk

**Start every session here. No file is currently OK TO SUBMIT.**

[Executive summary](docs/index.html) · [Submission instructions](docs/executive-summary.html) · [Research / next steps](docs/research.md) · [Run card](docs/run-card.json)

## Standing project brief (normalized from the supplied repeated prompt)

Maximize P(Win); own the outcome. Build an auditable, autonomous geothermal-fault prediction project, not a fabricated high-score claim. Focus on GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36. Explain the best reported submissions and maintain an executive table with download, estimated performance, uniqueness, and explicit submission status. Generate a **scientifically unique TIFF**, never disguise a previous submission. Provide a distinct name and note ≤140 characters. Make a certified artifact easy to download at the beginning of the site.

Before implementing a model, rank 3–5 geological hypotheses with layers, physical signatures, missing-fault rationale, novelty and cost. Use official/free data and preserve sources. Clearly distinguish unread source leads, owner reports, local measurements and organizer receipts. Do not claim exhaustive verification when evidence is unavailable. Contradictory leaderboard claims must be flagged, not selected opportunistically.

### Parallel-run protocol
1. Stay within the explicitly assigned single method lane. If absent, do not autonomously claim a lane in the parallel project.
2. Reuse the canonical cached feature stack, `evaluate_holdout.py` and `submission_writer.py`; no private evaluator/writer. Hide whole fault segments with a buffer, rebuild catalogue-derived features from visible faults only, mask visible faults pixel-exactly. Pooled DTI uses alpha 0.2, beta 0.8, a 300 m triangular kernel.
3. Label measurements HOLDOUT-DTI with evaluator version, withheld-positive count and 95% CI, or ORGANIZER-CONFIRMED with a submission receipt. Projections are not scores. Supplied unverified score claims are separately labeled OWNER-REPORT.
4. Feature-only holdout AUC >0.90 is leakage until proven otherwise. Require a same-evaluator paired holdout improvement against the current best before selector consideration.
5. Compare both pre-placement surfaces and final dots against every registry raster. Rank correlation >0.90 or >70% dots within 3 px is a duplicate stop. Hash differences alone do not prove uniqueness.
6. Stop after three experiments or two hours. Promotion to an actual weekly slot is a separate selector step. Never spend slots for unvalidated ideas.
7. End with a JSON run card: hypothesis, mechanism, named non-fault mimic, holdout + CI, registry comparisons, raster SHA256, saved-byte validator results, name, short note, promote/negative verdict. Negative results are deliverables.

GeoTIFF validation must check single band, exact official-template CRS/shape/geotransform, no NaN inside the footprint and values in [0,1]. No human inspection waiver is needed; missing evidence automatically fails closed. Do not conflate format validity with scientific performance or slot authorization.

## Current evidence and progress — 2026-10-27

**No new candidate is OK TO SUBMIT.** [Executive desk](docs/index.html) · [Why GEMSDOE32 led](docs/historical-review.html) · [Measured raster audit](docs/historical-audit.json) · [Readiness](docs/readiness.json).

A parallel session went beyond the prior metadata-only review:
- A parallel session restored **all four core owner-mirror files**, including the 418,912,844-byte 19-band training raster. Its receipt records SHA256 pins and grid metadata; mirrors are **not organizer-authenticated**. Large inputs are ignored by Git and must be restored in a fresh checkout.
- Recovered unchanged, commit-pinned canonical evaluator, writer, validator dependency modules and restoration source in `evidence/template-inspection/`. They are an inspected upstream snapshot, **not a private fork or a recovered feature cache**. Verify its manifest before execution.
- Downloaded and inspected the nine cited historical leaders plus the earlier GEMSDOE28 solo base, for learning only. The unchanged canonical validator accepts all ten in all-finite mode against the mirrored template.
- Confirmed GEMSDOE32 is exactly the 40,199-dot solo base minus 2,545 dots within two pixels of the catalogue: 37,654 dots, **no new dots**. This proves construction, not the reason for the OWNER-REPORTED 0.2778.
- Confirmed GEMSDOE25/GEMSDOE30 positive-pixel equality and GEMSDOE31/earlier GEMSDOE28 solo equality despite different TIFF hashes.
- Every historical leader violates the literal 70% overlap rule against another audited pattern. The audit is a **partial registry**; it cannot certify a uniqueness pass. Continuous surfaces were not recovered.
- Hardened the evidence gate against malformed JSON structures, missing comparison coverage, mismatched baseline/folds, inconsistent confidence intervals, over-budget experiments, and validator/candidate digest mismatches. It still consumes metadata and cannot authenticate an untrusted producer.

No model experiments, new candidate TIFF generation, HOLDOUT-DTI measurements or competition submissions occurred. An assigned lane, canonical cached feature stack, complete fresh registry including surfaces, and same-evaluator baseline remain missing. The original checkout history did not include the ready training pipeline described in the repeated prompt.

## Reproduce autonomously
```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
python scripts/audit_sources.py               # gh; refresh pinned source reports
.venv/bin/python scripts/restore_core_data.py  # gh; canonical restoration, ~422 MB core inputs
.venv/bin/python scripts/audit_historical_rasters.py  # gh; pinned historical learning only
python scripts/check_readiness.py             # expected exit 2 while blocked
.venv/bin/python -m unittest discover -s tests -v
npm ci --no-audit --no-fund && npm test          # browser-DOM success/failure checks
python scripts/promotion_gate.py docs/run-card.json  # expected exit 2: negative
python -m http.server 8000 --bind 0.0.0.0 --directory docs
```
No credentials are requested or stored. GitHub authentication is supplied by the environment. Do not upload any historical artifact obtained by the restoration/audit tools. No new download is enabled until the release gates and separate selector succeed.

Canonical tools are intentionally unchanged. Inspection found their path-based evaluator converts positive fields to binary masks; the writer also emits a binary mask from positive input. They **must not be presented as probability-preserving continuous evaluation/writing APIs**. Their sanitizing behavior must not conceal upstream model errors. If continuous probability support is needed, fix and test it in the shared upstream template once, not in a private fork here. See [template inspection](evidence/template-inspection/README.md).

## Earlier parallel audit (preserved; superseded for preparation status)

The local [raster audit](docs/historical-raster-audit.json) verifies nine pinned TIFF hashes and 72 directed dot comparisons. Every pair exceeds the protocol's 70% within-three-pixels cutoff (minimum 86.72%). GEMSDOE25 and GEMSDOE30 have identical positive masks. This is **LOCAL-RASTER-AUDIT**, not HOLDOUT-DTI or an organizer score. Historical TIFFs were downloaded for education only, remain ignored under `data/historical/`, and are not presented as new submissions.

Reproduce with an optional isolated environment:
```sh
python -m venv .venv
.venv/bin/pip install -r requirements-audit.txt
.venv/bin/python scripts/verify_historical_rasters.py
python scripts/build_comparison.py
```
That earlier audit recovered evaluator/writer entry points for inspection and did not have the upstream modules or data. **The present follow-up recovered the dependency modules and core data mirrors as described above**, but still lacks a feature cache, assigned lane and baseline. Earlier source provenance and hashes are retained in `evidence/upstream/recovered-manifest.json`. Its historical variants and report remain separate from the newer ten-artifact canonical-validator audit.

## Limitations and next-session priorities
1. Obtain the parallel coordinator's actual lane assignment; the prompt contains no identifiable single-method paragraph. Do not invent one across concurrent runs.
2. Restore the canonical cached feature stack with its checksum and source/band provenance. The observed mirrored feature raster has 19 bands, but no `.cache/gems_work/feature_stack.npy` exists here.
3. Restore a complete fresh registry of both continuous surfaces and final dots. Pinned historical references are not a live exhaustive inventory.
4. Establish a fold-local current-best baseline using the pinned shared evaluator. Test feature-only canaries and at most three preregistered experiments; stop on duplicate drift.
5. Release a new method-derived TIFF only after paired improvement, literal novelty, saved-byte checks, and independent weekly-slot selection. Record a real organizer receipt after upload, never a projected leaderboard score.

The four hypotheses in [research.md](docs/research.md) remain untested. No estimate can honestly be given for a new candidate. CPU training is supported by the official reference; a GPU is not inherently required. DrivenData, USGS, Dropbox and literature hosts are outside the sandbox network allowlist. This session independently read the public rules and leaderboard through page extraction, but organizer data authentication, account quota and artifact-linked receipts remain unavailable. Conflicting supplied leaderboard claims are not current facts.

Only this repository's site is changed; the nine external sites are represented in the central summary, not edited. The existing GitHub Pages configuration is legacy `main:/`; the root redirect opens `docs/index.html`. CI tests the site evidence; legacy Pages performs deployment. Source refresh is reproducible, not falsely advertised as an official live feed.

The standing brief above is a normalized, deduplicated requirements record, not a verbatim archive of the repeated prompt. Read it at the beginning of every session. Core values remain **Maximize P(Win)** and **Own the Outcome**: negative evidence is useful; fabricated readiness is not.

## Additional independent preflight and source watch

[Research dashboard](docs/preflight.html) · [Nine-site scorecard and submission guide](docs/preflight-executive.html) · [Scientific review](research/2026-10-27-review.md) · [Lattice and geometry audit](evidence/geometry_audit.json) · [Negative run card](evidence/run_card.json)

A separately reproduced, hash-pinned audit verifies that the registered 13GEMSDOE lattice leaves only 6,649 of 5,167,373 mirrored footprint pixels outside its three-pixel halo. Under the literal any-registry rule, **every 37,654-dot in-footprint candidate has at least 82.34% lattice overlap**, exceeding the 70% stop. This is a geometry bound at that budget, not a measured score or a proof about all smaller budgets. No exemption or new candidate is claimed. Four additional ranked hypotheses are planning only, not proven novel or tested.

On 2026-10-27 a direct public-page extraction showed an organizer-public leaderboard leader of **0.4544**, not a receipt for any specific local file. Automated HTTPS refresh from the sandbox failed, so the checked-in observation is labeled stale. The browser can refresh public GitHub commit metadata without credentials; failures cannot authorize a submission. The official rules PDF states three entries per week (subject to current site limits), requires narrative disclosure of generative-AI use, and requires reproducible code/documentation from finalists. Account usage is unknown.

`scripts/check_format.py` examines exact TIFF bytes without repair and explicitly separates in-footprint range from conservative outside-null and whole-array range checks. The official wording and portal's reported range rejection leave an outside-footprint encoding ambiguity; passing either local validator alone is not proof of organizer acceptance. The metadata promotion gate requires this diagnostic, bound to the same candidate hash, as well as the shared validator. `evidence/shared_tool_repro.json` records a software-only independent reproduction of [upstream issue #37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37); an attempted comment was rejected by integration permissions.

The native legacy Pages build continues to publish this repository automatically. A separate scheduled artifact-deployment workflow is gated because the integration received HTTP 403 when attempting to switch Pages to Actions: an authorized admin would need to enable that source and set `ACTIONS_PAGES_ENABLED=true`. No current feed changes promotion state. This integration preserves the previous evidence desk, gate, and source snapshots rather than replacing them.

Local additional checks: `.venv/bin/python -m unittest discover -s tests -v`, `node --test tests/test_browser_feed.js`, and `.venv/bin/python scripts/audit_registry.py --fetch`.
