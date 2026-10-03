# F0 model assumptions and rule conventions

This document describes implemented F0a, F0b, and F0.5 behavior under the approved
[specification](project-spec.md). The spec's later mechanisms are planned;
see [status](status.md) and [decisions](decisions.md) for the milestone boundary.

## Synthetic model

One controlled car drives a constant synthetic dry circuit. Every physical
parameter in `scenarios/synthetic.json` is an illustrative assumption. There is
no noise, seed, traffic, overtaking, fuel burn, weather, safety car, tire failure,
driver variance, or calibration to a historical event. A tire can complete any
remaining number of laps; degradation plateaus at its configured cap.

For lap `l`, compound `c`, and tire age `a` (completed laps on that set **before**
this lap):

```text
degradation(c, a) = min(degradation_cap_s[c], degradation_s_per_lap[c] * a)
warmup(c, a)      = warmup_s[c][a] if that entry exists, otherwise 0
pit(l)           = pit_loss_s if a pit was chosen after lap l-1, otherwise 0
lap_time_s(l)    = base_lap_time_s + pace_offset_s[c]
                   + degradation(c, a) + warmup(c, a) + pit(l)
total_elapsed_s  = sum(lap_time_s(l) for all completed laps)
```

`pace_offset_s` may be negative; the base plus offset must remain positive.
Degradation slopes, caps, warm-up costs, and pit loss are finite and nonnegative.
Times are seconds; degradation slope is seconds of lap-time penalty per completed
tire lap; ages, lap counts, and pit boundaries are integers. Boolean values are
not accepted as numbers. NaN, infinity, and parameters whose race-time upper bound
overflows are rejected.

The initial scenario has 12 laps, base pace 90 s/lap, and incremental pit loss
18 s per stop:

| Compound | Pace offset (s) | Degradation (s / tire lap) | Cap (s) | Warm-up costs at ages 0, 1 (s) | Fresh sets |
| -------- | --------------: | -------------------------: | ------: | ------------------------------ | ---------: |
| Soft     |            -1.0 |                       0.80 |     6.0 | 1.0, 0.3                       |          2 |
| Medium   |             0.0 |                       0.45 |     4.0 | 1.4, 0.4                       |          2 |
| Hard     |             0.7 |                       0.25 |     3.0 | 2.0, 0.6                       |          2 |

Warm-up is an additive penalty on the first two laps of **every** newly fitted
set, including the starting set. Age 0 has zero degradation. Warm-up and
degradation both apply at age 1; neither replaces the other. An empty warm-up
array explicitly disables warm-up. This is not a thermal tire model.

## Race boundaries, age, and inventory

1. Construction fits the configured starting compound and consumes one fresh set.
   State has zero completed laps and tire age zero. No compound counts as used
   until its first lap is completed.
2. At boundary 0, only `stay_out` is allowed. It runs lap 1 on the starting set.
3. At boundary `k`, after lap `k` and before lap `k+1`, select an action. A pit
   is possible only for `1 <= k < total_laps`.
4. A pit consumes a previously unfitted set, resets age to zero, and adds pit
   loss exactly once to the upcoming lap interval. The previous lap is unchanged.
   There is no separate out-lap multiplier or second pit charge.
5. Calculate the lap with the current age, then increment age by one. Thus a
   state age of 1 after a fresh lap corresponds to a recorded lap age of 0.
6. At the finish every action is masked, including `stay_out`. There is no
   post-finish pit opportunity.

Fitting another fresh set of the same compound is permitted when inventory and
finish feasibility allow it. It starts a new stint, consumes a set and stop, and
incurs warm-up/pit costs; it does not add a distinct compound. Removed sets are
discarded for this simulation and can never be fitted again. Inventory records
**unfitted** sets in `(soft, medium, hard)` order; no per-set identity is needed
without reuse.

The included arena has maximum two stops and requires at least two distinct
compounds actually driven by the finish. Rules and inventory are explicit
configuration fields so experiments can override them. Under the default rules
a no-stop strategy is illegal; “no optional stops” means just one mandatory stop.

## Mask and validation

Mask order is `(stay_out, pit_soft, pit_medium, pit_hard)`. `Observation.allows`
accepts an `Action` enum value. Observations and exposed state use immutable
dataclasses, tuples, and frozensets, so policies cannot mutate the race through
them. The engine requires typed actions; a raw string is rejected.

For each candidate action, the mask first checks timing, remaining inventory,
and the stop limit. It then considers completing the next lap on the candidate
compound. Let:

```text
missing = max(0, required_distinct - distinct_compounds_after_next_lap)
new_available = number of not-yet-used compounds with a remaining fresh set
future_boundaries = total_laps - completed_laps - 1
```

The action is finish-feasible exactly when `missing` is no greater than **each**
of `new_available`, stops remaining after this action, and `future_boundaries`.
This is sufficient for this model: each missing compound requires one future
stop and one lap, and tires have no maximum stint length. No strategy optimization
or recursive search runs inside the mask.

On the final lap, staying out is forbidden if a different compound is still
needed. Spending the final available stop on the current compound is forbidden
when another distinct compound is required, even if many laps remain.

Invalid actions raise `InvalidAction` before changing state, elapsed time,
inventory, or recorded actions/laps. Rejected actions are not appended to the
trace. An independent terminal check also verifies race completion, mandatory
compounds, stop count, valid boundaries, inventory bounds, and consumed-set count.
Calling `Race.result()` before the finish produces an explicitly illegal partial
result rather than claiming success.

Configuration validation rejects an impossible initial finish: too few laps,
too few allowed stops, too few available compounds, or no starting set. Schedule
validation rejects non-integer, duplicate, unordered, pre-start, and finish-or-later
boundaries. Fixed policies never substitute another action to repair a schedule.

## Reproducibility and trace contract

The engine uses Python floating-point arithmetic in a fixed operation order,
without random or clock inputs. Repeated identical inputs on the same runtime
produce identical results and JSON bytes. CLI times are rounded to three decimal
places for display; traces keep full floating-point values. Verification requires
the exact supported model and values; cross-language/future-model approximate
comparisons are not part of the replay contract.

Elapsed time accumulates sequentially without per-lap rounding. A different
summation algorithm may differ by floating-point rounding at the last few bits;
the independent accounting tests use absolute tolerances of 1e-10 seconds for cumulative totals
and 1e-12 seconds for the small precision fixture. Displaying 210.000 s does not
discard a trace value of 210.000246 s.

Each JSON trace contains:

- `trace_version: 1` and `model_version: "f0a-linear-capped-v1"`.
- `configuration`: every model/rule/inventory parameter and starting compound.
- `strategy`: name and ordered fixed pit boundaries/compounds.
- `actions`: every accepted decision, including boundary-0 stay-out, with `after_lap`.
- `laps`: lap number, compound, pre-lap tire age, base pace, offset, degradation,
  warm-up, pit loss, interval time, and cumulative elapsed time.
- `result`: elapsed time, completed laps, pit boundaries, inclusive tire stints,
  legality boolean, and any legality errors.

Action and lap arrays are aligned: action `after_lap: 6` corresponds to the
lap record `lap: 7`. Both sides of the decision boundary are therefore explicit
without changing the version-1 schema. Complete traces and partial snapshots
have distinct schemas.

There are no timestamps, machine paths, or random identifiers in trace contents.
Schema and model versions are separate so a future equation change can be
distinguished from a storage-format change. F0b explicitly supports the original
F0a version-1 trace and model version without changing their meaning. Replay
executes saved actions, not reconstructed policy decisions. It validates exact
versions, configuration, consecutive action boundaries, legal actions, all lap
fields, cumulative time, stints, terminal legality, and final results. Strategy
metadata must describe the same pit decisions as the accepted action history.

JSON objects reject duplicate and unknown fields. Arrays, strings, booleans,
integer counters, and enums must have their expected types. Finite numeric time
values can be integer or floating-point JSON numbers, but never booleans. NaN,
infinity, and overflowing exponent notation are rejected. Values must equal the
engine's repeated calculation exactly: externally rounded/edited records are
not accepted with a tolerance. This differs from independent arithmetic tests
whose summation order may differ.

## Exhaustive search

Let `N` be race laps and `K = min(max_pit_stops, N-1)`. The search space contains
`sum(C(N-1, k) * 3**k for k in 0..K)` candidates. It includes all increasing pit
boundary tuples, all three compounds at each stop (including the current one),
and zero stops. The starting compound stays fixed. Engine simulation and terminal
legality determine which candidates are legal; no alternate scoring formula or
inventory approximation is used.

Default explicit operational limits are 100,000 candidates and 2,000,000 potential
lap evaluations (`candidate_count * N`). Preflight checks both before simulation.
SearchLimits/CLI flags can override them. No truncation or timeout produces an
exhaustive result. Completion is reported only after enumeration ends; interrupted
searches propagate interruption and unsupported searches raise SearchTooLarge.

Full-precision elapsed time orders results. Exact ties use fewer stops, then the
lexicographic boundary tuple, then compound order soft, medium, hard. Only the
requested top `k` full results are retained; all candidates are evaluated. Gaps
are unrounded differences from the winner. The bounded reference search assumes
complete knowledge of this fixed synthetic model and stays outside observations.

For the unchanged 12-lap arena, candidate counts are `1 + 33 + 495 = 529`.
Zero stops cannot satisfy two compounds; each of 11 one-stop boundaries permits
medium or hard, giving 22. Each of 55 two-boundary combinations has eight legal
compound sequences; soft/soft would consume three soft sets, so 440 are legal.
Total: **462**. The unique optimum fits medium after lap 5 at **1113.550 s**.
The after-lap-6 baseline is **0.300 s** slower.

The four-lap independent optimum test uses base 100 s, pit loss 3 s, at most one
stop, soft slope 4 s/lap, medium slope 1 s/lap, hard offset 5 s, and no warm-up.
Caps do not bind. Medium after lap 1 totals `100 + 103 + 101 + 102 = 406 s`.
Medium after 2/3 totals 408/415; hard after 1/2/3 totals 418/417/420. The engine
search reproduces all six legal totals and the unique 406 s winner.

## Snapshots, continuation, and independent forks

Snapshot version 1 stores model version, full configuration, a configuration ID,
current state, all accepted actions/laps from reset, and a partial/final result.
The ID is SHA-256 of sorted, compact JSON containing model version and configuration.
It identifies the exact serialized configuration, not authenticity or a signature.
Optional expected configuration checks reject incompatible callers' inputs.

Restoration always creates a fresh Race and replays the validated action prefix,
then compares every state/result field. It never trusts imported inventory, age,
elapsed time, or terminal legality alone. Reset, pre-pit, post-pit, pre-final-lap,
and finished boundaries are supported. A post-pit step has already completed the
new tire's first lap; there is no separate transient pit-in-progress state.
Cost/storage grow with history length; no arbitrary object serialization is used.

`fork(race)` uses the same validated restoration path and creates independent
action/lap lists. Immutable configuration/state values can safely be shared.
Accepted/rejected actions in one child cannot change the parent or siblings.
An intentional new continuation creates new records; modifying a saved trace
does not bypass replay verification. Observations contain no snapshots, history
serialization, optimizer results, or hidden model parameters.

FixedSchedule policies are stateless. Snapshots do not serialize policy objects
or memory; the caller supplies future actions/policy after restoration. CLI
restore/fork builds a fixed continuation from the remaining `--pit` arguments
and derives complete strategy metadata from actual accepted actions. Reusing
the original name and continuation reproduces the full original trace.

## Independent accounting check (2026-10-02)

A five-lap fixture used base 80.25 s and a 7.5 s pit after lap 2. Soft parameters
were offset -0.5 s, slope 0.75 s/tire-lap, cap 1 s, warm-up `[1.25, 0.5]` s;
hard parameters were offset 0.25 s, slope 0.2 s/tire-lap, cap 0.3 s, warm-up
`[0.6]` s. Both start and pit sets were fresh.

| Lap | Compound / pre-lap age | Hand calculation (s)         | Interval (s) |
| --- | ---------------------- | ---------------------------- | -----------: |
| 1   | soft / 0               | 80.25 - 0.5 + 0 + 1.25       |         81.0 |
| 2   | soft / 1               | 80.25 - 0.5 + 0.75 + 0.5     |         81.0 |
| 3   | hard / 0               | 80.25 + 0.25 + 0 + 0.6 + 7.5 |         88.6 |
| 4   | hard / 1               | 80.25 + 0.25 + 0.2 + 0       |         80.7 |
| 5   | hard / 2               | 80.25 + 0.25 + 0.3 + 0       |         80.8 |

Expected total: **412.1 s**. The engine and separate read-only reviewer reproduced
these intervals and a legal finish. This is an arithmetic check, not calibration.

## F0.5 playable challenge conventions

Three versioned, server-owned synthetic fixtures exercise second-stop cost,
compound choice, and the final compound requirement. Their titles do not reveal
the winning action. Each fixture contains a saved version-1 snapshot with full
history, validated through the existing restoration path. The core model and
Observation dataclass are unchanged. Public assumed pit loss, base pace, tire
curves, warm-up arrays and rules are disclosed separately in the challenge API.

At the fixed decision boundary, the player chooses one engine action. All legal
alternatives fork that same canonical parent and use continuation `stay-out-v1`:
execute that call for the next interval, then stay out to finish. Fixtures are
chosen so this continuation is legal for every action in the original engine
mask. The final-compound fixture uses the boundary before the final lap, so
staying out or fitting the already-used compound is unavailable; distinct
available compounds remain meaningful legal alternatives.

```text
remaining_s(action) = finish_elapsed_s(action) - boundary_elapsed_s
score_s(action) = remaining_s(action) - min(remaining_s(legal alternatives))
fork_gap_s(lap) = alternative_cumulative_remaining_s(lap)
                   - original_cumulative_remaining_s(lap)
```

Scores mean excess time within this disclosed synthetic model and fixed
continuation. They are not global schedule optima, real-world F1 performance, or
uncertainty-aware grades. Negative fork gaps mean the alternative is faster after
the indicated completed lap; the chart starts at zero at the original boundary.
Exact ties use engine action order: stay out, pit soft, pit medium, pit hard.

Python aggregates the recorded remaining lap components into base, compound pace,
degradation, warm-up, and incremental pit costs. Debrief deltas are selected minus
best; fork deltas are alternative minus original. Common base pace cancels in
paired comparisons. Fresh-set warm-up can differ by compound and only applies to
new sets, so these fixtures permit meaningful warm-up and degradation tradeoffs.
Display rounding never changes scores or simulation values. Component sums can
differ by last-bit floating-point rounding from elapsed-time subtraction.

All state, metrics, rankings, and future traces are generated in Python. A
pre-submit payload exposes only current/past situation, original legal masks
with reasons, the briefing, continuation, objective, and public assumptions.
Client configurations, snapshots, scores, and optimizer requests are not accepted.
At most four alternatives over fixtures with at most 20 total laps are evaluated.
The request body is capped at 1024 bytes. This is a local stateless service, not
a multi-user deployment or abuse-resistant hosted platform.

Browser playback reveals complete lap intervals from the returned run; it is not
a continuous vehicle-physics simulation. Rewind returns to the original boundary
and evaluates a new independent call while retaining the first result. Browser
history is local, version-keyed, user-editable practice, not benchmark evidence.

The independent scoring test uses a three-lap race at boundary one, base 10 s,
soft degradation 2 s per age-lap, and no compound requirement beyond one compound.
Staying out costs `(10 + 2) + (10 + 4) = 26 s`. A fresh hard set has -1 s pace,
2 s first-lap warm-up, zero degradation and a 3 s pit loss:
`(10 - 1 + 2 + 3) + (10 - 1) = 23 s`. Thus staying out scores 3 s excess.
This arithmetic is independent of the evaluator; fresh soft and medium yield
25 s and 26 s respectively, so hard is the best of all four legal calls.
