# Three-pass review — literal duplicate stop

> Historical review. For current shared-tool behavior and the latest decision, see [the 28 October session review](review-2026-10-28-session.md).

**Decision: negative / DO NOT SUBMIT.** No new geological experiment, candidate,
score estimate or competition upload was made. The requested method paragraph
is not identifiable in the prompt. The ignored feature stack is absent in this
checkout, and previous results cannot be reproduced from JSON alone.

## Pass 1 — examine and independently verify

The inherited H-K3C page said PROMOTE despite its own run card recording
`literal_all_rasters_final_passed: false`; its gate replaced the user's literal
threshold with a null-calibrated rule. A dense calibration lattice can make the
literal rule difficult to satisfy; it does not authorize rewriting the rule.
Using the SHA-pinned owner-mirrored template and a pinned registered lattice,
[a fresh independent audit](../evidence/k3c-literal-witness-audit-20261028.json)
found **37,654** in-footprint dots, of which **99.351994%** are within 3 pixels
of that witness. This is a geometry measurement, not a score. The lattice is
not organizer data and this one-witness check is not a complete registry audit.
The saved raster's whole array was finite and in [0,1]; band count, CRS, shape
and transform matched that owner mirror. Outside-footprint null checking failed,
which is distinct from the whole-array check; official acceptance remains unknown.
Reproduce with `.venv/bin/python -m scripts.audit_k3c_literal_witness --out .cache/k3c-recheck.json` (choose a new path; existing receipts are never overwritten) (GitHub
access required when the cache is empty).

The earlier numerical **HOLDOUT-DTI** results remain historical and are not
reproduced here. The available prior H-K3C card reports **0.111044**, evaluator
`GEMSDOE32-HIDE-RECOVER-v3.1-24cell`, withheld positives **66,904** (repeated
across draws, not unique faults), 95% CI **[0.098990, 0.122727]**. This is not
a forecast or an organizer result. User-supplied historical values and the two
conflicting claimed leaderboard highs are not organizer-confirmed. The best
reported GEMSDOE32 dot lineage is consistent with thinning and collar pruning;
less redundant prediction mass is a plausible, not demonstrated, explanation of
its reported performance. Fault prediction is not proof of geothermal vents.

## Pass 2 — fix safety and regressions

The local promotion screen now requires literal overlap <= 70% at both stages
and cannot treat calibrated overlap as literal. The preflight stops budgets
that the pinned geometry proves cannot pass. The current landing page and guide
now say DO NOT SUBMIT; the research file remains explicitly labeled as such.
The old run card stays unchanged as historical evidence, but no longer drives
a positive gate. Automated tests cover the threshold, calibrated false passes,
missing literal fields, and published decision agreement.

The upstream shared evaluator/writer issue, silently binarizing probability
inputs, is [still open](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37)
as verified via GitHub in this session. No private fork was made. No shared
upstream fix was implemented: this branch is restricted to this repository and
the shared-template repository is separate. The literal check above is an
independent forensic audit, not a replacement for the shared evaluator or writer.

## Pass 3 — outstanding work and sources

The [previous research slate](review-2026-10-28.md#ranked-research-slate--not-an-assigned-lane-or-new-experiment)
contains four qualitative, untested ideas with layers, mechanisms, confounders,
and data availability limitations. Their ranking is judgment, not a DTI score.
Do not assume global novelty. A valid future run needs a clearly assigned
single lane, official data provenance and the shared cached features, a fixed
shared evaluator, and a frozen complete registry. Then run feature canaries,
whole-segment buffered hide-and-recover, a matched baseline with paired spatial
confidence intervals, literal registry comparisons at both stages and saved-byte
validation. The separate slot selector must respect the actual current cap.
The filtered registry fetcher alone cannot establish completeness. Do not
exploit holes in the lattice to evade the rule.

[Official DrivenData reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution)
was reachable via GitHub; [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[competition data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/),
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/),
[USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
and [GDR 1391](https://gdr.openei.org/submissions/1391) were not reachable in
this network-restricted sandbox; their current content, data rights, and quota
were not independently checked here. No claim about the present leaderboard or
external data obtainability follows from these links.

Verification after the three passes: `pytest -q` 165 passed, one optional-cache
skip, 49 subtests; `unittest discover` 105 passed; dashboard Node suite four
passed; browser feed suite two passed; root site build check and `git diff
--check` passed. These are engineering checks, not new HOLDOUT-DTI measurements
or evidence of organizer acceptance.
