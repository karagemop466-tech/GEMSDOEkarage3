# Project brief — retained user request

**Read at the start of every session.** This is a consolidated archive of the user's request; repeated passages in the original message are not duplicated. Statements and numerical historical results below are the user's input, **not independently verified organizer receipts or leaderboard forecasts**. The current [run card](data/current-run.json), [independent audit](data/historical-audit.json), and [source register](data-sources.md) supersede historical assumptions. Follow the operative protocol without inventing missing inputs.

## Objective and product

> I want to focus on the highest scoring submissions from GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36. I want an executive summary on every site that is clear and obvious which is the best submission to submit to obtain a high score on the leaderboard. It should also be unique and not an exact duplicate of any previous submission. Keep iterating and testing until we have the highest scoring submission to download and submit.
>
> We should be able to estimate the score for a submission. I want a table in the executive summary that clearly lists what file to download, what the estimate score is, and whether it is a unique submission unlike any of the other GEMDOE sites listed below.
>
> THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED! MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.
>
> There should be an easy to download submission tif file as described by the prompt. Read the entire prompt. A lot of sites mention inspection only and a human inspector, but the inspection needs to be done through the project and needs to be validated for submission without human intervention.

The user experienced the portal error **“Predicted values must be in range [0, 1]”** and requested a unique submission name and a short distinguishing note. The submission form accepts one single-band GeoTIFF or a ZIP containing one GeoTIFF, matching the sample CRS, shape and geotransform. The user asked for a clear executive-summary subpage explaining exactly how to submit and for a clean, user-friendly GitHub Pages site with source links and a current feed. Do not misrepresent a format check, an owner score, or a stale source as authorization.

## Parallel-run protocol — user supplied

1. **LANE.** Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds 0.90, or more than 70% of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement **and** on the final dots.
2. **REUSE, DON'T REBUILD.** Use the template's cached feature stack, `evaluate_holdout.py` and `submission_writer.py`. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.
3. **LABEL EVERY NUMBER** as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score. Historical values in this brief are explicitly **USER-REPORTED / UNVERIFIED**, not confirmed scores.
4. **LEAKAGE CANARY.** Test each feature alone on the holdout before trusting any result. AUC above 0.90 means leakage until proven otherwise.
5. **RUN CARD.** End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.
6. **BUDGET.** Stop after 3 experiments or 2 hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.

The original prompt refers to “the single method paragraph below” but does not identify a specific method paragraph in this checkout. Do not turn the hypothesis slate into an assumed assignment.

## Research and validation instructions

> Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.

The user asked for PhD-level investigation into why the GEMSDOE32 H33-B2 file was reported at 0.2778, whether a genuinely new file can do better, and scientific research into geothermal systems, official/free data and overlooked geological processes. Avoid claiming a fault is a proven vent or forecasting hidden test performance from an uncalibrated proxy. User-supplied competing leaderboard-high claims of 0.3195 and 0.4413 require an official check, not reconciliation by assumption.

**Core values:** Maximize P(Win), balancing risk and information gain; Own the Outcome, treating success and failure as signals and following through end to end. Work autonomously, verify line by line, give official links for review, flag irregularities and do not hallucinate. Run three passes: implement and verify; review for bugs and edge cases; re-check the full request and improve reliability. The user requested a pull request and merge to main, followed by next steps and limitations.

The prompt also claimed that data placement alone was the remaining blocker and mentioned `scripts/download_competition_data.sh`, `scripts/prepare_data.py`, and GPU training. This was a user-supplied claim about earlier work, **not a description of the initially empty checkout**; evaluate current conditions rather than assume that pipeline exists.

## Requested sources

* [Competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/), [problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [about](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) and [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
* [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [NLR official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [INGENIOUS](https://gbcge.org/current-projects/ingenious/), [GDR 1391](https://gdr.openei.org/submissions/1391), [EPSG:32611](https://epsg.io/32611) and [Tversky index](https://en.wikipedia.org/wiki/Tversky_index).
* User-supplied Dropbox links: [rules PDF](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0), [example submission](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0), [existing faults](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0), [numerical features](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0), and [DEM links PDF](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0). They were provided by the user; this runtime did not independently access or authenticate them.

## User-reported historical inventory

These are copied from the request as context, **not organizer-confirmed measurements, current recommendations, or estimates**. Repeated entries are consolidated. The focus-site exact-file hashes and geometry were independently checked in [the audit](data/historical-audit.json); other entries were not individually rechecked in this checkout.

| Site | User-supplied file identifier and reported value |
|---|---|
| [GEMSDOE](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html) | `gems-submission-20260925T001403Z-7f00890a`: 0.1563 |
| [6GEMSDOE](https://buffedlizard55-lab.github.io/6GEMSDOE/) | `gems6_hgb88-topk03_33cec71ff0`: 0.0286 |
| [GEMSDOE3](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html) | `pindrop-v4-nodes-20260925T152420Z-f347b70daa`: 0.1193; `pindrop-v4-discovery-20260925T152423Z-37f9d5b855`: 0.0830; `pindrop-v4-ridge-20260925T152422Z-4e03fc9705`: 0.1152 |
| [GEMSDOE2](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html) | `gemsdoe2-dual-family-union-20260925T160406Z-f68e590f`: 0.1560 |
| [GEMSDOE4](https://buffedlizard55-lab.github.io/GEMSDOE4/) | `gems-submission-20260926T163915Z-237f0063`: 0.0343 |
| [5GEMSDOE](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html) | `gems-submission-20260926T175114Z-7f00890a`: 0.1563 |
| [7GEMSDOE](https://buffedlizard55-lab.github.io/7GEMSDOE/) | `lidarscarp-ridge-top2pct-36c3a3f341c8`: 0.1461 |
| [8GEMSDOE](https://buffedlizard55-lab.github.io/8GEMSDOE/) | `Hedge-v2_submission`: 0.1563 |
| [GEMSDOE9](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html) | `2314b599`: 0.0107 |
| [11GEMSDOE](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html) | `gems-structural-area06-v1`: 0.0202 |
| [12GEMSDOE](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html) | `r7-nms3-dem10-scarp_0c9199f14e62`: 0.1294; `_allfinite`: 0.1294 |
| [15GEMSDOE](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html) | `gems-tso1-20260929T005627Z-conj_alteration_mag`: 0.0782 |
| [14GEMSDOE](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html) | `GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f`: 0.0020 |
| [17GEMSDOE](https://buffedlizard55-lab.github.io/17GEMSDOE/) | `17GEMSDOE_F-ensemble-2pct_20260930T050626Z`: 0.0187 |
| [18GEMSDOE](https://buffedlizard55-lab.github.io/18GEMSDOE/) | `H19-C_20260930T212401Z_c11e495e`: 0.0297 |
| [19GEMSDOE](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html) | `h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan`: 0.1894; `h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan`: 0.1922 |
| [GEMSDOE10](https://buffedlizard55-lab.github.io/GEMSDOE10/) | `h16-continuation-20260927T065521077735Z-3431b83c7c`: 0.0461; `h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686`: 0.0921; `H25-ctx-ridge-20260927T232947704150Z-6452ae1d00`: 0.1280; `h28-dotted-ridge-20260928T020256236880Z-6452ae1d00`: 0.1839 |
| [13GEMSDOE](https://buffedlizard55-lab.github.io/13GEMSDOE/) | `20261001_r13-lattice-s5_v2_nan-outside`: 0.0904 |
| [16GEMSDOE](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html) | `h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan`: 0.1855; `h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan`: 0.0976; `h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan`: 0.0360 |
| [GEMSDOE21](https://buffedlizard55-lab.github.io/GEMSDOE21/) | `h19-4-reference-20260930-691e4dfa`: 0.1894 |
| [20GEMSDOE](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html) | `h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan`: 0.1890; `h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan`: 0.1859 |
| [GEMSDOE22](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html) | `h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan`: 0.1002; `h23-b-dti-optimal-emission-10pct-20261002-86176698-nan`: 0.0748 |
| [GEMSDOE23](https://buffedlizard55-lab.github.io/GEMSDOE23/) | `h30-arrangement-matched-habitat-20261002-0d4e02e8-nan`: 0.1352 |
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan`: 0.2477; `gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros`: 0.0859 |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan`: 0.2600; `gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros`: 0.0742 |
| [GEMSDOE26](https://buffedlizard55-lab.github.io/GEMSDOE26/) | `dilcond-oof-v1-20261003-47629f496133-nan`: 0.1223 |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan`: 0.2449; `gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite`: 0.2190; `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite`: 0.2250 |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan`: 0.2708; `h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan`: 0.2649; `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan`: 0.2710; `h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan`: 0.2707; `gems28-s18-mxtp-20261025-3e95505c011a-allfinite`: 0.0217; `gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite`: 0.0206 |
| [GEMSDOE29](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html) | `efd28-repro-20261003-1cc7dc534d51-nan`: 0.2600; `repo-c0-habitat-emission-20261003-a4d439b07426-nan`: 0.0041; `sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan`: 0.0512; `wormrank-d28-20261003-59dcaf6dd11d-zeros`: 0.2560; `wormsurv-filter-20261003-921f10960d6e-zeros`: 0.0532; `xfit-c0-habitat-20261003-ca879db0089a-zeros`: 0.0439; `xfit-h41-union-qfaults-20261003-9edb34b99e3a-zeros`: 0.0356 |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca`: 0.2600; `gems30-MSDB1-edge44090-20261025-e7856ec3f14a`: 0.1462 |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | `h27-4-solo-d28-20261004-8acb75e1-nan`: 0.2708 |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`: 0.2778 |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30-20261004-cb490425926e`: 0.2632; `gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros`: 0.0963 |
| [GEMSDOE34](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html) | `h34-scatter-q50-arr-matched-20261004T223317Z`: 0.0778 |
| [GEMSDOE35](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html) | `h35-06-aaa86efb25-20261004T225420098147Z-candidate`: 0.0418 |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros`: 0.2750; `gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros`: 0.1647 |
| [GEMSDOE37](https://buffedlizard55-lab.github.io/GEMSDOE37/) | `h6-physics-dotted-80k-20261005T055000Z-0bef9211631c`: 0.1193 |
| [GEMSDOE38](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html) | `D-step-3p0-07pct-tipProt-20261005-ecfbf59e2b48-zero`: 0.0763 |
| [GEMSDOE39](https://buffedlizard55-lab.github.io/GEMSDOE39/) | `h40-e-disc-h40e-30k-zeros`: 0.0339 |
| [GEMSDOE40](https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html) | `h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1`: 0.0355; `h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1-hard`: 0.0397; `h45-eulerdepthreadcluster-20261006-f28e5cff6826-zeros`: 0.0984 |
| [GEMSDOE41](https://buffedlizard55-lab.github.io/GEMSDOE41/docs/index.html) | `h42-submission-primary`: 0.0245 |
| [GEMSDOE42](https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html) | `xscale-worm-persistence-20261006T000541Z-nan`: 0.0581 |
| [GEMSDOE43](https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html) | `sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan`: 0.0424 |
| [GEMSDOE44](https://buffedlizard55-lab.github.io/GEMSDOE44/docs/) | `h46-twostageAB_20261006T160000Z_b0cfe956-zeros`: 0.0715 |
| [GEMSDOE45](https://buffedlizard55-lab.github.io/GEMSDOE45/) | `h51-km-faultzone-20261006-zeros`: 0.0106 |
| [GEMSDOE46](https://buffedlizard55-lab.github.io/GEMSDOE46/) | `r11f-scarp-radiometric-fusion-00e049b51218-zeros`: 0.1589; `r12-scarp-rad-concordance-23e807e2de9f-zeros`: 0.0843 |
| [GEMSDOE47](https://buffedlizard55-lab.github.io/GEMSDOE47/) | `h60-lidarscarp-s2p0-20261007-nanoutside`: 0.0430 |
| [GEMSDOE48](https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html) | `h59-cover-ds-belief-b2xh33d-20261008T184547Z-b79c4c61d8d8`: 0.2296 |
| [GEMSDOE49](https://buffedlizard55-lab.github.io/GEMSDOE49/) | `gate_ortho_w0.25-40k-20261006T213721Z-nan`: 0.2376 |
| [GEMSDOE50](https://buffedlizard55-lab.github.io/GEMSDOE50/) | `h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite`: 0.0764 |
| [GEMSDOE51](https://buffedlizard55-lab.github.io/GEMSDOE51/) | `h53-twostage-20261008T040951Z-9a0b32c871`: 0.1047 |
| [GEMSDOE52](https://buffedlizard55-lab.github.io/GEMSDOE52/) | `h97b-candidate`: 0.0856 |
| [GEMSDOE53](https://buffedlizard55-lab.github.io/GEMSDOE53/docs/index.html) | `h8-tiprelay-ridgeconcord-pr2-n80000-20261009-49bec522-zeros`: 0.0159 |
| [GEMSDOE54](https://buffedlizard55-lab.github.io/GEMSDOE54/docs/) | `h54c-manifest-edge-20261009T025732Z-73454bc5`: 0.0449 |
| [55GEMSDOE](https://buffedlizard55-lab.github.io/55GEMSDOE/docs/index.html) | `tensor_full-n16000-sep3-20261009T211747Z-nan`: 0.0290 |
| [56GEMSDOE](https://buffedlizard55-lab.github.io/56GEMSDOE/docs/index.html) | `h56-final-dotted-ridge-d2p8-20261009T190421Z`: 0.0658 |
| [57GEMSDOE](https://buffedlizard55-lab.github.io/57GEMSDOE/docs/index.html) | `h57r-joint-strata-38000-20261010T214547Z-00cf5b2066f1-zeros`: 0.0254 |
| [58GEMSDOE](https://buffedlizard55-lab.github.io/58GEMSDOE/docs/index.html) | `ml-binary-ridge-20261012T000000Z`: 0.0180 |
| [59GEMSDOE](https://buffedlizard55-lab.github.io/59GEMSDOE/docs/index.html) | `h59j-coherence-consensus-dotted-20261011T043000Z`: 0.0499 |
| [60GEMSDOE](https://buffedlizard55-lab.github.io/60GEMSDOE/docs/index.html) | `h73-chi-coherent-corridor-12000-20261011T195818Z-zeros`: 0.0351 |
| [61GEMSDOE](https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html) | `h61a-basement-step-20000dots-20261011T012029Z-eb2ae4bb024b-zeros`: 0.0009; `h61o-vardepth-none-40000dots-20261011T160711Z-28d4fac611ea-zeros-zeros`: 0.0751 |
| [62GEMSDOE](https://buffedlizard55-lab.github.io/62GEMSDOE/) | `datum-lahontan-strain-gauge-defensible-440dots-zeros`: 0.0000 |
| [GEMSDOE63](https://buffedlizard55-lab.github.io/GEMSDOE63/) | `cvarlw-thin-s3p17-54864-20261011T220606Z-c58f60c4-zeros`: 0.2303 |
| [GEMSDOE64](https://buffedlizard55-lab.github.io/GEMSDOE64/) | `h64-lidar-scarp-cv-20261011T220000Z`: 0.0383 |
| [GEMSDOE65](https://buffedlizard55-lab.github.io/GEMSDOE65/docs/index.html) | `sar-em-propensity-half-20261011T223500Z-5e4660cd-zeros`: 0.0431 |
| [GEMSDOE66](https://buffedlizard55-lab.github.io/GEMSDOE66/docs/index.html) | `gems66-lidar03-cvretrain-reliefdecile-37654dots-20261020T190152Z-zeros`: 0.1152 |
| [GEMSDOE67](https://buffedlizard55-lab.github.io/GEMSDOE67/) | `h67a-orientip-lane-29447dots-20261012T021226Z-allfinite`: 0.0356; `ovtr-ml-cover-tau3p0-20261012-nan`: 0.1426 |
| [GEMSDOE68](https://buffedlizard55-lab.github.io/GEMSDOE68/) | `gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04-nan`: 0.0437; `...-zeros`: 0.0437 |
| [GEMSDOE69](https://buffedlizard55-lab.github.io/GEMSDOE69/) | `h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5`: 0.0053 |
| [GEMSDOE70](https://buffedlizard55-lab.github.io/GEMSDOE70/) | `gems70-p5-dual-submod300-oof38k-20261020`: 0.2478 |
| [GEMSDOE71](https://buffedlizard55-lab.github.io/GEMSDOE71/) | `gems71-hydro-conduit-38800-20261020T120000Z-zeros`: 0.0558 |
| [GEMSDOE72](https://buffedlizard55-lab.github.io/GEMSDOE72/) | `gemsdoe72-h72-1-sgmc-offcatalogue-20261020T195456Z-6e6525e5-zeros`: 0.0492 |
| [GEMSDOE73](https://buffedlizard55-lab.github.io/GEMSDOE73/) | `gems73-h73-mcsc-seamfree-blakely-37654dots-20261021T073716Z-b27ac445-zeros`: 0.1917 |
| [GEMSDOE74](https://buffedlizard55-lab.github.io/GEMSDOE74/) | `gemsdoe74-triregime-radon-piedmont-37654-20261021T051000Z-zeros`: 0.0669 |
| [GEMSDOE75](https://buffedlizard55-lab.github.io/GEMSDOE75/) | `gems75-trlt-radon-loco-ridge-20261021-zeros`: 0.1627 |
| [GEMSDOE76](https://buffedlizard55-lab.github.io/GEMSDOE76/) | `gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros`: 0.1555; `gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros`: 0.2343 |
| [GEMSDOE77](https://buffedlizard55-lab.github.io/GEMSDOE77/) | `gems85-h85-edti-collar35-skel-r33-20261021-d97b248e-zeros`: 0.0964 |
| [GEMSDOE78](https://buffedlizard55-lab.github.io/GEMSDOE78/) | `gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros`: 0.1564 |
| [GEMSDOE79](https://buffedlizard55-lab.github.io/GEMSDOE79/) | `gems79-tilt-ring-100000dots-20261022T212135Z-50a5d7498c71-zeros`: 0.0005 |
| [GEMSDOE80](https://buffedlizard55-lab.github.io/GEMSDOE80/) | `gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros`: 0.0943 |
| [GEMSDOE81](https://buffedlizard55-lab.github.io/GEMSDOE81/) | `gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros`: 0.0041 |
| [GEMSDOE82](https://buffedlizard55-lab.github.io/GEMSDOE82/) | `gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros`: 0.1886 |
| [GEMSDOE83](https://buffedlizard55-lab.github.io/GEMSDOE83/) | `gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros`: 0.0573 |
| [GEMSDOE84](https://buffedlizard55-lab.github.io/GEMSDOE84/) | `gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros`: 0.0132 |
| [GEMSDOE85](https://buffedlizard55-lab.github.io/GEMSDOE85/) | `gemsdoe85-hjcd-ventbridge-submod-zeros`: 0.1110 |
| [GEMSDOE86](https://buffedlizard55-lab.github.io/GEMSDOE86/) | No value supplied. |
| [GEMSDOE87](https://buffedlizard55-lab.github.io/GEMSDOE87/) | `h87-h87-cmgep-20261022T060000Z-8f394f43`: 0.0500 |
| [GEMSDOE88](https://buffedlizard55-lab.github.io/GEMSDOE88/) | `gems88-bpwd88-baranov-worm-conduit-37654-20261025-b8543782-zeros-DO-NOT-SUBMIT`: no value supplied. |
| [GEMSDOE89](https://buffedlizard55-lab.github.io/GEMSDOE89/) | `gemsdoe89-bh-rtp-habc-20261024-d7e1507c-zeros`: 0.0301 |
| [GEMSDOE90](https://buffedlizard55-lab.github.io/GEMSDOE90/) | `gems90-cnc-35000dots-20261024T084324Z`: 0.0749 |
| [GEMSDOE91](https://buffedlizard55-lab.github.io/GEMSDOE91/) | `gems91-s17-cwpc-e3-37654dots-20261025T150000Z-4d124f1d-zeros`: 0.1367; `gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros`: 0.1823; `gems91-S18-UNIQUE-curvtilt-20000dots-20261025T182858Z-29db2405`: no value; `gems91-s22-omtj-e1-20261026-a99b8923f0-zeros`: 0.0298 |
| [GEMSDOE92](https://buffedlizard55-lab.github.io/GEMSDOE92/) | `gemsdoe92-listricdip-updip50-37654-20261025T190000Z-zeros`: 0.0255 |

The prompt also listed [KANLERGEMSDOE1](https://kanlerxz87-cyber.github.io/KANLERGEMSDOE1/), [KANLERGEMSDOE2](https://kanlerxz87-cyber.github.io/KANLERGEMSDOE2/), [KANLERGEMSDOE3](https://kanlerxz87-cyber.github.io/KANLERGEMSDOE3/docs/index.html), [EUGGEMSDOE1](https://eugboogieman123-ops.github.io/EUGGEMSDOE1/), [EUGGEMSDOE2](https://eugboogieman123-ops.github.io/EUGGEMSDOE2/), [EUGGEMSDOE3](https://eugboogieman123-ops.github.io/EUGGEMSDOE3/), [WBGGEMSDOE1](https://wingbangboozle1-lang.github.io/WBGGEMSDOE1/docs/index.html), [WBGGEMSDOE2](https://wingbangboozle1-lang.github.io/WBGGEMSDOE2/docs/), [WBGGEMSDOE3](https://wingbangboozle1-lang.github.io/WBGGEMSDOE3/docs/index.html), and [GINNYGEMSDOE1](https://ginnymcfiner23-ux.github.io/GINNYGEMSDOE1/), [GINNYGEMSDOE2](https://ginnymcfiner23-ux.github.io/GINNYGEMSDOE2/), [GINNYGEMSDOE3](https://ginnymcfiner23-ux.github.io/GINNYGEMSDOE3/) without numerical results. Names supplied without scores included `kanlergemsdoe3-h-k3-1-cadg-submod-exp-k3-3-oof8f-37654-20261026-f0565e6d10f9-zeros`, `kanlergems2-htcads-exp-2-37654dots-20261026T235227Z-11a2f251-zeros`, `wbg3-h3pack-34k-20261027T174337Z-zeros`, `wbggemsdoe3-skarpline-union-20261027-610acf58-zeros`, and `wbg2-offcatalogue-density-36k-20261027`.
