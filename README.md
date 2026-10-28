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

Readiness is measured at execution time, not a live feed. Page metadata refresh does not authenticate scores, validate files, or grant a submission slot. Official references: [competition problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [submission data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), and [DOE INGENIOUS dataset](https://gdr.openei.org/submissions/1391).

The local promotion screen additionally requires a pinned registry manifest digest and a per-reference correlation **and** overlap measurement at both pre-placement and final-dot stages. It checks card consistency only: a digest written in a card is not proof that its inventory was complete or current. A separate evidence audit and selector remain mandatory.

Ignored data/cache must be restored separately for integration training and
holdout reproduction. This runtime only permits GitHub and package-registry
network access; official competition pages and Dropbox cannot be reverified.
No claim of winning, hidden-score estimation, complete current registry coverage,
or a newly generated submission is made.
