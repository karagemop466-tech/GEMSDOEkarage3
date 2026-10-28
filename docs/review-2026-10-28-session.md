# Three-pass review — 28 October 2026 UTC

## Executive decision: NEGATIVE / DO NOT SUBMIT

No new model experiment, HOLDOUT-DTI, candidate TIFF, selector decision, or weekly submission was made in this session. A historical H-K3C TIFF was re-audited for research only: **99.351994%** of its 37,654 dots fall within 3 pixels of one pinned registered lattice. The literal stop is **strictly greater than 70%**, so this file fails regardless of its past format or filtered-registry claims. [Current JSON run card](data/latest-run.json) · [rerun witness receipt](../evidence/k3c-literal-witness-reaudit-20261028-final.json) · [nine-site Pages table](../index.html#scorecard).

The request says to use a single assigned method paragraph, but no such paragraph identifies a lane in this request. A smaller, scientifically motivated budget might avoid this particular count bound; that does **not** establish uniqueness. Do not place points in lattice holes to evade the rule.

## Pass 1 — independently check the scientific evidence

The nine pinned historical TIFFs and a pinned lattice were fetched and hash-checked again; [the new geometry receipt](../evidence/historical-reaudit-20261028-session.json) retains the exact file identities, mirror grid, hashes and 72 directional comparisons. All 72 comparisons exceed 70%; every file also exceeds 99.9% overlap with the lattice. This is a **geometry audit, not a score**, a new submission, or a complete-registry audit. Current heads for all nine repositories differed from those pinned snapshots when checked; changed metadata does not re-audit new files.

The following figures are **USER/OWNER-REPORTED and UNVERIFIED**, not organizer-confirmed receipts or predictions. Linked files are historical research references, not submissions to copy or re-upload. The [interactive table](../index.html#scorecard) names each file, its pinned source and comparison.

| Site | Reported best | Strongest focus-site overlap | Submit? |
|---|---:|---:|---|
| GEMSDOE24 | 0.2477 | 100.00% vs GEMSDOE25 | No |
| GEMSDOE25 | 0.2600 | 100.00% vs GEMSDOE24 | No |
| GEMSDOE27 | 0.2449 | 98.02% vs GEMSDOE24 | No |
| GEMSDOE28 | 0.2710 | 100.00% vs GEMSDOE24 | No |
| GEMSDOE30 | 0.2600 | 100.00% vs GEMSDOE24 | No |
| GEMSDOE31 | 0.2708 | 100.00% vs GEMSDOE24 | No |
| GEMSDOE32 | 0.2778 | 100.00% vs GEMSDOE24 | No |
| GEMSDOE33 | 0.2632 | 99.71% vs GEMSDOE27 | No |
| GEMSDOE36 | 0.2750 | 97.58% vs GEMSDOE27 | No |

**Why GEMSDOE32 might have reported 0.2778.** Its pinned support is the GEMSDOE31 support minus 2,545 dots near the mirrored catalogue. Under the [official distance-weighted Tversky metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), removing spatially redundant or false-positive mass could improve precision while preserving coverage. Hidden labels and an artifact-linked submission receipt are unavailable, so neither the claimed result nor causation is verified. A predicted fault is not direct proof of a geothermal vent.

**Why the lattice matters.** Of 5,167,373 mirrored footprint cells, only 6,649 lie farther than 3 pixels from the pinned lattice. For any set of `N` distinct in-footprint dots, at least `max(0, N − 6649)/N` must overlap. At `N=37,654`, the lower bound is `31,005/37,654 = 82.34%`. The maximum `N` not ruled out by this *one necessary bound* is 22,163; it is not a recommendation, experiment, or uniqueness pass.

The historical H-K3C TIFF's saved bytes passed local in-footprint finiteness/range and mirror CRS/shape/transform checks and a whole-array finite/range diagnostic. Its zero-filled outside did **not** satisfy the separate conservative template-null interpretation. Neither diagnostic proves actual organizer acceptance or explains the past portal error. The comparison template and labels are **owner mirrors**, not authenticated organizer inputs; the mirrored sample's positive pixels match the labels, despite the official description of an absence example. This discrepancy remains unresolved.

## Ranked research slate — planning only

These are not assigned lanes or executed experiments. The ordering is qualitative expected fault-recovery benefit, then cost; it is not a numerical DTI score. Novelty relative to the entire fleet is unverified. Any catalogue-derived feature must be rebuilt from visible faults in every fold.

| Rank | Layers, physical signature and off-catalogue rationale | Non-fault mimics / difference from existing local approaches | Expected benefit and cost; data access |
|---|---|---|---|
| 1 | **Signed multi-scale edge offsets:** mirrored band 13 isostatic gravity, band 02 RTP magnetics, band 12 detrended elevation. Compare cross-strike gravity and magnetic edge signs and offsets across smoothing scales under weak relief; a buried juxtaposition may be missing from a surface catalogue. | Lithologic contacts, dikes, remanence, survey seams. Tests signed relative displacement against unsigned-edge controls, rather than simply multiplying edge magnitudes; no fleet-wide uniqueness claim. | Highest qualitative priority; moderate cost. The 19 raw owner-mirror bands were prepared, but the required shared derived stack is absent and organizer authenticity is unverified. |
| 2 | **Repeated drainage deflections:** 3DEP DEM, 3DHP flowlines and independent gravity edges. Repeated aligned cross-stream offsets may reveal a concealed structural corridor. | Lava dams, roads, erosion and stream capture. Requires repeated cross-channel evidence rather than single-scarp curvature. | Medium qualitative priority; high cost. [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) describes free unrestricted elevation; [3DHP](https://www.usgs.gov/3d-hydrography-program/access-3dhp-data-products) advertises downloads. Exact tiles, coverage and 3DHP license not checked. |
| 3 | **Matched shallow-temperature residual:** [INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391) 2 m temperatures, terrain and conductivity; cross-fit terrain/survey backgrounds and test residual clusters only against independent geophysics. | Insolation, groundwater and uneven sampling. Residual/confounder controls differ from raw well proximity. Temperature anomalies are not fault labels. | Medium-to-low qualitative priority; moderate–high cost. GDR advertises public CC BY 4.0 data, but exact coverage and binary retrieval were not verified. |
| 4 | **Acquisition-block radiometric residual:** [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) K/eTh/eU, acquisition metadata and independent magnetics; test whether an alteration residual survives held-out acquisition blocks. | Rock type, moisture, vegetation and processing seams. Acquisition-block invariance differs from an unqualified ratio hotspot; similar peer approaches exist. | Uncertain-to-low qualitative priority; moderate–high cost. USGS advertises CC0 products, but the exact grid, flight-line metadata, coverage and derivatives were not verified locally. |

## Pass 2 — safety and tool-chain review

- Restored four SHA-verified owner mirrors and prepared 19 raw bands; the large files and derived arrays are ignored/ephemeral. They are **not** the shared derived model feature cache. [Readiness snapshot](readiness.json) was refreshed after restoration; rerun it on each checkout.
- Restored the active shared evaluator, writer, holdout, submission, release gate, metric and paths byte-for-byte to [GEMSDOE32 commit `97597a…`](../registry/shared_template_97597a.json). Exact matching is provenance, not correctness. That pin explicitly rejects non-binary inputs instead of silently thresholding probabilities; the competition format also permits continuous values.
- The shared holdout still has open upstream issues: [truth/visible buffer #60](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/60), [zero-truth FP pooling #41](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/41), and [static catalogue leakage diagnostic #61](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/61). The shared [surface gate #42](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/42) measures but ignores preview-dot overlap at the surface stage. Historical holdout numbers are exploratory and cannot establish a qualifying win until the shared instrument is fixed and revalidated.
- A synthetic 3×3 regression also confirmed that the pinned `gems32.submission.audit_geotiff` can pass a masked in-footprint value; the related [upstream issue #66](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/66) is open. An attempted issue comment was denied by GitHub integration permissions. We have read-only access to that repository and did not privately modify its shared implementation or claim an upstream fix.
- The separate local saved-byte diagnostic and `scripts/check_submission.py` now reject masked in-footprint pixels and externally dependent TIFF sidecars. Range, finite values, mask, dtype, single band, exact CRS, shape and transform are checked. Outside-null and whole-array-finite results remain separate; neither is portal authorization.
- The self-reported promotion screen now requires source/fold/protocol provenance and a same-fold baseline, rejects the pinned defective holdout implementation, and checks literal overlap at both stages. Even a synthetic technical `promote` is **not** selector approval: `ok_to_submit` remains false and no slot is used. It is a screening layer, not independent verification of a complete registry or authenticity of self-reported evidence.
- Nine old experiment/generation entry points now stop before creating candidate outputs. The literal witness CLI requires a new output path and refuses to overwrite an old receipt. Tests exercise these stops, the selector boundary, masked pixels, sidecars, exact upstream bytes, and malformed evidence.

## Pass 3 — product, sources and next steps

The Pages decision and submission guide make the negative verdict prominent, link research-only files honestly, and distinguish exploratory historical holdouts from qualifying results. The browser can check public GitHub metadata; it cannot turn a changed head into a new audit. [DrivenData's terms](https://www.drivendata.org/termsofuse/) prohibit automated access, so the scheduled metadata code **does not fetch the leaderboard**. The retained public-board observation is dated, stale and not tied to any artifact; follow the official link for current information. Legacy GitHub Pages currently publishes from `main:/`; its optional scheduled Actions publisher is disabled unless an administrator changes the source and variable.

To resume responsibly: obtain a specific lane; authenticate permitted inputs and restore the shared feature cache; repair and release the shared issues upstream; establish a complete, immutable current registry and an incumbent on exactly the same valid folds; run every feature canary and at most three buffered whole-segment experiments within two hours; compare both uniqueness criteria at both stages; independently re-read and validate saved bytes; then let a separate selector consider the current weekly cap. The [official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) allow up to three submissions weekly and one selected final submission, and require disclosure of generative-AI use in the narrative. They do not establish the account's current quota.

Software tests and reproducible forensic audits are not new HOLDOUT-DTI results. See the root [README](../README.md) for commands and the [project brief](PROJECT_BRIEF.md) for the retained user requirements.
