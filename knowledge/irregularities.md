# Irregularities register (karage3)

Each entry: what was verified, where (file/line or command), impact, disposition.

## IR-K3-01 — Shared LiDAR composite reads the wrong bands (template bug)
Verified 2026-10-27 by opening the hash-pinned raster with rasterio:
`lidar_scarp_features_u8.tif` band descriptions =
1 `ex_max`, 2 `ex_mean`, 3 `step_max`, 4 `lapneg_max`, 5 `lappos_max`, 6 `downface_max`,
7 `upface_max`, 8 `cross_max`, 9 `relief`, 10 `coh100`, 11 `strike`, 12 `valid`.
GEMSDOE32 `src/gems32/h33.py:lidar_scarp_composite` (and copies in `hypotheses.py`,
`h35_new.py`) docstring claims `0.45*ex_max + 0.35*step_max + 0.20*downface_max` but reads
bands 1, 2, 5 = `ex_max, ex_mean, lappos_max`. Impact: every registry surface using that
composite is mislabelled; its true inputs are ex_mean/lappos, which may still correlate with
scarps, so scores are not invalidated, but mechanism claims are. Disposition: karage3 reads
bands by **description name**, never by assumed index; bug reported here per protocol
(“fix once in the template and report”) — the fix lives in `src/karage3/surfaces_k3.py`;
sister repos were not edited from this session.

## IR-K3-02 — Literal ≤70 % / 3 px uniqueness vs “any registry raster” is impossible at normal budgets
The registry contains `20261001_r13-lattice-s5` (owner-reported 0.0904), a 5-px calibration
lattice. Sister-repo measurement (GEMSDOE24 README, 2026-10-27): only 6,649 in-footprint
pixels lie outside the lattice's 3-px union, so *every* 37,654-dot set overlaps it ≥82.34 %
and every 44,090-dot set ≥84.92 %; ≥22,164 dots already force >70 % by pigeonhole.
Disposition: report (a) genuine-detector gate (focus-9 bests + champion lineage) as the lane
test, (b) literal lattice overlap as a disclosed geometric constant. Deliberately placing
dots in the 6,649 uncovered pixels to “pass” would be gaming and is prohibited by the brief's
intent; it is not done here. To be re-measured in Exp 3 if a lattice raster is available.

## IR-K3-03 — Leaderboard #1 stated as 0.4413, 0.4437 and 0.3195
Owner prompt (new copies): 0.4413. GEMSDOE28 fetched the public board 2026-10-26: #1 = 0.4437.
Older brief copies embedded in the same prompt: 0.3195. These are time-separated snapshots;
0.3195 is stale. The sandbox cannot fetch drivendata.org. Disposition: cite as
“≈0.44 (owner 0.4413; sister fetch 0.4437 on 2026-10-26)” and require a fresh manual check
before any slot decision.

## IR-K3-04 — All programme “live scores” lack organizer receipts
No focus repo stores a DrivenData receipt linking file hash → score; GEMSDOE24's current
review explicitly demotes 0.2778 to OWNER-REPORTED / UNVERIFIED. Disposition: every historical
score in karage3 outputs is labelled OWNER-REPORTED with source URL. Nothing is labelled
ORGANIZER-CONFIRMED.

## IR-K3-05 — Official band-6 (`tc`) semantics ambiguous in the mirror
Raster description: “tc - Tilt angle or total curvature - magnetic field derivative…”.
Sister code variously treats `tc` as radiometric total count. karage3 does not use band 6 in
any K3 surface, so the ambiguity cannot affect results; flagged for the template.

## IR-K3-06 — `sample_submission.tif` is not “total fault absence”
Per GEMSDOE32 manifest provenance (to be re-counted in prepare step): its 60,988 pixels equal
to 1 sit on labelled faults. It is used here only as grid/footprint template, never as a
prediction prior.

## IR-K3-07 — This repo started empty
At session start `GEMSDOEkarage3@85359a3` contained only `README.md` (“# GEMSDOEkarage3”) —
no code, data, evaluator, or site. All shared tools were vendored verbatim from
`buffedlizard55-lab/GEMSDOE32@73485f27` (`src/karage3/{metric,holdout,submission}.py`,
`scripts/restore_data.py`) with only package-name/prefix adaptations, recorded in
`src/karage3/PROVENANCE.md`. Prior-session instructions in the prompt that presuppose existing
repo machinery therefore apply to the vendored copies.

## IR-K3-09 — The champion *mask* is mechanically censored on any catalogue holdout (measured Exp 1)
H33-2-B2 was constructed with the full catalogue (all dots >2 px from every catalogue pixel,
including segments a holdout would withhold). Withheld truth ⊂ catalogue, kernel radius 3 px,
so almost no champion dot can earn credit: measured pooled HOLDOUT-DTI 0.00452 [0.00394,
0.00520] (`GEMSDOE32-HOLDOUT-v3-visible-only`, 22,232 withheld) — an artefact of construction,
not a quality estimate (its own sister audit prints the same 0.0046-class number). The honest
fold-local estimate of the champion *rule* is the pre-prune D2.8 mask gated per-cell by
visible-fault distance (B=2): **0.09920 [0.08149, 0.12041]**, identical to the “champion
0.099202” quoted in sister reports. Gate G1 therefore compares against the champion-rule
control (D2.8 + visible-B2), and the literal champion-mask number is reported only as a
censoring diagnostic. K3 candidates use no catalogue in construction, so their gated
evaluations are uncensored and comparable to the rule control.

## IR-K3-08 — `labels.tif` ≡ `existing_faults.tif` byte-identical
Both SHA-256 `7ba308cc…` in the pinned manifest. Consistent with the competition design
(catalogue = label support to be masked), noted so no one treats them as independent sources.
