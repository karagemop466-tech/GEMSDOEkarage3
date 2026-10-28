# Lane H-K3B-1 (`CSST-BGHF`) Research Monograph & 9-Site Forensic Audit (2026-10-28)

## 1. Validated Deliverable Receipt (`verdict = "negative"` · **DO NOT SUBMIT**)
- **GeoTIFF Filename:** `docs/csst-bghf/downloads/gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.tif`
- **GeoTIFF SHA-256:** `4b47a37ecf91384b2202897dd695219d23375cab2a300106feaf541d60fc9c5b`
- **Single-File ZIP:** `docs/csst-bghf/downloads/gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.zip` (`08159cb3c603dc1e629da3bb49b71e4b65abb0094ebf01b6293357a20ffd31eb`)
- **Submission Note (107/140 chars):** `H-K3B-1 CSST-BGHF: Coulomb shadow+Baranov leach+Euler N0+Bajada hinge+Dual57 OOF d=3.1 (37654d [0,1] zeros)`
- **Grid & Format:** Single-band `float32`, `3730 x 3292` (`12,279,160` finite pixels, `0` NaN anywhere), `EPSG:32611`, `[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]`, `nodata = None`, `37,654` binary `{0.0, 1.0}` dots (`B = 2` collar -> `0` on `existing_faults.tif`), `13/13` checks passed.

## 2. 3-Experiment Preregistered Ablation Results
| Arm | Hide-and-Recover v3.0 (`n=22,232`) | Detached >=600m (`n=15,504`) | SGMC-cal v3.0 (`n=62,703`) |
|---|---:|---:|---:|
| `0.2778` Champion (`H33-2-B2`) | `0.099202` `[0.0860, 0.1127]` | `0.094324` `[0.0792, 0.1098]` | `0.064121` `[0.0567, 0.0716]` |
| `EXP-1`: Unsupervised `CSST-BGHF` Ridge (`d=3.1`) | `0.078489` `[0.0691, 0.0876]` | `0.069453` `[0.0602, 0.0788]` | `0.067410` `[0.0590, 0.0751]` |
| `EXP-2`: Dual-Cover `57/52`-ch SAR-PU OOF Isotropic (`d=3.1`) | `0.110196` `[0.0955, 0.1254]` | `0.095273` `[0.0799, 0.1115]` | `0.053794` `[0.0451, 0.0622]` |
| **`EXP-3`: `CSST-BGHF` Coulomb + Pre-Sharpened MaxEnv (`d=3.1`)** | **`0.104700`** `[0.0904, 0.1203]` | **`0.099958`** `[0.0846, 0.1173]` | **`0.070171`** `[0.0595, 0.0798]` |

- **Paired Bootstrap Deltas (`EXP-3` minus `0.2778` Champion):**
  - `Hide-and-Recover v3.0`: `+0.005435` (`95% CI [-0.003328, +0.013882]`, `P(Δ > 0) = 88.9%`, wins `4/4` quadrants `NW, NE, SW, SE`).
  - `Detached >= 600 m`: `+0.005665` (`95% CI [-0.003199, +0.014885]`, `P(Δ > 0) = 89.1%`).
  - `Off-Catalogue SGMC-cal v3.0`: `+0.005618` (`+0.006050` pooled delta, `95% CI [-0.003734, +0.016116]`, `P(Δ > 0) = 86.5%`).
- **Fail-Closed Slot Verdict (`scripts/promotion_gate.py`):** `verdict = "negative"`, `ok_to_submit = false`, `selector_required = true` (two-sided 95% paired CI spans zero by `0.0033` and literal `r13-lattice-s5` `206,895`-dot lattice covers `99.36% > 70%`).

## 3. Uniqueness Across All 112 Repositories (`2,355` Rasters / `1,913` Unique SHA-256s), `K3-CCL`, & 9 Focus Sites
- **Pre-placement surface max `|Spearman|` across all `1,913` unique rasters:** `0.519299 <= 0.90` (`PASS`)
- **Final dots max `|Spearman|` across all `1,913` unique rasters:** `0.072324 <= 0.90` (`PASS`)
- **Discrete (`<= 100k` dots, `1,687` unique rasters) max 3-px overlap:** `66.53% <= 70.0%` (`PASS`, `buffedlizard55-lab/GEMSDOE23:docs/downloads/gemsdoe23-h29-dealiased-habitat-20261002-7bf9fac6-allfinite.tif`)
- **Sibling Lane `K3-CCL` (`c7f2433c-zeros.tif`) 3-px overlap:** `29.18% <= 70.0%` (`PASS`, `dots_rho = +0.011092`)
- **Focus-9 (`GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36`) max 3-px overlap:** `59.39% <= 70.0%` (`9/9 PASS`)
- **Prior `GEMSDOEkarage3` PR #9 (`CRSB-GUB`) 3-px overlap:** `57.21% <= 70.0%` (`PASS`)
- **Literal space-filling lattice (`13GEMSDOE` `r13-lattice-s5`, `206,895` dots):** `99.36% > 70.0%` (`literal_all_rasters_final_passed = False`; `IR-K3-02` pigeonhole stop).
