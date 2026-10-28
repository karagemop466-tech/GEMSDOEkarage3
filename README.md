# GEMSDOEkarage3 — current release decision (2026-10-28)

**DO NOT SUBMIT existing files.** The earlier approval claims below are withdrawn.
All five saved TIFFs fail the literal any-registry overlap gate. No new model
experiment or competition slot was used in this review. No leaderboard estimate
is available. A different hash alone is not uniqueness.

Start every session with this section, the [retained consolidated user request](docs/PROJECT_BRIEF.md),
[three-pass review and ranked hypotheses](research/2026-10-28-review.md), and
[current run card](evidence/run-card-20261028.json). Maximize P(Win): preserve
slots and reject unsupported claims. Own the Outcome: fix misleading release
labels rather than bypassing scientific gates.

- [Current executive release review and archive download table](docs/release-review.html)
- [All nine focus sites and historical best filenames](docs/preflight-executive.html)
- [Reproduced saved-byte / literal uniqueness audit](evidence/release-audit-20261028.json)
- Reproduce: `.venv/bin/python -m scripts.audit_release_20261028`
- Build correction: `.venv/bin/python scripts/build_release_review.py`

Existing zero-filled TIFFs pass local finite/range checks but fail uniqueness;
NaN companions fail the whole-array finite/range diagnostic. Organizer acceptance
and external-data provenance remain unconfirmed. Feature caches are absent in
this fresh checkout. One explicit lane and verified cache/fold restoration are
required before another scientific experiment. No access to non-allowlisted
DrivenData/USGS/GDR/Dropbox/NLR hosts is available here. Other sites were audited
through pinned mirrors, not edited.

## Archived candidate inventory — research only

- `docs/downloads/gemsdoe32-hk3-smgc-maxenv-axial28-37654-20261027T213000Z-c886c782-nan.tif` · SHA256 `d425f6f3e17743157ed950cf250c9bfa120c68be0fdff09a0cf8566039fdfaee` · **DO NOT SUBMIT**
- `docs/downloads/gemsdoe32-hk3-smgc-maxenv-axial28-37654-20261027T213000Z-c886c782-zeros.tif` · SHA256 `f21a0e831e6307d1d8230119c4d2f9812646fa8b092b2326b180a54feccea33f` · **DO NOT SUBMIT**
- `docs/downloads/gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.tif` · SHA256 `2a1fed302d1fe1c556c86467ef687782d30eedf5361eff57a711ae5925a237c3` · **DO NOT SUBMIT**
- `docs/downloads/karage3-k3-fuse-greedy-b2-20261027T212847Z-80117cd2-nan.tif` · SHA256 `04cdc5fe41fdc5ef1b148cf8352015d25d37763f1f847838f0f96cd0d342a993` · **DO NOT SUBMIT**
- `docs/downloads/karage3-k3-fuse-greedy-b2-20261027T212847Z-80117cd2-zeros.tif` · SHA256 `9b2656c4a7afb9969df7ee93bbf4e9b4fa8f313465964d79fc9194718f95fafa` · **DO NOT SUBMIT**


## Concurrent review retained

# GEMSDOEkarage3 — evidence-led fault discovery

## Current decision (2026-10-28): DO NOT SUBMIT

**The previous “PROMOTE / OK TO SUBMIT” recommendation is retracted.**
The retained SMGC TIFF's own registry evidence records **99.6866%** overlap within
3 px of the registered calibration lattice, over the literal **70%** limit.
Dense-raster exemptions were not authorized. Stop means stop: no new raster,
experiments, or competition slots in this review.

- [Executive summary and nine-site table](docs/executive-summary.html)
- [Three-pass review, ranked hypotheses, limitations and next steps](docs/review-2026-10-28.md)
- [Corrected candidate card](docs/run-card.json) · [Automated gate](docs/current-gate-decision.json)
- [Historical forensics and source links](executive-summary.html)

### Retained artifact — research download only, NOT CLEARED

[`gemsdoe32-hk3-smgc-maxenv-axial28-37654-20261027T213000Z-c886c782-zeros.tif`](docs/downloads/gemsdoe32-hk3-smgc-maxenv-axial28-37654-20261027T213000Z-c886c782-zeros.tif)

SHA256: `f21a0e831e6307d1d8230119c4d2f9812646fa8b092b2326b180a54feccea33f`.
Byte novelty and [0,1] format validity do not establish lane uniqueness or high scores.
Saved HOLDOUT-DTI: `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives,
0.107297, 95% CI [0.093004, 0.120923]. **Not reproduced this review; not a
leaderboard estimate.** No organizer receipt authenticates the supplied historical results.

Earlier CRSB-GUB artifact (also research only):
`gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.tif`
SHA256 `2a1fed302d1fe1c556c86467ef687782d30eedf5361eff57a711ae5925a237c3`.
Use its [archive card](docs/crsb-gub/run-card.json) for the exact filename and context.

## Standing owner prompt — read at the start of every session

The deduplicated prompt is maintained in [knowledge/owner_brief.md](knowledge/owner_brief.md).
It is a requirements summary, not a verbatim transcript. Focus sites:
GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31,
GEMSDOE32, GEMSDOE33, GEMSDOE36.

Generate genuinely unique GeoTIFFs, never copied submissions. Apply the literal
registry correlation and 3-px overlap stops before placement and on final dots.
Reuse the shared cached features, `evaluate_holdout.py`, and `submission_writer.py`.
Withhold buffered whole segments, rebuild catalogue features using visible faults
only, mask visible pixels exactly, and report pooled HOLDOUT-DTI with evaluator,
withheld-positive count and 95% CI. Test every feature alone; AUC above 0.90 is
leakage until disproven. Never label a projection as a score or a reported result
as ORGANIZER-CONFIRMED without a submission-page receipt. Stop after three
experiments or two hours. Slot selection is separate and subject to the actual
weekly cap. Negative results are deliverables.

Make download status obvious; include unique name and note <=140 characters.
Validate saved single-band bytes, finite [0,1] values, CRS/shape/transform against
the real template. Do not claim validation when data is absent. Rank geological
hypotheses before implementation; establish external data availability before
calling an idea viable. Perform three review passes. Preserve official links,
provenance, limitations and irregularities. Maximize P(Win); own the outcome.

## Reproduce this decision

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/promotion_gate.py docs/run-card.json # expected exit 2 (negative)
.venv/bin/python scripts/build_review_status.py
.venv/bin/python -m pytest -q
```

Ignored data/cache must be restored separately for integration training and
holdout reproduction. This runtime only permits GitHub and package-registry
network access; official competition pages and Dropbox cannot be reverified.
No claim of winning, hidden-score estimation, complete current registry coverage,
or a newly generated submission is made.
