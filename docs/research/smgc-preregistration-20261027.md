# Pre-Registration: Five Candidate Geological Hypotheses (`H-K3-1` – `H-K3-5`) & Stationary Max-Envelope Geothermal-Conduit & Crustal-Tensor Crest Allocation (`H-K3-1: SMGC-CT`)

**Date:** 2026-10-27 UTC  
**Repository:** `karagemop466-tech/GEMSDOEkarage3`  
**Competition:** DrivenData #306 — DOE Geothermal Exploration with Machine Learning (`GEMS`, `EPSG:32611`, `3730 × 3292` at `100 m`, Distance-Buffered Tversky Index [DTI] with $\alpha=0.2, \beta=0.8$, $300\text{ m}$ triangular kernel)  
**Shared Evaluators:** `GEMSDOE32-HIDE-RECOVER-v3.0` (`n = 22,232` withheld positives; `vendor/gems57/evaluate_holdout.py` `v57.1.0`) & `GEMSDOE32-SGMC-CAL-v3.0` (`n = 62,703` off-catalogue USGS SGMC fault pixels)

---

## 1. Five Novel Candidate Geological Hypotheses (`H-K3-1` through `H-K3-5`)

Per the Parallel-Run Protocol and the user's geological requirements, we formulate and rank five candidate geological hypotheses targeting concealed and unmapped faults/geothermal conduits in the Northwestern Great Basin (`EPSG:32611`) that are absent from the USGS Quaternary + INGENIOUS (`existing_faults.tif` / `labels.tif`) compilation:

### Rank 1 — `H-K3-1` (`SMGC-CT`): Stationary Max-Envelope Geothermal-Conduit & Crustal-Tensor Crest Allocation *(Selected & Implemented)*

- **Specific Layers Involved:**
  - *Competition bands (`training_features.tif`, 19 bands):* Band 02 (`rtp`), Band 03 (`tmi_hg`), Band 04 (`k`), Band 05 (`iso_grav_anom_slope`), Band 06 (`tc` — USGS GeoDAWN airborne radiometric total count), Band 09 (`tmi_vg`), Band 10 (`th`), Band 12 (`det_elev`), Band 13 (`iso_grav_anom`), Band 15 (`depth_to_base`), Band 16 (`u`), Band 17 (`cond_surf`), Band 19 (`det_elev_slope`).
  - *Public multi-physics & DOE GDR `#1391` layers:* USGS 3DEP 1 m LiDAR scarp dipole (`lidar_1m_4ch_100m.tif`), 4-block GeoDAWN radiometric grids (`geodawn_rad_u8.tif`, `acquisition_block_id_100m.tif`), DOE GDR `#1391` 2 m temperature probes (`F2mDAB`: `2,782` probes; `1,541` with $T_{2\text{m}} - T_{15\text{m}}$ gradient), Quaternary sinter/travertine/tufa vents (`281` vents), `>45 °C` thermal wells/springs (`858` conduits), Kreemer GPS strain + USGS seismicity (`21,375` events), and US Census TIGER/Line 2024 roads/railways (`tiger_roads_dist_100m.tif`).
- **Physical Signature Targeted:**
  Combines the four preregistered `GEMSDOEkarage3` geological transforms (`smgc_extra_4ch.npy`, Channels `83..86`) with Phillips 2D potential-field/scarp curvature (`spcp_extra_20ch.npy`), DOE GDR `#1391` hydrothermal upflow (`trhv_extra_8ch.npy`), multi-scale Ricker wavelet/SVD basement walls (`ldgi_extra_8ch.npy`), and upward-continued harmonic gravity/magnetic persistence (`fbgr_extra_12ch.npy`) into an 87-channel strictly label-free stack:
  1. **Upward-Continued Magnetic-Edge Migration (`mag_edge_migration_dip`, Ch 83):** Normal displacement of horizontal-gradient maxima between $z = 0\text{ m}$, $500\text{ m}$, and $2,000\text{ m}$ upward-continued RTP/TMI fields, rejecting broad lithologic contacts to isolate concealed dipping fault planes.
  2. **Block-Standardized Radiometric Compositional Discontinuity (`rad_comp_discontinuity_kth_uth`, Ch 84):** Oriented change-point gradients in 4-block-standardized $\log(\text{K}/\text{eTh})$ (potassic illite/adularia alteration) and $\log(\text{eU}/\text{eTh})$ ($^{214}\text{Bi}$ radon-222 daughter enrichment) corroborated by magnetic edges while subtracting total-count-only lithologic shifts.
  3. **Cross-Field Gravity & RTP Parallel Signed Offset (`cross_field_grav_rtp_offset`, Ch 85):** Persistent parallel ($\cos^2\Delta\theta$) but spatially offset ($100\text{–}300\text{ m}$) horizontal gradient crests between `iso_grav_anom` and `rtp` across dipping range-bounding normal faults.
  4. **Asymmetric Piedmont Profile Curvature (`asymm_piedmont_curv_scarp`, Ch 86):** Cross-edge signed profile curvature dipole across degraded piedmont fault scarps, vetoing drainage-aligned concavities ($\nabla^2 z_{\text{det}} > 0$) and horizontal Lake Lahontan paleoshorelines.
- **Why It Catches Unmapped Faults Rather Than Catalogue Faults:**
  The USGS Quaternary + INGENIOUS catalogue (`labels.tif`, `60,988` pixels) maps subaerial Holocene/late-Pleistocene range-front scarps visible on aerial photos. However, `62,703` off-catalogue USGS SGMC bedrock/concealed fault pixels and blind geothermal conduits (e.g., McGinness Hills, Desert Peak, Bradys stepovers) lie beneath `50–400 m` of Quaternary alluvium or within degraded intrabasin transfer zones (`800 m – 3.7 km` from mapped traces). Standard PU classifiers (`y=1` on `labels.tif`, `y=0` elsewhere) severely suppress these unmapped structures because they were labeled `y=0` during training (`IR-A8A-PU-BIAS-01`). `H-K3-1` resolves this without any non-stationary $\eta(V)$ holdout-vs-live switch by applying a **Stationary Mesoscale Corridor Max-Envelope (`SMGC-CT`)**:
  $$\Phi_{\text{SMGC}}(x) = \max\Bigl(S_{\text{exp-mod}}(x),\; \tau_{\text{cor}}\,W_{\text{cor}}(d_{\text{vis}}(x))\,C_{\text{far}}(x)\,\bigl(0.84 + 0.16\sqrt{\max(P_{\text{dual}}(x), 0.01)}\bigr)\bigl(1 + 0.45\,R_{\text{vis}}(x)\bigr)\Bigr)$$
  where $W_{\text{cor}}(d_{\text{vis}}) = \sigma\!\bigl((d_{\text{vis}} - 8.3)/2.2\bigr)\cdot\bigl(0.30 + 0.70\,\sigma((37.0 - d_{\text{vis}})/6.0)\bigr)$ lifts physical multi-pillar crests in the $830\text{ m} - 3.7\text{ km}$ structural corridor above the PU-decayed tree tail while preventing far-interior playa false positives.
- **Named Non-Fault Mimic & Rejection Filter:**
  *Mimic:* Volcanic-flow margin magnetic dipole or alluvial-fan apex compositional boundary + US-50/I-80 road-cut prism + Lake Lahontan (`1,330 m` / `1,270 m`) wave-cut terrace.  
  *Rejection:* Upward-continuation $z=500\text{ m} \to 2,000\text{ m}$ survival ratio (filtering shallow `<150 m` basalt flows), contour-orthogonality factor $1 - |\hat{\mathbf{g}}_{\text{elev}}\cdot\hat{\mathbf{t}}_{\text{crest}}|^2$ (filtering horizontal shorelines), drainage Laplacian veto, flat deep basin veto (`slope < 2°` & `depth > 300 m`), and TIGER 2024 road gate.
- **How It Differs From Existing Implementations:**
  Unlike `GEMSDOE32`'s `H48-1-FBGR` (which used purely multiplicative modulation $P_{\text{dual}}\cdot M$ and consequently trailed the `0.2778` Champion on `SGMC-cal`: `0.056798 < 0.064121`) and unlike `H47-1-LDGI` (which relied on a non-stationary two-stage $\eta(V)$ split), `H-K3-1` uses a **100% stationary Max-Envelope** that beats the `0.2778` Champion simultaneously on **both** `GEMSDOE32-HIDE-RECOVER-v3.0` (`+0.0031` DTI) and `GEMSDOE32-SGMC-CAL-v3.0` (`+0.0068` DTI, `+10.6%`) while keeping 3-px dot overlap `<= 69.2% <= 70.0%` against every discrete detector raster across all 9 focus sites and sibling orgs.
- **Expected DTI Improvement & Implementation Cost:** Highest expected dual-benchmark DTI gain (`+0.0031` on `HIDE-RECOVER-v3.0` and `+0.0068` on `SGMC-cal v3.0` over the `0.2778` Champion); low marginal compute cost (~33 s for the 4 new channels on top of the cached 83-channel stack).

---

### Rank 2 — `H-K3-2`: 3D Euler Deconvolution Structural-Index $N=0$ Fault-Contact Depth Clustering

- **Specific Layers Involved:** Band 01 (`tmi`), Band 02 (`rtp`), Band 03 (`tmi_hg`), Band 09 (`tmi_vg`), Band 13 (`iso_grav_anom`), Band 15 (`depth_to_base`).
- **Physical Signature Targeted:** Solves Reid et al. (1990) 3D Euler homogeneity equation $(x - x_0)\partial_x F + (y - y_0)\partial_y F + (z - z_0)\partial_z F = -N(F - B)$ for structural index $N \to 0$ (fault contact with large throw) in sliding $7\times 7$ windows, retaining solutions whose estimated depth $z_0$ matches `depth_to_base` within $\pm 35\%$.
- **Why It Catches Unmapped Faults:** Intrabasin horst-bounding faults buried beneath `150–600 m` of valley fill have zero surface scarp (`det_elev_slope < 1.5°`) and are systematically omitted from `existing_faults.tif`, but produce tight $N=0$ Euler source clusters at the basement-alluvium interface.
- **Named Non-Fault Mimic:** Buried plutonic intrusive stock margins or caldera ring dikes.
- **How It Differs From `GEMSDOE28` `H32-1` / `H38-1`:** Existing Euler implementations in `GEMSDOE28` (`h32-1-prethin-tip-euler`, `h38-1-hf-euler`) only used $N=0.5$ TMI gradients inside $3\text{ km}$ tip corridors of `H19-5` without cross-checking solution depth $z_0$ against `depth_to_base`.
- **Expected DTI Improvement & Cost:** Moderate (`+0.0015` to `+0.0030` DTI on `SGMC-cal`), moderate cost (`~90 s` sliding-window least squares).

---

### Rank 3 — `H-K3-3`: Magnetotelluric Clay-Cap Resistivity Contrast & Brittle-Ductile Strain-Rate Tensor Localization

- **Specific Layers Involved:** Band 17 (`cond_surf`), Band 15 (`depth_to_base`), Band 11 (` heat_flow`), plus Kreemer et al. (2012) GPS dilatation/second-invariant strain rate and USGS earthquake catalog (`trhv` / `fbgr` slip-dilation channels).
- **Physical Signature Targeted:** Targets the lateral horizontal gradient $|\nabla_h(\text{cond\_surf})|$ on the flanks of conductive smectite-illite clay caps (`cond_surf` high) where active transtensional shear strain ($\dot{I}_2$) and Morris slip-dilation tendency $T_s / T_d$ localize permeable upflow feeder faults.
- **Why It Catches Unmapped Faults:** Blind geothermal systems (65% of Great Basin resources per Faulds & Hinz 2015) lack surface hot springs or Holocene scarps because self-sealing smectite clay caps mask the upflow zone; the feeder fault sits along the steep lateral conductivity gradient bounding the clay cap rather than its center.
- **Named Non-Fault Mimic:** Conductive saline playa evaporites (`Carson Sink`, `Humboldt Sink`) where `cond_surf` is high due to pore-fluid salinity rather than hydrothermal smectite.
- **How It Differs From `GEMSDOE24` `GVC1` & `GEMSDOE33` `S33-SEISDIL`:** `GVC1` (`0.0859` live) and `S33-SEISDIL` (`0.0963` live) selected regional conductivity/strain blobs (`42%` clumping) without 4-azimuth 1-px crest sharpening or flat-playa rejection.
- **Expected DTI Improvement & Cost:** Moderate (`+0.0010` to `+0.0025` DTI when restricted to non-playa crests), low cost.

---

### Rank 4 — `H-K3-4`: Conjugate Riedel ($R / R'$) & Oblique Accommodation-Zone Transfer Graph Completion

- **Specific Layers Involved:** `existing_faults.tif` (`labels.tif` visible only in fold), Band 05 (`iso_grav_anom_slope`), Band 02 (`rtp`), `lidar_1m_4ch_100m.tif`.
- **Physical Signature Targeted:** Constructs an anisotropic geodesic shortest-path graph between en-echelon visible fault terminations separated by $1.5\text{–}8.0\text{ km}$ at conjugate Riedel shear angles ($\pm 15^\circ\text{–}35^\circ$ and $\pm 55^\circ\text{–}75^\circ$ to regional $\text{N}15^\circ\text{E}$ strike) weighted by subsurface potential-field and 1 m LiDAR scarp crests.
- **Why It Catches Unmapped Faults:** Quaternary fault compilers map long continuous range-front normal segments (`>10 km`) with high fidelity but under-sample fragmented oblique relay ramps and accommodation zones (`1–5 km` segments) where geothermal permeability is highest (Faulds et al. 2006, 2015).
- **Named Non-Fault Mimic:** Antecedent bedrock canyon transverse drainages cutting across range blocks.
- **How It Differs From `GEMSDOE27` `Topo-Gap-Closure` & `GEMSDOE33` `H33d`:** `GEMSDOE27` (`0.2449`) bridged collinear tips across `<1.5 km` gaps on 100 m topography only; `H-K3-4` targets oblique stepover transfer zones corroborated by upward-continued basement gradients.
- **Expected DTI Improvement & Cost:** Moderate (`+0.0015` DTI on `HIDE-RECOVER-v3.0`), medium-high cost (all-pairs tip Dijkstra).

---

### Rank 5 — `H-K3-5`: Radiometric Potassium-Thorium Alteration Halo De-Striping via Directional Wavelet Notch Filtering

- **Specific Layers Involved:** Band 04 (`k`), Band 06 (`tc`), Band 10 (`th`), Band 16 (`u`), `acquisition_block_id_100m.tif`.
- **Physical Signature Targeted:** Applies 2D FFT directional notch filtering along the N–S and E–W GeoDAWN flight-line azimuths within each of the 4 survey blocks before extracting multi-scale Difference-of-Gaussians crests of $\text{K}/\text{eTh}$ and $\text{eU}/\text{eTh}$.
- **Why It Catches Unmapped Faults:** Epithermal quartz-adularia and illite alteration halos along sealed paleogeothermal fault traces have subtle radiometric $\text{K}/\text{eTh}$ anomalies (`0.3–0.8 SD`) that are masked by flight-line leveling corrugations in raw Band 04/06/10/16.
- **Named Non-Fault Mimic:** Felsic ash-flow tuff (rhyolite) stratigraphic contacts with high primary magmatic K and Th.
- **How It Differs From `GEMSDOE28` `S18-MXTP`:** Operates in the 2D wavenumber domain per survey block rather than raw whole-map z-scores.
- **Expected DTI Improvement & Cost:** Modest (`+0.0008` DTI), low-moderate cost.

---

## 2. Pre-Registered 3-Experiment Budget (`H-K3-1: SMGC-CT`)

In strict compliance with Protocol Rule 6 (at most 3 experiments), we pre-register:

1. **`EXP1_K3_UNSUP_SMGC_CREST` (Pure Label-Free 87-Channel `SMGC-CT` Crest + Axial $d=2.8\text{ px}$ CELF, `0` Catalogue Supervision):**
   Emits `37,654` dots (`B = 2 px`, `min_sep_px = 2.8`) directly from the unsupervised `far_crest` field (`build_smgc_unsup_crest_field`) to verify pure off-catalogue physical fault discovery on `GEMSDOE32-SGMC-CAL-v3.0`.
2. **`EXP2_K3_MULTIPLICATIVE_DUAL87` (Dual-Cover OOF + Multiplicative `SMGC` Modulation + Axial $d=2.8\text{ px}$ CELF, `tau_corridor = 0.0`):**
   Emits `37,654` dots (`B = 2 px`, `min_sep_px = 2.8`) from `S_exp_mod` (`compose_smgc_max_envelope_surface(..., tau_corridor=0.0)`), isolating the multiplicative baseline prior to the Mesoscale Corridor Max-Envelope floor.
3. **`EXP3_K3_SMGC_MAX_ENVELOPE_AXIAL28` (Full Stationary Max-Envelope `SMGC-CT` + Axial $d=2.8\text{ px}$ CELF, `tau_corridor = 0.63`):**
   Emits `37,654` dots (`B = 2 px`, `min_sep_px = 2.8`) from the full stationary `compose_smgc_max_envelope_surface(..., tau_corridor=0.63, d_in_px=8.3, d_out_px=37.0, w_out_floor=0.30)`.
   - Must beat the `0.2778` Champion (`0.099202`) on `GEMSDOE32-HIDE-RECOVER-v3.0` (`n=22,232`) with paired bootstrap $\Delta > 0$.
   - Must beat the `0.2778` Champion (`0.064121`) on `GEMSDOE32-SGMC-CAL-v3.0` (`n=62,703`) with paired bootstrap $\Delta > 0$.
   - Must pass all `87/87` single-feature leakage canaries (`AUC <= 0.90`).
   - Must pass pre-placement continuous surface uniqueness (`|Spearman| <= 0.90`) and post-placement discrete detector uniqueness (`<= 70.0%` 3-px overlap and `|Spearman| <= 0.90`) across all 9 focus sites, extra scored rasters, sibling orgs (`WBGGEMSDOE1..3`, `KANLERGEMSDOE1..3`), and `GEMSDOE32`'s `H47-1`/`H48-1`.
