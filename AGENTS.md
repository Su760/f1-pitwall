# PitWall Arena repository guidance

Read `tasks/lessons.md`, `tasks/todo.md`, [the approved spec](docs/project-spec.md),
[model assumptions](docs/model-assumptions.md), and [status](docs/status.md).
Inspect Git status and preserve existing work. Work only on the authorized
milestone; F0b requires a separate task. Record corrections in `tasks/lessons.md`.

## Setup and checks

Python 3.11+; run from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-build-isolation --no-deps -e .
python -m pytest -q
ruff check .
ruff format --check .
python -m pip wheel --no-build-isolation --no-deps . --wheel-dir dist
pitwall scenarios/synthetic.json --trace-dir traces
```

## Invariants

- Engine I/O stays outside `src/pitwall/engine.py`. Policies receive immutable
  observations and return typed actions; do not expose future events, hidden
  parameters, snapshots, or evaluator state through that interface.
- A pit after lap `k` fits tires for lap `k+1`; its incremental loss occurs once
  on that next interval. No pit before lap 1 and no action after the finish.
- Fresh tire age is zero during calculation, then increments after the lap.
  Starting tires consume a set; each fitted set is consumed once, including
  same-compound changes. Removed sets cannot be reused.
- Respect inventory, stop limits, and mandatory compounds. Mask actions that
  make a legal finish impossible; retain terminal checks. Rejected actions must
  leave state, inventory, elapsed time, and trace unchanged.
- Keep full float precision in state/traces. Round only for display; use tight
  tolerances for totals computed in a different addition order. No randomness in F0a.
- All circuit/tire parameters are synthetic assumptions supplied by configuration.
  Consistency checks do not establish realism or an optimum.

## Workflow

Record a scoped plan in `tasks/todo.md`. Diagnose concrete bugs before editing,
add a focused regression test, and verify visible behavior with the CLI or an
independent calculation. After two unsuccessful fixes, stop patching and revisit
the causal chain. Avoid unrelated refactors and speculative dependencies.

For unfamiliar or changed tooling/APIs, check current official documentation.
Research modeling choices for their milestone; record consequential findings,
primary-source links, and check dates in [decisions](docs/decisions.md). Use an
independent read-only reviewer where available. Update status after each milestone;
report local checks, independent review, remote CI, and tooling issues separately.

Commit/push only when requested. Inspect staged files for credentials, `.env`,
databases, caches, environments, datasets, and generated traces. Use
`<type>: <description>` commits; never force-push or reset unrelated work.
