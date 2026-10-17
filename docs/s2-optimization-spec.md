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
adding search scope or historical/adaptive modeling. This proposal is not implemented.
