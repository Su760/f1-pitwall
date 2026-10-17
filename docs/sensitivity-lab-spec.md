# S1 — synthetic strategy sensitivity lab

A product extension at `/lab`, separate from historical calibration and F2.
Compare only the named one-stop and two-stop schedules in `scenarios/synthetic.json`.
Use the existing Python engine and legality checks for every point; no optimizer.

Controls are illustrative assumptions: incremental pit loss 0–40 s/stop (default
18), degradation multiplier 0–3 (default 1), warm-up multiplier 0–3 (default 1).
Multiply BOTH each compound's degradation slope and cap. Multiply every warm-up
entry, including starting-set penalties. Preserve base pace, offsets, inventory,
rules, starting compound, race length and fixed schedules. Never use historical
parameters. Version bounds/defaults/grid/tolerance in scenarios/sensitivity-lab.json.

Python returns both legal total times, signed `two_stop - one_stop` seconds
(positive means one-stop faster), engine stints and complete cost components.
Within 1e-9 seconds classify numerical tie; otherwise classify by full-precision
sign. Differences below 0.001 s are labelled near-tie while preserving the faster
schedule and exact difference. UI shows three decimals normally and more for
small differences. Rounded equal totals do not override Python classification.
No global-optimality, probability, confidence or real-world claim.

The map samples inclusive pit-loss/degradation axes at a chosen fixed warm-up.
Integer square grid size 2–21; default 21. At most 441 points, two schedules per
point, plus the selected comparison: 884 simulations / 10,608 lap evaluations
for the fixed 12-lap scenario. Enforce size/body/race/work limits server-side.
Each cell has a text symbol and accessible label with controls, difference and
classification. Adjacent changed winners indicate only a sampled transition,
not an exact crossover; no interpolation or exact boundary is calculated.

GET /api/v1/lab supplies controls/defaults/grid and assumption metadata.
POST /api/v1/lab accepts only three numeric finite controls and integer grid_size.
Reject boolean/string/null/unknown/duplicate/nonfinite fields and oversized bodies.
No caller-supplied scenarios or schedules. Run bounded engine work off the async
request loop. Existing challenge endpoints and observation boundaries unchanged.

The UI has reset, loading/error/retry states and cancels superseded requests.
Render only responses matching the current input identity, including during the
debounce window. Export loader-compatible scenario JSON and version-1 result JSON
with controls, resolved parameters, schedules, model/source identities, comparison
and sampled grid. Recompute scenario comparison using the offline module command;
verify the exported result via canonical baseline/controls and exact full replay.

Acceptance: default multipliers and pit18 =>1113.850/1124.700; pit7.15 =>
1103.000/1103.000 within tolerance; pit0 =>1095.850/1088.700. Test scaling,
legality, component sums, pit marginal cost, exports/recomputation, bounds and
stale responses. Inspect reversal/reset/rapid changes and desktop/mobile; obtain
independent read-only review. Preserve challenges and historical artifacts.
