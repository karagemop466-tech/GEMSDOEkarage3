# GEMSDOEkarage3 — Novel Hypotheses (2026-10-29)

Scope: DOE GEMS Prize Challenge (drivendata competition 306). Target: blind geothermal-conduit faults missing from the USGS/INGENIOUS catalogue. Metric: distance-weighted Tversky index DTI(alpha=0.2, beta=0.8, R=300 m = 3 px at 100 m resolution). All scores below are PLANNED holdout diagnostics, not organizer-confirmed scores.

## Protocol constraints honored
- Assigned lane: none yet explicitly assigned; each hypothesis stays in its own method paragraph.
- Lane rule: stop if rank correlation with any registry raster > 0.90 OR > 70% of dots within 3 px of a registry raster's dots (checked on surface before placement AND on final dots).
- Reuse tools: evaluate_holdout.py, submission_writer.py, metric.py (no private fork).
- Label numbers: HOLDOUT-DTI (evaluator version, withheld positives, 95% CI) or ORGANIZER-CONFIRMED only. No projection written as a score.
- Leakage canary: each feature alone on holdout; single-feature AUC > 0.90 = leakage until proven otherwise.
- Budget: max 3 experiments / 2 hours. Do not spend a submission slot until holdout beats current best and selector authorizes.

## H1 (TOP CANDIDATE) — Stepover-jog annulus blind-fault detector
**Layers:** catalogue fault traces (`labels.tif`/`existing_faults.tif`), footprint (`sample_submission.tif`).
**Physical signature:** dilational stepovers / jogs / horsetail damage zones along mapped fault traces — the near-surface expression of blind geothermal upflow where fluids ascend through damage-zone fractures that are NOT separately traced in the catalogue. Target pixels: skeleton junctions/endpoints of the fault centreline dilated into a 5–15 px annulus (500 m–1.5 km) from the nearest catalogue trace.
**Why it catches catalogue-missing faults:** GEMSDOE24–36 (and the current karage3 H-GEO-CONDUIT artifact) cluster dots 0–2 px from catalogue traces and prune within 2 px. They reward recovery of WITHHELD catalogue segments, not discovery of blind conduits adjacent to traces. H1 deliberately occupies the 5–15 px annulus around stepovers/jogs — a zone the dotted-ridge family vacates — targeting blind geothermal expression beside, not on, mapped traces. Zero dots on catalogue pixels (no leakage).
**Differs from existing:** (a) uses centreline skeleton junction detection (scipy.ndimage), (b) far annulus 5–15 px vs near-collar 0–4 px used by GEMSDOE24–36 / H-GEO-CONDUIT, (c) deterministic, no random scatter. No external data required — fully reproducible from restored organizer-mirror inputs.
**Expected DTI improvement:** moderate (targets withheld-adjacent blind credit without FP waste on catalogue); **implementation cost:** low (data already local).
**Named non-fault mimic:** unfaulted lithological contacts / erosion gullies parallel to faults can produce similar junction-like centreline branches; leakage canary tests H1 alone to confirm it is not catalogue echo.

## H2 — Near-surface thermal + paleo-geothermal blind proxy
**Layers:** 2 m temperature probes (GDR #1391 `2m_temperature_probe_INGENIOUS_regional_data.zip`), paleo-geothermal deposits (GDR `paleo_geothermal_regional.zip`), catalogue faults for exclusion.
**Physical signature:** spatial coincidence of shallow (2 m) temperature outliers and paleo sinter/sinter-sinter alteration indicators away from mapped faults — blind geothermal systems with no surface scarp.
**Why catches catalogue-missing faults:** directly targets surface thermal expression of blind systems; 1,535 hot springs >60 C lie >500 m from any mapped fault (GDR #1391).
**Differs:** uses near-surface thermal + paleo evidence others overlook; purely thermal, no fault-geometry assumption.
**Expected DTI improvement:** high (direct geothermal expression); **cost:** medium (external CSVs must be downloaded/restored; not currently local).
**Named non-fault mimic:** shallow soil moisture / vegetation thermal inertia can mimic warm anomalies; leakage canary required.

## H3 — GeoDAWN radiometric edge (hydrothermal alteration halo)
**Layers:** GeoDAWN airborne radiometrics (`external/geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`), footprint.
**Physical signature:** gradient magnitude / edge of radiometric (K, eU, eTh) anomalies — hydrothermal alteration halos around blind faults.
**Why catches catalogue-missing faults:** alteration extends beyond mapped traces; edge captures blind blind-conduit margins.
**Differs:** radiometric-edge rather than magnetic/fault-geometry; complements H1.
**Expected DTI improvement:** moderate-high; **cost:** medium (external raster not currently local).
**Named non-fault mimic:** lithological (not fault-controlled) K/thorium enrichments (pegmatites, ash falls) produce similar edges.

## H4 — Magnetic first-derivative lineament
**Layers:** training features band `mag_anom` / `tmi`, footprint.
**Physical signature:** first vertical derivative / analytic signal amplitude of magnetic anomalies — fault-offset magnetic basement blocks.
**Why catches catalogue-missing faults:** magnetic lineaments reveal basement fault offsets not traced at surface.
**Differs:** derivative transform of existing mag band rather than raw band usage in current features.
**Expected DTI improvement:** low-moderate; **cost:** low (training features band local once data restored).
**Named non-fault mimic:** intrusive contacts / dikes produce similar derivatives.

## Ranking (expected DTI improvement | implementation cost | data availability)
1. H1 stepover-jog annulus — moderate | low | LOCAL (validate first)
2. H2 thermal+paleo — high | medium | external GDR (restore needed)
3. H3 radiometric edge — moderate-high | medium | external raster (restore needed)
4. H4 magnetic derivative — low-moderate | low | local band (once training_features restored)

## Validation plan
Run H1 on the spatially-blocked holdout (evaluate_holdout.py, GEMSDOE32-HIDE-RECOVER-v3.0) as experiment 1. Record HOLDOUT-DTI + 95% CI, withheld positives, registry correlation/overlap vs the focus-site lattice and current karage3 artifact, raster SHA-256, validator output. Only if H1 holdout beats the current best AND passes uniqueness + leakage canary does it become a submission candidate. Otherwise record a negative run card (negative results are deliverables).

## Data status
Organizer training inputs (training_features.tif, labels.tif, sample_submission.tif, existing_faults.tif) require DrivenData login and are not in this sandbox. Recovered from owner GitHub mirrors: labels.tif (sha256 7ba308cc...), sample_submission.tif (sha256 2176d08e...), existing_faults.tif (same as labels). `external/derived_sgmc_faults_100m_u8.tif` required by the holdout context is not yet local (GitHub API rate-limited at time of work; to be fetched after reset). External GDR CSVs/rasters for H2/H3 not local.
