# F0a model assumptions and rule conventions

This document describes implemented F0a behavior under the approved
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
places for display; traces keep full floating-point values. Cross-language or
future model-version comparisons should allow numeric tolerance.

Elapsed time accumulates sequentially without per-lap rounding. A different
summation algorithm may differ by floating-point rounding at the last few bits;
the trace checks use absolute tolerances of 1e-10 seconds for cumulative totals
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
without changing the version-1 schema. This audit trace is not a saved snapshot.

There are no timestamps, machine paths, or random identifiers in trace contents.
Schema and model versions are separate so a future equation change can be
distinguished from a storage-format change. Configuration plus accepted actions
supports future replay; F0a tests rerun fixed schedules from their initial
configuration. Loading/restoring a running snapshot and forking state are not
implemented.

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
