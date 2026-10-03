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
