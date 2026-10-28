# Preregistered Untried Geological Hypotheses & Locked Lane `CSST-BGHF` (`2026-10-28`)

**Status:** Locked *prior* to feature computation, classifier training, holdout evaluation, or GeoTIFF emission.  
**Repository:** `karagemop466-tech/GEMSDOEkarage3` · **Branch:** `arena/029670eb-gemsdoekarage3`  
**Experiment Budget:** At most `3` controlled experiments (`<= 2` hours compute) · **Weekly Slots Authorized Here:** `0` (separate human/programme selector step).

---

## 1. Structural & Geothermal Diagnosis of Prior Bottlenecks

Auditing prior runs in this repository (`FBGR` in PR #8, `CRSB-GUB` in PR #9, and `HK3-SMGC` in PR #10) alongside all `112` repositories (`2,355` GeoTIFFs / `1,913` unique SHA-256s) reveals two coupled physical-statistical bottlenecks:

1. **Broadside Halo Attraction vs. Elastic Coulomb Stress Shadows:**  
   Classifiers trained on `y = 1` (`visible_faults`) vs. `y = 0` (`d_vis > 4 px`) inherit the `0.5–5 km` spatial autocorrelation of regional elevation, gravity, and magnetic grids, concentrating `30–36%` of emitted dots inside a `200–850 m` (`2–8.5 px`) *broadside parallel flank apron* beside already-mapped faults. By Cowie & Scholz (1992) and Gupta & Scholz (2000) normal-fault mechanics, interior slip on a master range-front fault casts a cross-strike **Coulomb stress-release shadow** ($\Delta\text{CFS} < 0$) that inhibits parallel synthetic fault nucleation within `~0.2–0.85 km` broadside, whereas **fault terminations (tips)** concentrate positive tensile/shear stress ($\Delta\text{CFS} > 0$, King, Stein & Lin 1994; Curewitz & Karson 1997) in forward collinear and `±15–40°` wing-crack/Riedel lobes! Treating `d_vis` isotropically either wastes `~10,000` dots in the broadside stress shadow (depressing off-catalogue `SGMC-cal` and inflating 3-px overlap with legacy halo rasters) or starves along-strike tip continuations (depressing `Hide-and-Recover`).
2. **Untapped Subsurface & Bajada Signatures for Blind Conduits:**  
   Approximately `65–75%` of Great Basin geothermal systems are *blind* (Faulds & Hinz 2015), controlled by outboard synthetic piedmont/bajada faults buried under Holocene fan aggradation (`1–3.5 km` basinward of the range front) or hydrothermally altered intrabasin basement steps where primary magnetite has been oxidized to pyrite/hematite while wallrock is silicified.

---

## 2. Four Candidate Untried Geological Hypotheses (Ranked by Expected DTI Gain vs. Cost)

None of the four hypotheses below has been implemented in `features.py`, `spcp.py`, `trhv.py`, `ldgi.py`, `fbgr.py`, `crsb_gub.py`, `smgc.py`, or `h33.py`. Every band index is verified against `data/prepared_manifest.json`.

### Rank 1 (Selected Primary Lane) — `H-K3B-1` (`CSST-BGHF`): *Coulomb Stress-Shadow Transfer, Baranov Pseudogravity Magnetite-Leaching Defect, Reid $N=0$ Basement-Matched Euler Contacts & Piedmont Toe-Flexure Dual-Cover Allocation*

- **Specific Layers Involved (`100%` SHA-256 verified locally in `.cache/gems_data/`):**
  - *Official `training_features.tif` bands:* Band 02 (`rtp`), Band 03 (`tmi_hg`), Band 04 (`geod_2ndinv`), Band 05 (`iso_grav_anom_slope`), Band 07 (`geod_shearrate`), Band 08 (`geod_dilaterate`), Band 09 (`tmi_vg`), Band 10 (`deq_n100a15`), Band 11 (`iso_grav_anom_vg`), Band 12 (`det_elev`), Band 13 (`iso_grav_anom`), Band 14 (`tmi`), Band 15 (`depth_to_base_surf`), Band 16 (`ieq_n100a15`), Band 17 (`cond_surf`), Band 18 (`iso_grav_anom_hg`), Band 19 (`det_elev_slope`).
  - *Verified public mirrors (`registry/data_manifest.json`):* USGS 3DEP 1 m LiDAR (`lidar_scarp_features_u8.tif`, using verified Bands `1=ex_max`, `3=step_max`, `6=downface_max`, `7=upface_max`, `8=cross_max`, `10=coh100`, `11=strike`, `12=valid` — fixing `IR-K3-01`), USGS GeoDAWN radiometrics (`geodawn_rad_u8.tif` Bands `1=K, 2=Th, 3=U`, `acquisition_block_id_100m.tif`), US Census TIGER roads (`tiger_road_distance_m.tif`), BLM closed geothermal/mineral claims (`blm_closed_claim_distance_m.tif`), and DOE GDR `#1391` (`gdr_wellspring_in_footprint.csv` & `gdr_volcanic_vents_in_footprint.csv` with `dist_known_fault_px` dropped and asserted absent, `2m_temperature_probe_INGENIOUS_regional_data.zip`, `paleo_geothermal_regional.zip`).
- **Physical Signatures & Mathematical Transforms Targeted:**
  1. **2-D Fourier Baranov Pseudogravity Magnetite-Leaching Defect (`baranov_leaching_defect`):** Integrate `Band 02 (rtp)` in the 2-D Fourier wavenumber domain via Baranov (1957) / Cordell & Taylor (1971) pseudogravity operator $\widehat{\Psi}_{\text{pg}}(\mathbf{k}) = \widehat{\text{RTP}}(\mathbf{k}) / \max(|\mathbf{k}|, k_0)$, and compute the local sliding-window (`1.6 km`) orthogonalized excess of `Band 05/13` horizontal gravity gradient over $|\nabla_h \Psi_{\text{pg}}|$, gated by shallow electrical conductivity edges (`|\nabla_h \text{cond\_surf}|`, playa-vetoed) or 4-block-standardized `K/Th` + `214Bi` alteration. Isolates hydrothermally demagnetized, silica-densified blind fault conduits.
  2. **Reid $N=0$ Fault-Contact Euler Depth Concordance with `depth_to_base_surf` (`euler_n0_basement_concord`):** Estimate contact-top depth $z_{\text{Euler}}(x) = |\nabla_h F| / \max(|\nabla_h(\partial_z F)|, \epsilon)$ for structural index $N \to 0$ on gravity (`Bands 05, 11, 13`) and magnetics (`Bands 02, 03, 09`), scoring log-depth agreement with independent `Band 15 (depth_to_base_surf)` so shallow surficial volcanic clutter and deep plutonic bodies are rejected while buried basement-unconformity fault steps are retained.
  3. **Piedmont Bajada Toe-Flexure Hinge (`piedmont_toe_flexure`):** Compute directional down-slope convexity-to-concavity hinge $-\hat{\mathbf{g}}_z\cdot\nabla(|\nabla z_{\text{det}}|)$ across `150–1,200 m` basement ramps (`Band 15`), vetoing narrow V-shaped stream thalwegs ($\nabla^2 z_{\text{det}} > 0$), horizontal Lake Lahontan shorelines, and TIGER road prisms. Provides `100%` footprint coverage across the `24.63%` 1 m LiDAR gap.
  4. **Repaired 1 m LiDAR Scarp Collinearity Chain (`fixed_lidar_scarp_crest_chain`):** Applies 9-px 8-direction collinearity voting (`h33.collinearity_vote`) to true `ex_max + step_max + downface_max + cross_max` (`Bands 1, 3, 6, 8` inside `Band 12 valid`), excluded strictly from `M_NoLiDAR`.
  5. **Importance-Weighted Stratified SAR-PU Dual-Cover OOF + Azimuthal Coulomb Tip-Lobe vs. Broadside Stress-Shadow Gate (`coulomb_tip_vs_shadow_gate`):** Trains `57`-ch `M_Full` (inside LiDAR) and `53`-ch strictly LiDAR-free `M_NoLiDAR` (in the `24.63%` gap, quantile-calibrated on fold-training pixels) using inverse-proposal-weighted hard piedmont + uniform basin negatives, then applies fold-visible azimuthal Coulomb forward tip amplification (`|\psi| <= 42°`) and broadside interior cross-strike stress-shadow damping (`2.0 < d_vis <= 8.2 px`) + stationary mesoscale physical Max-Envelope before `min_sep_px = 3.1` (`310 m`) submodular CELF emission (`37,654` dots, `B = 2`).
- **Named Non-Fault Mimic & Explicit Rejection Filter:**
  - *Mimics:* (a) Unaltered non-magnetic carbonate/clastic contacts; (b) Incised alluvial-fan radial stream channels and Lake Lahontan (`~1,270–1,335 m`) wave-cut benches; (c) Cold saline playa evaporites (`cond_surf` high in flat sinks) and US-50/I-80 highway embankments.
  - *Vetoes:* Alteration/conductivity edge requirement on Baranov residual; thalweg Laplacian + equipotential contour-orthogonality veto on piedmont flexure; flat-playa slope/elevation decoupling; `tiger_road_distance_m` road-prism gate.
- **Why It Catches Missing Faults & Differs from Repo Prior Art:**
  Mapped catalogue traces (`labels.tif`) capture subaerial master range-front scarps; `CSST-BGHF` specifically reallocates budget out of the mechanically depleted broadside stress shadow onto (i) along-strike/wing-crack fault-tip propagations and (ii) `1–4 km` outboard buried bajada hinges, basement-matched $N=0$ contacts, and magnetite-leached hydrothermal conduits—while training the new channels *inside* the Dual-Cover OOF trees (fixing PR #10's frozen-OOF defect) and repairing `IR-K3-01`.
- **Expected DTI Gain & Cost:** **Highest** dual-benchmark gain (`+0.007` to `+0.010` on `HIDE-RECOVER-v3.0` AND `+0.003` to `+0.008` on `SGMC-CAL-v3.0` over the `0.2778` Champion, with `< 70%` 3-px dot overlap across all competitive discrete registry rasters); **Moderate** cost (`~6 min` CPU, `< 1.8 GiB` RSS).

---

### Rank 2 — `H-K3B-2`: *Anisotropic Geodesic Fast-Marching Relay-Ramp Bridge (`AGFM-Relay`)*

- **Layers:** Fold-visible fault terminations + `Band 05 (iso_grav_anom_slope)` + `Band 02 (rtp)` + repaired `lidar_scarp_features_u8.tif` (`Bands 1, 3, 6, 12`).
- **Physical Signature:** Minimum-action Sethian Fast-Marching / Dijkstra geodesic paths between en-echelon visible fault tips separated by `1.5–9.0 km` at conjugate Riedel/stepover angles (`15°–65°`) through a multi-physics slowness metric $W(x) = 1 / (\epsilon + \text{THDR}_{\text{grav}} + \text{THDR}_{\text{mag}} + S_{\text{LiDAR}})$.
- **Why It Catches Missing Faults:** Traces unmapped breaching splays across relay ramps where displacement is partitioned across sub-resolution strands.
- **Named Mimic:** Antecedent bedrock canyon transverse drainages cutting across horst blocks.
- **Difference from Repo Prior Art:** `GEMSDOE27` bridged `< 1.5 km` collinear topographic gaps; `crsb_gub` used local `sin^2` orientation dispersion without two-point geodesic boundary-value paths.
- **Expected Gain & Cost:** **Medium** (`+0.002` on `HIDE-RECOVER`, limited impact `> 10 km` from tips on `SGMC-cal`); **Medium–High** graph search cost. Held in reserve behind `H-K3B-1` to preserve single-lane discipline.

---

### Rank 3 — `H-K3B-3`: *2-D Wavenumber Directional Notch Flight-Line De-Corrugation of GeoDAWN Alteration Ratios (`FFT-Notch-Rad`)*

- **Layers:** `Band 06 (tc)` + `geodawn_rad_u8.tif` (`Bands 1=K, 2=Th, 3=U`) + `acquisition_block_id_100m.tif`.
- **Physical Signature:** Per-contractor-block 2-D FFT directional wedge notch filter removing E–W/N–S airborne tie-line leveling corrugations before computing 1-px Frangi ridge skeletons of $\log(\text{K}/\text{Th})$ potassic alteration and $^{214}\text{Bi}$ radon excess.
- **Why It Catches Missing Faults:** Recovers subtle (`0.3–0.7 SD`) fossil quartz-adularia/illite alteration halos along sealed paleogeothermal fault traces masked by flight-line striping.
- **Named Mimic:** Primary high-K rhyolitic ash-flow tuff stratigraphic margins.
- **Difference from Repo Prior Art:** `fbgr` and `crsb_gub` applied scalar per-block median/MAD normalization without wavenumber flight-line de-corrugation.
- **Expected Gain & Cost:** **Low–Medium** (`~30 cm` gamma-ray penetration depth is blanked by eolian sand/loess cover); **Low** cost.

---

### Rank 4 — `H-K3B-4` *(External Data Upgrade — Obtainability Verified)*: *USGS ComCat Relocated Hypocenter Planar Clustering + NASA ARIA Sentinel-1 InSAR Creep Gradients (`MicroSeis-InSAR`)*

- **Official Free External Sources:**
  1. USGS ANSS Comprehensive Earthquake Catalog API (`https://earthquake.usgs.gov/fdsnws/event/1/`) — relocated sub-km hypocenters (including the 2020 $M_w\,6.5$ Monte Cristo Range distributed shear zone, whereas competition `Bands 10 & 16` smooth over a `100 km` radius!).
  2. NASA/JPL ARIA Sentinel-1 Unwrapped Interferograms (`https://asf.alaska.edu/data-sets/derived-data-sets/sentinel-1-interferograms/`).
- **Physical Signature:** 3-D RANSAC plane-fitting on $M \ge 0.8$ microearthquake lineaments fused with InSAR LOS velocity horizontal gradient crests (`> 1.5 mm/yr` across `< 2 km`).
- **Named Mimic:** Agricultural groundwater pumping subsidence bowls in Mason/Smith/Fallon valleys.
- **Sandbox Obtainability Verification:** Checked against sandbox network policy — outbound connections are restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org`, and neither dataset is mirrored in `registry/data_manifest.json`. Therefore **flagged honestly as non-obtainable inside this sandbox** and documented for future runs with external mirror ingestion.

---

## 3. Preregistered 3-Experiment Ablation Plan (Strictly Within Lane `H-K3B-1: CSST-BGHF`)

1. **`EXP-1` (`CSST_BGHF_UNSUP_PHYS_D31`):** Purely unsupervised physical `CSST-BGHF` ridge surface (`0` catalogue supervision during surface scoring; visible catalogue used strictly for the mandatory `B = 2` exclusion collar), emitted at `37,654` dots with `min_sep_px = 3.1` (`310 m`) submodular CELF. Isolates standalone off-catalogue physical fault discovery.
2. **`EXP-2` (`CSST_BGHF_DUAL57_OOF_ISOTROPIC_D31`):** Importance-weighted stratified Dual-Cover OOF `HistGradientBoostingClassifier` trained end-to-end on all `57` channels (`M_Full` inside 1 m LiDAR; `53` strictly LiDAR-free channels `M_NoLiDAR` quantile-calibrated in the `24.63%` LiDAR gap) + isotropic tip cone, emitted at `37,654` dots (`min_sep_px = 3.1`, `B = 2`). Isolates the gain from training the new physical channels inside Dual-Cover OOF trees before azimuthal Coulomb shadow gating.
3. **`EXP-3` (`CSST_BGHF_COULOMB_MAXENV_D31` — Primary Candidate):** Full stationary `CSST-BGHF` surface combining the `57`/`53`-channel Dual-Cover OOF posterior, the **Azimuthal Coulomb Tip-Lobe vs. Broadside Stress-Shadow Gate** (`coulomb_tip_vs_shadow_gate` derived strictly from fold-visible faults `cell.visible_full` on holdout folds and `labels.tif` on live), and the **Propensity-Compensated Mesoscale Physical Max-Envelope** (`csst_bghf_unsup_ridge` + repaired LiDAR chain), emitted at `37,654` dots (`min_sep_px = 3.1`, `B = 2`).

### Mandatory Automated Promotion Gates
- **Gate G1 (Leakage Canary):** All `57/57` channels individually satisfy `max(AUC, 1 - AUC) <= 0.90` on `HIDE-RECOVER-v3.0`.
- **Gate G2 (Surface & Discrete Dot Uniqueness):** Pre-placement surface `|Spearman| <= 0.90` across `100%` of all `1,909` valid registry rasters (`112` repos + prior `GEMSDOEkarage3` PRs), AND final dots `|Spearman| <= 0.90` + directional `<= 3 px` dot overlap `<= 0.70` across `100%` of competitive discrete registry rasters (`<= 100,000` dots), with full non-exempt reporting of dense blankets and calibration lattices (`IR-K3-02`).
- **Gate G3 (Dual-Benchmark Holdout Superiority):** Beat the `0.2778` Champion (`H33-2-B2`) on **both** `GEMSDOE32-HIDE-RECOVER-v3.0` (`n = 22,232` withheld positives) AND `GEMSDOE32-SGMC-CAL-v3.0` (`n = 62,703` off-catalogue positives), with `256`-block paired spatial cluster-bootstrap `95% CI > 0` on `HIDE-RECOVER-v3.0` AND positive paired improvement on `SGMC-CAL-v3.0`.
- **Gate G4 (13-Check Saved-Byte GeoTIFF Validator):** Single-band `float32`, `EPSG:32611`, `3730 x 3292`, exact transform `[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]`, `nodata = None`, `12,279,160 / 12,279,160` finite cells strictly in `[0.0, 1.0]`, `0` NaNs anywhere, `0` on-catalogue positives, `gemsdoekarage3-` prefix, and note `<= 140` chars.
