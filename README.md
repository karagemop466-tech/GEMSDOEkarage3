# GEMSDOEkarage3 — evidence before submission

**Current decision: NOT OK TO SUBMIT.** No newly generated candidate is approved. Do not upload the historical TIFFs. [Executive summary and nine-site comparison](index.html) · [Submission guide](executive-summary.html) · [Research slate](research/2026-10-27-review.md) · [Latest safety review](docs/review-2026-10-28.md) · [Current run card](docs/data/current-run.json).

## Starting point for every session

Read the [standing project brief](docs/PROJECT_BRIEF.md), a consolidated (not verbatim) record of the user's repeated prompt; [prior review](research/2026-10-27-review.md); and [current run card](docs/data/current-run.json). The objective is a genuinely unique, high-performing, validated GeoTIFF, not merely a differently named copy. Respect the parallel-run protocol, three-experiment/two-hour budget, literal all-registry stop, fold-local hide-and-recover, leakage canaries, and separate slot selector. **Maximize P(Win)** by measuring tradeoffs and **Own the Outcome** by reporting failures and limitations. Do not invent an assigned method lane, score receipt or organizer acceptance.

## Executive decision

| Item | Evidence and action |
| --- | --- |
| New submission file | **None approved; do not submit.** Prior GeoTIFFs remain available as research artifacts only. |
| New leaderboard score estimate | **Unavailable.** A local holdout is not an estimate of the hidden organizer score without calibration. |
| Focus sites | GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36. [Site-by-site table and exact historical filenames](index.html#scorecard). |
| Historical high claim | GEMSDOE32 H33-B2 **0.2778, USER-REPORTED / UNVERIFIED**; no hash-linked organizer receipt was found. No current leaderboard position can be inferred. |
| Why might H33-B2 perform well? | On the pinned mirrors, B2 removes pixels near mapped faults from the preceding raster. Under the distance-weighted metric, fewer redundant predictions could improve the precision–recall tradeoff. The hidden truth and receipt are unavailable; this is a hypothesis, not proof or a forecast. [Detailed audit](research/2026-10-27-review.md). |
| Critical uniqueness failure | The older SMGC candidate's own record reports **99.6866%** directional overlap with a registered lattice and `literal_all_rasters_final_passed: false`; it is not eligible under the literal 70% stop. A filtered subset had been incorrectly presented as a complete pass. [Historical run card](evidence/hk3_smgc_run_card.json) and [review](docs/review-2026-10-28.md). |
| Previous CRSB-GUB artifact | Research only: `gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.tif`, SHA-256 `2a1fed302d1fe1c556c86467ef687782d30eedf5361eff57a711ae5925a237c3`. Its scientific gate is negative; its filtered uniqueness claim is not a literal all-registry pass. No organizer acceptance is established. |

## Known limitations and next steps

The new request does not identify its promised single method paragraph. Historical preregistrations describe different previous lanes, not a reliable assignment for this session. Competition data in this checkout, the cached feature stack, complete current registry and matched baseline are absent; ignored files may differ across workspaces. Organizer-authenticated data, quota, receipts and leaderboard access are not available in this sandbox. Public GitHub mirrors are not proof of organizer authenticity. The legacy SMGC runner is disabled because it excluded registry classes from promotion, wrote before the final literal check, and deleted existing downloads. Its historical evidence has not been erased.

Next: coordinate a specific lane and resolve the literal lattice conflict; obtain authorized official data and complete hash-pinned registry/cache; repair the shared upstream evaluator/writer (see [issue #37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37)); run per-feature leakage canaries and matched, buffered whole-segment holdout with CIs; check both stages against **every** registered raster; verify exact saved bytes against the official template; then use a separate selector. Do not use a weekly slot without these gates. Historical hypotheses, input sources and availability caveats are documented in the [research slate](research/2026-10-27-review.md).

## Local checks

```sh
python scripts/check_readiness.py  # exits 2 when prerequisites are missing
python scripts/build_site.py --check
python -m pytest -q
```

Readiness is measured at execution time, not a live feed. Page metadata refresh does not authenticate scores, validate files, or grant a submission slot. Official references: [competition problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [submission data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), and [DOE INGENIOUS dataset](https://gdr.openei.org/submissions/1391).

The local promotion screen additionally requires a pinned registry manifest digest and a per-reference correlation **and** overlap measurement at both pre-placement and final-dot stages. It checks card consistency only: a digest written in a card is not proof that its inventory was complete or current. A separate evidence audit and selector remain mandatory.
