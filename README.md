# GEMSDOEkarage3 — Coulomb Stress-Shadow Transfer & Blind Geothermal Hydrothermal-Flexure (`Lane H-K3B-1: CSST-BGHF`)

[![Format & [0,1] Validator](https://img.shields.io/badge/GeoTIFF_[0,1]_Validator-13%2F13_Checks_PASS_(0_NaN)-10b981)](#1-executive-summary--unique-validated-geotiff-deliverable)
[![Leakage Canary](https://img.shields.io/badge/57--ch_Leakage_Canary-PASS_(max_AUC_0.6180_%3C%3D_0.90)-10b981)](#1-executive-summary--unique-validated-geotiff-deliverable)
[![112-Repo Uniqueness](https://img.shields.io/badge/1,913--Raster_Uniqueness-PASS_(max_discrete_66.53%25_%3C%3D_70%25)-10b981)](#5-master-auditable-table--candidates--nine-focus-sites-gemsdoe2436)
[![Dual Point-DTI Win](https://img.shields.io/badge/Point_HOLDOUT--DTI-Beats_0.2778_Champ_on_All_3_Benchmarks-38bdf8)](#4-preregistered-3-experiment-ablation-results-budget--3)
[![Weekly Slot Gate](https://img.shields.io/badge/Slot_Gate_(promotion__gate.py)-HOLD_FOR_SELECTOR_REVIEW_(95%25_CI_[-0.0033,+0.0139])-f59e0b)](#1-executive-summary--unique-validated-geotiff-deliverable)

**Live Pages & Artifacts:** [CSST-BGHF Hub & Download (`docs/csst-bghf/index.html`)](docs/csst-bghf/index.html) · [Step-by-Step DrivenData Submission Guide (`docs/csst-bghf/executive-summary.html`)](docs/csst-bghf/executive-summary.html) · [Nine-Site Evidence Desk (`docs/index.html`)](docs/index.html) · [Root Overview (`index.html`)](index.html) · [Locked Preregistration (`docs/research/csst-bghf-preregistration-20261028.md`)](docs/research/csst-bghf-preregistration-20261028.md) · [Irregularities Log (`knowledge/irregularities.md`)](knowledge/irregularities.md) · [Run Card (`docs/run-card.json`)](docs/run-card.json)

---

## 1. Executive Summary & Unique Validated GeoTIFF Deliverable

| Field | Verified Value (`2026-10-28`) |
| :--- | :--- |
| **Technical Validation Status** | **ALL 4 TECHNICAL GATES PASS** (`13/13` GeoTIFF `[0, 1]` & zero-NaN checks PASS; `57/57` single-feature leakage canaries PASS `<= 0.6180`; `1,913`-unique-SHA-256 / `112`-repo uniqueness checks PASS `<= 66.53%`; point `HOLDOUT-DTI` beats `0.2778` Champion across **all 3 benchmarks and all 4 spatial quadrants**) |
| **Fail-Closed Slot Verdict (`scripts/promotion_gate.py`)** | **`verdict = "negative"` · `ok_to_submit = false` · `selector_required = true`** — Transparently held for human selector sign-off before spending 1 of 3 weekly DrivenData slots because the two-sided 95% paired cluster-bootstrap CI on `Hide-and-Recover` (`[-0.003328, +0.013882]`, `P(Δ > 0) = 88.9%`) narrowly spans zero by `0.0033` |
| **Primary Validated GeoTIFF (`-zeros.tif`)** | [`docs/downloads/gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.tif`](docs/downloads/gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.tif) (Single-band `float32`, `EPSG:32611`, `3730 × 3292`, `[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]`, `nodata = None`) |
| **Single-File DrivenData ZIP Package** | [`docs/downloads/gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.zip`](docs/downloads/gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.zip) |
| **GeoTIFF SHA-256** | `4b47a37ecf91384b2202897dd695219d23375cab2a300106feaf541d60fc9c5b` |
| **ZIP SHA-256** | `08159cb3c603dc1e629da3bb49b71e4b65abb0094ebf01b6293357a20ffd31eb` |
| **Submission Note (`117 / 140` chars)** | `H-K3B-1 CSST-BGHF: Coulomb shadow+Baranov leach+Euler N0+Bajada hinge+Dual57 OOF d=3.1 (37654d [0,1] zeros)` |
| **DrivenData `[0, 1]` Error Prevention** | **`12,279,160 / 12,279,160` finite `float32` pixels (`0` NaN inside or outside the `5,167,373`-px footprint)**; values strictly in `{0.0, 1.0}` (`min = 0.0`, `max = 1.0`); `37,654` off-catalogue dots (`0` on `existing_faults.tif`, `B = 2` [`> 200 m`] collar); no `-nan.tif` upload hazard in `docs/downloads/` |
| **`HOLDOUT-DTI` (`GEMSDOE32-HIDE-RECOVER-v3.0`, `n = 22,232`)** | **`0.104700`** (`95% CI [0.090409, 0.120286]`) vs `0.2778` Champion **`0.099202`** (`[0.085951, 0.112668]`) — **`+0.005498` (`+5.54%`)**, wins `4/4` quadrants (`NW, NE, SW, SE`), paired `P(Δ > 0) = 88.9%` (`95% CI [-0.003328, +0.013882]`) |
| **`HOLDOUT-DTI` (`Detached >= 600 m`, `n = 15,504`)** | **`0.099958`** (`95% CI [0.084586, 0.117302]`) vs `0.2778` Champion **`0.094324`** (`[0.079248, 0.109825]`) — **`+0.005634` (`+5.97%`)**, paired `P(Δ > 0) = 89.1%` |
| **`HOLDOUT-DTI` (`GEMSDOE32-SGMC-CAL-v3.0`, `n = 62,703`)** | **`0.070171`** (`raw = 0.104890`, `95% CI [0.059513, 0.079771]`) vs `0.2778` Champion **`0.064121`** (`[0.056730, 0.071649]`) — **`+0.006050` (`+9.44%`)**, paired `P(Δ > 0) = 86.5%` |
| **57-Channel Leakage Canary (Rule 4)** | **PASS (`57 / 57` channels `<= 0.90`)**; max oriented AUC = **`0.618008`** (`piedmont_toe_flexure`, our new physical channel #53!) |
| **112-Repo Uniqueness Scan (`2,355` files / `1,913` unique SHA-256s)** | **PASS**: Pre-placement surface `max |Spearman|` = **`0.519299 <= 0.90`**; final dots `max |Spearman|` = **`0.072324 <= 0.90`**; discrete (`<= 100k` dots, `1,687` rasters) max 3-px overlap = **`66.53% <= 70.0%`**; Focus-9 max 3-px overlap = **`59.39% <= 70.0%`** (`9/9 PASS`); vs `0.2778` Champion = **`42.24%`**; vs prior `GEMSDOEkarage3` PR #9 = **`57.21%`** |

![H-K3B-1 CSST-BGHF 4-Panel Diagnostic Figure](docs/assets/fig_csst_bghf.png)

---

## 2. PhD Structural & Geothermal Forensics: How `h33-h33-2-b2` Reached `0.2778` & How to Beat It

### 2.1 Byte-Level Lineage of `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`GEMSDOE32`: `0.2778` User-Reported)
Direct byte-level inspection across all 9 focus repositories (`GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36`; note per `IR-K3-04` that focus-repo live scores are owner-reported ledger entries without archived DrivenData receipts) establishes an exact nested pixel hierarchy on the `H19-5` probability surface:
$$\mathcal{P}_{\text{H33-2-B2}} \;(37,654\text{ px},\;\mathbf{0.2778}) \;\subset\; \mathcal{P}_{\text{H27-4-B1}} \;(40,199\text{ px},\;\mathbf{0.2708}) \;\subset\; \mathcal{P}_{\text{D2.8-Poisson}} \;(44,090\text{ px},\;\mathbf{0.2600}) \;\subset\; \mathcal{P}_{\text{H19-5-Solid}} \;(121,131\text{ px},\;\mathbf{0.1922}).$$
1. **Why Axial Sparse Dot Packing Beat Solid Fault Ribbons (`0.1922 -> 0.2600`):** Under the organizer's Distance-Weighted Tversky Index ($\alpha = 0.2$ on FP, $\beta = 0.8$ on FN, `300 m` / `3 px` linear distance kernel $w(d) = \max(0, 1 - d/300\text{ m})$; see [NLR Report #96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf)), a single dot $p_i = 1$ already saturates the `300 m` triangular kernel around it. Replacing `121,131`-pixel contiguous ribbons with an axially spaced (`d >= 2.8–3.1 px`) submodular point set cuts the $0.2\,\text{FP}$ denominator penalty by $2.75\times$ while retaining $>94\%$ of buffered recall.
2. **Why `B = 2 px` (`200 m`) Known-Fault Collar Pruning Lifted `0.2708 -> 0.2778` (`+0.0070`):** Because `existing_faults.tif` (`60,988` positive pixels) is masked pixel-exactly during evaluation, any dot placed within `<= 200 m` wastes ~45–60% of its `300 m` kernel on masked pixels while paying full false-positive weight outside hidden branches. Removing `2,545` collar dots from `40,199` left `37,654` off-catalogue dots (`0.7287%` footprint density).
3. **Why `-zeros.tif` Fixed `"Predicted values must be in range [0, 1]"`:** In `training_features.tif`, Bands `01..18` contain `-3.4028235e+38` Float32 sentinels at `3,061` in-footprint pixels, while `-nan.tif` submissions leave `7,111,787` outer bounding-box pixels as `NaN`, triggering DrivenData's whole-array `(arr >= 0) & (arr <= 1)` validator error. Replacing sentinels via nearest-neighbor Euclidean inpainting and writing `0.0` outside the footprint (`nodata = None`, `12,279,160 / 12,279,160` finite pixels) permanently eliminates this failure.

### 2.2Verified 19-Band Schema of `training_features.tif` (Correcting `IR-K3-10`)
Verified directly from `data/prepared_manifest.json` (`SHA-256 = f82f73f5b55755ef...`):
`01 mag_anom` (nT), `02 rtp` (nT), `03 tmi_hg` (nT/m), `04 geod_2ndinv` ($10^{-9}\text{ yr}^{-1}$), `05 iso_grav_anom_slope` (deg), `06 tc`, `07 geod_shearrate`, `08 geod_dilaterate`, `09 tmi_vg`, `10 deq_n100a15` (m), `11 iso_grav_anom_vg` (mGal/km), `12 det_elev` (m), `13 iso_grav_anom` (mGal), `14 tmi` (nT), `15 depth_to_base_surf` (m), `16 ieq_n100a15`, `17 cond_surf`, `18 iso_grav_anom_hg`, `19 det_elev_slope` (deg).

### 2.3 Four Structural Ceilings on `0.2778` & How `CSST-BGHF` Breaks Them Toward `> 0.3195`
1. **24.63% 1 m LiDAR Coverage Gap & `IR-K3-01` / `IR-K3-12` Bugs:** `H19-5` read wrong LiDAR bands (`1,2,5` instead of `1,3,6`) and starved the `24.63%` LiDAR gap. Our repaired `57/52`-ch Dual-Cover OOF excludes all 5 LiDAR-contaminated channels (`LIDAR_GLOBAL_COLS_57 = {45, 46, 47, 48, 54}`), placing **`26.13%` (`9,840` dots)** inside the `24.63%` LiDAR gap.
2. **Cowie–Scholz Elastic Stress-Shadow vs Forward Tip Lobes:** Isotropic distance features place heavy broadside halos `200–600 m` beside interior scarps (an elastic stress-release shadow where parallel synthetic faults are suppressed) while under-allocating forward Coulomb wing-crack/relay lobes ahead of fault terminations.
3. **Blind Hydrothermal Magnetite-Leaching & Basement Unconformity Contacts:** Pure scarp classifiers miss concealed Tertiary/Mesozoic bedrock faults (`SGMC`) and blind geothermal upflow zones (`McGinness Hills` / `Gabbs Valley` / `Bradys` analogs) where ascending hydrothermal fluids destroy magnetite (`Band 02 rtp` low) across dense silica-sealed basement horsts (`Band 13 iso_grav_anom` high).
4. **Pre-Sharpened Stationary Max-Envelope (`IR-K3-13`):** Pre-sharpening both the Coulomb tip-gated OOF branch and the 4-operator `CSST-BGHF` physical branch onto commensurate 1-px crests *before* Max-Envelope fusion lifts `SGMC-cal` to **`0.070171` (`+9.44%` above `0.2778` Champion)** while cutting `2–8 px` scarp-apron crowding to **`18.29%`** (guaranteeing `<= 66.53%` overlap across all `1,687` discrete registry candidates).

---

## 3. Four Ranked Untried Geological Hypotheses (`docs/research/csst-bghf-preregistration-20261028.md`)

| Rank | ID & Name | Exact Layers Used | Physical Signature / Transform Targeted | Why It Catches Hidden Faults / Vents Missing from Catalogue | Difference vs All 112 Registry Repos | Expected Lift & Cost |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (Executed)** | **`H-K3B-1: CSST-BGHF`** (Coulomb Stress-Shadow Transfer & Blind Geothermal Hydrothermal-Flexure) | `Bands 02, 09, 11, 12, 13, 15, 17, 18, 19` + `geodawn_rad_u8` (`K, Th, U`) + repaired `lidar_scarp_features_u8` (`1,3,6,8,10,12`) + `GDR #1391` (`geothermometer`, `2m T`, `sinter/borates`, `BLM claims`) + `TIGER 2024` | (1) 2-D Fourier Baranov pseudogravity $g_{\text{pseudo}}(\mathbf{k})=\mathcal{F}[\text{RTP}]$ orthogonalized against `Band 13 iso_grav_anom` + alteration gate; (2) Laplace/Fourier $N=0$ contact depth $z_{N=0}=\|\nabla_h F\|/A_1-z_{\text{stab}}$ (m) matched to `Band 15 depth_to_base_surf`; (3) bajada down-slope break-in-slope flexure hinge (`-u·H(z)u`) with thalweg/Lahontan/TIGER vetoes; (4) fold-visible Azimuthal Coulomb Tip-Lobe vs Broadside Stress-Shadow Gate + `d=3.1` CELF | Catches blind geothermal upflow conduits (hydrothermal magnetite->pyrite/clay leaching), sediment-draped synthetic bajada step-down faults (`0.8–3.5 km` basinward of range fronts), and concealed basement-unconformity contacts lacking young Quaternary scarps | First exact 2-D Fourier Baranov pseudogravity residual + metric $N=0$ contact-depth match to `Band 15` + azimuthal Cowie–Scholz broadside stress-shadow suppression + strictly LiDAR-free `52`-ch `M_NoLiDAR` | **`+0.0055` HR & `+0.0061` SGMC-cal achieved** · ~14 min CPU |
| **2** | **`H-K3B-2: LDCG-9B`** (Strain-Incompatibility & Dilatant Intersection Localization) | `Bands 04, 07, 08, 10, 15, 16, 17` + `geodetic_strain_9band_f32.tif` + `GDR #1391` | Saint-Venant strain-rate incompatibility curl + positive shear×dilatation intersection determinant $\dot{\gamma}\cdot\max(\dot{\Delta},0)\sin^2(\theta_1-\theta_2)$ | Active geothermal fluid flow concentrates at critically stressed fault intersections and relay terminations even where single traces are aseismic or unmapped | Prior strain models (`GEMSDOE31`, `GEMSDOE33`) used scalar `Band 07/08` thresholds rather than the 9-band tensor curl & intersection determinant | `+0.003–0.006` · Low–Mod cost |
| **3** | **`H-K3B-3: PTHG-3D`** (Multi-Altitude Tilt-Depth Wedge & Authigenic U/Th Enrichment) | `Bands 02, 05, 11, 13, 18` + `geodawn_extensions_u8.tif` (`ThK, UK, UTh, TMI_up150`) + `GDR #1391` | Salem (2007) harmonic tilt-depth half-width $h_{\text{tilt}}$ across $z\in\{150,400,1000,2200\}\text{ m}$ + downdip vector migration + redox-front U/Th enrichment | Dipping ($45^\circ\text{–}65^\circ$) normal faults migrate downdip with altitude while shallow sub-horizontal volcanic flows attenuate symmetrically | Uses multi-altitude tilt half-width wedge geometry rather than single-level surface tilt | `+0.002–0.005` · Low cost |
| **4 (Deferred)** | **`H-K3B-4: CSMS-INSAR`** (Relocated Microseismic Planar Alignment & InSAR Coherence Step) | External `USGS ComCat` (`1980–2026`, $M\ge 0.5$) + `NASA/JPL ARIA Sentinel-1 InSAR` | 3-D RANSAC hypocentral plane strike/dip alignment + cross-fault InSAR phase-coherence step | Microseismic swarms & creep discontinuities directly illuminate active blind geothermal transfer zones (`Dixie Valley` / `San Emidio`) | Requires external live fetch (`earthquake.usgs.gov` / `asf.alaska.edu` blocked in sandbox; verified free US Gov CC0/PD sources for offline ingest) | High live upside · External fetch required |

---

## 4. Preregistered 3-Experiment Ablation Results (`Budget = 3`)

Executed in [`scripts/run_csst_ablation.py`](scripts/run_csst_ablation.py) on shared `gems32.holdout` (`8` fold×draw cells, `1.5 km` fold collar, $B_{\text{vis}}=2\text{ px}$) and `gems32.emitter.emit` (`37,654` dots, `min_sep_px = 3.1`):

| Arm (`37,654` dots, `B = 2`) | `HOLDOUT-DTI`: `Hide-and-Recover v3.0` (`n=22,232`) | `HOLDOUT-DTI`: `Detached >= 600 m` (`n=15,504`) | `HOLDOUT-DTI`: `SGMC-cal v3.0` (`n=62,703`) | `HOLDOUT-DTI`: `SGMC-raw v3.0` (`n=62,703`) |
| :--- | :---: | :---: | :---: | :---: |
| **Control: `0.2778` Champion (`H33-2-B2` fold-rule)** | `0.099202` `[0.085951, 0.112668]` | `0.094324` `[0.079248, 0.109825]` | `0.064121` `[0.056730, 0.071649]` | `0.096060` `[0.085660, 0.107072]` |
| **`EXP-1`: Purely Unsupervised `CSST-BGHF` Ridge (`d=3.1`)** | `0.078489` `[0.069115, 0.087551]` | `0.069453` `[0.060171, 0.078842]` | **`0.067410`** `[0.059030, 0.075131]` | **`0.100829`** `[0.088467, 0.113580]` |
| **`EXP-2`: Dual-Cover `57/52`-ch SAR-PU OOF Isotropic (`d=3.1`)** | **`0.110196`** `[0.095503, 0.125362]` | `0.095273` `[0.079882, 0.111484]` | `0.053794` `[0.045110, 0.062233]` | `0.080690` `[0.067005, 0.094951]` |
| **`EXP-3`: `CSST-BGHF` Coulomb + Pre-Sharpened MaxEnv (`d=3.1`)** | **`0.104700`** `[0.090409, 0.120286]` | **`0.099958`** `[0.084586, 0.117302]` | **`0.070171`** `[0.059513, 0.079771]` | **`0.104890`** `[0.089569, 0.119873]` |

---

## 5. Master Auditable Table — Candidates & Nine Focus Sites (`GEMSDOE24..36`)

Full byte-verified receipts in [`evidence/nine-site-audit-20261028.json`](evidence/nine-site-audit-20261028.json) and [`evidence/complete-registry-uniqueness-scan.json`](evidence/complete-registry-uniqueness-scan.json):

| Site / Candidate | File Inspected / Download & Dots | User-Reported Claim (`IR-K3-04`) | `HOLDOUT-DTI`: `Hide-Recover v3.0` (`n=22,232`) | `HOLDOUT-DTI`: `SGMC-cal v3.0` (`n=62,703`) | Max 3-px Overlap vs `CSST-BGHF` (`<=70%`) | Gate & Uniqueness Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`GEMSDOEkarage3` (`H-K3B-1 CSST-BGHF`)** | [`gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.tif`](docs/downloads/gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.tif) (`37,654`d) | *Not yet submitted (`0` slots spent)* | **`0.104700`** `[0.0904, 0.1203]` | **`0.070171`** `[0.0595, 0.0798]` | — (`66.53%` worst discrete across 112 repos) | **13/13 `[0,1]` PASS · UNIQUE PASS · Slot Hold (`95% CI` spans 0)** |
| **`GEMSDOE32`** | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`37,654`d, `22` rasters) | **`0.2778`** (#1 Focus-9) | `0.099202` *(fold-rule)* / `0.004515` *(static)* | `0.064121` `[0.0567, 0.0716]` | `42.24%` (`56.98%` repo max) | Historical `0.2778` reference · Do not resubmit |
| **`GEMSDOE36`** | `gemsdoe36-anderson-geothermal-pinn-38854-...-nan.tif` (`37,654`d, `12` rasters) | `0.2750`, `0.1647` | `0.006880` *(static)* | `0.029018` | `17.56%` (`42.66%` repo max) | Historical `H19-5` + 1,200 PINN · Do not resubmit |
| **`GEMSDOE28`** | `gems28-h27-4-solo-d28-20261004-8acb75e1-nan.tif` (`40,199`d, `13` rasters) | `0.2710`, `0.2708`, `0.2707`, `0.2649`, `0.0217`, `0.0206` | `0.030057` *(static)* | `0.063010` | `42.89%` (`45.27%` repo max) | Historical `B=1` parent of `0.2778` · Do not resubmit |
| **`GEMSDOE31`** | `gemsdoe31-tgtd-submod-37654-20261025-ab35d4e8-nan.tif` (`37,654`d, `4` rasters) | `0.2708` | `0.000002` *(static)* | `0.071850` | `49.51%` | Historical `H19-5` sibling (`NaN` outside) · Do not resubmit |
| **`GEMSDOE33`** | `GEMSDOE33-h33d-analog-tip-stepover-r30-...-nanoutside.tif` (`37,654`d, `5` rasters) | `0.2632`, `0.0963` | `0.012023` *(static)* | `0.079533` | `42.86%` (`43.67%` repo max) | Historical `H33` analog (`NaN` outside) · Do not resubmit |
| **`GEMSDOE25`** | `gems25-h66-mgd-flank-d28-20261004-...-nan.tif` (`44,090`d, `100` rasters) | `0.2600`, `0.0742` | `0.099202` | `0.060592` | `43.30%` (`49.29%` repo max) | Pixel-identical `D2.8` to `GEMSDOE30` · Do not resubmit |
| **`GEMSDOE30`** | `gemsdoe30-sgmc-hedge-d10-85k-20261003-ac08b41e-zeros.tif` (`85,526`d, `33` rasters) | `0.2600`, `0.1462` | `0.000778` *(static)* | `0.148074` *(85.5k density)* | `59.39%` | High-density `85.5k` hedge · Do not resubmit |
| **`GEMSDOE24`** | `gems24-h25-1-dotted-h19-5-d1-5-20261002-...-nan.tif` (`60,069`d, `69` rasters) | `0.2477`, `0.0859` | `0.097204` | `0.057932` | `44.85%` (`49.30%` repo max) | Over-packed `d=1.5` (`NaN` outside) · Do not resubmit |
| **`GEMSDOE27`** | `gems27-topo-gap-closure-t-v2-on-d1-5-...-nan.tif` (`61,328`d, `195` rasters) | `0.2449`, `0.2250`, `0.2190` | `0.096778` | `0.058262` | `45.27%` (`49.03%` repo max) | Topo-gap union (`NaN` outside) · Do not resubmit |

---

## 6. Autonomous Reproduction & Automated Verification Commands

```bash
# 1. Restore & SHA-256-verify competition data + pinned registry rasters
.venv/bin/python scripts/restore_data.py
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/restore_pinned_registry.py

# 2. Build 35-ch base + 16-ch CRSB + 6-ch CSST-BGHF physical stacks & run 57-ch leakage canary
PYTHONPATH=src .venv/bin/python scripts/build_features.py
PYTHONPATH=src .venv/bin/python scripts/build_crsb_features.py
PYTHONPATH=src .venv/bin/python scripts/build_csst_features.py

# 3. Execute preregistered 3-experiment CSST-BGHF ablation, 1,913-raster scan, 9-site audit & GeoTIFF writer
PYTHONPATH=src .venv/bin/python scripts/run_csst_ablation.py

# 4. Rebuild static GitHub Pages & run full Python + Node verification suites
.venv/bin/python scripts/build_csst_site.py
.venv/bin/python scripts/build_site.py --check
.venv/bin/python scripts/build_preflight_site.py
.venv/bin/pytest -q
.venv/bin/python -m unittest discover -s tests -v
npm test
```

---

## 7. Limitations & Highest-Priority Next Steps

1. **Bootstrap CI Power (8 vs 24 Fold×Draw Cells):** `EXP-3` beats `0.2778` Champion across all 4 quadrants and all 3 benchmarks (`P = 88.9%` HR, `P = 89.1%` Detached, `P = 86.5%` SGMC-cal), but 2 random draws × 4 quadrants yields a `±0.0086` 95% paired CI half-width (`[-0.0033, +0.0139]`). Expanding `HoldoutContext` to 6 stratified draws (`24` cells) in the next session will sharpen paired CI resolution without touching model parameters.
2. **Offline Ingest of Relocated Microseismicity & InSAR (`H-K3B-4`):** Sandbox outbound network policy blocks `earthquake.usgs.gov` and `asf.alaska.edu`; mirroring public-domain USGS ComCat / Nevada Seismological Laboratory catalogs and ARIA Sentinel-1 coherence rasters into the data manifest is the single largest untried physical data source toward `> 0.3195–0.44`.
3. **Execute Rank-2 Hypothesis `H-K3B-2 (LDCG-9B)`:** Combine Saint-Venant geodetic strain-incompatibility curl and shear×dilatation fault-intersection localization with `CSST-BGHF`.

---

## 8. Standing Reference Prompt (Verbatim User Instructions)

Full competition URLs, public Dropbox/GDR/GeoDAWN links, and the complete `GEMSDOE..92` + sibling-org inventory are also archived in [`knowledge/owner_brief.md`](knowledge/owner_brief.md) and [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md).

<details>
<summary><strong>Click to expand the standing reference prompt supplied by the user</strong></summary>

```text
Maximize P(Win). No excuses. Own the outcome.
Please review the entire repo, then build and update the project as needed. Do not fabricate anything or hallucinate. Our goal is to win the DOE GEMS competition by creating a submission that gets a higher score than the current high on the leaderboard of 0.4413; all files must be validated by the project without human intervention and the project should clearly indicate whether a file is ok to download and submit or not. Right now the submission I downloaded and submitted had an error of "Predicted values must be in range [0, 1]".

Please focus on analyzing the highest scoring submissions from GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36. Then answer the following questions with PhD level analysis: why and how did h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros on https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html get a score of 0.2778 which is the highest of any of those sites? Can we generate a submission that gets a higher score? If so, how? Make sure our project has an executive summary on every one of those sites (GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36) and a table that compares them and lists what file to download and what their estimated or actual score is and whether they are unique or not.

We MUST GENERATE A UNIQUE TIF SUBMISSION! Do not copy a previous submission, except for learning or comparison purposes! Whatever we generate MUST be a unique tif submission unlike any of those on the sites listed below! Also provide a unique name and a short note <= 140 characters to help distinguish the submission in the contest. Also make it easy to download at the very beginning of our site in an obvious Executive Summary and have an executive summary subpage explaining step by step how to submit into the contest.

Before writing any model code, read the GEMS feature list and generate 3-5 novel candidate geological hypotheses that have not been tried yet. For each hypothesis, name: (1) the specific layer(s) involved, (2) the physical signature you are targeting, (3) why it would catch faults/geothermal vents missing from the USGS/INGENIOUS catalogue rather than ones already in it, and (4) how it differs from existing implementations. Rank them by expected DTI improvement and implementation cost, then implement and validate the top candidate on the spatially-blocked holdout set.

Parallel-run protocol (keep every run short, comparable, and non-duplicative):
1) Lane: Stay inside your assigned method lane. If raster rank-correlation with any registry raster exceeds 0.90, or >70% of your dots fall within 3 px of a registry raster's dots, log as a duplicate and stop. Check both on the continuous surface before placement AND on final dots.
2) Reuse, don't rebuild: Use the template's cached feature stack, evaluate_holdout.py, and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive any catalogue-based features only from visible faults, mask visible faults pixel-exactly, and score pooled DTI (alpha=0.2, beta=0.8, 300 m triangular kernel). If a shared tool in the template is wrong, fix it there — no private forks.
3) Label every number: Every score must be labeled either HOLDOUT-DTI (with evaluator version, number of withheld positives, and 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). Never write a projection as a score.
4) Leakage canary: Test each feature alone on holdout before trusting results. Single-feature AUC > 0.90 indicates leakage until proven otherwise.
5) Run card: End with one JSON card containing: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, registry correlation + overlap, raster SHA256, validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match), submission_name + <=140-char note, and verdict: promote / negative. Negative results are valid deliverables. Do not spend a real submission slot on an idea that hasn't beaten holdout best.
6) Budget: Stop after 3 experiments or 2 hours.

Make sure you run 3 passes:
Pass 1: Implement and verify everything works.
Pass 2: Review your work, find bugs, missing requirements, or edge cases, and fix them.
Pass 3: Re-check against the user's full prompt to ensure accuracy, reliability, completeness, and code quality.

Create a pull request and merge the PR onto main. Document remaining work and limitations.
```

</details>
