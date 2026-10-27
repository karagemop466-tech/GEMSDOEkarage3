# K3 pre-registration (frozen before any holdout result in this repo)

Date (UTC): 2026-10-27. Lane: **K3 — corrected-LiDAR scarp-pair + depth-persistent potential-field
worms, with a geothermal-upflow boost, emitted by expected-DTI greedy coverage.**
Budget cap: 3 experiments. This file must not be edited after Exp 1 runs; amendments go in a
dated addendum.

## Why the champion scored 0.2778 (verified mechanism, to be re-measured as Exp-1 controls)

Source files read line-by-line in the sister clones pinned in `registry/focus9_registry.json`:

* `GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json`:
  H33-2-B2 = “0.2708 base with every dot at d(catalogue) ≤ 2 px deleted (37,654 dots)”.
* `evidence/h33_validation.json`: base = `gems28-h27-4-r1-solo-d2-8…` (40,199 dots,
  owner-reported 0.2708); B2 removed 2,545 dots (the d≤2 ring); B3 (35,483) scored lower on the
  live-mirror instrument → B=2 is the measured optimum of that one-parameter family.
* `GEMSDOE28/README` forensic: H19-5 (121,131 px) → dotted d2.8 (44,090) → solo (40,199) →
  champion (37,654), dot-set symdiff 0 at each step; GEMSDOE36 “PINN” = champion + 1,200 dots;
  GEMSDOE25-best ≡ GEMSDOE30-best; GEMSDOE28-solo ≡ GEMSDOE31-best.

PhD-level explanation. The metric pays, per hidden-fault pixel, the best triangular-kernel
credit (radius 3 px) among predicted dots, and charges α=0.2 × FP mass. Three nested effects
explain the whole lineage 0.1922 → 0.2600 → 0.2708 → 0.2778:

1. **Dotting (emission geometry).** On a 1-px ridge, adjacent pixels are kernel-redundant:
   the second pixel adds ~0 marginal TP (max-credit already ≈1) but pays full FP weight where
   the ridge is wrong. Priority Poisson thinning at 2.8 px keeps one dot per 300 m kernel
   footprint *along the crest* (1-D retention 0.9063 measured live, GEMSDOE28), so TP falls
   ~9 % while emitted mass falls 64 % → DTI 0.1922→0.2600 with the *same* geology.
2. **Catalogue-flank shadow.** The organizer masks known faults; the 1-px rasterized trace is
   offset 100–400 m from the true scarp, so scarp detectors fire on the 1–2 px flank of
   *known* faults. Those dots can only win if an unmapped parallel splay sits exactly there —
   measured credit/FP ≈ 0.004 vs the α·S ≈ 0.052 break-even at S=0.26 (GEMSDOE28). They are
   near-pure FP tax. Deleting the ≤1 px ring (solo, −3,891 dots) and then the ≤2 px ring
   (B2, −2,545 more) removes tax, not signal → 0.2600→0.2708→0.2778.
3. **Nothing else.** B2 contains no new geological detector. The 0.2778 → 0.44 gap to #1
   therefore cannot be closed by more pruning of the same dots (B3 already declines); it
   requires a better *ranking surface* (more true hidden-fault crest per dot), which five
   consecutive catalogue-blind attempts in the programme failed to produce (GEMSDOE28
   standing finding). Any honest new lane must be judged against that base rate.

Corollary for evaluation: a catalogue-hidden holdout that prunes with the *full* catalogue
(incl. withheld segments) mechanically zeroes the B-family (champion “catalogue_hidden_mean
0.0046” in its own audit) and cannot rank it. Only visible-only pruning (shared evaluator
`GEMSDOE32-HOLDOUT-v3-visible-only`) + the off-catalogue SGMC instrument are admissible here.

## Untried hypotheses (ranked before implementation)

| Rank | ID | Layers | Signature | Why a *missing* fault | Differs from prior art | Mimic (non-fault) | Cost |
|---|---|---|---|---|---|---|---|
| 1 | K3-H3 scarp-pair | 3DEP LiDAR u8 bands **3 step_max, 4 lapneg, 5 lappos, 6 downface, 10 coh100** (raster-description order) | crest–base dipole: lapneg crest within ≤2 px of lappos base, step_max & coh100 high | sub-grid scarplets of faults below map scale; dipole = true scarp profile | **every registry composite read bands 1,2,5 (ex_max, ex_mean, lappos) while claiming ex/step/downface (IR-K3-01)**; no dipole pairing anywhere | Lahontan paleo-shorelines, terrace risers, road cuts, landslide heads | ~1 min CPU |
| 2 | K3-H1 worm persistence | rtp(2), tmi(14), TMI_up150 (ext 4), iso_grav_anom(13), tmi_hg(3), iso_grav_hg(18) | multi-scale (σ=1,2,4) HG-ridge persistence × strength | buried basement offset: edge survives upward-continuation proxy; surficial noise does not | prior “worm” rasters were filters/re-ranks of D28 dots or single-scale HG; standalone persistence surface is new here | lithologic contacts, dike margins | ~2 min CPU |
| 3 | K3-H2 upflow boost | GDR well/spring CSV (temp, quartz/chalcedony/cation geothermometers; **excluding label-derived `dist_known_fault_px`**) + paleo sinter/tufa CSV from local GDR zip | temperature-weighted point raster → Gaussian density + collinearity vote | permeable (incl. blind) faults channel upflow; paleo deposits mark now-blind conduits | H33-1 used thermal points only as +900 dots on the champion base; never a standalone/boost surface; 2 m/paleo listed “missing” in GEMSDOE32 but zips verified present in GEMSDOE24 | lateral outflow, road/valley sampling bias | ~1 min CPU (sparse → boost only, cannot fill 37 k budget) |
| 4 | K3-H5 greedy emission | winning surface from Exp 1 | greedy maximum-coverage, kernel-novelty discount, stop at marginal credit ≈α·Ŝ | n/a (decision layer) | fixed 2.8 px Poisson is surface-blind; H37-1 coverprob was falsified far-field on H19-5 — retest on new surface with SGMC far-field gate | core-cluster overpacking | ~2 min CPU |
| 5 | K3-H4 strain ridges | geod_2ndinv(4), geod_shearrate(7), geod_dilaterate(8) | Hessian line response on 2nd invariant | active blind faults localise interseismic strain | used only as ML scalars before | block-rotation/GPS-interpolation gradients; km-scale smoothness vs 300 m kernel | ~30 s CPU, screen only |

External data check (done before proposing): GDR 1391 resources are free (CC BY 4.0,
https://gdr.openei.org/submissions/1391); the exact well/spring CSV + paleo zip bytes are
already hash-verified in `.cache/gems_data/external/` (see restore receipt) → obtainable with
no new download. USGS ComCat seismicity (H33-E in GEMSDOE32) is *not* reachable from this
sandbox and is therefore **not** proposed as viable in this session.

## Experiments (3 maximum)

* **Exp 1 — screen.** Build S(H3), S(H1), S(H4), S(H2-boost). Per-surface: canary AUC alone
  (pooled withheld truth vs active negatives); HOLDOUT-DTI visible-only (B=2, pooled, CI) at
  budgets 20,000 and 37,654 under template D2.8 emission; SGMC-cal HOLDOUT-DTI + CI; Spearman
  vs champion-dot kernel density (proxy, labelled) and 3-px dot overlap vs champion.
  Controls on identical evaluator: champion H33-2-B2, dotted D2.8, H19-5 parent (+ lineage
  nesting re-verification). Any surface with canary AUC > 0.90 is stopped as leakage-suspect.
* **Exp 2 — fusion + emission.** Rank-fusion of the top-2 Exp-1 surfaces with |Spearman| < 0.90
  to each other, × (1 + upflow boost). Arms: D2.8 control vs K3-H5 greedy, budgets 20,000 /
  37,654. Same instruments + uniqueness pre-check vs the 9 focus bests.
* **Exp 3 — final.** Single best Exp-2 configuration → paired `-zeros`/`-nan` GeoTIFFs via the
  shared writer, strict validator, full uniqueness audit, run card, site rebuild.

## Promotion gates (all required for verdict `promote`)

G1 pooled visible-only HOLDOUT-DTI > champion control on the same evaluator (point estimate
   and paired direction reported; CI overlap disclosed).
G2 SGMC prevalence-calibrated HOLDOUT-DTI ≥ 0.9 × champion control.
G3 genuine uniqueness: vs every focus-9 best *detector* raster, 3-px dot overlap ≤ 70 % and
   surface-proxy |Spearman| ≤ 0.90. Literal lattice overlap reported separately (IR-K3-02).
G4 validator: single band float32, EPSG:32611, 3730×3292, transform exact, footprint all
   finite in [0,1], 0 on-catalogue dots, `-zeros` file fully finite on the whole grid.
G5 canary: every input feature/surface AUC ≤ 0.90.

Fail any gate → verdict `negative`, site banner **DO NOT SUBMIT**, file remains a research
download. No fourth experiment; no slot recommendation from this repo (selector is separate).
