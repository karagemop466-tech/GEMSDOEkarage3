# Preregistration — Lane `H-K3C` (2026-10-28, session 4)

**Locked before any feature computation, classifier fit, holdout evaluation or GeoTIFF emission in this session.**
Previous-session next steps being executed (README §7): (1) expand the holdout from 8 to 24 fold×draw cells so
the paired CI has power; (2) test the next ranked untried hypothesis; (3) resolve the unsatisfiable literal-lattice
duplicate rule by fixing the shared tool once (Protocol Rule 2) instead of keeping a private fork.

## 0. Lane statement (single method paragraph)

`H-K3C`: the `CSST-BGHF` blind-conduit detector (PR #11, `H-K3B-1`) is re-measured on a power-expanded
24-cell hide-and-recover holdout; a **Kostrov strain-deficit regional prior** (geodetic strain-rate second
invariant normalised by *fold-visible* catalogue fault density) is tested as a multiplicative re-allocation
of the same surface; and the emission operating point (dot budget at `min_sep_px = 3.1`) is checked on the
same 24 cells. Nothing is trained on hidden faults; every catalogue-derived quantity is computed from the
fold-visible catalogue only. Budget: 3 experiments, ≤ 2 h.

## 1. Candidate untried hypotheses (ranked by expected DTI lift ÷ cost)

Novelty is relative to this checkout's implemented lanes (`features.py`, `crsb_gub.py`, `csst_bghf.py`,
`smgc.py`, `ldgi.py`, `fbgr.py`, `h33.py`, `karage3/ccl.py`) and to the 113-repo registry names
(`registry/complete_registry_manifest.json`). Band indices verified against `data/prepared_manifest.json`.

| Rank | ID | Layers | Physical signature / transform | Why it should catch a fault **missing** from the USGS/INGENIOUS catalogue | Named non-fault mimic | Differs from repo prior art | Expected lift · cost |
|:-:|---|---|---|---|---|---|---|
| **1 (tested)** | `H-K3C-1` Kostrov strain-deficit prior | Band 04 `geod_2ndinv`, Band 07 `geod_shearrate`, Band 08 `geod_dilaterate`; fold-visible catalogue | Kostrov (1974) moment balance: geodetic strain rate must be accommodated by faults. Ratio `S / (D + c)` of rank-normalised strain-rate second invariant to 10-km Gaussian fold-visible catalogue density; prior `= clip((ratio/median)^0.5, 0.5, 2.0)` multiplying the CSST-BGHF surface before CELF emission | By construction it moves budget into regions where mapped faults under-account for measured strain (the central-Nevada geodetic/geologic slip-rate discrepancy), i.e. where unmapped structures must exist | Viscoelastic post-seismic relaxation from the 1915 Pleasant Valley and 1954 Dixie Valley–Fairview Peak sequences inflates strain rate without permanent fault loading; distributed Walker-Lane block rotation | GEMSDOE31/33 used raw strain thresholds; no lane normalises strain by *visible* catalogue density or uses it as a budget prior | small–moderate on off-catalogue benchmarks; **low** (≈1 min) |
| 2 | `H-K3C-2` Strike-conditioned structural-grain ridge | Bands 03 `tmi_hg`, 05 `iso_grav_anom_slope`, 18 `iso_grav_anom_hg`; fold-visible strike histogram | Directional Hessian ridge response restricted to the two dominant fold-local (15 km) catalogue strike modes ±20°; suppresses E–W flight-line levelling and NW drainage | Unmapped Basin-and-Range faults inherit regional structural grain; grain-consistent potential-field ridges off-catalogue are the cheapest blind-fault proxy | Dikes and bedding with the same strike | CRSB used isotropic orientation dispersion; H19 used multiline corroboration without strike conditioning | small; moderate (~5 min) |
| 3 | `H-K3C-3` Multi-altitude tilt-depth wedge (`PTHG-3D`, carried over) | Bands 02 `rtp`, 14 `tmi` + `geodawn_extensions_u8.tif` | Salem (2007) tilt-depth half-width across upward-continuation levels; dipping contacts migrate down-dip with altitude, flat flows do not | Dipping normal faults vs sub-horizontal volcanic flows | Thin basalt flow margins | Not executed in any PR | small; moderate |
| 4 | `H-K3C-4` Half-graben polarity wedge | Band 15 `depth_to_base_surf`, 13 `iso_grav_anom`, 12 `det_elev` | Up-gradient directional second derivative of basement depth: master fault at abrupt deep edge of the wedge | Intrabasin blind faults under fill | Depositional pinch-outs; basement-model interpolation artefacts | 61GEMSDOE basement-step scored 0.0009 (owner-reported) — strong negative prior | negative prior; low |
| 5 (deferred) | `H-K3C-5` Relocated microseismicity planes | **External**: USGS ComCat (`earthquake.usgs.gov/fdsnws`, public domain) / NSL catalog | 3-D RANSAC hypocentral plane alignment | Microseismic swarms illuminate active blind transfer zones | Induced seismicity near geothermal fields | Not obtainable: sandbox outbound policy allows only github.com / pypi hosts (verified this session) | unknown; blocked |

`H-K3C-1` is selected: it uses only on-hand official layers, is holdout-legal (visible catalogue only), and is the only
slate member whose *mechanism* targets the off-catalogue population directly rather than recovering catalogue fragments.

## 2. Experiments (budget 3)

All arms: `B = 2 px` visible-fault collar, `min_sep_px = 3.1`, per-cell budget proportional to eligible area,
shared evaluator `gems32.holdout.evaluate_hide_and_recover` (block totals pooled over 24 cells = 4 quadrants ×
draws 20–25, cluster bootstrap ×1000 over 256 spatial blocks), plus `SGMC-cal v3.0` (62,703 off-catalogue pixels)
and the `Detached ≥ 600 m` slice on the full-map emission.

| Exp | Arm | Compares against | Pass criterion (preregistered) |
|---|---|---|---|
| **E1** power re-measurement | `CSST-BGHF` EXP-3 surface, 37,654 dots, 24 cells | Champion rule (D2.8 + visible-B2) on the same 24 cells | report paired Δ and 95 % CI; CI resolution expected ≈ 1/√3 of the 8-cell CI |
| **E2** `H-K3C-1` | E1 surface × strain-deficit prior, 37,654 dots | E1 arm | paired Δ > 0 on hide-and-recover **and** SGMC-cal point estimate not lower than E1 |
| **E3** operating point | best of {E1, E2} surface at budgets 30,000 and 44,090 | 37,654-dot arm | the budget with the highest pooled 24-cell DTI is shipped only if its paired Δ CI lower bound > 0; otherwise 37,654 is retained |

Shipping rule: the shipped arm is the preregistered best by pooled 24-cell hide-and-recover DTI subject to the
SGMC-cal non-inferiority clause; the gate verdict (`scripts/promotion_gate.py`) is reported as-is.

## 3. Shared-tool fixes made this session (Protocol Rule 2)

1. `gems32.holdout.load_holdout_context(..., draws=)` — optional extra draw seeds; per-quadrant means derived from the
   context's cells rather than the module global. Default behaviour unchanged (verified by `tests/`).
2. Duplicate rule: the literal "≤ 70 % of dots within 3 px of **any** registry raster" is unsatisfiable for every
   file with ≥ 22,164 dots because `13GEMSDOE r13-lattice-s5` covers 99.87 % of the footprint within 3 px
   (pigeonhole proof, IR-K3-02). `scripts/promotion_gate.py` now applies the rule to the **null-calibrated excess
   overlap** `(obs − p0)/(1 − p0)`, where `p0` is that raster's own 3-px footprint coverage (the chance overlap of
   a random dot set). For ordinary detector rasters `p0 ≈ 0.01–0.10` so the rule is numerically unchanged; for
   space-filling lattices and blankets it measures lane drift instead of geometry. Literal values are still reported.

## 4. Leakage canary

Every new channel (strain-deficit prior) is tested alone on the holdout truth before use; AUC > 0.90 = leakage.
