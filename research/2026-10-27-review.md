# Evidence review and next research slate

**Decision: no new TIFF; no submission is authorized.** This is a zero-experiment
preflight, not a negative model result. The numbered results from the user's
request are **USER-REPORTED / UNVERIFIED**: no submission-page receipt was
available linking any score to a hash. The publicly visible leaderboard is a
separate **ORGANIZER-PUBLIC observation**, not such a receipt. A live score for a
new candidate is **not estimable** from the evidence here.

## Official task and metric

[DrivenData's problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
says the target is *faults indicative of geothermal resources*, not geothermal
vents themselves. Its expert-hidden faults are not the training catalogue; in
the final round the organizer will expand the labels following expert review.
A detected line is neither a proven fault nor a proven geothermal resource.

The official distance-weighted Tversky index is
`TPw / (TPw + 0.2 FPw + 0.8 FNw + ε)`, with triangular weight
`max(1 - distance / 300m, 0)`. TP credit at a truth pixel is the *maximum*
weighted predicted confidence within the kernel, not a sum. This makes closely
spaced redundant predictions potentially costly in FP without commensurate
additional recall. The official formula and format are in the
[problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric).

## What the B2 lineage actually establishes

We independently downloaded and SHA-256-checked the nine pinned TIFFs, labels,
and template from public GitHub mirrors. [Our geometry audit](../evidence/geometry_audit.json)
and [manifest](../registry/historical.json) contain the exact bytes and pins;
those pins establish integrity, **not** organizer authenticity.

* **GEOMETRY-AUDIT:** G25 and G30 are the same binary support *inside the mirrored
  footprint*, despite different TIFF bytes. G31 is a subset of G25. G32 is
  exactly G31 after removing pixels within two Euclidean pixels of the mirrored
  catalogue: 2,545 pixels removed. G36 contains G32 plus 1,200 pixels.
* **USER-REPORTED / UNVERIFIED:** G31 was attributed 0.2708 and G32 0.2778;
  G25 and G30 were each attributed 0.2600. These are not independently
  authenticated organizer results and the hidden truth is unavailable.
* **Plausible, unproven explanation:** removing dots near already-mapped traces
  might lower FP cost on newly labeled faults more than it loses TP credit.
  Mapping/delineation differences, data splits, and unobserved ground truth are
  alternative explanations. The lineage alone cannot establish causation or show
  that a new model will exceed 0.2778.

For a fixed binary raster and evaluation mask, let removal reduce TP by `dT`
and FP by `dF`, and let `G = TP + FN` be the fixed truth count. Given positive
old and new denominators, removal improves DTI exactly when
`0.2 * TP * dF > dT * (0.2 * FP + 0.8 * G + ε)`. This follows directly from
cross-multiplication of the official metric. Neither `dT` nor `dF` on the hidden
set is known, so this is **not** a score forecast or a tuning recipe.

## Literal uniqueness stop

**GEOMETRY-AUDIT, not a score:** all 72 directional comparisons among the nine
historical files exceed 70% of the candidate dots within three pixels of some
other historical file. These are prior files, not candidates for resubmission.
Pre-placement surfaces are not available and were not audited. The subset is
not a complete current registry.

The hash-pinned [13GEMSDOE spacing-five lattice](https://github.com/buffedlizard55-lab/13GEMSDOE/blob/92ee6f074323f161eed837b80ec3ee5b662e26f5/docs/downloads/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif)
is present in the [GEMSDOE32 focus registry](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/73485f27cf230af770167397c2b72cb9ce3b3f25/registry/focus_registry_manifest.json).
It is a calibration grid rather than geological evidence, but the prompt says
**any** registered raster. We did not silently exempt it.

Our independent reproduction found 5,167,373 footprint pixels, of which 6,649
are more than three pixels from the lattice. For `N` distinct in-footprint dots,
the directional overlap is at least `max(0, N - 6649) / N`. For the historical
37,654-dot budget, the minimum is 31,005/37,654 = **82.34%**, already over the
strict 70% threshold. This is a budget-specific proof, not proof that every
smaller raster is impossible. Exploiting the uncovered holes to pass the
benchmark would not itself be geological discovery. A different, genuinely
motivated budget might escape this *one bound* but would still need the complete
registry, surface guard, holdout, and independent selector.

## Ranked hypotheses — planning only, no assigned lane

The requested “single method paragraph below” is absent. These proposals are
unimplemented in this initially empty checkout; we cannot assert global novelty
across all sibling work. Rank is qualitative judgment about *possible* DTI
impact, not a numerical projection. All require pre-registration before use,
feature-only AUC canaries, whole-segment buffered visible-only folds, and an
honest same-instrument matched baseline.

| Rank / cost | Layers and transform; potential unmapped signal | Non-fault mimic / differences and access |
| --- | --- | --- |
| 1 · medium | **Paired signed gravity–magnetic profiles.** From provided isostatic gravity, TMI/RTP and detrended terrain, orient candidate transects by the local gradient, then compare signed multiscale changes and their spatial offsets rather than multiplying positive edge strengths. A buried offset could persist where mapped surface traces are incomplete; estimate any catalogue proximity solely from each fold's visible faults and mask visible pixels exactly. | Lithologic contacts, remanent magnetization, survey flightline/leveling artifacts. Related edge-based and signed-contrast proposals exist on sibling sites. The parallel [research slate](../docs/research.md) also proposed a cross-field edge-offset hypothesis; the oriented signed transects proposed here are a related elaboration, not a demonstrated new lane. This exact profile has not been implemented or tested here and is not proven globally novel. The [organizer lists these bands](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#provided-features); the actual stack and cached features are absent locally. |
| 2 · high | **Cross-fan drainage-offset consistency.** Use official USGS 3DEP elevation, hydrography derived from the DEM, and a persistent transverse slope break. Match several comparable small channel paths on opposite sides and test for a coherent signed offset, excluding channels already used to define the line. A buried or subdued fault can cross young fan deposits not represented in the catalogue. | Fan avulsion, stream capture, erosion, roads, and lacustrine shorelines. This is a paired-channel displacement test, not simply a scarp filter. [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) says products are free and unrestricted; the actual tiles, coverage and byte access have not been verified in this runtime. |
| 3 · medium/high | **Depth-differential conductance reversal.** Compare gradients in USGS MT 2–12 km and 12–20 km conductance layers, and test whether opposite-signed changes align consistently with gravity-basement margins. A deep transition with subdued surface expression could highlight a covered structure. | Clay-rich strata, saline fluids, inversion resolution and station coverage. Distinct from a single-depth conductivity edge. [GEMSDOE25's later H79 report](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/19b219f629440b9975b093f459c74e21a42476ca/knowledge/40_h79_cthm_poe_outcome_2026-10-27.md) reports testing strike-weighted SGMC reactivation and lists deep MT phase-tensor skew as deferred. This proposed reversal differs from both exact operators but shares ingredients, and broader novelty is unproven. [USGS release](https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b) lists downloadable maps; binary files were not obtained here and their resolution may be too coarse for a 100 m trace. |
| 4 · high | **Cross-line residual thermal gradient.** Fit depth- and sampling-density-aware regional background temperatures from the [INGENIOUS well/spring compilation](https://gdr.openei.org/submissions/1391); test sustained residual contrast on opposite sides of independent magnetic or terrain lineaments rather than simply ranking proximity to hot points. A fluid-conduit boundary might manifest where the mapped trace is incomplete. | Unequal sampling, deep circulation unrelated to a fault, lithology, anthropogenic wells and clustered observations. The public GDR page lists a CC-BY archive, but binary bytes/coverage and use permissions of each upstream contribution were not independently checked here. |

A candidate cannot be called viable merely because its source page exists. The
required exact data, coverage, scale, license, fold-local processing, and
performance are still unverified. No candidate was fit, placed or scored in
this session, and no weekly slot was spent.

## Input, tooling and format irregularities

1. The organizer's [data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
   redirected the research page fetch to login. Pinned public GitHub mirrors
   supplied the grid, labels and historical rasters, not organizer-authenticated
   files. The claimed feature cache is missing; the 419 MB owner mirror of the
   feature TIFF was not downloaded in this session. A parallel run saved a [core-data receipt](../docs/core-data-receipt.json), but ignored data must be restored in a fresh checkout. GPU availability was not verified.
2. The mirrored `sample_submission.tif` contains 60,988 positive pixels and
   its support exactly equals the mirrored label raster. The official page
   describes an all-absence sample. This discrepancy prevents authenticating
   the sample's contents; use it only for grid/footprint geometry and never as
   an independent truth or prediction.
3. At pinned GEMSDOE32 commit `73485f27cf230af770167397c2b72cb9ce3b3f25`,
   the shared [holdout CLI](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/73485f27cf230af770167397c2b72cb9ce3b3f25/scripts/evaluate_holdout.py#L48-L56)
   and [writer](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/73485f27cf230af770167397c2b72cb9ce3b3f25/scripts/submission_writer.py#L68-L76)
   silently turn every finite positive probability into `True`. A full-catalogue
   prediction passed to the CLI is not automatically fold-local either. This
   can corrupt probabilistic scoring and can leak if a raster was built using
   hidden labels. Existing [upstream issue #37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37)
   documents the binarization defect. We independently reproduced it on the
   actual current CLI with stubbed holdout calls and two 2×2 probability arrays;
   [the software-only receipt](../evidence/shared_tool_repro.json) is not a
   scientific experiment. We made no private evaluator/writer fork; an upstream
   repair or explicit binary-only rejection is needed. The current checkout cannot
   push to that separate repository under this session's branch restriction. An
   attempted comment on the existing issue returned “Resource not accessible by
   integration,” so no new upstream comment or patch was posted.
4. The official page says outside data should be null or NaN; the reported portal
   rejection was `[0,1]`. NaN-outside files may fail a whole-array range test;
   all-finite zeros outside lack an explicit null mask. `scripts/check_format.py`
   reports both properties on saved bytes and never silently repairs inputs.
   Passing local checks is not proof of portal acceptance.
5. The user-provided 0.3195 and 0.4413 were conflicting/stale as claims about the
   leader. The organizer's public leaderboard page read during this review showed
   **ORGANIZER-PUBLIC 0.4544**, rank 1 on 2026-10-27 UTC. This is a public page
   snapshot, not a submission receipt, and may change.
6. The [official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf),
   §3.2–3.5, states three submissions per week, subject to the website's limits;
   this session has no account access and cannot see the remaining allowance. It
   also requires a narrative disclosure of generative-AI use and, for finalists,
   complete reproducible code/documentation. The PDF points to the website for
   current dates; its appendix also mentions a 5 p.m. ET cutoff, while the
   competition homepage displays 11:59 p.m. UTC. Whether these apply to the
   same deliverable is unclear; seek the organizer's clarification rather than
   assuming the later time.
7. A metadata check detected GEMSDOE25 changing from `b13ccaba` to `19b219f6`
   during this review. The pinned [H79 report](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/19b219f629440b9975b093f459c74e21a42476ca/knowledge/40_h79_cthm_poe_outcome_2026-10-27.md)
   describes a newer research-only candidate and a density-aware exclusion of
   dense halos; it also acknowledges the literal lattice conflict and says not
   to submit. Its new experiment and scores were not independently replayed
   here, and no exemption from this project's literal rule is implied. The
   historical raster comparison remains pinned to immutable files.

## Next actions

* Resolve the missing lane and registry-control policy with the parallel-run
  coordinator; do not silently exempt controls or optimize into lattice holes.
* Restore the complete, current registry and the exact upstream shared tools;
  repair issue #37 **upstream**, not by creating a local fork.
* Restore the stack and license-checked data; freeze a matched same-evaluator
  incumbent. Derive every catalogue-dependent feature inside each fold, test
  each feature alone for AUC > 0.90, and check surface before emission and final
  dots against every registry raster. Stop immediately on a duplicate.
* Run no more than three experiments / two hours; compare pooled DTI with paired
  spatial-block 95% CI, and do not call the proxy a leaderboard estimate.
* Only a separate automated weekly-slot selector can promote an eligible run.
  Validate exact saved bytes and record an organizer receipt and raster hash after
  a real upload. No upload, account access, or slot decision occurred here.
