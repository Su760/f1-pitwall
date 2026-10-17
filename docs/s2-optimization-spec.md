# S2 — explicit bounded synthetic optimization

Authorized extension of S1.1 (`6a0cf12`); approved project spec and historical
quality gate remain unchanged. No calibration, adaptive planning or RL.

## Contract

An explicit “Find best legal strategy” action uses the selected pit loss,
degradation and warm-up controls. Reuse S1 validation/resolution: multiply both
slope and cap, and every warm-up entry. Keep 12 laps, soft start, inventory,
mandatory compounds and maximum two stops. Neither control edits nor the map
invoke optimization.

POST `/api/v1/lab/optimize` accepts exactly the three numeric controls. The server
owns `scenarios/lab-optimization.json`: version 1, top-k 3, at most 600 candidates
and 7,200 potential search lap evaluations. Existing preflight rejects either
budget before any simulation. Two benchmark simulations add 24 potential lap
evaluations outside the search budget. Limits bound each request, not aggregate
multi-client traffic. Work runs off the API event loop; no public deployment is
part of S2.

Use the existing exhaustive optimizer and engine unchanged. Enumerate every
increasing boundary tuple and compound sequence, including fresh same-compound
changes and zero stops. Engine legality filters candidates. Require a complete
search with a legal winner before returning any optimum. Rank full precision;
exact ties retain the existing fewer-stops, boundary-tuple, soft/medium/hard order.
Never collapse near-equal times. Retain three results; this is not truncation of
the candidate search.

Return versioned controls, source/config hashes, resolved loader scenario,
search budgets/counts/completion/top-three schedules, winning version-1 trace,
stints/time and Python-computed benchmark improvements (benchmark minus winner).
Export scenario, trace and complete search record separately. Existing CLI replay
and optimize reproduce the winner and counts; no new format for engine traces.

## Interaction and claims

Label: “Best legal fixed schedule under these synthetic assumptions.” Explain
fixed start, all legal 0–2 stop schedules, synthetic scope, exact tie order, and
three-decimal display rounding with full precision in exports. Show schedule,
tire timeline, elapsed time, both benchmark improvements and search counts.

Keep a persistent keyboard-operable action, loading and retry states, an immediate
in-flight guard, and cancel/ignore late requests on edits/reset. Every edit,
including equivalent numeric text, and reset invalidates optimization and exports.
A fresh explicit activation is required. Preserve S1.1 map navigation and touch
targets. No optimization response can populate a newer control revision.

## Verification

Default: 529 candidates, 462 legal; complete; medium after lap 5; 1113.550 s;
gains 0.300 / 11.150 s. Pit 7.15: benchmarks 1103.000, winner 1102.700.
Pit 0: winner 1088.700, existing exact tie order. Test controls/scaling, both
preflight limits, incomplete-search rejection, deterministic exports and CLI
replay/recomputation. Browser checks explicit-only requests, duplicate activation,
stale/equivalent edits, reset/retry, keyboard, actual downloads and desktop/mobile.
Run existing S1, arena, core/API and historical checks; independent read-only
backend and client reviews. Preserve unrelated local files and inspect staged
changes before authorized commit/push, then check hosted CI.

## Delivery evidence — 2026-10-17

Implemented the separate optimization wrapper/API and an explicit lab action.
Engine, optimizer, S1 numerical behavior and export formats remain unchanged.
`source.optimization_settings_sha256` identifies the separate search config.
API requests cannot change budgets, top-k, race length, starting compound or rules.
Default search uses 6,348 potential search laps plus 24 benchmark laps.

Local verification:

- 327 core/API tests (including 30 focused S2 cases) and 129 offline historical
  tests pass. Both budgets reject before any simulation; incomplete, empty or
  illegal search results cannot become an optimum. Acceptance uses 1e-9 s
  absolute tolerance with no relative relaxation. Existing S1 cases are preserved.
- Ordinary lint with retained generated artifacts, TypeScript, production build,
  Ruff lint/format, packaging and original CLI comparison/optimization/replay pass.
- All 36 desktop/mobile production browser cases pass without retries, including
  18 existing challenge cases, 10 S1/S1.1 cases and 8 S2 cases. They cover explicit-only activation, all
  three times and zero-pit exact tie, synchronous duplicates, Enter/Space/Tab,
  persistent focus, failed/incomplete response retry, every control, equivalent
  text, same-default reset, late response after reset and after a newer winner.
  Downloaded scenario/trace replay using the existing CLI; two independent CLI
  search outputs equal the browser trace and each other byte-for-byte. A newer
  result's downloaded record still matches it after the stale response arrives.
- Root inspected rendered desktop/mobile optimization sections; independent client
  reviewer inspected the same screenshots. Labels, three-stint timeline, gains,
  focus/44px targets and wrapping commands are readable, with no page overflow.
  Generated evidence is ignored under `web/test-results/optimization-*/`.

Independent read-only review:

- Backend reviewer `/root/s2_backend_review`: budgets, validation, legality,
  ranking, export formats and provenance. Ran 30 focused cases; independently
  enumerated 36 control combinations with Decimal arithmetic, all optima within
  2.274e-13 s of the independent minimum, always 529 candidates/462 legal.
  Existing CLI reproduced exact trace JSON. No substantive finding.
- Client reviewer `/root/s2_client_review`: explicit activation, request lifetime,
  duplicate prevention, reset/retry, focus, exports, test coverage and rendered
  layouts. No outstanding finding. Clarified original “schedules stay fixed” text
  to scope it to benchmark/map comparisons; the search varies fixed schedules.

Initial verification failures were test-harness issues, resolved before delivery:
pytest `import file mismatch` from duplicate test basenames (API file renamed);
`KeyError: 'pit_stops'` from a test/client type using the wrong schedule field
(corrected to the read-back existing `stops` contract); CLI output uses
`529 candidates; 462 legal`, not a comma; unscoped `getByRole('alert')` also matched
Next's route announcer (scoped to the optimizer section). npm commands initially
run at repository root returned `ENOENT ... package.json`; all actual npm gates
ran from `web/`. No remaining failed gate is hidden by these corrections.

Implementation [`4304f43`](https://github.com/Su760/f1-pitwall/commit/4304f43952d8c9f165d0be2f8065c54f3a4cd914)
is pushed. [CI 39054603883](https://github.com/Su760/f1-pitwall/actions/runs/39054603883)
passes all four jobs: Python 3.11/3.14, historical and production arena/browser.
The final documentation-closure commit/CI is supplied in the handoff.

### Actual tools and references

UI/UX Pro Max instructions read at
`~/.claude/plugins/antigravity-skills/skills/ui-ux-pro-max/SKILL.md`;
SHA-256 `6aad875f675e5909272c78ed2b9011115566233059ea2b71ba4d4a5c3a5d78f7`.
The existing bundle identity is git `d25d06c29b32148be51505c5c9b84b3e38e0e2b1`
(no standalone skill semver). Used its documented `scripts/search.py` for a
targeted design-system query, UX loading/focus/error guidance and React async
cleanup guidance. Kept the existing visual identity; no generated redesign.
Ponytail, PStack and Thermo Nuclear Code Review remain unavailable as recorded in
[S1.1 tool inventory](reports/s1-1-review.md); none ran. Independent agents and
Playwright supplied the requested reviews/checks instead.

Primary documentation checked 2026-10-17:
[React keyed state reset](https://react.dev/learn/preserving-and-resetting-state),
[effect cleanup](https://react.dev/reference/react/useEffect) and
[WAI button pattern](https://www.w3.org/WAI/ARIA/apg/patterns/button/).
A new input revision resets the optimization lifetime; cleanup aborts/ignores old
requests. Native buttons preserve keyboard semantics; `aria-disabled` plus an
immediate handler guard prevents activation while retaining focus.

### Limits and stopping point

No aggregate service quota, public deployment or cross-browser/screen-reader
certification. Aborted client requests may leave bounded server work completing.
CLI replay validates the trace; CLI optimize recomputes the winner, not the entire
search-record wrapper. Hashes identify inputs, not authenticity. Historical
cohort calibration remains closed and the full circuit gate remains blocked.
Approved spec SHA-256 remains
`518ebe5e9e6473266d36338c41975054233b3e4b2ab091c4ac772588834671b3`.
Unrelated next-env edit and downloaded original spec are preserved locally.

Stop after S2. One proposed next product task: display the already returned top
three legal fixed schedules side by side, with their stints and gaps, without
adding search scope or historical/adaptive modeling. This proposal was subsequently authorized and delivered as S2.1 below.


## S2.1 — retained top-three comparison contract

Authorized from S2 `b02a670`. Consume `search.ranked` in server order. Add each
entry's one-based `rank`, `stints` serialized directly from its retained engine
result, and `exact_tie_ranks`: other retained ranks whose full-precision elapsed
time equals this entry exactly. No tolerance, formatted comparison, extra engine
simulation or second search. Existing version-1 fields, winning trace, scenario,
budgets, top-k and ranking/tie rules retain their meanings.

Show three aligned cards on desktop and a vertical stack on mobile: rank,
pit-after-lap decisions, elapsed time, engine gap to fastest and stints. Each
race-lap timeline uses identical twelve-column widths with visible 1–12 labels.
Short stints retain their true width; compound letters on bars and full compound
names/lap ranges below them provide textual identification. This is race-lap
alignment, not simultaneous elapsed-clock alignment. Card content rows align
across desktop columns. No card interaction adds Tab stops.

Each card identifies exact ties only from Python's `exact_tie_ranks`; untied
entries explicitly say no exact elapsed-time tie among these three. Display
elapsed/gaps to 0.001 s and expose the full-precision serialized values in text.
Equal rounded values therefore cannot manufacture exact ties. Exact ties retain
fewer stops, boundary-tuple, soft/medium/hard ordering. Small gaps say nothing
about robustness, confidence or real-world superiority.

The trace download is explicitly **rank 1 only**; its filename/schema remain
unchanged. The search record gains the ranked fields. Edits/reset remove the
entire comparison and all optimization exports. Existing explicit activation,
request lifetime guards, limits, retry focus and map keyboard behavior remain.

Acceptance: defaults rank pits after 5/6/4 to medium; totals
1113.550/1113.850/1114.500 s and gaps 0/0.300/0.950 s. At pit7.15 ranks 2/3
exactly tie at 1103.000 s, both 0.300 s behind the winner. At pit0 ranks 1/2
exactly tie at 1088.700 s; preserve existing compound-order tie-break. Verify
stints against engine results, equal-display-but-unequal-time behavior, no added
simulation/search work, desktop/mobile alignment, stale/reset invalidation,
keyboard and actual downloaded winner replay. Independent read-only backend
and client reviews precede the authorized commit/push and hosted CI check.


### S2.1 verification evidence — 2026-10-17

- 34 focused backend/API cases and 331 complete core/API tests pass. Tests added
  before implementation initially failed with `KeyError: 'rank'`, proving the
  existing response lacked the new contract; all four new cases now pass.
  Retained stints match fresh engine replay of each schedule, including separate
  soft-to-fresh-soft sets. Both work-budget rejections and S2 acceptance remain.
  Spies verify one optimizer invocation, 529 candidate simulations and two
  benchmark simulations: zero extra simulations for comparison serialization.
- 129 offline historical tests, Ruff lint/format and wheel build pass. Ordinary
  npm lint with retained generated artifacts, typecheck and production build pass.
- All 42 desktop/mobile production browser cases pass without retries (18
  existing challenge, 10 S1/S1.1, 8 S2 and 6 S2.1 cases). Actual downloaded
  scenario/winning trace replay through the existing CLI; two CLI recomputations
  equal the downloaded trace and each other byte-for-byte. Six focused S2.1
  desktop/mobile browser cases cover ordered cards, totals/gaps,
  exact ties at pit7.15/pit0, rounded-only match at pit7.1501, matching timeline
  widths/coordinates, one-lap stint widths, accessible descriptions, keyboard
  search→exports flow, reset and equivalent-edit removal. The existing S2 tests
  now explicitly check removal of every card and the rank-1 export label.
- Root inspected actual default desktop/mobile, rounded-only and one-lap-stint
  screenshots; independent client reviewer inspected default, exact-tie,
  rounded-only and short-stint cases. Additional generated layout evidence at
  375/768/1024/1440px is under ignored `web/test-results/s21-responsive/`.
  A supplementary 1024px capture was initially blank after rapid viewport
  resizing despite passing geometry; stabilized the test's instant positioning
  and paint wait, reran the targeted case and inspected the regenerated image.
  No application change was needed. Root inspected the resized layouts, with no
  page overflow; lap axes/segments are readable and correctly scaled.
- Independent read-only backend reviewer `/root/s21_backend_review` ran the
  34 focused cases and checked 36 control combinations against S2 `b02a670`.
  Removing only `rank`, `stints`, `exact_tie_ranks` makes every response identical
  to baseline, including counts/ranking, source hashes, scenario and winning trace.
  Every winning trace replayed; exact-tie relationships are symmetric and exact.
- Independent read-only client reviewer `/root/s21_client_review` checked data
  use, semantics, layout, tie text, stale/reset behavior, keyboard flow and winner
  export labeling; inspected real rendered screenshots. Neither reviewer found
  an outstanding issue. Client reviewer did not claim independent browser execution.

UI/UX Pro Max used from the same installed path/identity documented above; root
and client reviewer read its actual instructions and ran its documented design
system and React/UX searches. Applied existing-theme responsive layout, semantic
ordered lists and text alongside color; generic redesign suggestions were outside
scope. Primary references checked 2026-10-17:
[W3C Grid Level 2 subgrids](https://www.w3.org/TR/css-grid-2/#subgrids) for aligned
card rows and [React list rendering](https://react.dev/learn/rendering-lists) for
stable schedule keys and ordered mapping. No new dependency or infrastructure.

Implementation [`1920319`](https://github.com/Su760/f1-pitwall/commit/1920319b39758fef1b1cb3a3256a6bc40a10f8ec)
is pushed; [CI 39056718773](https://github.com/Su760/f1-pitwall/actions/runs/39056718773)
passes all four jobs (Python 3.11/3.14, historical and production arena/browser).
The final documentation-closure commit/CI is supplied in the handoff.

S2.1 stops here. Full historical gate remains blocked and cohort calibration
remains closed. Next proposal only: export one chosen retained alternative trace,
clearly labelled by rank, with existing CLI replay; do not expand search scope.
