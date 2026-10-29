# Project prompt (read first, every session)

This file restates the operating prompt for GEMSDOEkarage3 so every session starts from the same goal and the same rules. The full request, with every leaderboard and site link, is kept in the session history. Leaderboard and site data live in the receipts listed under "Where the data is", not in this file.

## Goal

Place at the top of the DrivenData **GEMS Prize** leaderboard (competition 306, `Geologic Enhanced Mapping System`) by producing a single-band GeoTIFF of fault predictions that is:

1. **Downloadable in one click** from the site, with the decision (safe to submit or not) obvious on arrival.
2. **Validated without human inspection**: format, range, grid and uniqueness are checked by the project's own tools, and the result is recorded.
3. **Unique**: not a copy of any earlier submission. Copies are allowed only for learning and education.

## Core values

- **Maximize P(Win).** In every decision, weigh trade-offs and choose the path that maximizes the probability that the project succeeds.
- **Own the outcome.** Treat failure and success as signals. Act on problems without waiting to be asked, and stay accountable for the end result.

## Non-negotiable rules

- **Uniqueness (protocol rule 1).** Stop if rank correlation with any registry raster exceeds 0.90, or if more than 70% of the candidate's dots lie within 3 px (300 m) of one registry raster's dots. Check this on the surface before placement and again on the final dots. Log duplicates and stop.
- **Shared tools.** Use the template's evaluator (`scripts/evaluate_holdout.py`, `src/gems32/holdout.py`) and writer (`scripts/submission_writer.py`). Do not fork them. If one is wrong, fix it once in the template and report it.
- **Holdout.** Withhold whole fault segments with a buffer, derive catalogue features only from visible faults, mask visible faults exactly, and pool DTI (alpha 0.2, beta 0.8, 300 m triangular kernel).
- **Labels.** Every number is labelled either `HOLDOUT-DTI` (evaluator version, withheld positives, 95% CI) or `ORGANIZER-CONFIRMED` (copied from a submission-page receipt). A projection is never written as a score. Scores on the GEMSDOE sites are `USER-REPORTED / UNVERIFIED` until a receipt exists.
- **Leakage canary.** Test each feature alone on the holdout. AUC above 0.90 means leakage until proven otherwise.
- **Budget.** At most three experiments or two hours per candidate.
- **Run card.** End every candidate with one JSON card: hypothesis, mechanism, named non-fault mimic, holdout DTI and CI, registry overlap, raster SHA-256, validator output, submission name, note of at most 140 characters, and verdict (`promote` or `negative`). Negative results are deliverables.
- **Format.** One float32 band, EPSG:32611, 3730 × 3292, the template's geotransform (100, 0, 243350, 0, −100, 4508550), values in [0, 1], and no NaN inside the footprint. Give each file a unique name and a short comment.
- **Sources.** Work line by line from official, verified sources, link them for manual review, flag irregularities, and do not hallucinate.

## Official sources

- Problem description and metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Official rules (NLR PDF, Sept 2026): https://docs.nlr.gov/docs/fy26osti/96647.pdf
  - Section 1.1: "Participants will submit a single entry."
  - Section 3.2: "a single GeoTIFF with a single raster layer at 100-meter resolution… three submissions per week." The narrative must disclose generative-AI use.
- Scoring clarification (DrivenData staff, 16 Sep 2026): known USGS/INGENIOUS fault pixels are masked from evaluation: https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516
- Public leaderboard (read 2026-10-29, top 50 visible; snapshot in `docs/data/leaderboard-snapshot-20261029.json`): https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- GeoDAWN data: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- CRS: https://epsg.io/32611

## Where the data is

| What | Where |
|---|---|
| Top-site files at pinned commits, SHA-256, format | `docs/data/gemsdoe-top9-audit.json` |
| Dot structure, catalogue distance bins, overlap matrix | `docs/data/gemsdoe-top9-analysis.json` |
| Same-evaluator holdout results (HOLDOUT-DTI) | `docs/data/evaluator/eval_<SITE>.json` |
| Lattice gap and recall ceiling | `docs/data/lattice-gap-analysis.json` |
| Blocked candidate H1 (build + uniqueness) | `docs/data/h1-candidate-receipt.json`, `docs/data/h1-uniqueness.json` |
| Executive summary (generated) | `submission-summary.html`, `docs/data/submission-summary.json` |
| Irregularities register | `knowledge/irregularities.md` |

## Access the project does not have (must be arranged by the user)

- DrivenData account login, to download the competition data and to see account-only submission receipts. The public problem page, rules, forum and public leaderboard were read directly; the build shell itself cannot reach drivendata.org.
- The complete leaderboard registry (every submitted GeoTIFF). Only nine site files and 14 scored rasters are reachable through GitHub, so the uniqueness check is partial. The public board lists ranks and scores only, not files.
- A decision on whether the internal 70% / lattice rule binds (see the summary, section 6).
