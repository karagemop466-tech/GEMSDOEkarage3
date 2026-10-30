# Review 2026-10-30 — executive summary (read first)

**Core values:** Maximize P(Win). Own the outcome.

## 1. Can I download and submit a file? — NO

**No file in this repository is cleared for upload.** Every candidate fails the project's literal uniqueness rule (`AGENTS.md`), and no file has an organizer receipt. No new TIFF was generated this session, because a new dot file cannot pass that rule (section 4). No method lane was chosen, because `AGENTS.md` forbids choosing one without an explicit user assignment, and none was given. No slot, upload, commit to a submission, or promotion was made.

## 2. Focus-site summary (nine sites)

Score labels: **USER-REPORTED** = the number in the request, not an organizer receipt. **Estimate** = not available. No local proxy tracks the leaderboard (section 5). **Unique?** uses the literal 3-px rule: "NO" means at least one other focus file has more than 70% of its dots within 3 px (the rule's threshold). Every focus file has at least 97.6% of its dots within 3 px of at least one other focus file.

| Site | File (link pinned to repo commit) · sha256 | Score (label) | Unique? | Exact relation (verified) |
|---|---|---|---|---|
| GEMSDOE24 | [gems24-h25-1-dotted-h19-5-d1-5-…-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) · `68d0e2e4` | 0.2477 USER-REPORTED · estimate: n/a | NO (100% within 3 px of 25, 30) | Dots ⊂ GEMSDOE27 |
| GEMSDOE25 | [gems25-dotted-h19-5-d2-8-…-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/04333cc3fbf7486c56e0324fd07aee684be614dc/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) · `91eae1ca` | 0.2600 USER-REPORTED · estimate: n/a | NO (same dot set as 30) | Same set as GEMSDOE30 |
| GEMSDOE27 | [gems27-topo-gap-closure-t-v2-on-d1-5-…-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/b8dd298e10884afffa05436673ac73aeaf850b8c/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) · `33003374` | 0.2449 USER-REPORTED · estimate: n/a | NO (98.0% within 3 px of 24) | Contains GEMSDOE24 |
| GEMSDOE28 | [gems28-h36-1-rung30-blind-r1-…-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/ec1d501fd12c8dee9dc062726003639dec9382ff/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) · `5556aa14` | 0.2710 USER-REPORTED · estimate: n/a | NO (100% within 3 px of 24, 25, 27) | — |
| GEMSDOE30 | [gemsdoe30-d28-poisson300m-offcat-44090-…-91eae1ca.tif](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/3d5bec2af5f29291617f97c9e2dfe443be6f55c3/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) · `8cf893ea` | 0.2600 USER-REPORTED · estimate: n/a | NO (same dot set as 25) | Same set as GEMSDOE25 (file name suffix `91eae1ca` is GEMSDOE25's hash prefix; bytes differ) |
| GEMSDOE31 | [gemsdoe31-h27-4-solo-d28-…-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/cf13282fcd86290f1539f0a86446c8ba7205a79b/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) · `07b6db44` | 0.2708 USER-REPORTED · estimate: n/a | NO (100% within 3 px of 25, 30) | Contained in GEMSDOE25, 30 |
| **GEMSDOE32** | [gemsdoe32-h33-h33-2-b2-…-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) · `c55bafc4` | **0.2778** USER-REPORTED · estimate: n/a | NO (100% within 3 px of 24, 25, 27, 30, 31, 33, 36) | Contained in GEMSDOE25, 30, 31, **36** (all 37,654 dots are in 36) |
| GEMSDOE33 | [GEMSDOE33-h33d-analog-tip-stepover-r30-…-cb490425926e.tif](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/f52533110fe62cd03e77f1228e9e5ecac412c463/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) · `87f857d5` | 0.2632 USER-REPORTED · estimate: n/a | NO (99.7% within 3 px of 24, 25, 27, 30) | — |
| GEMSDOE36 | [gemsdoe36-anderson-geothermal-pinn-38854-…-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/c9ad59ec6f969ed931d089a03044c1567a633e84/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) · `e1589102` | 0.2750 USER-REPORTED · estimate: n/a | NO (97.3–97.6% within 3 px of each other focus file) | Contains all of GEMSDOE32 |

Sources: file paths, repo refs and sha256 values are from [data/focus_registry.json](../data/focus_registry.json), SHA-256 verified on 2026-10-30. Pairwise and structure numbers: [evidence/focus9-structure-20261030.json](../evidence/focus9-structure-20261030.json) (script [scripts/focus9_structure.py](../scripts/focus9_structure.py)). Subset relations are exact pixel-set subsets computed on the same receipt.

**Leaderboard (live fetch 2026-10-30; not a receipt):** #1 xiaofanhu **0.4544**; #2 cfld__ 0.3916; #3 Batik Shirt Brothers 0.3911; #46 tran.thuy.trang 0.3231; #47 like60986 0.3217; #48 kpomazi 0.3195; #49 drjy 0.3180; #50 twang 0.3169. The figure 0.4413 is not in the top 50. Source: [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). The earlier README recorded 0.3195 as rank #47; the live page shows #48.

## 2a. Gates run this session (local checks, not organizer receipts)

| Gate | File | Result | Meaning |
|---|---|---|---|
| Template grid (core group) | `training_features`, `labels`, `existing_faults`, `sample_submission` | All four: EPSG:32611, shape 3730×3292, transform (100, 0, 243350, 0, −100, 4508550) | MATCH |
| Format (`scripts/check_format.py`) | GEMSDOE25 `…-nan.tif` | `format_gate_pass: true`; 7,111,787 outside-footprint NaN; 0 inside non-finite; 0 out of range | Format only; still **not OK to submit** (uniqueness fails) |
| Format | GEMSDOE32 `…-zeros.tif` (scored 0.2778 per user) | `format_gate_pass: false`: outside-footprint pixels are 0 (not null or NaN); inside values binary and in range | **Does not meet the official null/NaN rule** (irregularity I-12) |
| Holdout (H-GEO quarantined `-zeros`) | see section 5 | HOLDOUT-DTI 0.3047 [0.2881, 0.3189] | Not a leaderboard estimate; `promotion_eligible: false` |
| Literal uniqueness | all nine focus files | every file fails | **Blocks submission** |

Per-file answer to "OK to submit?": **NO for all nine**, for the uniqueness reason; GEMSDOE32 additionally fails the official format rule as published. Format passes do not imply submission eligibility.

## 3. Why GEMSDOE32 scored 0.2778 — what the evidence shows and what it does not

**Official facts used.** (a) Organizer staff state on the forum that pixels on known USGS/INGENIOUS faults are masked and excluded from evaluation, and that re-evaluation masks the existing faults ([forum topic 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)). The problem page does not state this. (b) The metric is a distance-weighted Tversky index with α = 0.2 (false positives) and β = 0.8 (false negatives) and a triangular kernel of radius 300 m = 3 px ([problem page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)). The repo's implementation of this (`src/gems32/metric.py`) matches the organizer's formula; its module docstring gives DTI = TP_w / (0.2·(TP_w + FP_w) + 0.8·|G|).

**Verified algebra.** I checked numerically that `dti_exact` equals TP/(0.2(TP+FP)+0.8|G|) to 1.6e-14 across 40 random fields.

**Measured structure** (receipt `evidence/focus9-structure-20261030.json`; catalogue = `labels.tif`; "on-catalogue (d=0)" dots are masked by the organizer rule):

| Site | Positive pixels | On trace d=0 | 0–2 px ring | 2–3 px | >3 px |
|---|---|---|---|---|---|
| GEMSDOE24 | 60,069 | 0 | 8,769 | 3,169 | 48,131 |
| GEMSDOE25 | 44,090 | 0 | 6,436 | 2,171 | 35,483 |
| GEMSDOE27 | 61,328 | 0 | 8,875 | 3,312 | 49,141 |
| GEMSDOE28 | 37,660 | 0 | 2,353 | 2,024 | 33,283 |
| GEMSDOE30 | 44,090 | 0 | 6,436 | 2,171 | 35,483 |
| GEMSDOE31 | 40,199 | 0 | 2,545 | 2,171 | 35,483 |
| **GEMSDOE32** | **37,654** | 0 | **0** | 2,171 | 35,483 |
| GEMSDOE33 | 41,865 | 0 | 3,894 | 2,130 | 35,841 |
| GEMSDOE36 | 38,854 | 0 | **0** | 2,281 | 36,573 |

**What this supports.** GEMSDOE32 is GEMSDOE25 with the 6,436-dot 0–2 px ring removed. The removal is a three-step ladder whose pixel subsets and counts are verified: 25 → 31 removes 3,891 dots (all in the ring, 6,436 − 2,545), and 31 → 32 removes 2,545 dots (exactly 31's ring). The user-reported scores along the ladder are 0.2600 → 0.2708 → 0.2778. GEMSDOE32 and GEMSDOE36 both have zero dots within 2 px of a catalogue trace. Across the nine files, the ring count and the user-reported score have Spearman ρ = 0.9958 (n = 9, one file family, exploratory, not an estimate). The receipt marks that label explicitly. The ladder has three points, so it cannot establish a trend.

**What it does not show.** GEMSDOE32 (0.2778) and GEMSDOE36 (0.2750) tie on the ring count, so the ring alone does not explain the 0.0028 gap between them. The receipt also has no hidden-fault positions, so the sign of each ring dot's contribution cannot be measured locally.

**Mechanism, stated as a hypothesis.** Removing a dot changes DTI according to its own TP credit `t` and FP mass `f` (its FP contribution). The exact condition for a removal to help is `t·D < α·TP·(t+f)`, with D = α(TP+FP) + β|G|. The simpler bar `t < α·DTI` is exact only when `t + f = 1` (the dot's exclusive credit is to its nearest truth pixel). In general `t + f ≤ 1`, so the simple bar overstates the gain. The repo's test `tests/test_session7_review.py::test_break_even_rule_matches_shared_metric` checks the simple bar on random removals with zero violations. A separate check over 1,200 random removals found zero disagreements between the exact and simple rules. That is evidence on those random fields, not a proof for all fields. At DTI 0.2778 the simple bar is t < 0.0556.

**Conclusion.** The most consistent explanation is that GEMSDOE32 removed low-credit dots near the catalogue traces (the 0–2 px ring), where FP mass was not offset by hidden faults. Whether those dots were net negative depends on hidden-fault positions, which are not available here. This explanation is a hypothesis, and it is not verified against any leaderboard receipt.

## 4. The uniqueness conflict (the real blocker)

- `AGENTS.md`: a candidate is a duplicate if rank correlation with any registered raster exceeds 0.90, or if more than 70% of candidate-support pixels lie within 3 px of that raster; checked before placement and on final dots. "No exemptions."
- Against the lattice witness (`r13-lattice-s5`, 206,895 dots): 5,160,724 of 5,167,373 footprint cells (**99.87%**) are within 3 px of a witness dot. 6,649 cells are uncovered, 6,580 of them in the 3-cell boundary ring. A compliant footprint-restricted file must put at least 30% of its dots in uncovered cells. Receipt: [evidence/lattice-feasibility-20261029.json](../evidence/lattice-feasibility-20261029.json). Its verdict: no non-degenerate in-footprint submission can satisfy the literal rule.
- Among the nine focus files, each file has at least one other with ≥ 97.6% of its dots within 3 px (matrix in the receipt).
- The organizer metric accepts per-pixel probabilities, and the reference solution outputs a continuous raster (its notebook says "it may be advantageous to threshold this map", [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)). The repo's `require_binary_mask` (`src/gems32/submission.py`) enforces binary masks, so a continuous candidate has no evaluator here.

**Result:** under the literal rule as written, no non-degenerate dot file can pass, and the best-scoring focus family is excluded. This is an owner decision (section 7).

## 5. Verified numbers (labelled)

| Number | Label | Value | Source |
|---|---|---|---|
| H-GEO-CONDUIT quarantined `-zeros` file, pooled DTI | **HOLDOUT-DTI**, evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives, 140 clusters, 95% cluster-bootstrap CI | **0.3047** [0.2881, 0.3189]; fold mean 0.3035; `promotion_eligible: false` | [evidence/holdout-reproduction-20261030-geoconduit-zeros.json](../evidence/holdout-reproduction-20261030-geoconduit-zeros.json) (file [docs/quarantine/geoconduit-hybrid/…-0a6974d8-zeros.tif](../docs/quarantine/geoconduit-hybrid/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif)) |
| Same file, off-catalogue SGMC calibrated | **HOLDOUT-DTI**, evaluator `GEMSDOE32-SGMC-CAL-v3.0`, 62,703 withheld positives | 0.0026 [0.0020, 0.0035] | same receipt |
| Earlier H-GEO card value | not reproduced | 0.4239 [0.4053, 0.4427] | reproduced only under an uncommitted gated variant |
| Historical focus-site scores | USER-REPORTED / UNVERIFIED | 0.2449–0.2778 | request text |
| Organizer receipt for any file | none | — | — |

**Holdout caveat.** The holdout withholds *catalogue* faults. The leaderboard uses *non-catalogue* faults. Calibration against the reported historical scores is negative for the catalogue proxy (ρ = −0.55, 18 rasters) and near zero for the off-catalogue proxy (ρ = 0.08). No local proxy estimates a leaderboard score.

## 6. Hypotheses (3–5), ranked — untested, no score claimed

Band numbers are from `training_features.tif` (19 bands; band descriptions read with rasterio this session).

| Rank | Hypothesis | Layers (band no.) | Target signature | Existing code that uses these layers | Cost |
|---|---|---|---|---|---|
| 1 | **Break-even credit gating.** Keep a dot only if its exact removal/addition condition (section 3) is favourable, not a distance-only cut. | labels (catalogue), plus whichever bands drive the candidate | Dots whose expected credit is below α·DTI | Metric in `src/gems32/metric.py` (`marginal_inclusion_threshold` is documented as idealized, not general) | Low; no local validator yet |
| 2 | **Edge-coincident corridors.** Tilt-angle (6) ridges that coincide with isostatic-gravity horizontal-gradient (18) maxima and sit >3 px from catalogue traces. | 6, 18 (and 3, tmi horizontal gradient) | Co-located magnetic and gravity edges with no mapped trace | `src/gems32/h36_tdr_pds.py` uses tilt and gravity gradients (see I-3 for a band-6 label conflict) | Low–medium |
| 3 | **Strain without topographic expression.** High geodetic second invariant (4) where the detrended-elevation slope (19) is low. | 4, 19 | Strain without a visible scarp | Largely covered by the K3C Kostrov strain-deficit prior (`src/karage3/strain_deficit.py`); overlaps existing work | Medium |
| 4 | **Seismicity lineation.** Alignments in earthquake density (16) and distance-to-earthquake (10). | 10, 16 | Linear seismicity alignments | `src/gems32/pfonly.py` already uses the 100 km earthquake bands 10 and 16 | Low; likely small (100 km scale vs 300 m kernel) |

Not carried forward: the earlier "top-of-crustal magnetic source-depth" hypothesis. `training_features.tif` has no band with that name. Band 15 is "depth to basement surface", so that hypothesis cannot run on this file as named.

Validation order for any candidate (per `AGENTS.md`): leakage check, then the shared holdout evaluator, then the literal uniqueness check on the continuous surface and on the final dots. No slot is used before all three pass.

## 7. Owner decisions required

1. **Uniqueness rule.** (a) Keep the literal rule, and accept that no dot file can be submitted; (b) amend the rule for discrete detector output, or allow continuous surfaces and compare by rank correlation (the organizer metric and reference solution use probabilities); (c) state which reading governs, footprint-restricted or all dots.
2. **Method lane.** `AGENTS.md` requires an explicit lane assignment before any experiment. None has been given.
3. **Subset relations.** Confirm whether an exact pixel-subset relation (e.g., GEMSDOE32 ⊂ GEMSDOE36) counts as a duplicate. The rule as written says yes.

## 8. Irregularities flagged for review

1. **README portal advice contradicts the official rule.** The README tells users to use the `-zeros.tif` (or `-allfinite.tif`) version to avoid "Predicted values must be in range [0, 1]". The official page says outside-bounds values must be **null or NaN**. The format audit shows `format_gate_pass: False` for `-zeros` files and `True` for `-nan` files (20 rasters, [evidence/saved-tiffs-literal-20261028.json](../evidence/saved-tiffs-literal-20261028.json)). The cause of the portal error is unknown; the exact file hash and the full portal message are needed.
2. **Saved-byte audit covered 18 of 20 TIFFs before this session.** The two `karage3-consensus-hgrad-k37654` files were missing, so the test suite had 6 failures at first. After the audit was regenerated with `scripts/audit_saved_tiffs.py --fetch`, all 20 TIFFs are covered and the suite passes (225 passed, 1 skipped, 0 failed).
3. **Band 6 has two labels in the repo.** The file description says "tc – Tilt angle or total curvature". `src/gems32/h36_tdr_pds.py` says "Band 6 (`tc`) is radiometric Total Count (Spearman +0.9994 with GeoDAWN TC)". Only one can be right. Any hypothesis using band 6 depends on this.
4. **Band names do not match the earlier hypothesis list.** Band 15 is "depth to basement surface". No band is named top-of-crustal magnetic source depth or conductive-base depth. The official feature documentation was not re-checked this session.
5. **README line 115 is out of date.** It labels the masking mechanism "UNVERIFIED; the official text does not mention masking". The forum (topic 11516) does state masking, so the label should change. Its statement that masked dots "still consume budget" is not supported by the forum wording, which says masked pixels add neither TP nor FP. Its attribution of the 0.2600 → 0.2708 → 0.2778 steps to near-zero-TP-loss removals is consistent with the ladder in section 3, but it is not verified by any receipt with per-step scores.
6. **Leaderboard rank.** 0.3195 is rank #48 on the live page, not #47 as the earlier README records.
7. **GEMSDOE30 file name vs hash.** The name ends in `91eae1ca`, which is GEMSDOE25's hash prefix; its own sha256 is `8cf893ea`. Dot sets are identical.
8. **`labels.tif` and `existing_faults.tif` are byte-identical** (sha256 `7ba308cc…`). Expected for the owner mirror; noted so they are not treated as independent sources.
9. **GEMSDOE32 vs GEMSDOE36.** Both have a zero 0–2 px ring, yet their scores differ by 0.0028 (0.2778 vs 0.2750). The ring alone does not explain the ranking.
10. **Unpublished lattice-gap candidate.** `karage3-lgap-scarpstep-19k` passed the lattice and focus checks but fails the full inventory (106 of 1,977 rasters over 70%). Only its card is published; no TIFF is published for it.
11. **H-GEO card 0.4239 not reproduced.** The committed CLI gives 0.3047 on the same file; 0.4239 required an uncommitted gated variant.
12. **GEMSDOE32 as published fails the official format rule.** Its outside-footprint pixels are 0, not null or NaN. The user reports a score (0.2778) for this file, so the portal evidently accepted it, which conflicts with the organizer page. Either the portal does not enforce the rule, or the score came from a different file. The file hash and the portal receipt would settle this.

13. **Historical `ok_to_submit: true` in `docs/k3c/run-card.json` (line ~32320).** It sits inside `historical_promotion_gate` with `selector_required: true` and empty `reasons`. It is a record of an earlier promotion step, not a current clearance; the top-level `ok_to_submit` is `false`. Readers can misread it, so it should be relabelled in the historical record.

## 9. What changed in the repository this session

- `scripts/focus9_structure.py` and `evidence/focus9-structure-20261030.json` (structure audit; exploratory, not a score). The 3-px pairwise matrix was added and the run completed.
- `evidence/holdout-reproduction-20261030-geoconduit-zeros.json` (HOLDOUT-DTI reproduction).
- `tests/test_session7_review.py` (receipt invariants, break-even check, holdout labels). Passes: 4 of 4.
- `docs/review-2026-10-30.md` (this document) and a short pointer in `README.md`.
- Restored data in `.cache/` (ignored by git, not committed): core and external groups, and the nine focus files.

**Reproduce:** `python scripts/restore_data.py --group core`; `--group external`; `python scripts/fetch_focus9_files.py`; `python scripts/focus9_structure.py`; `python scripts/evaluate_holdout.py <file> --out <json>`; `python scripts/audit_saved_tiffs.py --fetch`; `python -m pytest -q`. Use `PYTHONPATH=.`.

## 10. Remaining work and limitations

1. Owner decisions in section 7.
2. Organizer-authenticated data (the DrivenData download requires a login) to confirm the band list and the file bytes.
3. The portal error needs the exact file hash and full portal message.
4. No organizer receipt exists for any file, so no score is confirmed.
5. The complete registry is not restored in this checkout (`literal_registry_complete: false`), so the full-inventory check cannot be closed here.
6. The competition rules PDF ([docs.nlr.gov 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf)) and the GDR #1391 page ([gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391)) are listed in the README as sources, and were not re-fetched in this session.
7. The shared evaluator is binary-only. A continuous candidate needs evaluator changes, which must go through the shared template, not a private fork.
8. The hypothesis slate is untested. None of it is scored.
