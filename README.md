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

## What actually exists
The initial checkout at `85359a3` contained only a one-line README. There was no previous training pipeline, dataset, cached stack, evaluator or writer to run. Claims in the supplied prompt about a ready pipeline or data being the sole blocker did not describe this checkout.

This revision adds a source-pinned nine-site dashboard, four preregistered hypotheses, a metadata evidence gate and tests. It does **not** implement or privately fork the template evaluator or writer. No model experiments, TIFF generation, or competition submission occurred. Upstream evidence was recovered over GitHub; those are third-party reports, not official organizer receipts. Missing lane and cache prevent honest completion of the requested competitive TIFF.

## Reproduce
```sh
python scripts/audit_sources.py          # gh authentication; refresh pinned GitHub evidence
python -m unittest discover -s tests -v
python scripts/promotion_gate.py docs/run-card.json  # expected exit 2: negative
python -m http.server 8000 --bind 0.0.0.0 --directory docs
```
The promotion gate consumes evidence metadata, not raster pixels; it cannot certify receipts supplied by an untrusted producer. Only canonical tools may produce the actual evaluator/writer/validator outputs. Even a `promote` result does not authorize upload.

## Follow-up review: recovered historical rasters

The local [raster audit](docs/historical-raster-audit.json) verifies nine pinned TIFF hashes and 72 directed dot comparisons. Every pair exceeds the protocol's 70% within-three-pixels cutoff (minimum 86.72%). GEMSDOE25 and GEMSDOE30 have identical positive masks. This is **LOCAL-RASTER-AUDIT**, not HOLDOUT-DTI or an organizer score. Historical TIFFs were downloaded for education only, remain ignored under `data/historical/`, and are not presented as new submissions.

Reproduce with an optional isolated environment:
```sh
python -m venv .venv
.venv/bin/pip install -r requirements-audit.txt
.venv/bin/python scripts/verify_historical_rasters.py
python scripts/build_comparison.py
```
Shared evaluator/writer entry points were recovered as source evidence, not installed as private forks. They depend on upstream `gems32` modules and data not present here. Their existence upstream does not make this checkout's training pipeline runnable. Provenance and hashes are in `evidence/upstream/recovered-manifest.json`.

## Limitations and next-session priorities
See [research.md](docs/research.md). Assign the lane, restore pinned shared cache/template and complete registry, establish fold-local baseline and run at most three experiments. CPU training is supported by the official reference; a GPU is not strictly required. DrivenData, USGS, Dropbox and literature hosts are outside this sandbox's network allowlist; no current cap, receipt, leaderboard or official-data authentication was verified.

We can modify this repository's site, not nine other repositories without separately scoped changes. GitHub Pages deploys `docs/` using the included workflow. Source refresh is explicit, not a claimed live leaderboard feed.
