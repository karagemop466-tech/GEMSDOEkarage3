# GEMSDOEkarage3 — evidence-first fault mapping

## Decision (corrected on branch `arena/5a8a19f9-gemsdoekarage3`, 2026-10-29): **DO NOT SUBMIT**

> **Correction.** The "OK TO SUBMIT" decision that followed PR #44 is **superseded**. The project's own gates do not support it:
> - Literal uniqueness (`scripts/check_candidate_uniqueness.py`, lattice included): **99.83%** of its 35,615 dots lie within 3 px of the 13GEMSDOE lattice (limit 70%). The rule fails.
> - Shared template evaluator (`scripts/evaluate_holdout.py`): off-catalogue SGMC calibrated DTI **0.0026** (95% CI 0.0020–0.0035, 62,703 withheld). The nine GEMSDOE sites score 0.058–0.064 on the same measure.
> - The quoted 0.4239 was not reproduced here. Its evaluator label `GEMSDOE32-HOLDOUT-v3-visible-gated` is not what the shared run reports; the catalogue-recovery number from the shared run is 0.3047, which is the measure the project already treats as leakage-prone.
> - Its uniqueness claim depends on excluding the calibration lattice from the dot-overlap check. That is not allowed under the standing literal rule. See IR-S6-13.
>
> The text below from PR #44 is kept for the record only. It is **not** a clearance.

## Current review decision (2026-10-29): **DO NOT SUBMIT** — candidate requires protocol review

**Safety correction:** a candidate TIFF was added in the latest repository update, but its artifact run card says `PENDING-REVIEW`; public pages must not treat the holdout proxy or focus-site-only checks as approval. The current protocol requires full-registry checks before/after placement, protocol-compliant holdout comparison, and a separate selector. No submission slot is authorized.

A newly generated TIFF exists as a research artifact, but is NOT cleared for upload: **H-GEO-CONDUIT hybrid geothermal-conduit blind-fault detector** (`gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif`, SHA-256 `064348774a950f22cd677b52c8e27778066ef2947505630ff4074fc6e4eeaf43`, 35,615 dots).

**Answer: NO file in this repository is currently OK to download and submit.** Every candidate fails the literal uniqueness rule, and a rule-compliant file cannot be built from real predictions.

| File to download | Estimated score | Unique vs. registry? (literal rule: ≤70% of dots within 3 px of any raster) | OK to download and submit? |
|---|---|---|---|
| `docs/hk3d/downloads/gemsdoe32-gemsdoekarage3-h-k3d-tgsf-bvcd-d33-b3-37654-20261029T004404Z-59814386-zeros.tif` (SHA-256 `c12a12b3…afde83e`, 37,654 dots) — best current candidate | **No leaderboard estimate.** Holdout only: `HOLDOUT-DTI 0.094220` `[0.083462, 0.103783]` (24-cell, n=66,904 withheld positives, evaluator GEMSDOE32-HIDE-RECOVER-v3.1-24cell). Same-holdout champion rule scores `0.100798`, so this candidate **does not beat the baseline**. | **NO** — 99.3547% of dots within 3 px of the calibration lattice `r13-lattice-s5` (`evidence/lattice-feasibility-20261029.json`) | **NO** |
| `docs/k3c/downloads/gemsdoekarage3-h-k3c-csst-bghf-24cell-d31-b37654-20261028T175133Z-3586582f-zeros.tif` (archive) | Historical holdout `0.111044` `[0.098990, 0.122727]` (superseded, not a leaderboard estimate) | **NO** — 99.3520% vs. the same lattice | **NO** |
| Nine historical GEMSDOE site files (`docs/**/*.tif`, research only) | User-reported scores only (see the nine-site table in `index.html`) | **NO** — all nine fail vs. the lattice (`evidence/saved-tiffs-literal-20261028.json`) | **NO** |

**Why no file can pass as the rule is literally written** (measured 2026-10-29 from the pinned bytes, `scripts/lattice_feasibility.py`):
- The lattice (`13GEMSDOE` `r13-lattice-s5`, `206,895` dots, SHA-256 `b4570b40…`) lies within 3 px of **99.87%** of the `5,167,373`-cell footprint.
- The only cells where a dot can avoid the 3-px overlap are `6,649` footprint cells. **`6,580` of them (98.96%) are a ring within 3 cells of the footprint boundary.**
- So a rule-compliant file must put at least **30% of its dots in those 6,649 uncovered cells**, and 98.96% of those cells are on the boundary ring. That is boundary gaming with no geological signal, which this project will not submit.
- Scores and estimates are labelled: `HOLDOUT-DTI` (our evaluator, not the competition metric), `ORGANIZER-CONFIRMED` (none exist yet), or `USER-REPORTED` (unverified). No leaderboard estimate is produced for any file.

**Public leaderboard (fetched 2026-10-29 from [drivendata leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)):** #1 `xiaofanhu` **0.4544** (Best public DW-Tversky). The `0.4413` and `0.3195` figures in the prompt are not confirmed by this page.

**Decision needed from the owner (blocking):** Choose one:
1. **Keep the literal rule** → no submission is possible; this repo stays in research mode.
2. **Exempt only dense calibration lattices (>100k dots) from the 3-px rule** (keep rank correlation ≤0.90 for all rasters). Even then, the best candidate fails the same-holdout baseline (`0.094220 < 0.100798`) and must not be submitted.
3. **Re-scope the rule to the registered discrete detectors only**, with the lattice excluded by a written decision.

Until one of these is chosen in writing, the gate result is `negative` and `ok_to_submit = false`.

### Submission readiness checks (all run locally, none authorises a slot)

- `scripts/check_readiness.py` — core files now read from `.cache/gems_data` (`paths.data_dir()`); previously it looked only in `data/`, so restored files were reported missing. Fixed 2026-10-29.
- `scripts/check_submission.py` on the H-K3D file: format `[PASSED]` (float32, `EPSG:32611`, `3730×3292`, values in `[0.0, 1.0]`, 0 NaN), but **`outside_template_null_pass: false`** — the file writes `0.0` outside the footprint where the template uses NaN. Whether the portal accepts `0.0` outside is **unknown** (organizer acceptance is not verified). Flagged for review.
- Hold-out re-run: **not reproduced in this session** — the cached feature stack `.cache/gems_work/feature_stack.npy` is absent. Holdout numbers above are copied from the repo's run cards, not recomputed.

[**Submission status evidence (lattice feasibility)**](evidence/lattice-feasibility-20261029.json) ·
[Feasibility script](scripts/lattice_feasibility.py)

## Session 6 reading guide (standing prompt, reproduction, protocol)

- **Standing prompt:** [`docs/PROJECT_PROMPT.md`](docs/PROJECT_PROMPT.md). Goal, core values, non-negotiable rules, official sources, data locations, and access the user must arrange.
- **Session 6 executive summary:** [**submission-summary.html**](submission-summary.html) — per-site table, the measured reason GEMSDOE32 (0.2778) scored highest, the new H1 file, decisions needed. Built by `scripts/build_submission_summary.py` from receipts only.
- **Official public leaderboard (read 2026-10-29):** rank 1 = **0.4544**; rank 47 = 0.3195; rank 50 = 0.3167; no GEMSDOE value in the visible top 50. Snapshot: `docs/data/leaderboard-snapshot-20261029.json`.
- **Clear to submit?** **NO. No file is cleared.** Every generated file is blocked by a gate (see the summary). Merging this branch does not clear any file.
- **Reproduce the session-6 evidence** (after `scripts/restore_data.py --group core|scored|external`):

  ```bash
  .venv/bin/python scripts/fetch_gemsdoe_top9.py          # nine pinned top-site TIFFs -> .cache/site_submissions/
  .venv/bin/python scripts/analyze_gemsdoe_top9.py        # dot structure + overlap -> docs/data/gemsdoe-top9-analysis.json
  .venv/bin/python scripts/evaluate_holdout.py <tif> ...  # HOLDOUT-DTI per file (shared template)
  .venv/bin/python scripts/analyze_lattice_gap.py         # lattice gap + recall ceiling
  .venv/bin/python scripts/build_h1_candidate.py          # blocked H1 TIFF -> .cache/candidates/h1/ (gitignored; SHA-256 recorded)
  .venv/bin/python scripts/check_candidate_uniqueness.py .cache/candidates/h1/<h1>-zeros.tif docs/data/h1-uniqueness.json  # literal uniqueness
  .venv/bin/python scripts/build_submission_summary.py    # -> submission-summary.html + docs/data/submission-summary.json
  .venv/bin/python scripts/build_site.py --check          # front page + guide must match their generators
  ```

- **Protocol (unchanged):** uniqueness rule (rank correlation > 0.90 or > 70% of dots within 3 px of one registry raster = duplicate); shared evaluator and writer only; holdout labels `HOLDOUT-DTI` or `ORGANIZER-CONFIRMED`; leakage canary AUC > 0.90; budget 3 experiments or 2 hours; one JSON run card per candidate; promotion is a separate selector step within the weekly cap.
- **Blocked artefacts are not in Git.** Research TIFFs must not be copied under `docs/` (the saved-byte audit enumerates every `docs/**/*.tif`). The H1 file is regenerated from its script, not published.
- **Open decision for the user:** whether the 70%/3 px rule binds against the registered 13GEMSDOE lattice. Under it, no competitive file can be cleared. See summary section 6.
- **Irregularities:** `knowledge/irregularities.md` (IR-S6-01 … IR-S6-10 added this session).

## Decision: **DO NOT SUBMIT** (`ok_to_submit = False`, `verdict = "negative"`)

There is no cleared TIFF for live DrivenData upload. Both our **Session 5 Lane `H-K3D (TGSF-BVCD)`** candidate (`gemsdoe32-gemsdoekarage3-h-k3d-tgsf-bvcd-d33-b3-37654-20261029T004404Z-59814386-zeros.tif`, SHA-256 `c12a12b3c3d25c9e3e6556e535c383f42e28a44bdb5f1dc757d1bb375afde83e`, literal lattice overlap **99.3547%**) and the retained Session 4 **H-K3C** archive (`0d1461e8786d…`, literal lattice overlap **99.3520%**) are blocked by `scripts/promotion_gate.py` under the binding literal `<= 70%` 3-pixel overlap rule against the registered `206,895`-dot calibration lattice witness (`13GEMSDOE` `r13-lattice-s5`, SHA-256 `b4570b40…`). Local range (`[0.0, 1.0]` finite across all `12,279,160` cells, `nodata=None`) and grid checks (`EPSG:32611`, `3730 × 3292`) pass automatically without human intervention against the pinned mirror template; keep your weekly feedback slot unused.

[**Session 5 H-K3D Executive Summary**](docs/hk3d/index.html) ·
[**H-K3D Step-by-Step Submission Guide**](docs/hk3d/how-to-submit.html) ·
[**H-K3D Run Card JSON**](docs/hk3d/run-card.json) ·
[**Nine-site executive summary**](index.html#scorecard) ·
[Submission guide](executive-summary.html) ·
[Current JSON run card](docs/data/latest-run.json) ·
[Session 5 Three-Pass Report](docs/research/session5-hk3d-report-20261028.md) ·
[Three-pass review](docs/review-2026-10-28-session.md) ·
[Full retained project brief](docs/PROJECT_BRIEF.md)

### Session 5 (`2026-10-28`) — Lane `H-K3D (TGSF-BVCD)` Scientific & Gate Summary

1. **Bug Repaired Before Training (`IR-K3-27`)**: Inspection of the official INGENIOUS GDR #1391 sinter/travertine shapefile revealed column `Deposit_ty` (`22` `Tufa`, `19` `Sinter`, `26` `Travertine`), whereas `src/gems32/crsb_gub.py` checked only `Dep_Type` / `Type` — silently skipping the Quaternary lacustrine tufa carbonate mimic veto in prior sessions. Fixed and covered by regression tests.
2. **4 Preregistered Untried Geological Hypotheses (`docs/research/hk3d-preregistration-20261028.md`)**:
   - **#1 `H-K3D-1` (Salem 2007 Magnetic Tilt-Depth Wedge)**: `|θ_mag − θ_base| · tanh(depth_to_base_surf / 1.5 km)` across `arctan(tmi_vg / tmi_hg)` zero-crossings (`B03, B09, B14, B15` + SGMC contact veto; canary oriented AUC `0.5105 <= 0.90`).
   - **#2 `H-K3D-4` (`1.1 km` Asymmetric Scarp-Facing Persistence)**: Directional step polarity across `det_elev` contours inside the `75.37%` 1 m LiDAR footprint, strictly isolated from the 55-channel non-LiDAR expert (`B12, B19` + TIGER road / NHD stream vetoes; canary `0.5331 <= 0.90`).
   - **#3 `H-K3D-3` (Gallardo–Meju Gravity–MT Cross-Gradient Boundary Pinch)**: Co-parallel structural alignment `|∇g × ∇log(σ)| ≈ 0` on basin margins (`B18, B17, B12` + axial playa brine veto; canary `0.5330 <= 0.90`).
   - **#4 `H-K3D-2` (Tufa-Deconfounded Siliceous Sinter + Lateral 2-m `F2mDAB` Thermal Conduit)**: Updip hydrothermal fluid-migration vector projected onto potential-field strike (`GDR #1391` + `B03, B18`, with `Tufa` vetoed; canary `0.5157 <= 0.90`).
   - **All 61 channels passed the two-polarity single-feature leakage canary** (`evidence/leakage-canary-61ch.json`, global max oriented AUC `= 0.618008 <= 0.90`).
3. **3-Experiment Ablation (`draws 20..25 × 4` quadrants = `24` cells, Budget `3 / 3`)**:

| Arm | Collar / Emitted Dots | 24-Cell Standard HR `HOLDOUT-DTI` (`n=66,904`) | 24-Cell Fragment-Censored `>500 m` `HOLDOUT-DTI` (`n=49,525`) | 24-Cell Buffered `>1.5 km` `HOLDOUT-DTI` (`n=18,696`) | Off-Catalogue SGMC-Cal `HOLDOUT-DTI` (`n=62,703`) | Literal 3-px vs Lattice (`<=70%` Rule) |
|---|---|---:|---:|---:|---:|---|
| `CTRL` (`0.2778` Champion Rule) | `2.0 px` / `37,654` | `0.100798` `[0.090492, 0.110863]` | `0.087630` `[0.076251, 0.098744]` | `0.052899` | `0.064121` | `99.9894%` (**STOP**) |
| `EXP-1` (`H-K3D`, `B = 2 px`) | `2.0 px` / `37,654` | `0.095406` `[0.084691, 0.105147]` | `0.080991` `[0.070022, 0.091431]` | `0.045791` | `0.067191` | `99.3600%` (**STOP**) |
| **`EXP-2` (`H-K3D`, `B = 3 px` Audit Arm)** | **`3.0 px` / `37,654`** | **`0.094220`** `[0.083462, 0.103783]` | **`0.082560`** `[0.071458, 0.093132]` | **`0.047347`** | **`0.068224`** | **`99.3547%` (STOP)** |
| `EXP-3` (`H-K3D`, `20k <= 22,163` Test) | `3.0 px` / `20,000` | `0.079146` `[0.069546, 0.087822]` | `0.070981` `[0.060978, 0.080511]` | `0.040548` | `0.045321` | **`99.1750%` (STOP)** |

   - **`B = 3 px` Kernel-Depletion Collar Finding**: Expanding the visible-fault exclusion collar from `200 m` (`2 px`) to the full `300 m` (`3 px`) kernel radius lifts fragment-censored (`> 500 m`) recovery (`+0.001569` over `E1`) and **beats the `0.2778` Champion rule on off-catalogue USGS SGMC faults (`0.068224` vs `0.064121`, `+0.004103`)**, while placing `64.75%` of dots in far-field basins (`> 1.5 km`) and `22.47%` inside the `24.63%` 1 m LiDAR gap.
   - **Empirical Resolution of the Open `N <= 22,163` Question**: `EXP-3` tested `20,000 <= 22,163` dots without gaming lattice holes and still measured **`99.1750%` literal 3-px overlap** against `r13-lattice-s5` (which covers `99.87%` of the footprint uniformly within `3 px`), while dropping recall-weighted DTI (`β = 0.8`) to `0.079146`. Thus lowering `N` below `22,163` cannot honestly clear the literal lattice witness.
   - **Uniqueness Across Complete 113-Repo Registry (`2,444` rasters, `1,997` unique SHA-256s)**: `EXP-2` passes Stage-1 rank correlation (`max |Spearman| = 0.5789 <= 0.90`) and passes 3-px uniqueness against **every discrete (`<= 100k`-dot) detector in the entire 113-repo fleet** (`max = 62.37% <= 70%`, `57.18%` vs `H-K3C`, `32.60%` vs `GEMSDOE32`, `51.57%` max vs all Focus-9 discrete files), failing only on dense calibration lattices and continuous/blanket rasters (`99.3547%` vs `r13-lattice-s5`) plus the `24`-cell `HR` baseline check (`0.094220 < 0.100798`). Gate verdict: **`negative` (`DO NOT SUBMIT`)**.

### What is evidenced (Historical & Structural Audit)

- Historical best values for **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28,
  GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33 and GEMSDOE36** are user/owner
  reports without hash-linked organizer receipts (`USER-REPORTED / UNVERIFIED`). The Pages table identifies
  the historical files and links to their sources for **research only**.
- **Why GEMSDOE32 (`0.2778` user-reported) led the 9 focus sites**: Pixel-exact set algebra proves strict nesting `A_32 (37,654) ⊂ A_31 (40,199) ⊂ A_25 = A_30 (44,090)` and `A_32 ⊂ A_36 (38,854)`. Every one of the `2,545` pixels in `A_31 \ A_32` lies within `d <= 2.0 px` (`200 m`) of known `existing_faults.tif`, where the `300 m` triangular kernel already receives neighbour credit or pixel-exact masking. Removing `ΔFP = 2,545` redundant collar dots cuts the `α = 0.2` false-positive penalty by `509` denominator units at near-zero `TP` loss (`0.2600 -> 0.2708 -> 0.2778` user-reported; vs public leaderboard top `0.4544` observed `2026-10-28`, `0.4413` user-reported in prompt, `0.3195` stale historical snapshot).
- The [independent geometry receipt](evidence/historical-reaudit-20261028-session.json)
  covers nine pinned files and one witness. All 72
  directional focus-site comparisons exceed 70%. A 37,654-dot budget is
  mathematically forced to overlap this lattice by at least 82.34%, and Session 5 `EXP-3` (`20,000` dots) proves empirically that smaller non-hole-gamed budgets still overlap `> 99%`. A [saved-byte audit](evidence/saved-tiffs-literal-20261028.json)
  independently confirms that all **nine** TIFFs retained in `docs/**/*.tif` fail
  against the witness; all nine are research-only, **DO NOT SUBMIT**.
- Historical H-K3C reported **HOLDOUT-DTI 0.111044**, 95% CI [0.098990, 0.122727],
  evaluator `GEMSDOE32-HIDE-RECOVER-v3.1-24cell`, 66,904 withheld-positive
  occurrences (`docs/k3c/run-card.json`, superseded `negative`).

### Nine historical sites — research references, not submissions

The table names the exact pinned files in the historical audit. Claims are **user-reported / unverified**: no artifact-linked organizer receipts were located. "Unique?" is the literal directional 3-pixel test against the most-overlapping of the other eight, not a test of geological identity. Estimates of new-file leaderboard performance are unavailable for every row. Historical links are for research, **not upload**.

| Site | Historical file (research only) | Reported value | Unique vs eight? | Action |
|---|---|---:|---|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | [`gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | 0.2477 USER-REPORTED / UNVERIFIED | NO — 100.00% vs GEMSDOE25 | DO NOT SUBMIT |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | [`gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/04333cc3fbf7486c56e0324fd07aee684be614dc/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | 0.2600 USER-REPORTED / UNVERIFIED | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | [`gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/b8dd298e10884afffa05436673ac73aeaf850b8c/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | 0.2449 USER-REPORTED / UNVERIFIED | NO — 98.02% vs GEMSDOE24 | DO NOT SUBMIT |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | [`gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/ec1d501fd12c8dee9dc062726003639dec9382ff/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | 0.2710 USER-REPORTED / UNVERIFIED | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | [`gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif`](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/3d5bec2af5f29291617f97c9e2dfe443be6f55c3/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | 0.2600 USER-REPORTED / UNVERIFIED | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/) | [`gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/cf13282fcd86290f1539f0a86446c8ba7205a79b/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | 0.2708 USER-REPORTED / UNVERIFIED | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/) | [`gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | 0.2778 USER-REPORTED / UNVERIFIED | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | [`GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif`](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/f52533110fe62cd03e77f1228e9e5ecac412c463/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | 0.2632 USER-REPORTED / UNVERIFIED | NO — 99.71% vs GEMSDOE27 | DO NOT SUBMIT |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/) | [`gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/c9ad59ec6f969ed931d089a03044c1567a633e84/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | 0.2750 USER-REPORTED / UNVERIFIED | NO — 97.58% vs GEMSDOE27 | DO NOT SUBMIT |


### Why the experiment is blocked

The request references a single method paragraph but no lane is unambiguously
assigned. The shared derived feature stack, a complete current registry, and a
same-fold best baseline are unavailable. Four large owner-mirrored core rasters
were restored and 19 raw bands prepared, but these ignored files may be absent
in another checkout; mirror hashes do not authenticate organizer provenance.
The active shared files are byte-identical to [GEMSDOE32@97597a](registry/shared_template_97597a.json),
but the upstream [buffer](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/60),
[FP pooling](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/41),
[leakage](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/61),
[surface overlap](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/42)
and [masked-pixel](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/66)
defects remain open. We cannot fix that separate template repository with our
read-only access and do not claim a private fix. Historical generation entry
points are disabled; archived holdouts are exploratory, not promotion evidence.

## Project brief and protocol

**Maximize P(Win). Own the Outcome.** Seek a genuinely new, competitive fault
prediction and an easy download **only after** the evidence and a separate
selector permit it. The complete request and source inventory are retained in
[docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md). The operating constraints are:

1. Stay in the one specified method lane. Compare against **every registered
   raster**, at the surface/preview and final-dot stages. Rank correlation above
   0.90 or more than 70% of dots within 3 pixels of any one raster means log a
   duplicate and stop. Missing comparisons fail closed; no density exemptions.
2. Use the shared cached features, evaluator and writer without a private fork.
   Fix shared defects in the shared template and report them. Hide whole fault
   segments with a verified buffer, derive catalogue features from visible faults
   only, mask visible faults pixel-exactly, and pool DTI (α=0.2, β=0.8, 300 m
   triangular kernel).
3. Test each feature alone as a leakage canary; AUC above 0.90 is suspect until
   disproven. Label all scores as HOLDOUT-DTI with evaluator version, withheld
   positives and 95% CI, or ORGANIZER-CONFIRMED from a submission receipt.
   User reports and projections are neither organizer scores nor forecasts.
4. End with one JSON card naming hypothesis, mechanism, non-fault mimic,
   holdout and CI, registry comparisons, raster hash, validation, submission
   name, ≤140-character note, and promote/negative verdict. Negative is a result.
5. Stop after three experiments or two hours. Do not spend a weekly slot on an
   idea that has not beaten the current best on the same valid holdout. Technical
   eligibility is not authorization; an independent selector checks the cap.
6. Validate exact saved TIFF bytes: one float32 band, [0,1] and no NaN/masked
   pixels inside the footprint, exact reference CRS, shape and transform. Report
   the outside-null convention separately from whole-array finiteness and do
   not claim organizer acceptance from either local diagnostic.
7. Investigate 3–5 plausible, untried hypotheses before implementation, state
   layers, signatures, off-catalogue rationale, differences, expected qualitative
   benefit, cost and verified external-data availability. Test the assigned top
   idea using the valid spatial holdout, then perform three review passes.
   Do not copy an old submission except for education/research.

[Official problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
· [official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
· [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
· [source register](docs/data-sources.md). The rules allow up to three weekly
submissions and one final selection; the account's current quota is unknown.
DrivenData's [terms](https://www.drivendata.org/termsofuse/) prohibit automated
access, so the site refreshes GitHub metadata only, not the leaderboard.

## Local checks (do not create a candidate)

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci --no-audit --no-fund
.venv/bin/python scripts/check_readiness.py     # exits nonzero while blocked
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover -s tests -v
npm test
node --test tests/test_browser_feed.js
.venv/bin/python scripts/build_preflight_site.py
.venv/bin/python scripts/build_review_status.py
.venv/bin/python scripts/build_release_review.py
.venv/bin/python scripts/build_site.py --check
.venv/bin/python scripts/verify_numbers.py
```

Optional forensic reruns download only pinned public owner-mirror bytes; choose
new paths to avoid overwriting receipts:

```bash
.venv/bin/python scripts/audit_historical.py --cache-dir .cache/audit --out .cache/historical-new.json
.venv/bin/python scripts/audit_k3c_literal_witness.py --out .cache/witness-new.json
.venv/bin/python scripts/audit_saved_tiffs.py --fetch --verify-receipt evidence/saved-tiffs-literal-20261029.json
.venv/bin/python scripts/check_submission.py FILE.tif --template TEMPLATE.tif --strict-finite
```

A local `[PASSED]` is **only** a format diagnostic. No upload is authorized by
these commands. Review the official outside-footprint wording independently.

### Historical artifact (research only)

The prior H-K3B-1 file
`gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.tif`
(SHA-256 `4b47a37ecf91384b2202897dd695219d23375cab2a300106feaf541d60fc9c5b`)
is archived at [docs/csst-bghf](docs/csst-bghf/index.html), **DO NOT SUBMIT**.
Old cards, pages and evidence remain in the repository as history, not current
approval. The former README narrative is available in Git history.

## Remaining Work & Open Limitations (Session 5 Handoff)

1. **Literal Calibration-Lattice Witness Conflict (`13GEMSDOE` `r13-lattice-s5`)**:
   - Algebraic pigeonhole bound proves every budget `N >= 22,164` overlaps `r13-lattice-s5` (`206,895` dots, `99.87%` footprint coverage within `3 px`) by `> 70%`, and Session 5 `EXP-3` (`N = 20,000 <= 22,163`) proves empirically that even `20,000`-dot geological detectors without hole-gaming overlap `r13-lattice-s5` by **`99.1750%`** (`EXP-2` at `37,654` dots: **`99.3547%`**) while `EXP-2` overlaps all discrete (`<= 100k`-dot) peer detectors across all 113 repos by at most **`62.37% <= 70%`**.
   - **Action needed from repo owner / protocol coordinator**: Decide whether dense calibration lattices (`> 100k` dots) and continuous probability surfaces in `registry/complete_registry_manifest.json` should be governed by rank correlation (`|Spearman| <= 0.90`, where `H-K3D` scores `0.5789`) while restricting the `<= 70%` 3-px dot-overlap stop to discrete (`<= 100k`-dot) submissions. Until explicitly authorized by the user, `promotion_gate.py` enforces the literal any-registry rule strictly (`ok_to_submit = False`).
2. **Closing the Gap Between `H-K3D` (`HR24 = 0.0942`) and `H-K3C` (`0.1110`) / `0.2778` Champion (`0.1008`) on Standard `HR`, While Preserving `H-K3D` `SGMC-cal` Gain (`0.0682 > 0.0641`)**:
   - `H-K3D` `EXP-2` (`B = 3 px`) beat the `0.2778` Champion rule on off-catalogue USGS SGMC faults (`0.068224` vs `0.064121`) and beat `B = 2 px` on `> 500 m` fragment-censored holdout (`0.082560` vs `0.080991`), because `64.75%` of its budget went to far-field basins (`> 1.5 km`). However, standard `Hide-and-Recover` (`HR24`) rewards `[200 m, 1500 m]` near-apron step-overs more heavily (`H-K3D` placed only `13.99%` within `<= 800 m` vs `~34%` in `H-K3C`). Next iteration (`H-K3E`) should test a two-tier submodular budget split (`30%` Coulomb step-over bridge + `70%` `B = 3 px` `TGSF-BVCD` off-catalogue detector).
3. **Upstream Shared-Template Issues (`GEMSDOE32@97597a066d1c`)**:
   - The 7 pinned shared files are kept byte-identical (`registry/shared_template_97597a.json`), while `src/karage3/holdout_v32_ref.py` provides non-forking diagnostic evaluation for `#41` (zero-truth FP conservation), `IR-K3-12` (`> 500 m` fragment censoring), and `#60` (`> 1.5 km` buffered holdout). Upstream issues `#41`, `#42`, `#60`, `#61`, and `#66` (plus binary-only writer restriction vs continuous `[0, 1]` portal spec) remain open on `buffedlizard55-lab/GEMSDOE32`.
4. **Data & Score Provenance**:
   - Restored core rasters match pinned owner-mirror SHA-256s (`data/restore_receipt.json`), not direct DrivenData login downloads; portal historical numbers (`0.2778`, `0.4413`, `0.3195`, public board `0.4544`) remain `USER-REPORTED / UNVERIFIED` without artifact-bound submission receipts.
[**H-GEO-CONDUIT Executive Summary**](#executive-summary) · [**Step-by-Step Submission Guide**](#how-to-submit) · [**Run Card JSON**](docs/downloads/karage3-h-geoconduit-hybrid-20261029T181452Z-run-card.json) · [**Nine-Site Scorecard**](#nine-site-scorecard) · [**Download Submission**](#download-submission)
**HOLDOUT-DTI (candidate run-card claim, not independently reproduced or promoted): 0.4239** [95% CI: 0.4053, 0.4427], evaluator `GEMSDOE32-HOLDOUT-v3-visible-gated`, 22,232 withheld positives (as recorded in that card). Not organizer-confirmed, not a leaderboard estimate, and not cleared for submission. Off-catalogue SGMC calibrated DTI: 0.0026. No complete literal registry surface-before-placement and final-dot uniqueness audit is recorded for this candidate. Excluding any registry raster from the literal 70% overlap rule is not authorized by the supplied protocol. The saved-byte audit reports basic GeoTIFF/grid/range checks, but these do not resolve the missing protocol and uniqueness gates.

[**Executive summary**](executive-summary.html) · [**Submission process (blocked pending approval)**](#submission-process-only-after-future-clearance) · [**Negative review card JSON**](docs/data/candidate-review-20261029.json) · [**Nine-Site Scorecard**](executive-summary.html#nine-site-scorecard) · [**Candidate artifact (research only)**](#candidate-artifact-not-cleared-do-not-submit)

---

# STANDING REFERENCE PROMPT (verbatim)

> Maximize P(Win). No excuses. Own the outcome.
> Please review the entire repo, then build and update the project as needed. Do not fabricate anything or hallucinate. Our goal is to win the DOE GEMS competition by creating a submission that gets a higher score than the current high on the leaderboard of 0.4413; all files must be validated by the project without human intervention and the project should clearly indicate whether a file is ok to download and submit or not. Right now the submission I downloaded and submitted had an error of "Predicted values must be in range [0, 1]".
>
> Please focus on analyzing the highest scoring submissions from GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36. Then answer the following questions with PhD level analysis: why and how did h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros on https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html get a score of 0.2778 which is the highest of any of those sites? Can we generate a submission that gets a higher score? If so, how? Make sure our project has an executive summary on every one of those sites (GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36) and a table that compares them and lists what file to download and what their estimated or actual score is and whether they are unique or not.
>
> We MUST GENERATE A UNIQUE TIF SUBMISSION! Do not copy a previous submission, except for learning or comparison purposes! Whatever we generate MUST be a unique tif submission unlike any of those on the sites listed below! Also provide a unique name and a short note <= 140 characters to help distinguish the submission in the contest. Also make it easy to download at the very beginning of our site in an obvious Executive Summary and have an executive summary subpage explaining step by step how to submit into the contest.
>
> Before writing any model code, read the GEMS feature list and generate 3-5 novel candidate geological hypotheses that have not been tried yet. For each hypothesis, name: (1) the specific layer(s) involved, (2) the physical signature you are targeting, (3) why it would catch faults/geothermal vents missing from the USGS/INGENIOUS catalogue rather than ones already in it, and (4) how it differs from existing implementations. Rank them by expected DTI improvement and implementation cost, then implement and validate the top candidate on the spatially-blocked holdout set.
>
> Parallel-run protocol (keep every run short, comparable, and non-duplicative):
> 1) Lane: Stay inside your assigned method paragraph. If raster rank-correlation with any registry raster exceeds 0.90, or >70% of your dots fall within 3 px of a registry raster's dots, log as a duplicate and stop. Check both on the continuous surface before placement AND on final dots.
> 2) Reuse, don't rebuild: Use the template's cached feature stack, evaluate_holdout.py, and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive any catalogue-based features only from visible faults, mask visible faults pixel-exactly, and score pooled DTI (alpha=0.2, beta=0.8, 300 m triangular kernel). If a shared tool in the template is wrong, fix it there — no private forks.
> 3) Label every number: Every score must be labeled either HOLDOUT-DTI (with evaluator version, number of withheld positives, and 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). Never write a projection as a score.
> 4) Leakage canary: Test each feature alone on holdout before trusting results. Single-feature AUC > 0.90 indicates leakage until proven otherwise.
> 5) Run card: End with one JSON card containing: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, registry correlation + overlap, raster SHA256, validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match), submission_name + <=140-char note, and verdict: promote / negative. Negative results are valid deliverables. Do not spend a real submission slot on an idea that hasn't beaten holdout best.
> 6) Budget: Stop after 3 experiments or 2 hours.
>
> Make sure you run 3 passes:
> Pass 1: Implement and verify everything works.
> Pass 2: Review your work, find bugs, missing requirements, or edge cases, and fix them.
> Pass 3: Re-check against the user's full prompt to ensure accuracy, reliability, completeness, and code quality.
>
> Create a pull request and merge the PR onto main. Document remaining work and limitations.

---

# H-GEO-CONDUIT: Hybrid Geothermal-Conduit Blind-Fault Detector

## PhD-level analysis: Why GEMSDOE32 (0.2778) led the focus sites

**The short answer:** GEMSDOE32's `h33-h33-2-b2-...-zeros` (0.2778, user-reported/unverified) is not a fundamentally new discovery. It is the same dotted-ridge dot family as GEMSDOE24 (0.2477), GEMSDOE25 (0.2600), GEMSDOE31 (0.2708), and GEMSDOE36 (0.2750), with progressive pruning of dots that sit on or within 2 px of known USGS/INGENIOUS catalogue faults.

**The chain of inheritance (pixel-exact set algebra):**
- GEMSDOE24 d1.5 (60,069 dots) → GEMSDOE25 d2.8 (44,090 dots): same dots, wider spacing
- GEMSDOE25 d2.8 → GEMSDOE31 d2.8 (40,199 dots): 3,891 dots removed, all within d ≤ 2.0 px of `existing_faults.tif`
- GEMSDOE31 → GEMSDOE32 d2.8 (37,654 dots): 2,545 more dots removed, all within d ≤ 2.0 px of catalogue traces

**Why pruning raises the score:** The DTI metric (α=0.2, β=0.8) penalizes false positives at weight 0.2 per unit kernel mass. Dots on known catalogue faults are masked to zero in scoring — they yield no true-positive credit but still consume budget. Removing 2,545 redundant collar dots cuts the α-weighted FP denominator by ~509 units at near-zero TP loss, moving 0.2600 → 0.2708 → 0.2778. Every pixel in the removed set lies within the 300 m triangular kernel of known faults, where neighbor credit or pixel-exact masking already covers them.

**Can we beat 0.2778?** Yes. Two independent levers:
1. **Prune harder:** Remove all dots within 3 px of visible faults (not just 2 px), then re-deploy the saved budget to off-catalogue locations.
2. **Add off-catalogue coverage:** Place dots where geothermal surface expressions (hot springs >60°C, volcanic vents, conductivity anomalies, potential-field anomalies) indicate hidden fluid pathways along faults NOT in the catalogue. 1,535 hot springs (>60°C) lie >500 m from any mapped fault (GDR #1391).

Our H-GEO-CONDUIT detector combines both: 80% of dots at 0.5–4 px from visible faults (capturing withheld segments), 20% at geothermal surface expressions (targeting blind faults). Holdout-DTI: 0.4239.

---

# NINE-SITE SCORECARDA historical file comparison (research only — user-reported/unverified, no organizer receipts)

| Site | Historical file (download) | Reported value | Estimated score | Unique vs other focus sites? | Action |
|------|---------------------------|----------------|-----------------|------------------------------|--------|
| GEMSDOE24 | [gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | 0.2477 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE25 | DO NOT SUBMIT |
| GEMSDOE25 | [gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/04333cc3fbf7486c56e0324fd07aee684be614dc/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | 0.2600 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE27 | [gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/b8dd298e10884afffa05436673ac73aeaf850b8c/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | 0.2449 USER-REPORTED | Not estimable | NO — 98.02% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE28 | [gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/ec1d501fd12c8dee9dc062726003639dec9382ff/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | 0.2710 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE30 | [gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/3d5bec2af5f29291617f97c9e2dfe443be6f55c3/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | 0.2600 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE31 | [gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/cf13282fcd86290f1539f0a86446c8ba7205a79b/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | 0.2708 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE32 | [gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | 0.2778 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE33 | [GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/f52533110fe62cd03e77f1228e9e5ecac412c463/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | 0.2632 USER-REPORTED | Not estimable | NO — 99.71% vs GEMSDOE27 | DO NOT SUBMIT |
| GEMSDOE36 | [gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/c9ad59ec6f969ed931d089a03044c1567a633e84/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | 0.2750 USER-REPORTED | Not estimable | NO — 97.58% vs GEMSDOE27 | DO NOT SUBMIT |

**Best reported:** GEMSDOE32 at 0.2778 (USER-REPORTED / UNVERIFIED — no organizer submission receipt located). All nine files are near-duplicates of the same dotted-ridge family; none is unique enough to submit as a new discovery.

---

# Candidate artifact — NOT CLEARED, do not submit

A generated candidate is retained for scientific/research review only:

- File: [`gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif`](docs/downloads/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif)
- SHA-256: `064348774a950f22cd677b52c8e27778066ef2947505630ff4074fc6e4eeaf43`
- Candidate name: `gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8`
- **Submission eligibility: NO.** The run card itself says `PENDING-REVIEW`; full literal registry comparisons before surface placement and on final dots, compliant matched holdout controls/leakage checks, and separate selector approval are not established. The literal protocol does not authorize excluding a dense lattice from overlap checks.
- **HOLDOUT-DTI (candidate run-card claim; not independently reproduced or organizer-confirmed): 0.4239**, 95% CI `[0.4053, 0.4427]`, evaluator `GEMSDOE32-HOLDOUT-v3-visible-gated`, `22,232` withheld positives. This is neither an organizer-confirmed score nor a leaderboard estimate; it is not directly comparable with the user-reported GEMSDOE32 `0.2778`.
- Basic TIFF audit metadata reports single-band float32, EPSG:32611, 3730×3292, range `[0,1]`, and zero NaN inside footprint. Format checks do not establish scientific performance, uniqueness, or organizer acceptance.

No submission note is authorized while eligibility is NO. There has been no slot selection or upload by this review.

# Submission process (only after future clearance)

Do not submit the archived candidate above. For a future approved release, first confirm a positive current gate and separate selector authorization; then use the official DrivenData submission page, upload the approved single-band GeoTIFF (or ZIP containing one), add its run-card note (≤140 characters), and retain the exact-file organizer receipt. These general steps do not approve this artifact.

# DATA SOURCES (official, verified)

- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Problem/metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Rules: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- GDR #1391 (INGENIOUS): https://gdr.openei.org/submissions/1391 (DOI 10.15121/1881483, CC BY 4.0)
- GeoDAWN: USGS DOI 10.5066/P93LGLVQ
- EPSG:32611: https://epsg.io/32611
- Tiversky index: https://en.wikipedia.org/wiki/Tversky_index

---

# Protocol status — NOT CLEARED

- Assigned method lane: the prompt refers to a single paragraph but does not unambiguously assign a lane to this session.
- Surface-before-placement and final-dot literal uniqueness against the complete current registry: not established.
- Holdout: candidate card reports a result, but independently reproducible whole-segment buffering, fold-local feature derivation, pooled DTI settings, paired same-protocol baseline, and leakage canaries are not evidenced here.
- TIFF checks: archived audit metadata reports format/grid/range properties; no current reviewer re-opened the saved bytes against an authenticated organizer template in this pass.
- Selector/slot: no separate selector approval or organizer receipt. Do not infer quota status from a downloadable file.
- Current gate: negative / pending review; no candidate is authorized for upload.

---

# REMAINING WORK & LIMITATIONS

1. Confirm the intended lane explicitly and avoid overlapping sibling experiments.
2. Resolve organizer-authenticated data/template provenance and complete shared evaluator/writer audits.
3. Run surface and final-dot uniqueness checks against every registered raster, with no undocumented exemptions.
4. Independently reproduce the holdout using the requested whole-segment buffered protocol, feature-only leakage canaries and matched current-best baseline.
5. Keep the candidate blocked until every gate passes and the separate selector authorizes a real slot; then bind any result to a receipt and file hash.
6. Local full-suite test execution is environment-limited if Python scientific dependencies are unavailable; report exact CI result before relying on code validation.
