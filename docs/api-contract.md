# F0.5 challenge API contract — version 1

Implementation contract, 2026-10-03. FastAPI owns simulation; Next.js/TypeScript
renders returned data. Core Observation and model `f0a-linear-capped-v1` are unchanged.
All times are full-precision seconds; UI rounding is display-only.

## Challenge and evaluation rules

Three server-owned fixtures: `closing-laps`, `stint-choice`, `final-stint`, each
challenge version 1. Titles/briefings are neutral and reveal no ranked answer.
Each stores a trusted version-1 engine snapshot at a completed-lap decision boundary,
plus descriptive metadata. The service restores/validates that snapshot for each
request. Fixtures are immutable inputs; no caller can upload or modify them.

Continuation `stay-out-v1`: execute the submitted action for the next interval,
then stay out until finish. Every action allowed by the original engine mask must
admit this continuation in these fixtures; validate that invariant in tests.
Evaluate each legal action from an independent fork of the same restored parent.
No optimizer is called. At most four alternatives, with fixtures bounded to 20
race laps, are simulated per evaluation. Request body limit: 1024 bytes.

`score_s = selected.remaining_elapsed_s - best.remaining_elapsed_s`.
This is excess time within the disclosed synthetic model and frozen continuation,
not global optimality, real F1 performance, or uncertainty-aware grading. Rank
full-precision values, breaking exact ties in engine action order: stay_out,
pit_soft, pit_medium, pit_hard. Repeat attempts are practice. No random inputs.

## Endpoints

- `GET /api/v1/challenges`: `{api_version: 1, challenges: ChallengeSummary[]}`.
- `GET /api/v1/challenges/{id}?version=1`: `ChallengeDetail` (version required).
- `POST /api/v1/evaluate`: `Evaluation` from the strict JSON request below.
- `GET /health`: readiness response; no challenge answers.

```ts
type Action = "stay_out" | "pit_soft" | "pit_medium" | "pit_hard";
type Compound = "soft" | "medium" | "hard";
type EvaluationRequest = {
  challenge_id: string;
  challenge_version: number; // strict integer, not boolean/string
  action: Action;
  compare_action?: Action; // original call, reevaluated from canonical boundary
};
type ChallengeSummary = {
  id: string;
  version: number;
  title: string;
  summary: string;
  remaining_laps: number;
};
type Continuation = { id: "stay-out-v1"; description: string };
type Stint = { compound: Compound; first_lap: number; last_lap: number };
type Costs = {
  base_s: number;
  pace_s: number;
  degradation_s: number;
  warmup_s: number;
  pit_s: number;
};
type ChallengeDetail = ChallengeSummary & {
  api_version: 1;
  briefing: string;
  objective: string;
  continuation: Continuation;
  situation: {
    completed_laps: number;
    total_laps: number;
    remaining_laps: number;
    current_compound: Compound;
    tire_age_laps: number;
    remaining_sets: Record<Compound, number>;
    used_compounds: Compound[];
    stops_remaining: number;
    elapsed_s: number;
    stints: Stint[];
  };
  actions: { action: Action; available: boolean; reason: string | null }[];
  assumptions: {
    label: string;
    base_lap_time_s: number;
    pit_loss_s: number;
    max_pit_stops: number;
    min_distinct_compounds: number;
    noise: "disabled";
    tires: {
      compound: Compound;
      pace_offset_s: number;
      degradation_s_per_lap: number;
      degradation_cap_s: number;
      warmup_s: number[];
    }[];
  };
};
type Lap = {
  lap: number;
  compound: Compound;
  tire_age_laps: number;
  base_lap_time_s: number;
  pace_offset_s: number;
  degradation_s: number;
  warmup_s: number;
  pit_loss_s: number;
  lap_time_s: number;
  elapsed_s: number;
};
type Outcome = {
  action: Action;
  remaining_elapsed_s: number;
  total_elapsed_s: number;
  excess_s: number;
  legal: boolean;
  components: Costs;
  laps: Lap[]; // only future intervals AFTER submission
  stints: Stint[]; // complete race, inclusive lap endpoints
  cumulative: {
    lap: number;
    remaining_elapsed_s: number;
    gap_to_best_s: number;
  }[];
};
type Evaluation = {
  api_version: 1;
  challenge_id: string;
  challenge_version: number;
  model_version: string;
  continuation: Continuation;
  decision_after_lap: number;
  selected_action: Action;
  score_s: number;
  score_label: string;
  best_action: Action;
  best_remaining_elapsed_s: number;
  selected: Outcome;
  alternatives: Outcome[]; // ranked, legal choices only
  debrief: {
    summary: string;
    reference_action: Action;
    delta_components: Costs;
  };
  comparison: null | {
    original_action: Action;
    alternative_action: Action;
    delta_remaining_s: number;
    components_delta: Costs;
    gap_series: { lap: number; gap_s: number }[];
  };
};
```

Components sum recorded remaining lap costs; `remaining_elapsed_s` is finish minus
boundary elapsed time, using the engine's full precision. Independent sums may
have last-bit floating-point differences. Delta components are selected minus
best; fork comparison deltas are alternative minus original. Gap series starts
at the decision boundary with zero, then compares cumulative remaining time after
each aligned lap. Negative means the alternative is faster. All time values,
rankings, deltas, and explanation numbers originate in Python; the UI only
formats numbers and maps returned values to chart coordinates.

## Boundaries and errors

Pre-submit endpoints return only the summary, current/past situation, original
legal-action mask/reasons, objective, continuation, and relevant public assumptions.
They exclude snapshots, internal fixture configuration, scores, best actions,
rankings, and future lap traces. Assumed tire curves are intentionally disclosed
through assumptions, not added to Observation. There is no unrestricted optimizer,
configuration, snapshot-upload, or persistent run endpoint.

POST accepts only the four request fields above. Reject unknown fields, invalid
JSON, duplicate fields, nonfinite numbers, untyped/unknown actions and noninteger
versions. Reject unknown identity (404), unsupported/stale version (409), illegal
selected/comparison action (422), invalid request (422), and oversized body (413).
Errors use `{detail: {code: string, message: string}}`; do not echo snapshots or
untrusted full payloads. GET unknown/missing query fields also fail validation.
No request can mutate the canonical fixture or any previous result. Repeating
identical requests returns identical evaluation values. Responses are not cached.

## Browser flow

Next.js proxies `/api/v1/*` to the local FastAPI service through a server-only
`PITWALL_API_URL` setting (default `http://127.0.0.1:8000`). The browser uses relative
URLs. No permissive CORS, remote services, accounts, or database are needed.
A completed initial evaluation is retained unchanged in browser state. “Rewind
this call” returns to the original detail; submitting an alternative adds
`compare_action` with the original choice. Python recomputes both from the same
canonical boundary. Keep the original and alternative results side by side.

Practice history uses a versioned localStorage format keyed by challenge ID and
version; it is user-editable local practice, never authoritative scoring evidence.
Handle malformed/blocked storage without blocking play. Abort/stale-response guards
prevent challenge switches from displaying another challenge's data. Disable and
guard duplicate submissions; visible error/retry states preserve the selected call.
Playback is a lap-record reveal with skip/replay and reduced-motion support.

## S1 lab endpoints — lab version 1 (2026-10-17)

Independent of challenge scoring; engine/model and existing endpoints unchanged.
`GET /api/v1/lab` returns `api_version: 1`, lab settings (bounds/defaults/steps,
grid/work limits and tie thresholds), and source identity. `POST /api/v1/lab`:

```json
{"pit_loss_s":18,"degradation_multiplier":1,"warmup_multiplier":1,"grid_size":21}
```

All fields required. Controls are strict finite numbers (no boolean/string/null):
pit loss 0–40 seconds/stop; multipliers 0–3. Grid size is an integer 2–21.
Both endpoints reject query parameters. POST uses the existing 1024-byte bounded
JSON reader, rejects duplicate/unknown keys/nonfinite values, requires JSON
content type and returns structured errors (422 invalid input or wrong content type,
413 body too large). It accepts no client scenario, schedule, snapshot or score.

Response is the exportable result: `api_version`, `lab_version`, `source`
(model version and SHA-256 of baseline scenario/settings), `controls`, `assumptions`,
tie thresholds, resolved loader-compatible `scenario`, `comparison`, and `grid`.
Comparison includes named strategies, engine legality, total seconds, pit counts/
boundaries, stints, per-lap engine records and component sums. `delta_s` is two-stop
minus one-stop. Python returns winner/label/symbol/near-tie; JS only formats/displays.
Grid contains inclusive axes, rows in ascending degradation order, sampled totals,
signed differences, classifications and the total lap evaluation count.

Fixed one-/two-stop schedules come from `scenarios/synthetic.json`. Both must
finish legally through the engine. Maximum work is 441×2 + 2 simulations of 12
laps = 10,608 lap evaluations; validate bounds before simulation. Bounded CPU work
runs in the API thread pool. This is a local tool, not a public multi-user service
with a global request/concurrency quota. These comparison endpoints do not invoke the optimizer.

Numerical ties use |delta| ≤ 1e-9 s. Outside this tolerance, sign determines the
faster schedule; |delta| < 0.001 s adds near-tie. The UI rounds totals to three
decimals and gives additional digits for tiny differences. Export/recomputation
preserves full precision. Hashes identify inputs, not authenticity. Browser abort,
request revision and input-identity guards prevent superseded results displaying
for newer controls, including during debounce. See [S1 spec](sensitivity-lab-spec.md).


## S2 explicit lab optimization — optimization version 1 (2026-10-17)

`GET /api/v1/lab` additionally supplies `optimization`: version, fixed `top_k: 3`,
`max_candidates: 600`, `max_lap_evaluations: 7200`. Reading metadata and computing
the S1 grid never run a search. `POST /api/v1/lab/optimize` accepts exactly:

```json
{"pit_loss_s":18,"degradation_multiplier":1,"warmup_multiplier":1}
```

Same strict finite numeric controls, ranges, 1024-byte JSON reader, duplicate/key
rejection, no query fields and no-store responses as S1. No client budgets, top-k,
grid, scenario or schedules. Reuse S1 scaling and the same baseline scenario.
Offload bounded computation to the thread pool. Server configuration is
`scenarios/lab-optimization.json`, separate from unchanged S1 export settings.

The existing optimizer preflights both search budgets before any simulation;
then evaluates the entire fixed-schedule space and returns three retained legal
results. Benchmark simulations happen only after successful complete search and
add 24 potential laps. Current actual upper work: 529×12 + 24 = 6,372 potential
lap evaluations. An abort invalidates the client result but need not stop a search
already running on the server. No aggregate concurrency/rate quota is claimed.

Failures: 422 `invalid_request` for invalid controls, 413 `body_too_large`,
422 `search_too_large` for preflight rejection (no candidates evaluated),
503 `search_unavailable` when no complete legal search result can be returned.
No partial winner or internal exception detail is exposed in these errors.

Success is a JSON result/export record with:

- `api_version: 1`, `optimization_version: 1`, exact `controls`, synthetic `label`.
- `source`: model version and SHA-256 hashes of baseline scenario, S1 settings and
  optimization settings. Hashes identify input bytes, not authenticity.
- `search`: completion, candidate/legal counts and counts by stops, conservative
  search work, separate benchmark work, limits, top-k, scope/tie rules, and
  full-precision `ranked` schedules/times/gaps. Schedule format is existing
  `{name, stops: [{after_lap, compound}]}`; gap is elapsed minus best. S2.1 adds
  one-based `rank`, `stints` directly from each retained engine result, and
  `exact_tie_ranks`: other retained ranks with exactly equal unrounded elapsed
  time. Empty list means no exact tie among these retained entries. This is an
  additive version-1 extension; existing fields keep their meanings. Equality
  uses neither the S1 tie tolerance nor formatted display strings. No extra
  optimization or simulation is run to supply these fields.
- `best`: schedule, full-precision elapsed seconds, legality, stints and boundaries.
- `benchmarks`: name, elapsed seconds and `improvement_s` (benchmark minus winner).
- `scenario`: existing loader version 1 with resolved configuration and original
  two benchmark schedules. `trace`: existing strict version-1 winning trace.

Full precision ranks time first; exact ties use fewer stops, boundary tuple, then
soft/medium/hard order. S1 tolerance never alters optimization ranking. Display
rounds to 0.001 s; zero displayed gain need not imply equality. The UI accepts only
a complete legal response for the requested controls. A new component lifetime
on every edit/reset removes old results/exports, aborts old fetches and ignores
late callbacks; an immediate in-flight guard prevents duplicate activation. Search
is invoked only by the explicit button. Retry retains keyboard focus on that same
button; S1.1 map navigation/exit is unchanged.

See [S2 specification](s2-optimization-spec.md) and
[CLI export reproduction](../README.md#explicit-strategy-search-s2).
