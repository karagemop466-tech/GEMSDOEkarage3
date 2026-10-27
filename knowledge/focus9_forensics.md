# Focus-9 forensics — measured in this repo, 2026-10-27

Sources: local clones pinned in `registry/focus9_registry.json` (repo HEADs recorded there);
measurements in `evidence/exp1_screen.json` (lineage, rings, controls),
`evidence/lineage_extra.json`, `evidence/extended_uniqueness.json`. All live scores are
**OWNER-REPORTED** (no organizer receipt exists in any clone; IR-K3-04). HOLDOUT-DTI values
below are ours, on `GEMSDOE32-HOLDOUT-v3-visible-only` (pooled, 22,232 withheld positives)
unless stated; SGMC-cal is `GEMSDOE32-SGMC-CAL-v3.0` (62,703 off-catalogue SGMC pixels,
prevalence-calibrated HOLDOUT-DTI).

## The nine “bests” are one family (exact dot-set algebra)

| Site | Best submission (owner catalogue) | Dots (measured) | OWNER-REPORTED | Measured relation |
|---|---|---:|---:|---|
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5 | 60,069 | 0.2477 | ⊂ H19-5 parent; denser (d=1.5) thinning phase |
| GEMSDOE25 | dotted-h19-5-d2-8 | 44,090 | 0.2600 | ⊂ parent; **≡ GEMSDOE30 best (symdiff 0)** |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5 | 61,328 | 0.2449 | = GEMSDOE24 best + 1,259 gap dots |
| GEMSDOE28 | h36-1-rung30-blind-r1 | 37,660 | 0.2710 | ⊂ parent; shares 26,248 dots with champion |
| GEMSDOE30 | d28-poisson300m-offcat-44090 | 44,090 | 0.2600 | **≡ GEMSDOE25 best (symdiff 0)** |
| GEMSDOE31 | h27-4-solo-d28 | 40,199 | 0.2708 | **≡ solo control (symdiff 0)**; champion ⊂ it |
| GEMSDOE32 | **h33-h33-2-b2 (champion)** | **37,654** | **0.2778** | = solo − 2,545 dots with d(catalogue) ≤ 2 px |
| GEMSDOE33 | h33d-analog-tip-stepover-r30 | 41,865 | 0.2632 | shares 31,614 dots (75.5 %) with champion |
| GEMSDOE36 | anderson-geothermal-pinn-38854 | 38,854 | 0.2750 | = champion + 1,200 dots (champion ⊂ it) |
| control | H19-5 parent ridge | 121,131 | 0.1922 | superset of 24/25/28/30/31/32 bests |

Catalogue-ring census (measured) explains the pruning ladder exactly: D2.8 has 3,891 dots at
d ≤ 1 px and 6,436 at d ≤ 2 px; solo removes the first ring (44,090→40,199), B2 removes the
rest of the second (40,199→37,654, −2,545); 35,483 D2.8 dots lie beyond 3 px (= the B3 count
in the sister validation). Champion still holds 2,171 dots in the (2, 3] px ring.

Controls on our uniform instrument: D2.8+visible-B2 (honest champion-*rule*) pooled
**0.09920 [0.08149, 0.12041]**; literal champion mask 0.00452 (construction-censored,
IR-K3-09 — do not quote as quality); H19-5 parent 0.07342 [0.06116, 0.08897]; PINN mask
0.00458 (same censoring). SGMC-cal: champion 0.06412 [0.0567, 0.0717], D2.8 0.06059,
parent 0.04407, PINN 0.06444.

## Why 0.2778, and can pruning go further? (answer to the owner's question)

Yes the mechanism is understood and now re-measured end-to-end; no, this family cannot reach
0.44 by more of the same. (1) *Dotting*: kernel-redundant ridge pixels pay FP tax without
marginal TP; 2.8 px crest thinning kept 90.6 % of live credit at 36 % of the mass
(0.1922→0.2600). (2) *Flank-shadow removal*: organizer masks catalogue traces; detectors fire
on the 100–200 m flank of known faults (trace vs scarp offset), earning ≈0.004 credit/FP
against the α·S≈0.052 break-even — deleting rings d≤1, then d≤2, removes tax
(0.2600→0.2708→0.2778). Fold-locally we re-measure the B2 rule itself as +0.0025 pooled over
B0 (0.09920 vs 0.09674). (3) B3 already declines on the sister live-mirror, so the
one-parameter family is at its optimum; the remaining gap to ≈0.44 is *surface recall of
truly blind faults*, which no emission trick creates.

## Per-site executive notes

* **GEMSDOE24** — best file is the d=1.5 sibling; useful as the density-control proving
  sparser wins at fixed surface. Current repo head correctly says SUBMIT: NO for its newer
  research files and owns the lattice-feasibility proof (IR-K3-02).
* **GEMSDOE25** — the d=2.8 emission is the family pivot. Its newer H75 lanes report small
  holdout wins over internal controls but literal-lattice failure; none is live-scored.
* **GEMSDOE27** — gap-closure adds 1,259 dots to d1.5 and *loses* live (0.2449 < 0.2477):
  additions on this surface pay more FP than TP at the margin. Newer hydro/piedmont files
  (0.2190/0.2250 owner-reported) stay below the family best.
* **GEMSDOE28** — hosts the lineage middle (solo) and rung30, the only focus best that is a
  *different selection* (still ⊂ parent). Its README forensic (five straight catalogue-blind
  failures) is the programme's most important negative result.
* **GEMSDOE30** — best file is byte-equivalent dots to GEMSDOE25's; the “Poisson 300 m”
  framing is the same 2.8 px rule. Also hosts rasterised GDR 2 m/paleo derivatives.
* **GEMSDOE31** — best ≡ solo. One extended-audit raster there
  (`gemsdoe31-csdu-stepover-…-nan.tif`) has non-finite values *inside* the footprint and
  would fail the DrivenData range validator — do not submit that file.
* **GEMSDOE32** — champion + the shared template (metric/holdout/writer vendored here).
  Also the source of IR-K3-01 (wrong-band LiDAR composite) affecting its H33/H35/H32
  surfaces' mechanism claims (scores unaffected; inputs mislabelled).
* **GEMSDOE33** — analog tip-stepover best is 75.5 % champion dots + additions; scores below
  champion (0.2632), consistent with marginal-addition economics.
* **GEMSDOE36** — “PINN” best = champion + 1,200 dots (0.2750 < 0.2778): the additions are
  net-negative live, the cleanest single proof that B2 sits at a local optimum.

## What would actually be needed to beat 0.2778

In order of expected value, given every measurement above: (i) a ranking surface with
independent blind-fault recall (new signal, e.g. raw seismicity catalogues at sub-km scale —
USGS ComCat/FDSN, free, but unreachable from this sandbox; or full-resolution InSAR/
gravity-gradient tensors), validated fold-locally, not another transform of the same 19
bands — five-plus such attempts now sit at pooled ≈0.03–0.06 vs the 0.0992 rule control,
including K3's 0.0522; (ii) fold-local *refill* after B-pruning at fixed budget from an
independent surface (only helps if (i) exists); (iii) budget/spacing micro-optimisation is
exhausted (d and B both at measured optima). K3's one positive signal — SGMC off-catalogue
0.0892 vs champion 0.0641 for the corrected scarp-pair fusion — says the corrected LiDAR
bands carry *some* blind-fault information the mislabelled composite missed; it is not, on
present instruments, enough to promote.
