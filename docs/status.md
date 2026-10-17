# PitWall Arena status

## S1.1 — bounded lab review and accessibility repair

The lab now has one map Tab stop with directional navigation, normal exit and
predictable refresh/retry focus. Touch targets are at least 44×44px; both axes stay
visible in a bounded map viewport. Normal local lint includes source/tests while
narrowly excluding the retained generated `web/artifacts/` directory.
See [review/tool inventory](reports/s1-1-review.md) and [task](../tasks/s1-1-review.md).

UI/UX Pro Max was available and used. Ponytail, PStack and Thermo Nuclear Code
Review were not found; independent backend and client reviewers supplied distinct
fallback reviews. No numerical/API/export compatibility change. Acceptance cases,
replay and historical/challenge regressions remain intact. 297 core/API tests,
129 historical tests and 28 browser cases pass; normal lint/typecheck/build and
rendered 375/768/1024/1440 checks pass. Publication evidence follows in the review.

S1.1 stops here. S2 is only a proposed explicit “Find best legal strategy” action
using the existing bounded optimizer at selected settings. No S2 implementation,
calibration, adaptive planning or RL; full historical gate remains blocked.

## S1 — synthetic strategy sensitivity lab

The discoverable `/lab` compares the existing one-stop and two-stop schedules
through the Python engine. Three bounded controls, legal outcomes, stint timelines,
component sums, signed differences and a 21×21 text-labelled sensitivity map are
implemented. Scenario/result exports support offline recomputation. See the
[spec](sensitivity-lab-spec.md), [usage](../README.md#synthetic-sensitivity-lab-s1)
and [scoped task](../tasks/s1-sensitivity-lab.md).

Verified default-multiplier outcomes (one-stop / two-stop): pit18 gives
1113.850 / 1124.700 s; pit7.15 gives 1103.000 / 1103.000 s; pit0 gives
1095.850 / 1088.700 s. Full precision determines Python classifications with
explicit numerical tie/near-tie conventions. The map shows sampled transitions,
not exact crossovers, probabilities or global optimality.

Local Python verification: 297 core/API tests and 356 core/historical tests,
Ruff lint/format and wheel pass. Web lint (excluding an existing ignored local
artifact), typecheck and production build pass. Independent read-only review
verified 47 focused tests and 1,323 grid points against independent arithmetic
(maximum discrepancy 4.55e-13 s). All 24 production-browser desktop/mobile cases
pass, including the preserved 18 challenge flows. Rendered screenshots were inspected by root and reviewer.
Actual browser downloads replay exactly; two canonical full-record builds match
byte-for-byte. Independent final review has no outstanding findings.
Implementation [`83636f7`](https://github.com/Su760/f1-pitwall/commit/83636f7ff6911c33de32fa09e3c40e259ee97d5a)
is pushed; [CI 39009001641](https://github.com/Su760/f1-pitwall/actions/runs/39009001641)
passed all four jobs, including production-browser checks. S1 is delivered; stop here.

S1 uses explicitly synthetic assumptions only. Historical reports/challenges and
the approved project spec are preserved. The full circuit gate remains blocked;
cohort calibration is closed. No F2, imports, model fitting, adaptive planner or RL.

## F1.3 — descriptive report delivered; historical workstream closed

The self-contained local report is `historical-data/f1-3-a/report.html`; run
`open historical-data/f1-3-a/report.html` from the repository root. It provides
19 driver/stint charts, exact lap coverage, counts, median/IQR, deletion annotations,
a labelled sensitivity table and SVG/JSON exports. See [F1.3 delivery and exact
commands](reports/f1-3-descriptive-report.md).

All **382** frozen members are preserved; **17** retrospective deletion tags
remain in the primary view; sensitivity contains **365** rows. All 1,129 source
laps reconcile against 747 exclusions. Manifest/artifact/source/code/quality
hashes are validated before analysis. Two fresh builds match all **22 files**
byte-for-byte and return expected exit 2 (partial source; full circuit gate
blocked). No source import, eligibility change, model fitting or calibration.

Verification: 19 focused / 332 core-historical (129 historical) / 250 core-API
tests, Ruff and wheel pass. Independent read-only review verified all 152 summary
statistics against Decimal/inclusive quantiles (maximum difference 1.50e−14 s).
Desktop/mobile Chromium inspection verifies driver selection, gap preservation,
17 diamonds, small samples, standalone SVG/JSON downloads, offline operation and
all-driver fallback without JavaScript. Final independent review passed.
Implementation [`edd96e6`](https://github.com/Su760/f1-pitwall/commit/edd96e68149efd03bf69249915f5dd744e3eff08)
is pushed; [CI 38999607994](https://github.com/Su760/f1-pitwall/actions/runs/38999607994)
passed all four jobs, including the production-browser arena. See
[task closure](../tasks/f1-3-descriptive-report.md). Approved spec and unrelated
local work are preserved; the existing synthetic arena remains unchanged.

**This cohort's calibration avenue is closed.** Historical description is the
completed deliverable; the blocked full quality gate is not claimed passed.
One next product proposal: a synthetic strategy sensitivity lab with explicitly
assumed pit-loss, degradation and warm-up parameters and reproducible comparisons.
It is not implemented; no further audit, calibration or RL is started.

## F1.2 — retrospective cohort audited; calibration unsupported

Verified 2026-10-17 UTC from retained snapshot and unchanged `f1-audit-v2`.
The [F1.2 cohort audit](reports/f1-2-cohort-audit.md) reproduces **382 members /
747 distinct exclusions / 1,129 source laps**, session 10014 excluding driver 27.
All nine session endpoints, included-driver coverage, 59 source stints and 382
control/weather interval checks validate. The 19 selected driver/stints span
laps 36–57; 17 members carry retrospective deletion notices and remain annotated
recorded elapsed laps. No new source import or threshold change was made.

Limited late-race description is supported. Within-event prediction is only a
conditional proposal requiring chronological validation; no experiment was run.
Whole-race tire calibration and strategy simulation are **not supported**: age,
race lap, compound and driver/stint effects are inseparable (rank 20 of 23),
with early-race/young-tire and independent-event evidence absent. That calibration
avenue is closed for this cohort. The full circuit gate stays **blocked**, and
the original partial cache, failed 2023 pit request and 2025 result null persist.
No F2, fitting, RL or arena changes occurred.

Two new offline builds `historical-data/f1-2-a` and `f1-2-b` match all four JSON
artifacts byte-for-byte; both return expected exit 2 / partial. The regenerated
v2 quality hash matches F1.1 exactly. The report records hashes and commands.
Local checks: 8 focused cohort, 313 combined core/historical (110 historical),
250 core/API tests; Ruff lint/format and wheel build pass. Independent read-only
code and final evidence/document reviews found no actionable issue. Implementation
[`65db62d`](https://github.com/Su760/f1-pitwall/commit/65db62d41d9ad24b32e3acb3f5dec78902f9a95a)
is pushed; [CI 38998554927](https://github.com/Su760/f1-pitwall/actions/runs/38998554927)
passed all four jobs, including the production-browser arena. No local UI
implementation was touched. The approved spec and
unrelated local work remain intact. See [scoped task](../tasks/f1-2-cohort-audit.md).
One proposed next task: a descriptive report of the frozen members with deletion
annotations, counts/dispersion and race-lap-aligned plots; no calibration.

## F1.1 — quality-gate repaired; full dataset still blocked

The following is the archived F1.1 checkpoint; F1.2 above completes its proposed
cohort suitability audit without promoting the full gate.

Verified 2026-10-16 local / 2026-10-17 UTC against `c503441`. Quality semantics
are now `f1-audit-v2`: unresolved stint consistency limits lap/stint and dry-pace
readiness even when all observed laps are individually eligible. The confirmed
four-lap finisher / stint ending at five now retains 4/4 usable laps but has a
blocked circuit gate. Completed retirement stints and pit-only purposes retain
their separate meanings. Source schema, thresholds and approved spec are unchanged.

The [F1.1 evidence review](reports/f1-1-readiness-review.md) records exact source
URLs/hashes, reconciliation, reproduction commands and a proposal for further
audit. FIA corroborates 50 2023 pit boundaries (its HTML page omits two PDF stops),
does not establish the missing 2024 initial global-clear baseline, and separates
2025 car 27's 57-lap physical participation from its final technical DSQ. No
external value replaces an OpenF1 row, null or failed request. The automated
2025 coverage result remains 19/20 until a separate evidence layer is authorized.

Both retained raw caches validate. Before editing, all 12 original v1 artifacts
were reproduced. New offline builds `historical-data/f1-1-a` and `f1-1-b` match
all 12 files, and all nine Parquet tables match the old build. Exit **2 / partial**
is expected. The complete candidate gate remains **blocked**; eligibility counts
in the archived F1 section below are unchanged. V2 adds 50 unresolved 2023 stint
rows due to missing pit evidence and zero for 2024/2025. Supplemental evidence
does not relax the gate. A 382-row 2025-only retrospective pace cohort is a
proposal with acceptance criteria, not an exported or calibration-ready dataset.

Checks: 37 focused quality / 102 historical / 305 combined core-historical /
250 core-API tests passed; Ruff lint/format, wheel build and synthetic CLI
comparison/optimization/replay passed. Packaging used `.venv-api` after the
historical environment reported `No module named pip`. Independent read-only
code and final documentation/evidence reviews passed, with source conflicts,
hashes and cohort counts independently verified. Implementation
[`880f11a`](https://github.com/Su760/f1-pitwall/commit/880f11aaf0db603676dc877dbe432abf5901b0da)
is pushed; [CI 38997040963](https://github.com/Su760/f1-pitwall/actions/runs/38997040963)
passed all four jobs, including the production-browser arena. This documentation
follow-up records that verified result; its own commit/CI are in the final handoff.
See [the completed F1.1 task](../tasks/f1-1-quality-readiness.md).
No core/API/web implementation changed; unrelated local work remains intact.

## F1 — importer implemented; historical quality gate blocked

The following is the archived **v1** checkpoint. Current builds use v2 and the
F1.1 hashes/reproduction instructions linked above; they do not recreate v1 report
hashes unless run with the original implementation.

Verified 2026-10-13 against reviewed baseline
`1c4b08177fc72306209d04ad0b04bb8815815b2a`. The separate historical package adds
bounded OpenF1 access, immutable raw snapshots, typed row-preserving Parquet,
provenance manifests and deterministic JSON/Markdown suitability reports. The
approved spec, engine, challenge fixtures, API and web implementation are unchanged.
Existing local `web/next-env.d.ts` edits and the downloaded spec are preserved.

### Actual source evidence

Metadata resolved all three candidates to circuit **63 / Sakhir**, country Bahrain,
session Race. Dates and keys below are returned source values, not invented IDs.

| Year / race date (UTC) | Session / meeting | Drivers | Source lap rows / positive timed | Stints | Pit rows              | Control / weather | Result rows |
| ---------------------- | ----------------- | ------: | -------------------------------: | -----: | --------------------- | ----------------: | ----------: |
| 2023-03-05             | 7953 / 1141       |      20 |                      1058 / 1055 |     70 | unavailable: HTTP 404 |          75 / 161 |          20 |
| 2024-03-02             | 9472 / 1229       |      20 |                      1129 / 1129 |     63 | 43                    |          71 / 157 |          20 |
| 2025-04-13             | 10014 / 1257      |      20 |                      1129 / 1128 |     62 | 42                    |          93 / 158 |          20 |

Both real bounded imports made 27 requests. The sole failed endpoint is
`https://api.openf1.org/v1/pit?session_key=7953`, returning **HTTP 404** with
`{"detail":"No results found."}`. It remains a failed request and the entire
candidate snapshot is **partial**. The successful 2024/2025 session downloads
are individually complete, but the conservative shared readiness gate retains
the candidate-set partial-source blocker. No replacement observations were made.

Expected coverage uses each driver's result, not the winner's 57 laps. Coverage
is supported for **20/20**, **20/20**, **19/20** drivers respectively. The three
2023 retirees and the 2025 retiree have an extra started, untimed lap; these are
identified separately rather than counted as missing completed race laps.
No expected completed lap numbers are missing for drivers with usable results.
The 2025 disqualified driver 27 has 57 observed timed laps but a null result
`number_of_laps`; its trailing completeness remains **unknown**.

There are no duplicate/conflicting logical keys or unmatched session/meeting/driver
joins in this snapshot. Four untimed retirement-tail rows have no completed-stint
join. All 3,316 lap rows remain in Parquet and the per-lap audit; all other source
rows are retained too. Fifty 2023 non-opening stint starts lack corroborating pit
records. The 85 available pit records preserve current/alias values without
conflicts; their timestamps fall outside the reported lap interval. Since source
pit timestamp semantics are unspecified, this remains an uncertainty flag and
is not a blanket exclusion from lane/stationary duration description.

### Readiness by purpose

Counts below are eligible rows after documented exclusions, not a calibration
sample recommendation. Every non-blocked purpose is still **limited** by the
partial candidate-set source audit and any local blockers in `quality.json`.

| Purpose                           | 2023                                         | 2024                 | 2025                 |
| --------------------------------- | -------------------------------------------- | -------------------- | -------------------- |
| Descriptive lap/stint rows        | limited: 955 / 1058                          | limited: 1129 / 1129 | limited: 1128 / 1129 |
| Dry-pace investigation candidates | limited: 258 / 1058                          | blocked: 0 / 1129    | limited: 404 / 1129  |
| Pit-lane duration description     | blocked: source unavailable                  | limited: 43 / 43     | limited: 42 / 42     |
| Stationary-stop description       | blocked: source unavailable                  | blocked: 0 / 43      | limited: 40 / 42     |
| Incremental race-time pit loss    | blocked: no counterfactual measurement       | blocked              | blocked              |
| Decision-time features            | blocked: publication times/delays unverified | blocked              | blocked              |

Dry-pace exclusions affect **800**, **1129**, and **725** distinct source rows;
per-reason counts overlap and are preserved with source references. No wet-condition
evidence was observed under these fields, which does not certify a dry session.
2024's zero eligible dry candidates reflects the conservative control baseline:
source `GREEN LIGHT - PIT EXIT OPEN` and session-start messages alone do not
establish global track-clear status. Local yellow/clear events and SC/VSC intervals
are scoped; missing/ambiguous context remains unknown, not wet. The report exposes
this policy uncertainty rather than treating absent neutralization evidence as
proof. Event dates are not established publication times. No future lap or
completed stint outcome is backfilled into a decision-time feature.

Missing stationary time is expected before the 2024 US GP, and two 2025 stops
also have no stationary measurement. Missing values remain null. Lane duration,
stationary duration and synthetic incremental pit loss remain separate concepts.
F1 has not passed the approved specification's circuit completeness exit gate;
real-data readiness for unsupported purposes is unverified. No model was fitted
and the playable arena remains explicitly synthetic.

### Reproduction and provenance

First snapshot: `historical-data/raw/20261013T173313.808650Z-78aa081d6315`.
Refresh: `historical-data/raw/20261013T173926.193125Z-f1d80d3ff360`.
Refresh created a distinct manifest and preserved the first evidence; all 27
response hashes were equal between these downloads. Latest raw-manifest SHA-256:
`22b92984adf14a904d3b3bfd924530dbcb903190a77f101c3280bd4ce6ffdc21`.

Final reports are local at `historical-data/f1-final-a/quality.md` and
`quality.json`; comparison build is `historical-data/f1-final-b/`. All **12 files**
(nine Parquet tables, JSON, Markdown, build manifest) are byte-identical between
offline builds using Python 3.11.14 / PyArrow 25.0.0. JSON report SHA-256:
`1b148ae5006e01adc79f85bb9f47e43b79b370c4ef6af7bb6e06b413f79e5792`.
Markdown SHA-256:
`631a155c21cec9b0afd5bb5f9160feb2298455e71f4747123bb53403d71b5346`.

After the [README locked setup](../README.md#historical-ingestion-and-offline-quality-audit-f1),
reproduce from this local cache into fresh directories:

```sh
SNAPSHOT=historical-data/raw/20261013T173926.193125Z-f1d80d3ff360
.venv-historical/bin/python -m pitwall_historical rebuild "$SNAPSHOT" --output historical-data/reproduce-a --config historical/config.json
.venv-historical/bin/python -m pitwall_historical rebuild "$SNAPSHOT" --output historical-data/reproduce-b --config historical/config.json
diff -r historical-data/reproduce-a historical-data/reproduce-b
```

Both rebuild commands intentionally return **exit 2 / partial** while writing
the auditable outputs. Do not chain them with `&&` expecting success. A corrupt
cache fails closed; existing build directories are never overwritten. Raw data
and reports are ignored, not in Git; another checkout must import a new snapshot
and may observe a different upstream revision. The first snapshot predates the
added `max_lap_number` audit bound; rebuilding it requires the explicit current
`--config` override, recorded in build provenance. Source config is not rewritten.

### Verification and review

- Historical offline fixtures: **100 passed**, including rate/retry/timeouts,
  malformed/partial input, hash corruption, joins, alias conflicts, retirements,
  missing fields, time alignment, bounded pathological values, and reproduction.
- Combined core + historical: **303 passed** both editable and from the final
  installed wheel in a separate Python 3.11.14 environment. Historical fixture
  namespaces prevent collisions with the core suite's existing `conftest` imports.
- Preserved core/API: **250 passed** in `.venv-api` (Python 3.14.2).
- Ruff lint/format: passed; wheel packaging and installed historical CLI help passed.
- Frontend lint/typecheck/production build passed. The default browser invocation
  initially stopped: `Error: http://127.0.0.1:8000/health is already used`.
  A temporary ignored config reused the unchanged running API and launched the
  production web build on 3001: **18 desktop/mobile cases passed**. Tracked browser
  configuration remains unchanged; CI uses its normal clean 3000/8000 setup.
- Synthetic CLI comparison, optimization and replay preserved 1113.850 / 1124.700 s,
  529 candidates / 462 legal, winner 1113.550 s.
- Independent read-only review verified joins, exclusions, provenance, report
  claims and actual source hashes. Concrete findings were fixed with regressions:
  missing control/metadata, boundary propagation, scoped control parsing, uncertain
  pit timestamps, extreme-value bounds, and failed metadata request summaries.
  Scoped final review approved; 99 historical tests passed independently before
  the final narrow classifier review (35 quality tests rerun for that check).
- Hosted publication/CI are recorded separately below; passing CI does not certify
  historical completeness or remove the source/analysis blockers.

### F1 publication and hosted CI

Implementation commit
[`496f02ef3609ce90c7a390dff6da4c66c666aed0`](https://github.com/Su760/f1-pitwall/commit/496f02ef3609ce90c7a390dff6da4c66c666aed0)
was pushed to `origin/main` without force. [CI run 38441425578](https://github.com/Su760/f1-pitwall/actions/runs/38441425578)
completed successfully for all four jobs: the isolated historical offline suite,
core Python 3.11/3.14 checks and CLI demos, and API/production-browser arena.
The initial status monitor encountered a transient GitHub connection reset;
the subsequent run query confirmed `completed / success` for every job.

This documentation-only follow-up records that observed result and closes the
task checklist. Its own commit and hosted CI are reported in the final handoff.
The quality gate remains blocked as reported above. No F2 work is authorized by
this checkpoint, and no generated historical datasets/reports enter Git.

## F0.5 — playable arena implemented and locally verified

The milestone adds a local FastAPI + Next.js/TypeScript practice arena with three
server-owned versioned synthetic challenges. The backend evaluates each legal
call on an independent fork under the same stay-out continuation. The public
contract is in [api-contract.md](api-contract.md); core equations, Observation,
CLI, dependency lock and approved specification remain unchanged.

Backend evidence on 2026-10-03: 203 preserved core tests plus 47 API/challenge
tests pass on Python 3.14.2 and 3.11.14 (**250 each**). Ruff lint/format pass.
The independent reviewer found no backend correctness issue and reproduced all
ten legal outcomes with separate Decimal arithmetic. The tiny hand calculation
has remaining times 26 s versus 23 s, giving 3 s excess time.

| Challenge v1 | Legal remaining times (seconds)                          |
| ------------ | -------------------------------------------------------- |
| Closing laps | Hard 481.000; soft 483.800; medium 484.000; stay 500.500 |
| Stint choice | Medium 368.400; soft 369.000; hard 375.600; stay 385.000 |
| Final stint  | Hard 108.900; medium 109.200; stay/soft unavailable      |

These are deterministic local comparisons under the disclosed continuation, not
global optima or real F1 predictions. Parameter-intervention tests show that pit
loss, warm-up and degradation affect the intended tradeoffs. Parent/sibling
histories and observations remain unchanged by evaluated or rejected actions.

Frontend source review found no substantive issue in server-derived scores,
original-result preservation, stale-request guards, duplicate submission handling,
or versioned local history. Browser inspection found joined words in the mobile
rail heading/intro when the desktop line break was hidden. Explicit whitespace
fixes it; the browser suite now checks the rendered text on both screen sizes.

### F0.5 verification evidence — 2026-10-03

| Check                                                                                               | Observed result                                              |
| --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `.venv-api/bin/python -m pytest -q tests apps/api/tests`                                            | 250 passed (203 core + 47 API/challenge)                     |
| Same suite in a separate Python 3.11.14 environment                                                 | 250 passed                                                   |
| `.venv-api/bin/ruff check .` / `ruff format --check .`                                              | Passed; 39 Python files formatted                            |
| `npm run lint` / `npm run typecheck` in `web/`                                                      | Passed                                                       |
| `npm run build`                                                                                     | Passed; Next.js production build                             |
| `npm run test:e2e`                                                                                  | 18 passed, Chromium desktop and mobile                       |
| All three challenge calls, playback/replay, rewind/fork, history reload                             | Passed against real API and production application           |
| Keyboard focus/Space/Enter, error/retry, duplicate clicks, stale responses, blocked/corrupt history | Passed                                                       |
| Desktop/mobile briefing and comparison screenshots                                                  | Inspected; mobile text spacing fixed and regression verified |
| Original comparison, optimize, replay, snapshot, restore, fork CLI demos                            | Passed; F0b results unchanged                                |
| `npm audit --omit=dev`                                                                              | Zero production vulnerabilities                              |

The isolated core Python dependency setup remains unchanged. Browser artifacts
are generated under `web/test-results` and `web/playwright-report`; they stay out
of Git and are uploaded by the new arena CI job. The existing Python 3.11/3.14
core jobs and CLI checks remain.

Independent read-only review covered scoring, state isolation, strict request
boundaries, pre-submit redaction, asynchronous UI state, and the completed user
flow. The reviewer reran 47 API tests, checked all ten outcomes with Decimal
arithmetic, and inspected fresh desktop/mobile screenshots for all challenges.
No substantive production finding remains. A test-only ambiguous paragraph
locator was corrected, and all 18 browser cases then passed.

F0.5 implementation commit
[`afab41c7fc2642f184ffc1e0e938e7387d43cf54`](https://github.com/Su760/f1-pitwall/commit/afab41c7fc2642f184ffc1e0e938e7387d43cf54)
was pushed to existing `main` without force-push. Its
[GitHub Actions run 37108789273](https://github.com/Su760/f1-pitwall/actions/runs/37108789273)
passed all three jobs: core Python 3.11 and 3.14 (203 tests each, lint, packaging,
CLI demos), and the arena job (47 API tests, pinned install, lint/typecheck/build,
18 production browser tests, uploaded evidence). This documentation follow-up
records that result; the final handoff reports its own commit and CI separately.
The approved spec and engine are unchanged, and the original untracked spec
remains local. F0.5 is complete and ready for independent use/review.

## F0a and F0b — implemented and locally verified

F0a supplies the deterministic single-car engine, fixed policies, tire/race rules,
synthetic scenario, comparison CLI, and versioned traces. F0b adds exhaustive
schedule optimization, verified action replay, versioned JSON snapshots,
restoration, and independent forks. The runtime still uses only the standard
library. The physical model and scenario parameters are unchanged.

Reviewed F0a reference: `68b99c5d5dd79d470497ab8a8c942854503eecfb`, with 80 tests
and passing GitHub Actions on Python 3.11 and 3.14. F0b builds on that history.
The approved version-2.1 [spec](project-spec.md) remains unchanged and byte-identical
to the original local download; historical checkpoint statements are preserved.

## F0b verification evidence — 2026-10-02

| Check                                                                   | Observed result                                            |
| ----------------------------------------------------------------------- | ---------------------------------------------------------- |
| `python -m pytest -q`, Python 3.14.2 editable install                   | 203 passed                                                 |
| Same suite, Python 3.11.14 separate environment / installed wheel       | 203 passed                                                 |
| Optimizer tests                                                         | 30 passed                                                  |
| Replay and snapshot/fork tests                                          | 82 passed                                                  |
| New CLI tests plus existing trace/CLI tests                             | 29 passed                                                  |
| `ruff check .`                                                          | Passed                                                     |
| `ruff format --check .`                                                 | Passed                                                     |
| `python -m pip wheel --no-build-isolation --no-deps . --wheel-dir dist` | Passed                                                     |
| Hash-locked setup and wheel install in separate Python 3.11 environment | Passed                                                     |
| Comparison, optimization, replay, snapshot, restore, fork CLI demos     | Passed                                                     |
| Restored complete trace versus original JSON document                   | Identical                                                  |
| Independent read-only engine/optimizer/replay/test review               | No substantive findings                                    |
| Independent action-tree reference versus optimizer                      | Counts and full rankings match for 60 small configurations |

Tests preserve the 80 F0a checks and add 123 focused F0b cases. They verify exact
search counts/ranking, resource rejection before scoring, interruption without a
completed search, same-compound replacement, alternative starting compounds, and
a tiny hand-calculated optimum. Replay checks saved actions rather than executing
FixedSchedule; corrupt components, metadata, types, versions, boundaries, final
results, duplicate fields, and nonfinite values are rejected.

Restoration tests cover reset, before a pit, after a pit, before the final lap,
and finish. Identical continuation reproduces the whole trace. Parent/two-child
fork tests compare state, observations, elapsed time and history after changed
and rejected actions. Invented but superficially legal state is rejected by
prefix replay. No substantive review finding required a production-code fix.

## Verified synthetic results

```text
529 candidates; 462 legal schedules (0 zero-stop, 22 one-stop, 440 two-stop)
Rank | Total elapsed (s) | Gap (s) | Pit after lap:compound
1 | 1113.550 | 0.000 | 5:medium
2 | 1113.850 | 0.300 | 6:medium
3 | 1114.500 | 0.950 | 4:medium
4 | 1115.050 | 1.500 | 5:hard
5 | 1115.300 | 1.750 | 4:hard
```

The unique winner improves the existing one-stop baseline by **0.300 s**.
The original comparison remains **1113.850 s** (medium after 6) versus
**1124.700 s** (medium after 4, soft after 8), both legal. A boundary-4 restoration
with the original continuation reproduces 1113.850 s and the entire trace;
a deliberate fork to medium after 5 yields 1113.550 s without changing the parent.
The separate four-lap arithmetic fixture has six legal totals
`[406, 408, 415, 417, 418, 420]` seconds, reproduced by the search.

These results are derived from the engine and hand calculations, not a claim of
historical realism. Exact setup, checks, and runnable commands are in the
[README](../README.md); conventions and independent accounting are in
[model assumptions](model-assumptions.md).

## Publication and CI

The F0b implementation checkpoint is
[`625d00e5ed081b7968b8f9d3885cbf0e51e6fa14`](https://github.com/Su760/f1-pitwall/commit/625d00e5ed081b7968b8f9d3885cbf0e51e6fa14),
pushed successfully to existing `main` on `Su760/f1-pitwall` without reset or
force-push. Generated traces, virtual environments, caches,
credentials, and the original spec download remain outside the commit.
The [F0 workflow](../.github/workflows/ci.yml) now includes the F0b CLI demos
alongside tests, Ruff, and packaging on Python 3.11 and 3.14.

The implementation's [GitHub Actions run 37097220137](https://github.com/Su760/f1-pitwall/actions/runs/37097220137)
passed on Python 3.11 and 3.14, with 203 tests in each job and all packaging,
lint/format, comparison, and F0b demo steps successful. This documentation-only
follow-up records that observed outcome and closes the task checklist. The final
handoff identifies its own commit and hosted run separately. F0b is ready for
independent review; no substantive correctness finding remains from this pass.

## Remaining limitations

- Arena scores compare one call followed by the disclosed stay-out continuation;
  they are not whole-race optimality claims. Three fixed version-1 challenges are
  supported. Playback is lap-level, and local history is browser-only practice.
- Browser automation covered Chromium at desktop and iPhone-sized viewports,
  not physical devices or Safari/Firefox. The service is for local use; deployment,
  authentication and multi-user abuse controls remain deferred.
- Full npm audit reports five development-tool entries for one unpatched `braces`
  advisory in the Next lint dependency chain; production audit is clean. See
  [the documented upstream limitation](decisions.md#2026-10-03--isolated-web-tooling-and-reproducible-browser-checks).
- Parameters are synthetic, deterministic, and uncalibrated; there is no traffic,
  weather, uncertainty, or historical rule fidelity.
- Search is bounded by explicit candidate/lap budgets and optimizes only the
  configured starting compound. It is a reference for small fixed models.
- Exact replay supports trace schema 1 and the current model only. It verifies
  consistency, not artifact authenticity; changed inputs require a new run.
- Snapshots store full history and restore by replay. Fixed policies are stateless;
  future policy memory, random generators, and external processes are not saved.
- Observations remain the minimal fixed-policy interface. No evaluator or
  snapshot data was added to them. JSON output is not crash-atomic.
- The previously diagnosed global Stop-hook formatting fault remains outside
  this repository; no hook was changed or bypassed. Its proposed fix and evidence
  remain in [decisions](decisions.md#2026-10-02--global-stop-hook-diagnosis-unresolved-outside-project).

## Next separately authorized task: 2025 retrospective cohort audit

Audit the proposed 382-row 2025 cohort's source membership, exclusions, control
boundaries, weather alignment and selection bias against the F1.1 acceptance
criteria, keeping the full circuit gate blocked. Deliver provenance and a
suitability decision only. F2 calibration/adaptive strategy, RL, live telemetry,
accounts and deployment remain deferred and require separate authorization.
