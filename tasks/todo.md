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
