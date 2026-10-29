# Session 5 Three-Pass Scientific & Verification Report — Lane `H-K3D (TGSF-BVCD)`

- **Date (UTC):** `2026-10-28` / `2026-10-29T00:44:04Z`
- **Branch:** `arena/185322d1-gemsdoekarage3`
- **Release Gate Verdict (`scripts/promotion_gate.py`):** **`negative` (`ok_to_submit = False`, `DO NOT SUBMIT`)**
- **Audited Research Artifact:** `docs/hk3d/downloads/gemsdoe32-gemsdoekarage3-h-k3d-tgsf-bvcd-d33-b3-37654-20261029T004404Z-59814386-zeros.tif`
  - **GeoTIFF SHA-256:** `c12a12b3c3d25c9e3e6556e535c383f42e28a44bdb5f1dc757d1bb375afde83e`
  - **Single-TIFF ZIP SHA-256:** `ec767f446017861799b0c2f555e37628c285905c55e3d6def84093e70765fc34`
  - **Submission Note (`97 <= 140` chars):** `H-K3D E2 TGSF-BVCD d=3.3 B=3 37654d [0,1] zeros; 24c HR 0.0942, FRAG500m 0.0826 (DO NOT SUBMIT)`

---

## 1. Previous-Session Next Steps Executed First

Before writing any new model code, we executed the open next steps left by Sessions 2–4 (`docs/review-2026-10-28-session.md`, `research/2026-10-28-ccl.md`, `AGENTS.md`):
1. **Standing Prompt Recorded:** Verified and updated the standing verbatim user prompt in `README.md` and `docs/PROJECT_BRIEF.md`.
2. **Tufa Carbonate Mimic Bug Repaired (`IR-K3-27`):** Inspected `.cache/gems_data/external/gdr_1391_sinter/Sinter_Travertine_GreatBasin.dbf` and discovered its deposit-type column is `Deposit_ty` (`22` `Tufa`, `19` `Sinter`, `26` `Travertine`), whereas `src/gems32/crsb_gub.py` checked only `("Dep_Type", "Type")`. Fixed in `src/gems32/crsb_gub.py` and rebuilt `crsb_gub_extra_16ch.npy` before training.
3. **Complete 113-Repo Registry Assembled (`IR-K3-29`):** Added `karagemop466-tech/GEMSDOEkarage3` to `scripts/fetch_all_registry.py` (`SIBLING_REPOS`) and fetched all `113` public repositories (`2,444` rasters, `1,997` unique SHA-256s, `0` failures).
4. **Non-Forking Multi-Evaluator Holdout (`src/karage3/holdout_v32_ref.py`):** Kept all 7 shared template files byte-identical to `GEMSDOE32@97597a066d1c` (`registry/shared_template_97597a.json`) while evaluating all 24 cells (`draws 20..25 × 4` quadrants) under `#41` zero-truth FP conservation (`GEMSDOE32-HIDE-RECOVER-v3.1-24cell-fpconserved`), `IR-K3-12` `> 500 m` fragment censoring (`FRAG500M-v3.2`), `#60` `> 1.5 km` buffered holdout (`BUF1500M-v3.2`), pinned 8-cell `v3.0`, and off-catalogue `SGMC-CAL-v3.0`.
5. **Tested Both `B = 3 px` Depletion Collar (`EXP-2`) and `N = 20,000 <= 22,163` Lattice-Pigeonhole Regime (`EXP-3`):** Directly resolved the two primary open scientific questions from Sessions 2 and 4.

---

## 2. PhD-Level Structural & Mathematical Analysis of `GEMSDOE32` (`0.2778` User-Reported)

### 2.1 Exact Set-Algebraic Lineage Across the Focus-9 Sites
Pixel-by-pixel boolean comparison of the primary Focus-9 rasters (`evidence/nine-site-audit-hk3d-20261028.json`, `docs/data/historical-audit.json`) proves deterministic subset nesting:
- `GEMSDOE25` (`44,090` dots, `0.2600` `USER-REPORTED / UNVERIFIED`) `=` `GEMSDOE30` (`44,090` dots, `0.2600` `USER-REPORTED / UNVERIFIED`) inside the valid `5,167,373`-pixel footprint (`100.00%` identical in-footprint support; differing only in `-nan.tif` vs `-zeros.tif` outside-footprint encoding).
- `GEMSDOE31` (`40,199` dots, `0.2708` `USER-REPORTED / UNVERIFIED`) `⊂` `GEMSDOE25` (`3,891` dots pruned).
- **`GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, `37,654` dots, `0.2778` `USER-REPORTED / UNVERIFIED`) `⊂` `GEMSDOE31`** (`2,545` dots pruned, `0` dots added) AND **`GEMSDOE32` `⊂` `GEMSDOE36`** (`38,854` dots, `0.2750` `USER-REPORTED / UNVERIFIED`, which adds `1,200` PINN dots onto `GEMSDOE32`).

### 2.2 Why Removing Those Exact `2,545` Dots Raised the Score (`0.2708 -> 0.2778`)
Every single one of the `2,545` pixels in `A_31 \ A_32` satisfies Euclidean distance `0 < d(x, F_known) <= 2.0 px` (`200 m`) to `existing_faults.tif`. Under the official Distance-Weighted Tversky Index ([DrivenData Problem Page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [Mask Clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4)):
$$\mathrm{DTI} = \frac{\mathrm{TP}}{\mathrm{TP} + 0.2\,\mathrm{FP} + 0.8\,\mathrm{FN}}, \qquad K(d) = \max\!\left(0,\,1 - \frac{d}{3}\right)$$
1. Known catalogue pixels `F_known` (`60,988` px) are masked pixel-exactly during scoring, and unmasked hidden truth rarely parallels a mapped fault trace within `100–200 m` without already receiving `1/3`–`2/3` kernel support from crests at `d >= 2.1 px`.
2. Consequently, deleting those `2,545` `<= 2 px` boundary-collar dots leaves `TP` essentially invariant (`ΔTP ≈ 0`) while removing `ΔFP ≈ 2,545` pure false positives (`0.2 × 2,545 = 509` denominator penalty units), shifting DTI upward by the exact `~+0.0070` step observed between `0.2708` and `0.2778` (while `GEMSDOE36` adding `1,200` extra dots diluted precision back to `0.2750`).

### 2.3 Can We Beat `0.2778` Toward the `0.4413` / `0.4544` Frontier — and How?
- **Yes on off-catalogue physics, conditional on protocol resolution of the lattice witness:** In `EXP-2`, widening the depletion collar to the full `300 m` kernel radius (`B = 3.0 px`) and fusing our 4 `TGSF-BVCD` operators **already beat the `0.2778` Champion architecture on off-catalogue USGS SGMC faults (`0.068224` vs `0.064121`, `+6.4%` relative lift)** and beat `B = 2.0 px` on fragment-censored (`> 500 m`) holdout (`0.082560` vs `0.080991`).
- Reaching the `0.44–0.45` leaderboard regime requires combining (a) high-precision `<= 800 m` step-over/tip relay bridges (which drive `HR24`) with (b) deep basin/blind-conduit operators (`TGSF-BVCD`, which drive `SGMC-cal`), AND (c) an explicit owner/protocol amendment excluding dense calibration lattices (`> 100k` dots) from the literal `70%` peer-overlap stop.

---

## 3. Four Preregistered Untried Geological Hypotheses (`H-K3D-1..4`)

Locked prior to training in `docs/research/hk3d-preregistration-20261028.md` and `registry/preregistration_hk3d_20261028.json`:
1. **`H-K3D-1` (Rank 1, Low Cost) — Salem (2007) Tilt-Depth Wedge vs `depth_to_base_surf`:** Targets blind intrabasinal half-graben growth faults beneath `0.5–3 km` valley fill via `|θ_mag − θ_base| · tanh(B15 / 1.5 km)` across magnetic tilt zero-crossings (`B03, B09, B14, B15` + SGMC lithologic contact veto; canary AUC `0.510494`).
2. **`H-K3D-4` (Rank 2, Low Cost) — `1.1 km` Asymmetric Scarp-Facing Persistence:** Targets unmapped synthetic/antithetic piedmont fault scarps via directional cross-contour step persistence (`B12, B19`), zeroed inside the `24.63%` 1 m LiDAR gap and excluded from the 55-channel non-LiDAR expert (`MNOLIDAR_COL_INDICES_55`; canary AUC `0.533113`).
3. **`H-K3D-3` (Rank 3, Low Cost) — Gallardo–Meju (2003) Gravity–MT Cross-Gradient Pinch:** Targets clay-sealed range-front/relay faults via structural cross-gradient alignment `|∇g × ∇log(σ)| ≈ 0` (`B18, B17, B12` + axial playa evaporite veto; canary AUC `0.533026`).
4. **`H-K3D-2` (Rank 4, Low Cost) — Tufa-Deconfounded Siliceous Sinter + Lateral 2-m `F2mDAB` Thermal Conduit:** Targets blind hydrothermal upflow faults (`GDR #1391` sinter/wells + `B03, B18`) with `22` Quaternary `Tufa` mounds vetoed via repaired `IR-K3-27` (canary AUC `0.515683`).

All free official external sources ([USGS GeoDAWN CC0](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR #1391 CC BY 4.0](https://gdr.openei.org/submissions/1391), [USGS SGMC](https://pubs.usgs.gov/ds/1052/), [Craig et al. 2021 Southern Gabbs Valley](https://pubs.usgs.gov/publication/70201803)) were verified and SHA-256-checked locally in `data/restore_receipt.json`.

---

## 4. Three-Pass Verification Summary

- **Pass 1 (Implement & Execute):** Repaired `IR-K3-27`, built 4 `H-K3D` channels (`hk3d_tgsf_extra_4ch.npy`), ran 61-ch two-polarity leakage canary (`passed = True`, max `0.618008 <= 0.90`), trained 24-cell `61`/`55`-ch Dual-Cover SAR-PU OOF surfaces, evaluated `CTRL`, `E1`, `E2`, and `E3` across 5 holdout views, scanned all `1,997` unique SHA-256 rasters across 113 repos, emitted `-zeros.tif` + `.zip`, and ran `promotion_gate.py` (`negative` / `ok_to_submit = False`).
- **Pass 2 (Edge Cases, Safety Invariants & Regression Suite):** Caught and fixed accidental `"OK TO DOWNLOAD AND SUBMIT: YES"` conditional prose inside `scripts/build_hk3d_site.py` flagged by `scripts/verify_numbers.py`; updated 9-TIFF inventory checks across `scripts/build_release_review.py`, `scripts/build_k3c_site.py`, `scripts/build_run_card.py`, and `scripts/verify_numbers.py`; added unit + byte-level regression tests in `tests/test_hk3d_session.py`.
- **Pass 3 (Line-by-Line Prompt & Anti-Hallucination Audit):** Verified every SHA-256, dot count, CI, overlap fraction, score label (`HOLDOUT-DTI` vs `USER-REPORTED / UNVERIFIED`), `<= 140`-char note (`97` chars), repeatable site builds (`--check`), clean `git status`, full `pytest`, `npm test`, and `test_browser_feed.js`.
