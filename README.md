# PitWall Arena

F0a: a deterministic, lap-level dry-race simulator for one car on a synthetic
circuit. It compares fixed pit schedules, enforces tire/race rules, and writes
versioned JSON traces. Runtime dependencies: Python's standard library only.

All parameters in `scenarios/synthetic.json` are **synthetic assumptions**, not
historical F1 measurements or calibrated predictions.

## Setup

Python 3.11 or newer. From this repository:

```sh
cd ~/Desktop/F1/Pitwall
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-build-isolation --no-deps -e .
```

The lock file pins development tools, transitive dependencies, and the build
backend with hashes. No global package changes are needed. With uv already
installed, the equivalent setup is:

```sh
uv venv --python 3.14
uv pip sync --require-hashes requirements-dev.lock
uv pip install --no-build-isolation --no-deps -e .
source .venv/bin/activate
```

To deliberately update the development lock (not required for setup):

```sh
uv pip compile pyproject.toml --extra dev --universal --generate-hashes -o requirements-dev.lock
```

## Demo

```sh
pitwall scenarios/synthetic.json --trace-dir traces
```

Observed output for the included 12-lap scenario:

```text
SYNTHETIC assumptions | Synthetic Arena — illustrative assumptions | 12 laps
Strategy | Total elapsed (s) | Pit after laps | Tire stints | Legality
one-stop | 1113.850 | 6 | soft 1-6; medium 7-12 | LEGAL
two-stop | 1124.700 | 4,8 | soft 1-4; medium 5-8; soft 9-12 | LEGAL
Trace (one-stop): traces/01.json
Trace (two-stop): traces/02.json
```

Run one configured strategy, or use the module entry point:

```sh
pitwall scenarios/synthetic.json --strategy one-stop --trace-dir traces/one
python -m pitwall scenarios/synthetic.json --trace-dir traces/module
python -m json.tool traces/01.json
```

Trace names follow the strategy's one-based position in the scenario. Repeating
a command overwrites those trace files with deterministic content. Use a new
`--trace-dir` to keep separate runs. The CLI rejects an output path that resolves
to the input scenario. Invalid scenarios/schedules return an error and exit 2;
the comparison is fully simulated before any traces are written. Filesystem
errors are reported; writing multiple trace files is not a filesystem transaction.

Edit the scenario to change lap count, base pace, pit loss, tire parameters,
starting compound, inventory, rules, or fixed pit boundaries. All configuration
fields are required; unknown/duplicate fields and impossible inputs are rejected.
The supplied arena uses two fresh sets per compound, at most two stops, and at
least two distinct compounds by the finish. A no-stop experiment requires an
explicit rule change to `min_distinct_compounds: 1`.

## Verification

```sh
python -m pytest -q
ruff check .
ruff format --check .
python -m pip wheel --no-build-isolation --no-deps . --wheel-dir dist
pitwall scenarios/synthetic.json --trace-dir traces
```

Tests cover hand-calculated accounting, warm-up/age transitions, capped
degradation, inventory, stop and timing limits, mandatory compounds, immutable
observations, rejected actions without mutation, repeatability, strategy tradeoffs,
strict scenario parsing, CLI errors, trace cumulative/final totals, and preservation
of precision through display rounding. CI runs these checks on Python 3.11 and
3.14. See [GitHub Actions](https://github.com/Su760/f1-pitwall/actions) for remote
results; local verification is recorded separately in [status](docs/status.md).

Tool configuration follows the official [pytest assertions](https://docs.pytest.org/en/stable/how-to/assert.html),
[Ruff configuration](https://docs.astral.sh/ruff/configuration/), and
[uv lock-file](https://docs.astral.sh/uv/pip/compile/) documentation.

## Code map

| Module                              | Responsibility                                          |
| ----------------------------------- | ------------------------------------------------------- |
| `config.py`                         | Validated immutable physical parameters and arena rules |
| `actions.py`, `observations.py`     | Typed policy interface and action mask                  |
| `state.py`, `engine.py`             | Immutable race state and deterministic lap transitions  |
| `results.py`                        | Lap components, action records, stints, and legality    |
| `policies.py`                       | Fixed schedules through the common policy interface     |
| `scenario.py`, `trace.py`, `cli.py` | JSON input/output and command-line comparison           |

The engine performs no I/O. `Race.observe()` returns policy data;
`Race.step(Action...)` calculates exactly one lap. `simulate(config, policy)`
runs any object implementing `choose_action(observation) -> Action` to completion.

The complete approved [project spec](docs/project-spec.md) is version 2.1. See
[model assumptions](docs/model-assumptions.md) for implemented equations,
[decisions](docs/decisions.md) for rationale and tooling findings, and
[status](docs/status.md) for verification evidence and remaining work.

F0a implements fixed schedules and audit traces. F0b is the next separate task:
exhaustive legal schedule optimization, verified replay, snapshot restoration,
and independent forks. None of those F0b capabilities is implemented yet. Real
data, UI, databases, and learning frameworks remain later milestones.
