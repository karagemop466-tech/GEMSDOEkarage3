# GEMSDOEkarage3 — K3 lane

> **Reading order every session:** this README → [`knowledge/owner_brief.md`](knowledge/owner_brief.md)
> (standing requirements, condensed verbatim-owner prompt) → [`knowledge/preregistration_k3.md`](knowledge/preregistration_k3.md)
> (frozen lane, hypotheses, promotion gates) → [`docs/executive-summary.html`](docs/executive-summary.html)
> (generated from `evidence/*.json`; never hand-edit numbers).

## Core values

**Maximize P(Win).** Every decision weighs trade-offs and risk and chooses the path that
maximizes the probability of winning the DOE GEMS Prize — emotions aside.

**Own the Outcome.** Results are owned end-to-end. When problems arise and we have the
means to act, we act without waiting for permission. Failure and success are both signals.

## Current decision (2026-10-27, K3 complete: 3/3 experiments)

🔴 **DO NOT SUBMIT — verdict `negative`.** Research download only:
[`docs/downloads/karage3-k3-fuse-greedy-b2-20261027T212847Z-80117cd2-zeros.tif`](docs/downloads/karage3-k3-fuse-greedy-b2-20261027T212847Z-80117cd2-zeros.tif)
(SHA-256 `9b2656c4…fafa`, 34,835 dots, validator PASS, genuinely unique: worst 65.3 % within-3 px
across 432 scanned registry rasters, 24.3 % vs the champion). HOLDOUT-DTI pooled **0.0522**
[0.0375, 0.0620] (`GEMSDOE32-HOLDOUT-v3-visible-only`, 22,232 withheld) vs champion-rule
control **0.0992** → gate G1 fails; SGMC-cal 0.0892 beats the champion's 0.0641 (G2 pass);
G3/G4/G5 pass. Leaderboard estimate: **NOT ESTIMABLE**. Full banner + tables in
[`docs/executive-summary.html`](docs/executive-summary.html); machine verdict in
`evidence/k3_run_card.json` (re-check with `scripts/verify_numbers.py`, 23/23).
A file is **OK TO SUBMIT** only if a future run card verdict is `promote`; promotion to a
real weekly slot is a separate selector step by the owner.

**Next session (suggestions, in expected-value order):** (1) obtain sub-km raw seismicity
(USGS ComCat/FDSN — free/official, unreachable from this sandbox) or another *independent*
blind-fault signal and repeat the visible-only screen before any slot; (2) test whether the
corrected-LiDAR SGMC advantage survives fold-local B2-refill at fixed budget against the
champion *dots* as base (a selector-level blend — would not be lane-unique, so it belongs to
the selector, not a parallel lane); (3) upstream the IR-K3-01 band fix into the template repo;
(4) re-verify the live leaderboard #1 manually (≈0.44 cited; sandbox cannot fetch it).

## What this repo is

One parallel lane (K3) for the DrivenData DOE GEMS competition
(<https://www.drivendata.org/competitions/306/competition-doe-gems/>): find fault traces
*missing* from the USGS/INGENIOUS catalogue on a 100 m, EPSG:32611, 3730×3292 grid. Scoring is
the distance-weighted Tversky index (DTI, α=0.2, β=0.8, 300 m triangular kernel) against a
hidden fault set; known catalogue faults are masked by the organizer.

The nine focus sister sites (GEMSDOE24/25/27/28/30/31/32/33/36) are *prior art and registry*,
not code to copy a submission from. Their verified forensic summary is in
[`knowledge/focus9_forensics.md`](knowledge/focus9_forensics.md). Headline verified facts:

* Every focus-site best is one nested family: H19-5 ridge (121,131 px, owner-reported 0.1922)
  → Poisson-dotted d=2.8 (44,090 px, 0.2600) → solo ring prune (40,199 px, 0.2708) →
  **H33-2-B2 (37,654 px, 0.2778)** = solo with every dot ≤2 px from the catalogue deleted.
* All live scores in this project are **owner-reported**; no organizer receipt is stored in any
  focus repo. They are labelled OWNER-REPORTED, never ORGANIZER-CONFIRMED.
* The public leaderboard #1 cited by the owner (0.4413) and fetched by a sister repo on
  2026-10-26 (0.4437) are snapshots from different times; 0.3195 in older brief copies is stale.

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python scripts/restore_data.py --group all   # hash-pinned mirror restore into .cache/gems_data (git-ignored)
PYTHONPATH=src .venv/bin/python scripts/prepare_data.py               # .cache/gems_work/bands/*.npy + data/prepared_manifest.json
PYTHONPATH=src .venv/bin/python scripts/build_focus_registry.py --registry-root /path/to/focus-clones
PYTHONPATH=src .venv/bin/python scripts/exp1_screen.py                # Experiment 1 of 3 (canaries + surface screen)
PYTHONPATH=src .venv/bin/python scripts/exp2_emission.py              # Experiment 2 of 3 (fusion + emission arm)
PYTHONPATH=src .venv/bin/python scripts/exp3_final.py                 # Experiment 3 of 3 (final TIF + validator + uniqueness + run card)
PYTHONPATH=src .venv/bin/python scripts/build_site.py                 # regenerates docs/*.html from evidence/*.json only
.venv/bin/python -m pytest tests/ -q
```

Data notes: competition rasters are login-walled on DrivenData; this repo restores
byte-identical, SHA-256-pinned *mirrors* from the owner's sister GitHub repos
(`registry/data_manifest.json`). Hash pins prove mirror integrity, **not** organizer
authentication. External layers are free/official (USGS GeoDAWN DOI 10.5066/P93LGLVQ,
USGS 3DEP, GDR 1391 CC BY 4.0) — see `registry/sources.json`.

## Labelling rule (no exceptions)

Every number is **HOLDOUT-DTI** (evaluator version, # withheld positives, 95 % CI),
**OWNER-REPORTED** (copied from the owner's brief), or **ORGANIZER-CONFIRMED** (organizer
receipt only). A projection is never written as a score. Leaderboard estimates for unscored
files are **NOT ESTIMABLE** unless an instrument validated on live orderings is named with it.

## Limitations (explicit)

* No DrivenData credentials in sandbox → cannot submit or fetch the live leaderboard here;
  submission is a manual owner step on the DrivenData form (see executive summary).
* CPU sandbox (2 cores / ~3 GB RAM observed 2026-10-27) → no GPU training; all K3 surfaces are
  CPU transforms by design.
* Outbound network from sandbox is restricted (github.com / codeload / PyPI class hosts);
  github.io and drivendata.org are not directly fetchable from inside — sister-repo *code* was
  audited from git clones pinned in `registry/focus9_registry.json`.
* The literal "≤70 % of dots within 3 px of *any* registry raster" uniqueness rule is
  geometrically impossible at winning budgets because the registry contains a 5 px lattice
  covering ≥99.8 % of the footprint at 3 px tolerance (IR-K3-02). This repo reports both the
  literal lattice number and the genuine-detector-raster gate, and never hides either.
