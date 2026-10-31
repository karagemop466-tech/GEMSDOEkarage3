# NOT CLEARED — H1 co-location (NMS ridges)

Verdict: **negative**. OK to download and submit: **NO**.

- File (NaN outside; format gate pass = True): `gemsdoe32-colocation-h1-20261031T000000Z-48e06738-nan.tif`
- SHA-256: `4cad920c36b7eb5afe2458c287497d8f3c6b61e5c9518bfb110feccfdd7e3f47`
- Dots: 12,177 (target 12,177)
- HOLDOUT-DTI (catalogue withheld, GEMSDOE32-HIDE-RECOVER-v3.0, 22,232 withheld positives): 0.0365 [0.0286, 0.0449]
- SGMC-calibrated HOLDOUT-DTI (GEMSDOE32-SGMC-CAL-v3.0): 0.0252 [0.0216, 0.0292]
- Budget-matched random control: HOLDOUT-DTI 0.0149–0.0163, SGMC-cal 0.0215–0.0226 (3 seeds)
- Nine-site uniqueness: max within-3 px 0.3964 vs GEMSDOE27, max |Spearman| 0.0111 (passes the 70% / 0.90 rule vs the nine)
- 13GEMSDOE lattice (`b4570b40…`): within-3 px **0.9993** → fails the literal full-registry 70% rule
- Did it beat the nine-site holdout best? HOLDOUT: False; SGMC-cal: False

Why it is not submitted: it does not beat the holdout best, and it fails the 13GEMSDOE lattice literal rule. Retained as research evidence only. Receipts: `evidence/run-card-20261031.json`, `evidence/session-20261031/`.
