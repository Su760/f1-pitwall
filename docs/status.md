# PitWall Arena status

## F0a — verified and ready for independent review

F0a includes the deterministic single-car engine, soft/medium/hard tire model,
fixed schedules, CLI comparison, versioned audit traces, synthetic scenario,
configuration validation, legality mask, and terminal rule checks. The runtime
uses only the standard library. No F0b feature has been implemented.

The approved version-2.1 [spec](project-spec.md) is copied in full from the root
`PitWall-Arena-Project-Spec (1).md` download; the original remains untouched.
The initial spec's October 2 checkpoint is historical; this status records the
subsequent verification. [Decisions](decisions.md) records provenance and rationale.

## Verification evidence — 2026-10-02

| Check | Result |
| --- | --- |
| Baseline `python -m pytest -q` | 79 passed |
| Final `python -m pytest -q`, Python 3.14.2 editable install | 80 passed |
| Final tests, Python 3.11.14 separate environment / installed wheel | 80 passed |
| `ruff check .` | Passed |
| `ruff format --check .` | Passed |
| Hash-locked pip setup and editable install from README | Passed |
| `python -m pip wheel --no-build-isolation --no-deps . --wheel-dir dist` | Passed |
| CLI demo and JSON audit | Both legal; totals unchanged |
| Independent read-only source/test review | No confirmed engine correctness bugs |
| Review of focused trace-test additions | 18 trace/CLI tests passed; no new findings |

Only test coverage changed: the existing trace test now checks cumulative/final
elapsed time, and a new two-lap case confirms full precision survives display
rounding. Production simulator code was preserved. Existing tests cover boundary
and tire indexing, single pit charging, same-compound sets, stop and inventory
limits, mandatory compounds, impossible/nonfinite inputs, atomic rejection, and
no post-finish action. Repeated identical CLI runs retain identical trace bytes.

Independent hand accounting: intervals `[81, 81, 88.6, 80.7, 80.8]` total
**412.1 s**, matching the engine with a pit after lap 2. The full calculation is
in [model assumptions](model-assumptions.md#independent-accounting-check-2026-10-02).
The demo pit after lap 6 leaves soft tires on lap 6, then fits medium at age zero
for lap 7 and charges 18 s once on that interval.

```text
Strategy | Total elapsed (s) | Pit after laps | Tire stints | Legality
one-stop | 1113.850 | 6 | soft 1-6; medium 7-12 | LEGAL
two-stop | 1124.700 | 4,8 | soft 1-4; medium 5-8; soft 9-12 | LEGAL
```

Run `pitwall scenarios/synthetic.json --trace-dir traces` after the
[README setup](../README.md#setup). Generated traces stay outside Git.
The 10.850 s difference compares these two schedules only, not an optimum.

## GitHub checkpoint and CI

Local `main` had no commits, and `git ls-remote origin` plus GitHub repository
metadata confirmed an empty remote before publication. The authorized handoff
publishes an initial checkpoint to `Su760/f1-pitwall` on `main`, without resets or
force-pushes. Only intended source, tests, scenario, configuration, lockfile, and
project documentation are staged; the downloaded original spec is preserved
locally outside the canonical committed copy.

The [F0a workflow](../.github/workflows/ci.yml) runs on Python 3.11 and 3.14.
Both action references were verified to exist. Local results above do not imply
hosted success: use the exact commit/push result in the handoff and the
[GitHub Actions run](https://github.com/Su760/f1-pitwall/actions) for remote status.
At preparation of this checkpoint, hosted CI had not yet run.

## Separate tooling issue and limitations

The global Stop-hook output bug remains outside this repository. Its echo-only
command returned plain text with exit 0, violating the installed Codex 0.160.0
contract. The proposed formatting-only fix preserves the reminder as JSON
`systemMessage`. No global/plugin hooks were changed or bypassed. Original-event
logs were unavailable; the active command reproduces the fault. See the
[diagnosis](decisions.md#2026-10-02--global-stop-hook-diagnosis-unresolved-outside-project).
This is separate from simulator correctness and test results.

Parameters are assumed, not calibrated; no historical rule fidelity or real-race
predictive performance is claimed. Traces are audit records, not restorable
snapshots. The observation payload is the minimal F0a fixed-policy interface;
planned pace estimates/history and policy memory are not implemented. Multi-file
trace output is not a filesystem transaction. No known F0a engine correctness
finding remains from this review.

## Next separate task: F0b (not started)

1. Exhaustive legal schedule optimization, with a tiny independently calculated
   optimum and deterministic tie handling.
2. Verified replay of versioned saved actions with incompatible inputs rejected.
3. Snapshot restoration and continuation that reproduce the original trace.
4. Independent forks that cannot mutate their parent or sibling states.

F0b completes the remaining F0 gate. F0.5 playable challenges follow afterward.
Historical data/calibration, uncertainty, UI, databases, Gymnasium, PyTorch, and
training remain later milestones. This verification pass stops at F0a.
