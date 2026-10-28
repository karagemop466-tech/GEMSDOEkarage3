# Owner brief (standing requirements — read every session)

Condensed from the owner's session prompt (2026-10-27). Where the prompt repeats itself, the
requirement is stated once. Contradictions found in the prompt are flagged, not resolved silently.

## Mission

Place at the top of the DrivenData DOE GEMS leaderboard
(https://www.drivendata.org/competitions/306/competition-doe-gems/) by discovering fault
traces missing from the USGS/INGENIOUS catalogue (geothermal relevance: faults are upflow
conduits). Design a *new, unique* strategy that can score above the owner's programme best.

Programme best to beat (OWNER-REPORTED): `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778`
from https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html.
Competition #1 cited in the prompt: `0.4413`. An older copy in the same prompt says `0.3195`
(**IR-K3-03: stale; treat 0.4413-class as the current bar, re-verify on the live page before
any slot decision**).

## Focus sites (highest-scoring submissions to study)

GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33,
GEMSDOE36 — full owner-reported score catalogue for all programme sites is preserved in
`registry/owner_score_ledger.csv`. An executive summary per focus site must make the best
file, its (labelled) score estimate, and its uniqueness obvious in one table.

## Hard rules

1. **Unique TIF.** Generate a unique submission GeoTIFF. Never copy a previous submission
   except for learning/education (forensic controls). It must be *obvious* on the site whether
   the generated file is OK to download and submit. Validation/inspection is automated inside
   the project — no human inspector step.
2. **Parallel-run lane.** Stay inside the assigned lane. If the surface rank-correlation vs any
   registry raster exceeds 0.90, or >70 % of dots fall within 3 px of one registry raster's
   dots, it is a duplicate lane: log and stop. Check on the surface before placement and on
   final dots. (See IR-K3-02 for the lattice pigeonhole that makes the *literal* rule
   impossible at normal budgets; report genuine-raster and literal numbers separately.)
3. **Reuse shared tools.** Cached feature stack, `evaluate_holdout`, submission writer.
   Holdout = hide-and-recover: withhold whole fault segments with a buffer; every
   catalogue-based feature derived only from visible faults; visible faults masked
   pixel-exactly; pooled DTI (α=0.2, β=0.8, 300 m triangular). Fix shared-tool bugs in the
   template copy and report them; no private silent forks.
4. **Label every number**: HOLDOUT-DTI (evaluator version, # withheld, 95 % CI) or
   ORGANIZER-CONFIRMED (submission-page receipt). A projection is never a score.
5. **Leakage canary.** Each feature alone on holdout first; AUC > 0.90 = leakage until proven otherwise.
6. **Run card** (JSON): hypothesis; mechanism; named non-fault mimic; holdout DTI + CI;
   correlation/overlap vs registry; raster sha256; validator output (no NaN in footprint,
   values in [0,1], CRS/shape/transform match); submission name + note ≤140 chars; verdict
   promote/negative. Negative results are deliverables.
7. **Budget**: ≤3 experiments or ≤2 h compute. Do not pick submissions; promotion to a real
   slot is a separate selector step within the weekly cap. Never spend a slot on an idea that
   has not beaten the current holdout best.
8. **Hypotheses before implementing**: 3–5 untried geological hypotheses, each naming
   layer(s), physical signature/transform, why it catches a catalogue-missing fault, and how
   it differs from this repo's prior art; ranked by expected DTI gain and cost. If external
   data is needed, name the free official source and verify obtainability first.
9. **Submission mechanics**: single-band GeoTIFF (or zip of one), CRS/shape/geotransform must
   match the sample; values must be in [0,1] (the owner hit `Predicted values must be in
   range [0, 1]` — the `-zeros` variant with no NaN anywhere is the safe file). Provide a
   unique name + short distinguishing note. Executive-summary subpage must explain exactly
   how to submit.
10. **Evidence discipline**: work line-by-line from official/verified sources with links for
    manual review; no hallucinations; flag irregularities. Three passes: implement, bug-hunt,
    re-check against this brief. Site must be a clean GitHub Pages UI with the download
    decision obvious at the top.

## Core values

**Maximize P(Win)** — choose the path that maximizes the probability Arena/the programme
succeeds. **Own the Outcome** — own results end-to-end; act without waiting for permission;
treat failure and success as signals.

## Key official links (manual review)

* Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
* Problem/metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
* About/resources: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
* Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
* Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
* Rules PDF (NLR 96647): https://docs.nlr.gov/docs/fy26osti/96647.pdf
* USGS GeoDAWN release: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (DOI 10.5066/P93LGLVQ)
* INGENIOUS project: https://gbcge.org/current-projects/ingenious/
* GDR submission 1391: https://gdr.openei.org/submissions/1391
* CRS EPSG:32611: https://epsg.io/32611
* Tversky index: https://en.wikipedia.org/wiki/Tversky_index

## Data access statement (verified in sandbox, 2026-10-27)

DrivenData data tab requires login; no credentials are available to the agent and none may be
requested in chat. The working substitute, used by every sister repo, is the SHA-256-pinned
owner mirror in `registry/data_manifest.json` (bytes fetched from the owner's GitHub repos via
codeload/api, each hash verified before use). Dropbox links in older prompt copies are not
reachable from the sandbox and are not needed.
