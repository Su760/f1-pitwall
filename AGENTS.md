# PitWall Arena repository guidance

Read `tasks/lessons.md`, `tasks/todo.md`, [the approved spec](docs/project-spec.md),
[model assumptions](docs/model-assumptions.md), and [status](docs/status.md).
Inspect Git status and preserve existing work. Work only on the authorized
milestone; F1 requires a separate task. Record corrections in `tasks/lessons.md`.

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
pitwall optimize scenarios/synthetic.json --output traces/optimal.json
pitwall replay traces/optimal.json --scenario scenarios/synthetic.json
```

The F0.5 web stack is separate from the stdlib-only core. See the
[README](README.md#play-the-local-arena) for setup and two-terminal launch commands.
The API environment installs both `requirements-dev.lock` and
`apps/api/requirements.lock` with hashes; web uses `npm ci` in `web/`.

```sh
.venv-api/bin/python -m pytest -q tests apps/api/tests
.venv-api/bin/ruff check .
.venv-api/bin/ruff format --check .
cd web
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Playwright starts the production web server and API itself; ports 3000 and 8000
must be free. Browser reports/screenshots, node_modules, .next, and environments
stay outside Git. Versioned server-owned challenge snapshot fixtures are intended
source inputs and are committed under `apps/api/fixtures`.

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
  tolerances for totals computed in a different addition order. No randomness in F0.
- Replay saved actions through the engine and verify all records. Restore snapshots
  by validated prefix replay; never assign imported state. Fork histories must be
  independent. Keep snapshots and optimizer results outside observations.
- Call search exhaustive only after all candidates within explicit resource limits
  have been evaluated. Rank full-precision times with documented deterministic ties.
- All circuit/tire parameters are synthetic assumptions supplied by configuration.
  Consistency checks do not establish realism. Search optimality applies only to
  the configured deterministic model, rules, and starting compound.
- For the playable arena, follow [the API contract](docs/api-contract.md). Restore
  canonical server fixtures; accept only challenge/version and typed actions.
  Every alternative uses the same frozen continuation and independent history.
  Score excess remaining time against evaluated calls, never claim global
  optimality. Pre-submit responses exclude answers and future traces; relevant
  synthetic assumptions are public and separate from engine Observation.
- Keep original browser results intact when rewinding. All times, cost deltas,
  rankings and chart gaps come from Python; frontend arithmetic only formats or
  positions supplied data. Repeated versioned local attempts are practice.

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
