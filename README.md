# PitWall Arena

F0: a deterministic, lap-level dry-race simulator for one car on a synthetic
circuit. It compares and exhaustively optimizes fixed pit schedules, verifies
saved traces, restores snapshots, and forks independent continuations. Runtime
dependencies: Python's standard library only.

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

## Exhaustive optimization

```sh
pitwall optimize scenarios/synthetic.json --top 5 --output traces/optimal.json
pitwall replay traces/optimal.json --scenario scenarios/synthetic.json
```

Verified result, derived by evaluating the included scenario:

```text
COMPLETE exhaustive search | 529 candidates; 462 legal | SYNTHETIC assumptions
0 stops: 0 legal
1 stops: 22 legal
2 stops: 440 legal
Rank | Total elapsed (s) | Gap (s) | Pit after lap:compound
1 | 1113.550 | 0.000 | 5:medium
2 | 1113.850 | 0.300 | 6:medium
3 | 1114.500 | 0.950 | 4:medium
4 | 1115.050 | 1.500 | 5:hard
5 | 1115.300 | 1.750 | 4:hard
Baseline one-stop: 0.300 s improvement
Baseline two-stop: 11.150 s improvement
Best trace: traces/optimal.json
```

Search keeps the configured starting compound and evaluates every permitted stop
count, increasing boundary combination, and compound sequence, including fresh
same-compound sets. The engine scores candidates and rejects illegal schedules.
`--top` only limits displayed/returned alternatives; it never truncates the search.
Exact ties use fewer stops, then earlier boundary tuples, then compound order
soft/medium/hard. Rounding is display-only.

Defaults permit at most **100,000 candidates** and **2,000,000 potential lap
evaluations** (candidates × laps). A larger space is rejected before scoring.
Explicitly change these operational budgets with `--max-candidates` and
`--max-lap-evaluations`; larger values can be expensive. Interrupted or unsupported
searches do not return a completed exhaustive result. The optimum is for this
synthetic deterministic model, not a real-race prediction.

## Replay, restore, and branch

After running the comparison demo above:

```sh
pitwall replay traces/01.json --scenario scenarios/synthetic.json
pitwall snapshot traces/01.json --after-lap 4 --output traces/boundary4.json
pitwall restore traces/boundary4.json --pit 6:medium --name one-stop --output traces/restored.json
pitwall fork traces/boundary4.json --pit 5:medium --name earlier-stop --output traces/forked.json
pitwall replay traces/restored.json --scenario scenarios/synthetic.json
pitwall replay traces/forked.json --scenario scenarios/synthetic.json
```

Restoration yields **1113.850 s**, with a complete trace identical to the original
when the same strategy name is supplied. The fork yields **1113.550 s** and leaves
the parent at boundary 4. A pit after lap 5 equips the car for lap 6.

The `snapshot` command verifies a complete trace, then saves its prefix at any
boundary from reset (0) through finish. `restore` resumes that saved boundary;
`fork` restores the parent and creates an independent child before continuing.
Repeat `--pit AFTER_LAP:COMPOUND` in increasing order for remaining decisions.
Only future stops are supplied, including a stop at the current boundary if legal;
omitted decisions stay out. Past decisions are preserved. `--scenario` is optional
for replay/snapshot/restore/fork and, when present, requires matching configuration.
`--name` labels the new complete trace, not the snapshot's policy memory.

Existing F0a version-1 traces are supported without reinterpretation. Verification
executes **every saved action** and checks every lap component, cumulative time,
stint, and result. It rejects duplicate/unknown fields, wrong types, nonfinite
numbers, illegal actions, inconsistent records, and unsupported schema/model
versions. Error paths identify the failing record. Editing records fails replay;
an intentional fork produces a separate valid run.

Snapshots use versioned JSON and validated prefix replay, never arbitrary Python
object deserialization. Fixed policies are stateless; policy memory for future
stateful policies is not captured. Python APIs are in `pitwall.replay` and
`pitwall.snapshots`; `fork(race)` permits multiple independent in-memory children.
CLI artifact commands refuse to overwrite their input; use distinct output paths.
Other existing output files can be overwritten. Writes are not crash-atomic.

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
of precision through display rounding. F0b adds exhaustive counts and independent
known-answer optima, strict replay corruption checks, restoration at five boundary
types, and parent/sibling independence under valid and rejected actions. CI runs
the tests, checks, and CLI demos on Python 3.11 and 3.14. See
[GitHub Actions](https://github.com/Su760/f1-pitwall/actions) for remote
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
| `optimizer.py`                      | Bounded exhaustive search and deterministic ranking     |
| `replay.py`, `serialization.py`     | Strict JSON loading and action-by-action verification   |
| `snapshots.py`                      | Verified restoration and independent forks              |
| `scenario.py`, `trace.py`, `cli.py` | Scenario/trace I/O and CLI commands                     |

The engine performs no I/O. `Race.observe()` returns policy data;
`Race.step(Action...)` calculates exactly one lap. `simulate(config, policy)`
runs any object implementing `choose_action(observation) -> Action` to completion.

The complete approved [project spec](docs/project-spec.md) is version 2.1. See
[model assumptions](docs/model-assumptions.md) for implemented equations,
[decisions](docs/decisions.md) for rationale and tooling findings, and
[status](docs/status.md) for verification evidence and remaining work.

F0a and F0b are implemented. Next is **F0.5**: a minimal playable synthetic arena,
three pit-call challenges, debriefs, and a user-facing fork comparison. No UI,
historical data, databases, uncertainty model, or learning framework is included.
