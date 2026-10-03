# PitWall Arena status

## F0a and F0b — implemented and locally verified

F0a supplies the deterministic single-car engine, fixed policies, tire/race rules,
synthetic scenario, comparison CLI, and versioned traces. F0b adds exhaustive
schedule optimization, verified action replay, versioned JSON snapshots,
restoration, and independent forks. The runtime still uses only the standard
library. The physical model and scenario parameters are unchanged.

Reviewed F0a reference: `68b99c5d5dd79d470497ab8a8c942854503eecfb`, with 80 tests
and passing GitHub Actions on Python 3.11 and 3.14. F0b builds on that history.
The approved version-2.1 [spec](project-spec.md) remains unchanged and byte-identical
to the original local download; historical checkpoint statements are preserved.

## F0b verification evidence — 2026-10-02

| Check                                                                   | Observed result                                            |
| ----------------------------------------------------------------------- | ---------------------------------------------------------- |
| `python -m pytest -q`, Python 3.14.2 editable install                   | 203 passed                                                 |
| Same suite, Python 3.11.14 separate environment / installed wheel       | 203 passed                                                 |
| Optimizer tests                                                         | 30 passed                                                  |
| Replay and snapshot/fork tests                                          | 82 passed                                                  |
| New CLI tests plus existing trace/CLI tests                             | 29 passed                                                  |
| `ruff check .`                                                          | Passed                                                     |
| `ruff format --check .`                                                 | Passed                                                     |
| `python -m pip wheel --no-build-isolation --no-deps . --wheel-dir dist` | Passed                                                     |
| Hash-locked setup and wheel install in separate Python 3.11 environment | Passed                                                     |
| Comparison, optimization, replay, snapshot, restore, fork CLI demos     | Passed                                                     |
| Restored complete trace versus original JSON document                   | Identical                                                  |
| Independent read-only engine/optimizer/replay/test review               | No substantive findings                                    |
| Independent action-tree reference versus optimizer                      | Counts and full rankings match for 60 small configurations |

Tests preserve the 80 F0a checks and add 123 focused F0b cases. They verify exact
search counts/ranking, resource rejection before scoring, interruption without a
completed search, same-compound replacement, alternative starting compounds, and
a tiny hand-calculated optimum. Replay checks saved actions rather than executing
FixedSchedule; corrupt components, metadata, types, versions, boundaries, final
results, duplicate fields, and nonfinite values are rejected.

Restoration tests cover reset, before a pit, after a pit, before the final lap,
and finish. Identical continuation reproduces the whole trace. Parent/two-child
fork tests compare state, observations, elapsed time and history after changed
and rejected actions. Invented but superficially legal state is rejected by
prefix replay. No substantive review finding required a production-code fix.

## Verified synthetic results

```text
529 candidates; 462 legal schedules (0 zero-stop, 22 one-stop, 440 two-stop)
Rank | Total elapsed (s) | Gap (s) | Pit after lap:compound
1 | 1113.550 | 0.000 | 5:medium
2 | 1113.850 | 0.300 | 6:medium
3 | 1114.500 | 0.950 | 4:medium
4 | 1115.050 | 1.500 | 5:hard
5 | 1115.300 | 1.750 | 4:hard
```

The unique winner improves the existing one-stop baseline by **0.300 s**.
The original comparison remains **1113.850 s** (medium after 6) versus
**1124.700 s** (medium after 4, soft after 8), both legal. A boundary-4 restoration
with the original continuation reproduces 1113.850 s and the entire trace;
a deliberate fork to medium after 5 yields 1113.550 s without changing the parent.
The separate four-lap arithmetic fixture has six legal totals
`[406, 408, 415, 417, 418, 420]` seconds, reproduced by the search.

These results are derived from the engine and hand calculations, not a claim of
historical realism. Exact setup, checks, and runnable commands are in the
[README](../README.md); conventions and independent accounting are in
[model assumptions](model-assumptions.md).

## Publication and CI

The F0b implementation checkpoint is
[`625d00e5ed081b7968b8f9d3885cbf0e51e6fa14`](https://github.com/Su760/f1-pitwall/commit/625d00e5ed081b7968b8f9d3885cbf0e51e6fa14),
pushed successfully to existing `main` on `Su760/f1-pitwall` without reset or
force-push. Generated traces, virtual environments, caches,
credentials, and the original spec download remain outside the commit.
The [F0 workflow](../.github/workflows/ci.yml) now includes the F0b CLI demos
alongside tests, Ruff, and packaging on Python 3.11 and 3.14.

The implementation's [GitHub Actions run 37097220137](https://github.com/Su760/f1-pitwall/actions/runs/37097220137)
passed on Python 3.11 and 3.14, with 203 tests in each job and all packaging,
lint/format, comparison, and F0b demo steps successful. This documentation-only
follow-up records that observed outcome and closes the task checklist. The final
handoff identifies its own commit and hosted run separately. F0b is ready for
independent review; no substantive correctness finding remains from this pass.

## Remaining limitations

- Parameters are synthetic, deterministic, and uncalibrated; there is no traffic,
  weather, uncertainty, or historical rule fidelity.
- Search is bounded by explicit candidate/lap budgets and optimizes only the
  configured starting compound. It is a reference for small fixed models.
- Exact replay supports trace schema 1 and the current model only. It verifies
  consistency, not artifact authenticity; changed inputs require a new run.
- Snapshots store full history and restore by replay. Fixed policies are stateless;
  future policy memory, random generators, and external processes are not saved.
- Observations remain the minimal fixed-policy interface. No evaluator or
  snapshot data was added to them. JSON output is not crash-atomic.
- The previously diagnosed global Stop-hook formatting fault remains outside
  this repository; no hook was changed or bypassed. Its proposed fix and evidence
  remain in [decisions](decisions.md#2026-10-02--global-stop-hook-diagnosis-unresolved-outside-project).

## Next separate task: F0.5 (not started)

Build the minimal playable synthetic arena with three pit-call challenges and
debriefs. A user must complete a challenge and compare an intentional fork with
clearly disclosed assumed parameters. Reuse the verified engine, snapshots, and
reference optimizer; design the player-facing loop in that separate task.
Historical data/calibration, databases, Gymnasium, PyTorch, and RL remain later
milestones. This pass stops at F0b.
