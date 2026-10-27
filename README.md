# GEMSDOEkarage3 — DOE GEMS Geothermal Fault Discovery (`H-K3-1: CRSB-GUB`)

> **UNMISTAKABLE SUBMISSION STATUS (`2026-10-27`):**
> - **Technical Format & `[0, 1]` Range Gate:** **`PASS`** — `13 / 13` automated saved-byte GeoTIFF checks passed (`EPSG:32611`, `3730 × 3292`, `float32`, `nodata = None`, **`12,279,160 / 12,279,160` cells finite inside `[0.0, 1.0]`**, `37,654` off-catalogue dots, `0` on-catalogue dots; immune to DrivenData's `Predicted values must be in range [0, 1]` error).
> - **Cross-Registry Uniqueness Gate:** **`PASS`** — Pre-placement continuous belief surface `max |Spearman| = 0.6525 <= 0.90` across **`1,789` unique SHA-256 rasters (`2,148` files across `104` repositories)**; final discrete dots `max 3-px overlap = 66.27% <= 70.00%` across all `1,577` discrete candidate rasters (`44.11%` vs. the `0.2778` `GEMSDOE32` Champion; `<= 65.05%` across all 9 focus sites `GEMSDOE24..36`).
> - **Scientific Weekly-Slot Promotion Gate (`scripts/promotion_gate.py`):** **`HOLD — DO NOT SPEND WEEKLY SUBMISSION SLOT YET` (`verdict: "negative"`, `ok_to_submit: false`)** — `EXP-3` (`CRSB-GUB MaxEnv`) beats the `0.2778` `GEMSDOE32` Champion in point `HOLDOUT-DTI` (`GEMSDOE32-HIDE-RECOVER-v3.0`: **`0.106042`** vs. `0.099202`, **`+0.006840` / `+6.9%`**, `93.1%` bootstrap win probability), while purely unsupervised `EXP-1` beats the Champion on off-catalogue `SGMC-CAL-v3.0` (**`0.067889`** vs. `0.064121`, **`+0.003768`**). However, `EXP-3`'s 256-block paired 95% CI (`[-0.002006, +0.016383]`) narrowly crosses zero and its `SGMC-CAL-v3.0` is `0.057360` vs. `0.064121`. Per Parallel-Run Protocol Rule 6, **hold weekly slot expenditure unless chosen by cross-lane portfolio selection.**

- **Executive Summary Dashboard:** [`docs/index.html`](docs/index.html)
- **Step-by-Step Contest Submission Guide:** [`docs/executive-summary.html`](docs/executive-summary.html)
- **PhD Technical Monograph & 9-Site Forensic Analysis:** [`docs/research.md`](docs/research.md)
- **Locked Preregistration (`H-K3-1`..`H-K3-4`):** [`docs/research/hypotheses-preregistration-karage3.md`](docs/research/hypotheses-preregistration-karage3.md)
- **JSON Run Card:** [`docs/run-card.json`](docs/run-card.json)
- **Audited Irregularities & Shared-Template Fixes:** [`registry/irregularities.json`](registry/irregularities.json)

---

## 1. Validated Unique GeoTIFF Download & DrivenData Submission Metadata

| Field | Value |
| :--- | :--- |
| **Primary GeoTIFF (`.tif`)** | [`docs/downloads/gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.tif`](docs/downloads/gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.tif) (`212,468` bytes) |
| **Single-GeoTIFF Archive (`.zip`)** | [`docs/downloads/gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.zip`](docs/downloads/gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.zip) (`179,446` bytes) |
| **Saved-Byte SHA-256 (`.tif`)** | `2a1fed302d1fe1c556c86467ef687782d30eedf5361eff57a711ae5925a237c3` |
| **Saved-Byte SHA-256 (`.zip`)** | `3ab00ae5be1068bd80df4788a403825162490a57942c70e1492a51185ea3556d` |
| **13-Check Validator Receipt** | [`docs/downloads/gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-audit.json`](docs/downloads/gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-audit.json) |
| **DrivenData Submission Note (`111 / 140` chars)** | `H-K3-1 CRSB-GUB: Verduzco THDR+Riedel stepover+GDR1391 geotherm diseq+DualCover OOF d=3.0 (37654d, [0,1] zeros)` |

---

## 2. Executive Summary Across `GEMSDOEkarage3` & Nine Focus Sites (`GEMSDOE24..36`)

Every supplied historical site winner was SHA-256-verified from local GeoTIFF bytes (`scripts/audit_exact_nine_winners.py` -> [`evidence/nine-site-audit-20261027.json`](evidence/nine-site-audit-20261027.json)) and scored on canonical `GEMSDOE32-HIDE-RECOVER-v3.0` (`n=22,232`) and `GEMSDOE32-SGMC-CAL-v3.0` (`n=62,703`):

| Site | Audited Candidate File | Measured `HOLDOUT-DTI` (`HIDE-RECOVER-v3.0` / `SGMC-CAL-v3.0`) | Historical (`OWNER-REPORT`) | Uniqueness vs. `GEMSDOEkarage3` | Upload Status |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **`GEMSDOEkarage3`** | `gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.tif` (`37,654` dots) | **`0.106042`** `[0.0915, 0.1192]` / `0.057360` `[0.0495, 0.0649]` | Not submitted (`0` slots) | **PASS** (`max 66.27% <= 70%` across `1,577` discrete rasters; `max |rho|=0.6525 <= 0.90`) | **FORMAT SAFE `[0,1]` · HOLD SLOT (`negative`)** |
| **`GEMSDOE32`** | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`37,654` dots) | `0.099202` *(d2.8 parent)* / `0.064121` `[0.0559, 0.0721]` | **`0.2778`** | `44.11%` 3-px overlap (site max `65.05%`) | Prior benchmark — do not re-submit |
| **`GEMSDOE36`** | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` (`38,854` dots) | `0.004577` *(in-sample B=2 censored)* / `0.064444` | `0.2750` | `44.70%` 3-px overlap (`96.9%` overlaps `GEMSDOE32`) | Prior duplicate family — do not re-submit |
| **`GEMSDOE28`** | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif` (`37,660` dots) | `0.028932` *(partial censor)* / `0.062967` | `0.2710` | `45.14%` 3-px overlap (site max `52.86%`) | Prior `H19-5` derivative — do not re-submit |
| **`GEMSDOE31`** | `gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite.tif` (`55,304` dots) | `0.038714` / `0.057724` | `0.2708` | `47.68%` 3-px overlap (identical to `GEMSDOE28` B1) | Prior duplicate — do not re-submit |
| **`GEMSDOE33`** | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` (`41,865` dots) | `0.050690` / `0.062551` | `0.2632` | `46.25%` 3-px overlap (site max `46.64%`) | Prior `H19-5` derivative — do not re-submit |
| **`GEMSDOE25`** | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` (`44,090` dots) | `0.099202` / `0.060592` | `0.2600` | `46.64%` 3-px overlap (`NaN` outside footprint) | `NaN`-outside hazard / prior — do not submit |
| **`GEMSDOE30`** | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` (`44,090` dots) | `0.099202` / `0.060592` | `0.2600` | `46.64%` 3-px overlap (`SHA == GEMSDOE25`) | Pixel-identical to `GEMSDOE25` — do not submit |
| **`GEMSDOE24`** | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif` (`60,069` dots) | `0.097204` / `0.057932` | `0.2477` | `48.26%` 3-px overlap (`d=1.5` over-dense) | Superseded — do not submit |
| **`GEMSDOE27`** | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif` (`61,328` dots) | `0.096778` / `0.058262` | `0.2449` | `48.84%` 3-px overlap (`d=1.5` + bridges) | Superseded — do not submit |

---

## 3. Reproducible End-to-End Commands

```bash
# 1. Restore SHA-256-verified competition + external + historical scored inputs (30 files)
.venv/bin/python scripts/restore_data.py --group all
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/build_features.py

# 2. Fetch complete 104-repository GeoTIFF registry (2,148 rasters / 1,793 unique SHA-256s)
.venv/bin/python scripts/fetch_all_registry.py --jobs 8

# 3. Build 16 label-free CRSB-GUB physical channels & run 51-channel single-feature leakage canary
.venv/bin/python scripts/build_crsb_features.py

# 4. Run 3-experiment ablation (EXP-1..3), 104-repo uniqueness scan, 9-site audit & 13-check GeoTIFF writer
.venv/bin/python scripts/run_crsb_ablation.py
.venv/bin/python scripts/audit_exact_nine_winners.py

# 5. Run automated fail-closed promotion gate & test suite
.venv/bin/python scripts/promotion_gate.py docs/run-card.json   # expected exit 2 ('negative')
.venv/bin/python -m pytest -v
```

---

## 4. Standing Reference: User Project Prompt & Parallel-Run Protocol

<details>
<summary><strong>Click to expand standing user instructions &amp; Parallel-Run Protocol</strong></summary>

### Standing Mission & Deliverables
- Compete in the DrivenData DOE GEMS Prize (`https://www.drivendata.org/competitions/306/competition-doe-gems/`): predict locations of hidden unmapped geothermal faults across the Northwestern Great Basin (`EPSG:32611`, `3730 × 3292` at `100 m` resolution) using airborne magnetics/radiometrics (GeoDAWN), gravity, detrended topography, geodesy, seismicity, conductivity, and verified public geothermal datasets.
- Focus sites to audit and compare: `GEMSDOE24` (`0.2477`), `GEMSDOE25` (`0.2600`), `GEMSDOE27` (`0.2449`), `GEMSDOE28` (`0.2710`), `GEMSDOE30` (`0.2600`), `GEMSDOE31` (`0.2708`), `GEMSDOE32` (`0.2778`, `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`), `GEMSDOE33` (`0.2632`), and `GEMSDOE36` (`0.2750`), alongside unverified prompt leaderboard reference values (`0.3195` / `0.4413`).
- Explain at PhD level why `GEMSDOE32` (`0.2778`) outperformed the peer sites and what physical/statistical advances are needed to surpass it.
- Propose and rank 3–5 untried geological hypotheses prior to implementation (naming layers, physical signature/transform, why it catches missing uncatalogued faults rather than mapped scarps, difference from existing repo methods, expected DTI gain, implementation cost, and free official data sources).
- Generate a genuinely unique single-band GeoTIFF (`.tif` and single-file `.zip`) matching `sample_submission.tif` CRS, shape, and geotransform, with values strictly in `[0, 1]` and zero NaNs inside the footprint (preventing `"Predicted values must be in range [0, 1]"`), automated validation checks, unmistakable top-of-site approval/status indicator, unique filename, and DrivenData submission note (`<= 140` chars).
- Complete 3 review passes (Pass 1: implement & verify; Pass 2: review & fix bugs/assumptions/edge cases; Pass 3: re-verify every requirement), then open and merge a PR onto `main`.

### Parallel-Run Protocol (Mandatory Rules)
1. **Lane uniqueness:** Check both continuous surface before placement AND final dots against all registry rasters; if rank correlation `|Spearman| > 0.90` OR `> 70%` of dots fall within `3 px` of a discrete candidate raster's dots, log as duplicate and stop.
2. **Reuse, don't rebuild:** Reuse the template's cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`. Holdout = hide-and-recover (withhold whole fault segments with spatial buffer, derive catalogue-based features solely from visible faults, mask visible faults pixel-exactly, score pooled DTI with `alpha=0.2, beta=0.8`, `300 m` triangular kernel). Fix shared tool bugs in the template; never keep a private fork.
3. **Score labeling:** Label every number `HOLDOUT-DTI` (with evaluator version, withheld positive count, 95% CI) or `ORGANIZER-CONFIRMED` (or `OWNER-REPORT` when unverified by portal receipt). Never write a projection as a score.
4. **Leakage canary:** Test each feature alone on holdout before trusting results; `AUC > 0.90` is leakage until proven otherwise.
5. **One run card at the end:** Output the JSON Run Card with hypothesis, mechanism, named non-fault mimic process, holdout DTI + CI, correlation/overlap vs registry, raster `sha256`, validator output, submission name + note (`<= 140` chars), and verdict (`promote` or `negative`).
6. **Budget:** Stop after `3` experiments or `2` hours. Do not spend a weekly submission slot on an idea that has not beaten holdout best.

</details>
