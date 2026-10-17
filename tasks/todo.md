# S2.1 — in progress

See [scoped task/spec](s2-1-comparison.md). Implement comparison of the three
already retained schedules, with engine stints and honest exact-tie labels.
Authorized through verification, scoped commit/push and hosted CI.

# S2 — delivered

See [scoped task](s2-optimization.md) and [spec/evidence](../docs/s2-optimization-spec.md).
Explicit bounded search, complete-result UI and replayable exports are implemented.
327 core/API, 129 historical and 36 desktop/mobile browser cases pass. Independent
backend/client reviews have no outstanding findings. Implementation `4304f43` is
pushed; [CI 39054603883](https://github.com/Su760/f1-pitwall/actions/runs/39054603883)
passes all four jobs. Existing challenges, S1.1 behavior and historical evidence
are preserved. Stop after S2. Proposed next task only: show the existing top-three
schedules side by side, with stints/gaps; no added search scope or calibration.

# S1.1 — delivered

See [scoped plan](s1-1-review.md). User authorizes implementation, verification,
commit/push and hosted CI. Preserve numerical/API/export behavior and historical
evidence. Implementation `34126a8` is pushed; [CI 39012839475](https://github.com/Su760/f1-pitwall/actions/runs/39012839475)
passes all four jobs. 28 browser, 297 core/API and 129 historical tests pass.
The separately authorized S2 milestone is delivered above.

# S1 — synthetic sensitivity lab delivered

See [scoped task](s1-sensitivity-lab.md) and [spec](../docs/sensitivity-lab-spec.md).
Implemented `/lab`, bounded engine/API comparisons, sampled map and offline exports.
297 core/API, 356 core/historical and 24 desktop/mobile browser tests pass.
Independent review and actual downloaded export replay pass. Implementation
`83636f7` is pushed; [CI 39009001641](https://github.com/Su760/f1-pitwall/actions/runs/39009001641)
passes all four jobs. No historical calibration. S1 stops here.

# F1.3 — descriptive report delivered; historical workstream closed

See [completed task](f1-3-descriptive-report.md) and [report](../docs/reports/f1-3-descriptive-report.md).
Open `historical-data/f1-3-a/report.html`: 382 frozen members, 365-row labelled
sensitivity, 19 SVGs and reconciled JSON statistics. Implementation `edd96e6` is
pushed; all four jobs in [CI 38999607994](https://github.com/Su760/f1-pitwall/actions/runs/38999607994) pass.
Calibration is closed for this cohort; the full circuit gate stays blocked.
Propose only a synthetic strategy sensitivity lab with explicitly assumed
parameters. That proposal is now implemented separately as S1 above; no further
historical audit or RL starts.

# F1.2 — cohort audit complete; calibration unsupported

See [the completed F1.2 task](f1-2-cohort-audit.md) and
[cohort audit](../docs/reports/f1-2-cohort-audit.md). Reproduced 382 members plus
747 distinct exclusions from unchanged v2; full gate remains blocked. Separate
age/lap/compound/driver effects are unidentified; calibration is unsupported.
Commit `65db62d41d9ad24b32e3acb3f5dec78902f9a95a` is pushed and all four jobs in
[CI 38998554927](https://github.com/Su760/f1-pitwall/actions/runs/38998554927) pass.
Stop after F1.2. The single proposed next task is a bounded descriptive report
of these frozen members; no fitting, calibration or RL is authorized.

# F1.1 — quality repair complete; historical gate still blocked

See [the completed F1.1 task](f1-1-quality-readiness.md) and
[readiness review](../docs/reports/f1-1-readiness-review.md). Implementation commit
`880f11aaf0db603676dc877dbe432abf5901b0da` is pushed; all four jobs in
[CI 38997040963](https://github.com/Su760/f1-pitwall/actions/runs/38997040963) passed.
The full data gate remains blocked. Stop after F1.1; the proposed cohort audit
requires separate authorization and does not include F2 fitting.

# Task 1 / F0a — deterministic dry-race simulator

Scope: Python engine, fixed schedules, CLI, synthetic scenario, versioned trace,
tests, dependency setup, CI, and documentation. No optimization, restoration,
data ingestion, web UI, databases, or training.

- [x] Confirm empty workspace, read applicable instructions, initialize Git and origin.
- [x] Write behavioral tests and reproducible Python development setup.
- [x] Implement typed configuration, state, observations, actions, results, engine,
      and fixed one-/two-stop policies.
- [x] Implement scenario loading, CLI comparison, and versioned JSON traces.
- [x] Document model conventions, setup/demo commands, F0a status, and next F0b work.
- [x] Run full tests, lint/format checks, packaging check, and CLI demo; inspect results.

Design: each step chooses an action at the current completed-lap boundary and
calculates exactly one subsequent lap. Initial step permits stay-out only. State
and observations are immutable. The mask checks local legality and whether enough
future boundaries, stops, and unused compounds remain for a legal finish. Linear
degradation is capped; warm-up is an explicit cost by tire age; no randomness.

Execution follows the explicit request to complete and verify F0a in this turn.

Verified: 79 tests pass on Python 3.14 and 3.11 (the latter from an installed
wheel), lint/format pass, pip setup and wheel build pass, CLI and trace inspection
confirm the documented results. Hosted CI is configured but not run. No commit,
push, or F0b implementation performed.

# F0a verification, documentation, and GitHub handoff

Authorized scope: inspect and verify F0a, reconcile the supplied specification,
update project guidance/documentation, diagnose the stop hook, then commit and
push a reviewable checkpoint using existing remote history. No F0b implementation.

- [x] Read/reconcile the downloaded spec and inspect local/remote Git history.
- [x] Run baseline checks, independently check small-race accounting, and obtain
      a read-only engine/test review; fix only confirmed substantive issues.
- [x] Diagnose the stop hook from installed Codex contract, configuration, and logs;
      preserve checks and avoid global/plugin changes.
- [x] Align AGENTS.md, README, assumptions, status, and decisions with verified facts.
- [x] Re-run affected/full checks and demo; prepare intended files for the authorized
      checkpoint. Publication evidence (commit, push, hosted CI) is reported in the
      final handoff and linked GitHub Actions runs.

Final local evidence: 80 tests on Python 3.14 and 3.11, lint/format, locked setup,
wheel build/install, and CLI demo pass. Independent reviewer found no engine bug;
one precision test and existing trace-total assertions address the concrete gap.
Global Stop-hook formatting fault reproduced; proposed fix documented, not applied.

# F0b — exhaustive optimization, verified replay, snapshots, and forks

Authorized: implement and verify F0b, independent review, commit/push. Preserve
unrelated work and the untracked original spec. No UI, historical data, or RL.

Interfaces/ownership agreed before parallel implementation:

- Optimizer module: accepts RaceConfig and explicit search limits; enumerate all
  stop counts/boundaries/compound sequences; score through simulate; return typed
  ranked schedules/results, candidate/legal counts, completion and tie convention.
- Replay/restore modules: retain version-1 traces; validate JSON/types/versions,
  execute saved actions, compare all recorded fields; snapshots retain config,
  state and action/lap prefix, restored only through validated replay. Expose
  replay_document/load_trace, snapshot_document/save_snapshot/load_snapshot,
  restore_snapshot and fork. No imported Python objects or observation changes.
- Root: CLI integration, end-to-end tests, README, AGENTS, assumptions, decisions,
  status, CI, final verification/publication. The approved spec stays unchanged.

- [x] Implement bounded exhaustive optimizer and independent known-answer tests.
- [x] Implement strict action replay, versioned snapshots, restoration, and forks.
- [x] Preserve comparison CLI and add optimize/replay/snapshot/restore/fork commands.
- [x] Run focused and full checks; exercise CLI demos and obtain read-only review.
- [x] Resolve substantive findings; update assumptions, decisions, README and status.
- [x] Inspect/stage intended changes, commit/push, and report exact hosted CI result.

Snapshot policy memory: existing FixedSchedule policies are stateless; only those
continuations are supported by CLI. Intentional branching creates a new trace;
changing an existing trace is a verification failure, not a replay feature.

Local evidence: 203 tests pass on Python 3.14.2 and Python 3.11.14 (separate
installed wheel); Ruff lint/format and wheel packaging pass. CLI derives 529
candidates / 462 legal schedules, winner medium after lap 5 at 1113.550 s.
Replay/restore/fork demos pass, including complete original/restored trace equality.
Read-only reviewer found no substantive bug; independent action-tree enumeration
matched counts and full rankings across 60 small configurations. No F0.5 work.

Publication: implementation commit `625d00e5ed081b7968b8f9d3885cbf0e51e6fa14`
pushed to `origin/main`; [hosted CI run 37097220137](https://github.com/Su760/f1-pitwall/actions/runs/37097220137)
passed on Python 3.11 and 3.14 (203 tests each, checks and all CLI demos). This
documentation-only follow-up records the result; the final handoff supplies its
commit/push/CI outcome. Original downloaded spec and generated files remain local.

# F0.5 — playable synthetic arena

Authorized implementation, verification, documentation and commit/push. Baseline
3fa643dfa7b637a61247db4a2a0adbc4dfa7851e; preserve the untracked original spec.
The user explicitly directs implementation after recording the contract/plan.

Scoped files/ownership:

- Root: docs/api-contract.md; README, AGENTS, assumptions, decisions, status,
  tasks/todo; .gitignore; .github/workflows/ci.yml; web/playwright.config.ts and
  web/tests/** for end-to-end verification. Approved spec/core invariants unchanged.
- Backend agent: apps/api/** (FastAPI app, stdlib challenge evaluator, server-owned
  versioned snapshot fixtures, focused tests, separate pinned Python web lock).
- Frontend agent: web/** except root-owned Playwright config/tests (Next.js,
  TypeScript, CSS, public assets, exact package pins and npm lock).
- Independent reviewer: read-only scoring/isolation/API and complete user-flow review.

Design: three server-owned versioned challenges, one submitted action, then frozen
stay-out continuation for every legal alternative. Reconstruct and fork trusted
snapshots server-side. Public situation and assumptions are separate from unchanged
engine Observation; no pre-submit rankings or future traces. Score is excess
remaining seconds within this disclosed deterministic comparison. Same-origin
Next.js proxy to local FastAPI; stateless API, browser-only version-keyed history.

Visual plan: graphite timing-board base, warm white text, ice-blue information,
red soft/yellow medium/white hard with explicit S/M/H labels. Distinct display
and numeric typography. Challenge rail + broad decision board on desktop; stacked
briefing/call/results on mobile. Playback shows lap-level timing, not vehicle
physics. Rewind retains the first result and compares one independent alternative.

- [x] Record API contract; verify official tooling docs and coordinate ownership.
- [x] Implement fixtures, bounded challenge evaluation, strict API, and focused tests.
- [x] Implement challenge/decision/playback/debrief/fork/history interface.
- [x] Run core/API checks, frontend lint/type/build, and real Playwright flows.
- [x] Inspect desktop/mobile screenshots and keyboard/error/retry behavior.
- [x] Obtain independent review and resolve substantive findings.
- [x] Update documentation/evidence, inspect/stage, commit/push and check hosted CI.

Boundaries: no historical data, RL, accounts, databases, live telemetry, deployment,
optimizer endpoint, arbitrary client configuration/snapshots, or global hook changes.

Local evidence (2026-10-03): 250 Python tests on both 3.14.2 and 3.11.14, Ruff
lint/format, TypeScript, ESLint, production build, and 18 real desktop/mobile
Playwright cases pass. All three challenges and independent rewind comparisons
are playable; keyboard, errors/retry, duplicate/stale requests, and local history
are covered. Desktop/mobile screenshots were inspected by root and reviewer.
Mobile heading/intro whitespace was corrected and regression-tested. Independent
review found no substantive scoring, isolation, API, or completed-flow defect;
separate Decimal arithmetic matched all ten legal outcomes. Existing CLI demos
retain their F0b results. Production npm audit is clean; one unpatched advisory
in the development lint dependency chain is recorded in decisions/status.

Publication: implementation commit `afab41c7fc2642f184ffc1e0e938e7387d43cf54`
pushed to `origin/main`. [CI run 37108789273](https://github.com/Su760/f1-pitwall/actions/runs/37108789273)
passed both core Python jobs and the API/production-browser arena job, including
all 18 browser cases. This documentation-only follow-up records the observed
result; its final commit and CI are reported in the handoff. Generated artifacts
and the original spec download remain outside Git. F0.5 stops here; F1 is separate.

# F1 — historical ingestion and one-circuit quality audit

Authorized 2026-10-13: implementation, verification, documentation, commit/push;
record plan then execute without a planning approval stop. Reviewed baseline
1c4b08177fc72306209d04ad0b04bb8815815b2a. Preserve existing web/next-env.d.ts
modification and untracked original spec. Approved docs/project-spec.md unchanged.

Goal: auditable, reproducible OpenF1 Bahrain 2023–2025 Race ingestion and honest
purpose-specific suitability evidence. No F2 fitting or changes to the arena.
Architecture: separate pitwall_historical package; stdlib HTTP/cache/quality,
explicit nullable Arrow schemas and separate hash-locked PyArrow dependency.
Contract: docs/data-contract.md; no invented session IDs or dry/completeness claims.

Files and ownership:

- Root: docs/data-contract.md; historical/config.json, requirements.in/lock;
  src/pitwall_historical/{**init**,**main**,schema,normalize}.py;
  historical/tests/test_normalize.py, test_historical_cli.py and conftest.py;
  historical/**init**.py and historical/tests/**init**.py (fixture namespace);
  pyproject.toml, .gitignore,
  .github/workflows/ci.yml; README, AGENTS, assumptions, decisions, status, todo.
- Ingestion agent: src/pitwall_historical/{client,cache}.py;
  historical/tests/test_client.py and test_cache.py.
- Quality agent: src/pitwall_historical/quality.py (and quality helpers if needed);
  historical/tests/test_quality.py, synthetic fixture helpers local to that suite.
- Independent reviewer: read-only contract/joins/exclusions/provenance/report claims.
- Generated evidence: ignored historical-data/ and .venv-historical/ only.

Review focus: null versus absent; duplicate versus conflicting natural keys;
retirees/DNS/lapped cars and unknown tails; stale/future weather and unresolved
control intervals; partial downloads/corrupt or mismatched cache provenance.
Each owner adds focused offline regression fixtures for these boundaries.

- [x] Establish dated source contract, schemas/config and team interfaces.
- [x] Implement bounded client and immutable complete/partial cache; offline tests.
- [x] Implement row-preserving quality flags, joins, coverage, exclusions/readiness.
- [x] Integrate typed Parquet/offline CLI, provenance, locked dependencies and CI.
- [x] Run actual bounded source import; rebuild twice offline and compare hashes.
- [x] Independently review and resolve substantive findings with regression tests.
- [x] Verify preserved core/API/arena and relevant packaging/lint checks.
- [x] Record identities, coverage, readiness/blockers and exact reproduction commands.
- [x] Inspect diff/staging, commit/push scoped changes and verify pushed-commit CI.

F1 local evidence: 100 offline historical tests, 203 preserved core tests (303
combined and from final installed wheel), 250 core/API tests, 18 production-browser
cases, Ruff and packaging pass. Initial combined-suite fixture import collision
was fixed by namespacing historical tests; default browser launch hit existing
services and passed using a temporary 3001 configuration without stopping them.
Independent review findings were regression-tested and final scoped review approved.

Actual OpenF1 snapshot is partial: 2023 session 7953 pit returns HTTP404; sessions
9472/10014 otherwise downloaded completely. Circuit 63/Sakhir candidate gate is
blocked; 2025 driver 27 completed-lap result is null. Two real snapshots retain
identical hashes for all 27 responses. Final two offline builds preserve all 3,316
lap rows and are byte-identical across 12 files. Exact identities, counts, caveats,
hashes and reproduction commands are in docs/status.md. No F2 work performed.

Publication: implementation commit `496f02ef3609ce90c7a390dff6da4c66c666aed0`
pushed to origin/main without force. [CI run 38441425578](https://github.com/Su760/f1-pitwall/actions/runs/38441425578)
passed all four jobs: historical, core Python 3.11/3.14 and playable arena.
This documentation-only follow-up records that verified outcome; its exact
commit/CI are supplied in the final handoff. Source readiness remains limited
and the circuit quality gate blocked; CI does not certify historical completeness.
