# Session 6 — geological hypotheses, ranked (2026-10-29)

Status: research note. Nothing here authorises an upload. Every candidate is
blocked by the literal calibration-lattice rule (see `evidence/dup-check-s6.json`).

## Honest scope statement

The brief asks for hypotheses "untried" in this repo. A full check is not possible:
the registry is not literal-complete (`registry/complete_registry_manifest.json`,
`literal_registry_complete=false`), and only 14 scored rasters are restored locally.
A word search of `src/` and `scripts/` found that **every input layer below was
already used in an earlier lane**. So the hypotheses differ by how the layers are
combined and tested, not by the data used. Each entry lists the earlier lanes that
touched the same inputs.

Sources are limited to those in `registry/sources.json`:
- official metric: DrivenData problem page (`page/967`, listed as `problem-metric`);
- masking clarification: the DrivenData forum thread 11516 (cited in the desk and
  the S6 cards, but NOT listed in `registry/sources.json`; flagged here, not added);
- official rules: NLR 96647 PDF;
- data: USGS GEODAWN (`usgs-geodawn`), INGENIOUS / GDR 1391 (`gdr-1391`),
  USGS 3DEP (`usgs-3dep`), EPSG:32611 (`epsg-32611`).

## Ranking

Ranked by (a) geological plausibility as a fault signal, (b) whether the test can
run on local data, and (c) whether it is still open. Rank 1 is the next to test.
Score is not used to rank.

| Rank | ID | Hypothesis (one line) | Status | Result |
|---|---|---|---|---|
| 1 | **H4** | Qfault traces that are NOT already in the catalogue mark off-catalogue faults. | **Not run. Precondition: check whether `gdr_qfaults_traces.csv` is already inside `labels.tif`.** | — |
| 2 | H3 | Radiometric K/Th alteration halos along LiDAR-coherent lineaments mark fault-controlled fluid pathways. | Not run. | — |
| 3 | H2 | Coherent LiDAR scarp steps (`step_max` × `coh100`) mark fault scarps not sampled by the focus files. | Run as S6-E2. **DUPLICATE_STOP** (lattice 99.88%). | Proxy 0.0990 [0.0750, 0.1213] vs random null 0.0693–0.0732. Logged, not advanced. |
| 4 | H1 | Off-consensus ridge crests of total magnetic intensity horizontal gradient (`tmi_hg`) carry off-catalogue faults. | Run as S6-E1. **DUPLICATE_STOP** (lattice 99.74%). | Proxy 0.0452 [0.0328, 0.0584], **below** the random null. Negative. |

### H4 — Qfault traces off the catalogue (rank 1, not yet run)
- **Layers:** `gdr_qfaults_traces.csv` (INGENIOUS / GDR 1391 Qfault traces, local CSV).
- **Signature:** dots on Qfault trace pixels that are NOT within 3 px of a `labels.tif` fault.
- **Why off-catalogue:** the catalogue is the USGS/INGENIOUS set; Qfault traces are a separate mapping and may contain faults the catalogue lacks.
- **Difference from repo:** earlier lanes read Qfault traces (`src/gems32/h36_tdr_pds.py`, `hypotheses33.py`, `spcp.py`) but I did not find an *off-catalogue-only* test. This must be verified before claiming novelty.
- **Precondition (must pass before any run):** measure how many Qfault pixels already lie in `labels.tif`. If nearly all do, H4 collapses into the catalogue and is dropped.
- **Named mimic:** mapped-trace stair-stepping and digitising error.
- **Validation plan:** duplicate check first, then SGMC proxy with a random null (same budget). Canary AUC ≤ 0.90.

### H3 — K/Th alteration halos on lineaments (rank 2, not yet run)
- **Layers:** `geodawn_rad_u8.tif` K and Th bands (by description); `lidar_scarp_features_u8.tif` `coh100` and `strike`.
- **Signature:** high K/Th ratio co-located with coherent lineaments.
- **Why off-catalogue:** fluid-altered ground can show radiometric anomalies with no mapped surface fault.
- **Difference from repo:** `geodawn_rad` is used in `src/gems32/crsb_gub.py`, `fbgr.py`, `h33.py`, `h35_new.py`, `spcp.py`, `hk3d_tgsf.py`. The K/Th *ratio gated by lineament coherence* combination is what is new here, and must be checked against those lanes.
- **Named mimic:** lithology contrast (granite, playa sediment) produces K/Th highs without faults.

### H2 — LiDAR scarp step × coherence (rank 3, tested, DUPLICATE_STOP)
- **Run:** S6-E2 (`scripts/exp_s6_lidar_lineament.py`, `evidence/exp-s6-e2-lidar-lineament.json`).
- **Inputs are not new:** `step_max` and `coh100` appear in `src/karage3/ccl.py`, `hk3d_tgsf.py`, `surfaces_k3.py`, and `src/gems32/mdrc.py`. Only the product surface is tested here.
- **Result:** proxy DTI 0.0990 [0.0750, 0.1213], inside the focus band on the point estimate (0.0943–0.1024), above the random null (mean 0.0710), and with a wide CI. Canary AUC 0.709 (≤ 0.90, passes). Road-control share 8.25% vs 16.2% of the footprint.
- **Why it is not advanced:** the literal 3-px overlap with the calibration lattice is 99.88%, which triggers DUPLICATE_STOP. The proxy was scored before the duplicate check ran (IR-S6-12). Nothing here is validated.

### H1 — tmi_hg ridge crests off the focus cluster (rank 4, tested, DUPLICATE_STOP)
- **Run:** S6-E1 (`scripts/exp_s6_offconsensus.py`, `evidence/exp-s6-e1-offconsensus.json`).
- **Inputs are partly prior art:** a 4-azimuth NMS ridge family exists in `src/gems32/crsb_gub.py` (`crsb_gub_unsup_ridge`, `sharpen_4azimuth_nms`). `tmi_hg` is the input this run adds.
- **Result:** proxy DTI 0.0452 [0.0328, 0.0584], **below** the random null (0.0693–0.0732). Canary AUC 0.490 (no single-feature signal). Lattice overlap 99.74%.
- **Reading:** on this proxy the magnetic ridge selection is anti-informative. It is not evidence that faults are absent from those crests.

## Controls used for every proxy claim
- Random-placement null, same budget, same SGMC evaluator: `evidence/control-random-null-sgmc.json` (five draws, 0.0693–0.0732).
- Focus-band comparison: `evidence/focus-site-audit-20261029.json` (nine files, 0.0943–0.1024).
- Duplicate check, run before any proxy claim: `evidence/dup-check-s6.json`.
- Leakage canary: single-feature AUC ≤ 0.90 (`evidence/exp-s6-e*.json`).

## Limits
- The SGMC proxy is off-catalogue but is not the organizer's hidden labels. No ORGANIZER-CONFIRMED receipt exists.
- The catalogue hide-and-recover holdout is misaligned with the official masking rule (IR-S6-02) and is not used to rank.
- The lattice rule is literal (user instruction: no exemptions). No candidate in this note can pass it.
- Experiments used in Session 6: 2 of a budget of 3. The next run should be H4, and only after its precondition check.
