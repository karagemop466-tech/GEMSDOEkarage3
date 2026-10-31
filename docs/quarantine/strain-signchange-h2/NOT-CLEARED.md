# NOT CLEARED — H2 dilatation sign-change x shear

Verdict: **negative**. OK to download and submit: **NO**.

- File (NaN outside; format gate pass = True): `gemsdoe32-strain-signchange-h2-20261031T010000Z-8e5a2122-nan.tif`
- SHA-256: `12497b0113d5873b7aba6f7707e46e0914e22f64729d5d4ee29a997e03fe1721`
- Dots: 5,660 (target 5,660)
- HOLDOUT-DTI (catalogue withheld, GEMSDOE32-HIDE-RECOVER-v3.0, 22,232 withheld positives): 0.0033 [0.0015, 0.0055]
- SGMC-calibrated HOLDOUT-DTI (GEMSDOE32-SGMC-CAL-v3.0): 0.0016 [0.0004, 0.0033]
- Budget-matched random control: HOLDOUT-DTI 0.0069–0.0090, SGMC-cal 0.0114–0.0119 (3 seeds)
- Nine-site uniqueness: max within-3 px 0.2256 vs GEMSDOE27, max |Spearman| 0.0020 (passes the 70% / 0.90 rule vs the nine)
- 13GEMSDOE lattice (`b4570b40…`): within-3 px **0.9972** → fails the literal full-registry 70% rule
- Did it beat the nine-site holdout best? HOLDOUT: False; SGMC-cal: False

Why it is not submitted: it does not beat the holdout best, and it fails the 13GEMSDOE lattice literal rule. Retained as research evidence only. Receipts: `evidence/run-card-20261031.json`, `evidence/session-20261031/`.
