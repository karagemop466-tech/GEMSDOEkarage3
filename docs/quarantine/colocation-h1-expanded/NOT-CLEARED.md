# NOT CLEARED — H1-expanded (no NMS, full budget)

Verdict: **negative**. OK to download and submit: **NO**.

- File (NaN outside; format gate pass = True): `gemsdoe32-colocation-h1-expanded-20261031T020000Z-57271256-nan.tif`
- SHA-256: `dc0aaa7fb6faf04f668079270d8a011b52f5811bffb74bca170ab49c25ec133d`
- Dots: 37,654 (target 37,654)
- HOLDOUT-DTI (catalogue withheld, GEMSDOE32-HIDE-RECOVER-v3.0, 22,232 withheld positives): 0.0047 [0.0028, 0.0071]
- SGMC-calibrated HOLDOUT-DTI (GEMSDOE32-SGMC-CAL-v3.0): 0.0167 [0.0112, 0.0223]
- Budget-matched random control: HOLDOUT-DTI 0.0304–0.0330, SGMC-cal 0.0470–0.0488 (2 seeds)
- Nine-site uniqueness: max within-3 px 0.3054 vs GEMSDOE27, max |Spearman| 0.0047 (passes the 70% / 0.90 rule vs the nine)
- 13GEMSDOE lattice (`b4570b40…`): within-3 px **0.9995** → fails the literal full-registry 70% rule
- Did it beat the nine-site holdout best? HOLDOUT: False; SGMC-cal: False

Why it is not submitted: it does not beat the holdout best, and it fails the 13GEMSDOE lattice literal rule. Retained as research evidence only. Receipts: `evidence/run-card-20261031.json`, `evidence/session-20261031/`.
