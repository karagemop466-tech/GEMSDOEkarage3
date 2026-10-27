# GEMSDOEkarage3 — evidence-first submission desk

**Start every session here. Current decision: NOT OK TO SUBMIT.**

[Root overview](index.html) · [Live activity desk](docs/index.html) · [Submission guide](docs/executive-summary.html) · [Research](docs/research.html) · [Detailed evidence ledger](docs/research.md) · [Historical forensics](docs/historical-review.html) · [Run card](docs/run-card.json) · [Project brief](docs/PROJECT_BRIEF.md)

## Standing project brief (normalized from the supplied repeated prompt)

Maximize P(Win); own the outcome. Build an auditable, autonomous geothermal-**fault** prediction project, not a fabricated high-score claim. Focus on GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36. Explain their highest supplied historical submissions; provide download, evidence, uniqueness and decision status. Generate a **scientifically unique TIFF**, never disguise a previous submission. A future approved artifact needs a distinct name, a note of at most 140 characters and a prominent one-click download. Do not confuse fault detection with proof of a geothermal vent.

Before implementing a geological model, rank 3–5 hypotheses with specific layers, physical signatures, missing-fault rationale, non-fault mimics, novelty and cost; identify and verify free official external sources where required. Distinguish user/owner reports, local measurements and organizer receipts. Do not manufacture an estimate of hidden leaderboard performance. Preserve and link official sources, flag irregularities, and revisit next steps each session. Review work in three passes.

### Parallel-run protocol

1. Stay within the explicitly assigned single method lane. The current request refers to a paragraph assigning one, but does not contain it; do not invent a parallel assignment.
2. Reuse the shared cached feature stack, `evaluate_holdout.py` and `submission_writer.py` rather than privately forking them. Hide whole fault segments with a buffer, rebuild catalogue-derived features from visible faults only, mask visible faults pixel-exactly, and score pooled DTI (α=0.2, β=0.8, 300 m triangular kernel).
3. Label candidate measurements HOLDOUT-DTI with evaluator version, withheld-positive count and 95% CI, or ORGANIZER-CONFIRMED with a submission-page receipt. Projections are not scores. Supplied historical claims remain USER/OWNER-REPORT, not receipts. A public-board snapshot is distinct from either.
4. Test every feature alone; an AUC above 0.90 is a leakage stop until proven otherwise. Require a same-evaluator, same-fold paired holdout improvement against the current best before selector consideration.
5. Compare both pre-placement surfaces and final dots against every registry raster. Rank correlation above 0.90 or more than 70% of candidate dots within three pixels of any registry raster is a duplicate stop. Hash differences alone do not prove uniqueness.
6. Stop after three experiments or two hours. Promotion to a real weekly slot is a separate selector step. Never spend a slot on an unvalidated idea.
7. End with one JSON run card: hypothesis, mechanism, named non-fault mimic, holdout + CI, registry comparisons, raster SHA-256, saved-byte validator results, name, short note and promote/negative verdict. Negative results are deliverables.

The exact saved TIFF must be single-band float32, match an authenticated organizer template's CRS/shape/geotransform, have no non-finite or masked values in the footprint, and contain [0,1] predictions. Check finite nodata sentinels as well and reject external mask sidecars not bound by the TIFF hash. The conservative gate independently requires both raw-array finite/range and outside-null diagnostics; a synthetic internal-mask file passes locally, but the shared writer does not currently emit this combined encoding and portal acceptance is unknown. A metadata gate is not a scientific evaluation or an upload authorization. No human inspection waiver can turn missing evidence into a pass.

## Current result

No new candidate, new TIFF, candidate holdout or weekly upload. A pinned shared template and its owner-hosted core mirrors were restored, and its 35-channel stack rebuilt in ignored cache using the upstream code. These mirrors are **not organizer-authenticated**; the mirrored sample contains the label positives despite the organizer describing a no-fault sample. Hashes and checks are recorded in [cache-restoration.json](evidence/cache-restoration.json); large data/cache files are not in Git.

An independent [historical raster audit](docs/priority-audit.json) found that GEMSDOE32's historical mask is GEMSDOE31's mask with the 2,545 pixels within two pixels of the mirrored catalogue removed. The 0.2778 value is **USER/OWNER-REPORT**, without a linked organizer receipt. All 72 directional comparisons among the selected nine historical masks exceed 70% proximity. The registered lattice covers all but 6,649 proxy-footprint cells within three pixels, giving an **82.34% lower bound** for any 37,654-dot candidate. This is a geometry result, not a score, full-registry audit, or impossibility proof for every smaller budget. See [research](docs/research.md#literal-lattice-stop-a-reproducible-counting-bound).

The [official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) showed a leader at 0.4544 on 27 October 2026. This is a public-board snapshot, not an organizer receipt for our file; it may already be stale. DrivenData's [terms](https://www.drivendata.org/termsofuse/) prohibit automated access, so the site checks public GitHub heads and displays commit subjects only, not the DrivenData leaderboard. That activity feed does not verify new scores or files. The signed-in submission page was inaccessible.

The shared writer and evaluator silently binarize positive probability values; the existing [upstream issue #37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37) documents it. This session has read-only upstream access, did not modify or privately fork those tools, and blocks continuous candidates until the shared contract is corrected. The requested verbatim prompt is not archived here; this is a normalized brief.

### Preserved parallel evidence

Additional independent sessions contributed [a ten-artifact audit](docs/historical-audit.json) (including the earlier GEMSDOE28 solo base), [a separate nine-raster audit](docs/historical-raster-audit.json), pinned source and dependency snapshots under `evidence/template-inspection/`, and separate restoration/verification scripts. Their results corroborate the lineage; some use all-finite encodings or earlier variants rather than the NaN-outside variants in our priority audit. They are research inputs, not approved candidates. Their historical [review](evidence/review-passes-20261027-followup.md) records its original availability limitations; the cache and official-source access findings above supersede those older statements. Their shared validator's all-finite-mode results do not establish portal acceptance.

## Reproduce the audit

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-audit.txt
.venv/bin/python -m unittest discover -s tests -v
npm ci --no-audit --no-fund && npm test  # browser-DOM rendering and fail-closed checks
# Fetch 12 small, immutable, hash-verified historical inputs via gh; no organizer access.
.venv/bin/python scripts/audit_priority_rasters.py
.venv/bin/python scripts/audit_saved_historical.py  # independently reopen the nine saved bytes
# Refresh pinned GitHub READMEs only, not organizer scores.
python scripts/audit_sources.py
# Reopen a future candidate with the exact organizer template; no clipping or rewriting.
.venv/bin/python scripts/validate_geotiff.py candidate.tif organizer-sample.tif
# A future gate invocation must include these actual bytes; promotion still requires a selector.
.venv/bin/python scripts/promotion_gate.py docs/run-card.json --raster candidate.tif --template organizer-sample.tif
python -m http.server 8000 --bind 0.0.0.0 --directory docs
```

Restore the unmodified pinned shared template, optionally its **owner-hosted, unauthenticated** core mirrors (~400 MB), or additionally rebuild the ~1.7 GB cache:

```sh
bash scripts/restore_shared_template.sh
PYTHON="$PWD/.venv/bin/python" bash scripts/restore_shared_template.sh --core
PYTHON="$PWD/.venv/bin/python" bash scripts/restore_shared_template.sh --build-stack
```

The restore helper checks archive and shared-tool hashes and delegates data/feature building to the pinned template. It requires `gh`, `curl`, sufficient disk/RAM and the audit requirements. Feature-cache rebuilding is not a model experiment; it does not validate provenance, leakage or a candidate.

## Next-session priorities and limitations

See [the detailed ledger](docs/research.md). Resolve the missing lane and literal calibration-lattice rule, authenticate the organizer template and data rights, repair the shared probability contract upstream, then run leak-safe holdout, complete registry comparisons and saved-byte validation. The selector and signed-in weekly quota remain separate. CPU training is supported by the [official reference](https://github.com/drivendataorg/gems-prize-reference-solution); a GPU is not strictly required. We can improve this repository's centralized site but cannot edit the nine third-party repositories from this branch.
