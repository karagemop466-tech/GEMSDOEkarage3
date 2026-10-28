# GEMSDOEkarage3 — evidence before submission

> **DO NOT SUBMIT: no new candidate has passed the literal parallel-run protocol.**
> Older reports in this repository contain contradictory promotion, novelty, and organizer-confirmation claims; they are historical claims, not current release decisions. A valid file format is not a proven high score or permission to spend a slot.

Start every session with [the project brief](docs/PROJECT_BRIEF.md), [the latest independent review](research/2026-10-27-review.md), and [the preflight run card](docs/data/current-run.json). Read the user's current instructions too. Work from **Maximize P(Win)** and **Own the Outcome**: establish the evidence, expose uncertainty and resolve failures rather than quietly presenting them as successes.

## Executive summary

[View the nine-site evidence and submission guide](executive-summary.html) · [Research hypotheses](research.html) · [Sources](sources.html) · [Detailed preflight](docs/preflight.html)

| File | Score estimate | Unique vs. listed sites? | Submission status |
| --- | --- | --- | --- |
| None cleared | Unavailable; a proxy is not a leaderboard forecast | Not demonstrated across the complete current registry | **DO NOT SUBMIT** |

The historical [GEMSDOE32 B2 file](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) has a **user-reported / unverified** score of 0.2778, the largest claim in the nine-site list. The [geometry audit](evidence/geometry_audit.json) shows B2 is the GEMSDOE31 pattern with dots within two pixels of the mirrored known faults removed. Less redundant placement and fewer predictions near masked mapped faults might explain its performance; hidden truth is unavailable, so causation and improvement beyond 0.2778 are not established. The user's conflicting leaderboard figures are unverified snapshots, not a current official observation.

The old `H-K3-1 SMGC-CT` run card reports `literal_all_rasters_final_passed: false`, yet also reports promote. Its filtered overlap result is not a pass under the requested **any registry raster** rule. Another archived candidate, `gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.tif` (SHA-256 `2a1fed302d1fe1c556c86467ef687782d30eedf5361eff57a711ae5925a237c3`), is research only. Neither is authorized for upload. Historical files remain in Git for reproducibility, not as new submissions. [Prior SMGC run evidence](evidence/hk3_smgc_run_card.json) is retained unmodified; its release claim is superseded.

## Reproducible work and limitations

- The lane-defining “single method paragraph below” is not identifiable in the current request. A prior branch's H-K3-1 assignment does not assign this parallel session. No new experiment or slot was used.
- [Readiness](docs/readiness.json) reflects this checkout; ignored data/cache does not persist between workspaces. Pinned mirror hashes prove integrity, not organizer provenance. Restore only permitted data; [official competition data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) may require login. Network access here is restricted, including Dropbox and DrivenData.
- [Shared evaluator issue #37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37) remains open: its CLI silently binarizes positive values. Do not claim it evaluates continuous predictions accurately. A shared upstream fix and parity tests are required, not a private fork.
- Before experimentation, resolve lane and registry-control policy, obtain and validate the cached stack and complete current registry, and establish a frozen same-protocol baseline. Check every feature for leakage, calculate pre-placement and final-dot overlap against every registry raster without silently excluding controls, and stop on duplicates. Compare whole-segment buffered hide-and-recover DTI with paired spatial confidence intervals. At most three experiments/two hours; a separate selector must approve a weekly slot. Check the [official submission format and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
- A local validator must inspect saved bytes against the actual template: one band, exact CRS/shape/transform, finite in-footprint values in [0, 1]. The reported portal range error and outside-footprint encoding need an actual organizer-confirmed resolution; a zero-filled file alone does not prove acceptance.

Run local checks: `python -m pytest -q`, `npm ci && npm test`, and `python scripts/build_site.py --check`. The repo is configured for GitHub Pages from `main:/`; account settings, upload limits, organizer receipts and external site changes are outside this checkout. External sites are not modified by this project.
