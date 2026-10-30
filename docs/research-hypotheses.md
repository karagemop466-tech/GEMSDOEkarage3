# Candidate geological hypotheses — GEMSDOE blind-fault / geothermal-vent detection

Status: **proposals only, not experiments.** None has been validated on a holdout set because this checkout does not contain `training_features.tif` or organizer-held labels (both require DrivenData login). No score or DTI estimate is claimed for any hypothesis. Per the parallel-run protocol, the top candidate must be validated on the spatially-blocked holdout (hide-and-recover, whole-segment buffering, pooled DTI alpha=0.2 beta=0.8, 300 m triangular kernel) and pass a single-feature leakage canary (AUC <= 0.90) before any weekly submission slot is used.

## Data basis (from the competition's training feature stack)

The pinned `training_features.tif` grid (SHA-256 `4371c82e…` per `data/prepared_manifest.json`) contains, among others, these bands used below:

| Band | Name | Meaning |
|---|---|---|
| 3 | `tmi_hg` | Total magnetic intensity horizontal gradient (edge/lineament detector) |
| 4 | `geod_2ndinv` | Geodetic 2nd invariant (distributed strain-rate magnitude) |
| 5 | `iso_grav_anom_slope` | Isostatic gravity anomaly slope |
| 7 | `geod_shearrate` | Geodetic shear-strain rate |
| 8 | `geod_dilaterate` | Geodetic dilation-strain rate |
| 13 | `iso_grav_anom` | Isostatic gravity anomaly |
| 15 | `depth_to_base_surf` | Depth to conductive / crystalline base |
| 17 | `cond_surf` | Surface conductivity (fluid / alteration proxy) |
| 18 | `iso_grav_anom_hg` | Isostatic gravity horizontal gradient (density-contrast edge) |
| 19 | `det_elev_slope` | Detrended elevation slope (topographic scarp proxy) |

Official/free sources referenced: USGS GeoDAWN airborne magnetic/radiometric survey (DOI 10.5066/P93LGLVQ), GDR submission 1391 / INGENIOUS (gdr.openei.org/submissions/1391, DOI 10.15121/1881483), competition problem page 967, NLR rules PDF, DrivenData reference solution.

## The target (from problem page 967)

The hidden test labels are faults **not** in the USGS/INGENIOUS catalogue. A detector that only re-dots catalogue traces cannot earn credit for hidden off-catalogue faults. Every hypothesis below therefore targets off-catalogue/blind structure and explicitly names the non-fault process that could mimic it (leakage canary required).

---

## H1 — Off-catalogue stepover / relay-ramp structural prior (top candidate for cost)

- **Layers:** `geod_2ndinv` (band 4), `geod_shearrate` (band 7), `geod_dilaterate` (band 8), `det_elev_slope` (band 19).
- **Physical signature:** Localized zones of moderate shear + dilation (relay ramps / step-overs between en-echelon fault strands) sitting OFF mapped catalogue traces. These are high-fracture-permeability conduits and classic blind geothermal upflow settings in the Great Basin.
- **Why it catches catalogue-missing faults:** Regional catalogues map discrete traces but systematically under-map relay ramps and blind step-overs hidden under cover. Those structures host geothermal circulation without a mapped surface trace.
- **Named non-fault mimic:** Landslide scarps, road cuts, fence/acquisition lineaments and lithologic contacts can also show shear/dilation-like gradients; a single-feature canary vs catalogue labels must stay under AUC 0.90.
- **Differs from existing work:** The GEMSDOE24/25/27/28/30/31/32/33/36 dotted-ridge family dots cluster ON/near catalogue traces and reuse one dot array. H1 places dots in the structural ZONE between traces, deliberately off-catalogue.
- **Implementation cost:** LOW–MED (all bands already in the feature stack; no new external data).
- **Expected DTI improvement:** MED (plausible blind-fault signal; unvalidated).

## H2 — Conductive-surface + gravity-gradient co-location (geothermal-fluid proxy)

- **Layers:** `cond_surf` (band 17), `iso_grav_anom_hg` (band 18), `iso_grav_anom_slope` (band 5).
- **Physical signature:** High surface conductivity (clay alteration / fluid-filled fractures) coincident with a gravity horizontal-gradient edge (density contrast across a fault). Co-location marks a fault-controlled fluid pathway.
- **Why it catches catalogue-missing faults:** Conductive alteration halos and blind fluid conduits commonly extend beyond the mapped fault trace. Gravity-gradient edges capture density contrasts from blind offset that surface mapping misses.
- **Named non-fault mimic:** Conductive clay beds, shallow groundwater, alluvial basins and radiometric anomalies can produce conductivity/gravity contrasts without a fault.
- **Differs from existing work:** Existing implementations lean heavily on magnetics + DEM scarps (dotted-ridge). H2 adds conductivity + gravity-gradient co-location, a different physical domain (fluid/density, not just structure/topography).
- **Implementation cost:** MED (bands 17/18/5 present; requires percentile-rank fusion and a canary).
- **Expected DTI improvement:** MED–HIGH (directly targets the geothermal-fluid signal, the actual prize target).

## H3 — Depth-to-conductive-base step + magnetic-gradient edge (basement control)

- **Layers:** `depth_to_base_surf` (band 15), `tmi_hg` (band 3), `cond_surf` (band 17).
- **Physical signature:** A sharp step in depth-to-conductive/crystalline base coincident with a magnetic horizontal-gradient edge. Basement-offset faults focus geothermal upflow where conductive cover is thinned.
- **Why it catches catalogue-missing faults:** Basement-involved faults can be blind at the surface (covered by younger alluvium) yet control geothermal systems; depth-to-base steps reveal them where surface fault mapping is absent.
- **Named non-fault mimic:** Intrusive contacts, dike margins and lithologic boundaries also produce depth-to-base and magnetic-gradient steps without being through-going faults.
- **Differs from existing work:** Most existing files use surface DEM/magnetics; H3 uses the structural-depth band (15), which no focus-site file is known to exploit as a primary detector.
- **Implementation cost:** MED (band 15 has ~30k sentinel pixels to handle; depth step must be derived carefully).
- **Expected DTI improvement:** MED–HIGH (novel structural-depth layer; unvalidated).

## H4 — Strain-rate second-invariant ridges (tectonic, lowest cost)

- **Layers:** `geod_2ndinv` (band 4) alone.
- **Physical signature:** Ridge lines of elevated distributed strain-rate magnitude.
- **Why it catches catalogue-missing faults:** Distributed deformation zones may not be individually mapped in the catalogue but concentrate strain where blind faults accommodate extension.
- **Named non-fault mimic:** Topographic scarps, landslides and erosional lineaments produce high strain-like gradients without being faults (highest leakage risk of the set — canary is essential).
- **Differs from existing work:** Single-band tectonic-strain detector; not yet represented among focus-site submissions.
- **Implementation cost:** LOW (one band).
- **Expected DTI improvement:** LOW–MED (signal is diffuse; leakage risk high).

## H5 — Radiometric / thermal + magnetic vertical-gradient alteration halo

- **Layers:** `tc` (band 6), `tmi_vg` (band 9), `tmi` (band 14).
- **Physical signature:** Coincident radiometric/thermal anomaly (`tc`) and magnetic vertical-gradient edge (`tmi_vg`), marking alteration around a blind fault.
- **Why it catches catalogue-missing faults:** Hydrothermal alteration halos extend around blind faults and can be detected radiometrically/magnetically even where no trace is mapped.
- **Named non-fault mimic:** Volcanic/sedimentary lithologic contacts, drainage patterns and cultural noise can mimic alteration/magnetic anomalies.
- **Differs from existing work:** Adds the magnetic vertical-gradient + radiometric thermal pair, not used as a primary detector in the focus-site files.
- **Implementation cost:** MED.
- **Expected DTI improvement:** LOW–MED (alteration is a proxy, not the fault itself).

---

## Ranking (expected DTI improvement vs implementation cost)

| Rank | Hypothesis | Expected DTI | Cost | Data needed to validate |
|---|---|---|---|---|
| 1 | H2 conductive-surface + gravity-gradient co-location | MED–HIGH | MED | `training_features.tif` + labels (DrivenData) |
| 2 | H3 depth-to-base step + magnetic-gradient edge | MED–HIGH | MED | `training_features.tif` + labels (DrivenData) |
| 3 | H1 off-catalogue stepover / relay-ramp prior | MED | LOW–MED | `training_features.tif` + labels (DrivenData) |
| 4 | H4 strain-rate second-invariant ridges | LOW–MED | LOW | `training_features.tif` + labels (DrivenData) |
| 5 | H5 radiometric/thermal + magnetic vertical-gradient | LOW–MED | MED | `training_features.tif` + labels (DrivenData) |

**Top candidate to implement next:** H1 (lowest cost, directly addresses catalogue-missing blind structure) — but H2/H3 target the geothermal-fluid signal more directly and are preferred if implementation budget allows.

## What was actually generated this session

`scripts/build_unique_submission.py` produced `karage3-offcat-corridor-prior-v1`, a **geometric prior placeholder** (off-catalogue exclusion + distance-from-catalogue weighting + Poisson-disc placement). It is format-valid and unique vs all 9 focus sites but is **NOT** a validated geological detector: it does not use any training_features band. It is marked **NOT OK TO SUBMIT** with no score estimate. It is a placeholder until training_features.tif is obtained and H1/H2/H3 can be implemented and holdout-validated.

## Blocker

`training_features.tif` is not in this checkout and cannot be downloaded without DrivenData authentication (the data page redirects to login; allowed sandbox hosts do not include drivendata.org). Until it is obtained (or a verified mirror with the same grid), no hypothesis can be holdout-validated, no leakage canary can be run, and no submission slot is justified.
