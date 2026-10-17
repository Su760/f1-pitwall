# F1 historical data contract — version 1

Source/schema contract 1; quality semantics `f1-audit-v2` (F1.1, 2026-10-16).
Endpoint meanings rechecked 2026-10-17 UTC. F1 audits suitability;
it does not calibrate the simulator.
The approved specification remains unchanged. These are retrospective analyst
tables, never policy observations or a claim of decision-time availability.

## Source and bounded selection

Use [OpenF1](https://openf1.org/) and its [API reference](https://openf1.org/docs/).
The candidate set is the Bahrain Race session in each of 2023, 2024 and 2025.
Request `sessions?country_name=Bahrain&session_name=Race&year=YEAR`; resolve
session/meeting/circuit keys from the returned metadata, require exactly one
matching race per year and a common circuit. Do not infer dry conditions or
invent keys. Missing/ambiguous metadata is a visible failed selection. Then fetch
`meetings` by meeting key and `drivers`, `laps`, `stints`, `pit`, `race_control`,
`weather`, and `session_result` by session key. The latter provides independent
completed-lap and DNF/DNS/DSQ evidence for participation-aware coverage.

The current community tier needs no authentication for historical sessions and
permits 3 requests/second AND 30/minute. Apply both rolling-window limits to
every attempt, including retries; one sequential importer owns this budget.
Run only one importer per source/IP budget. Connection/read timeout, response-size
limit, attempt budget, exponential backoff and maximum accepted Retry-After are
in `historical/config.json`. Retry transient HTTP 429/5xx and transport failures;
honor delta-seconds and HTTP-date Retry-After. A server delay exceeding the budget
fails explicitly rather than retrying too soon. Other HTTP errors and malformed
JSON fail explicitly. No credentials or paid/live access are used.

OpenF1 describes educational, research, personal and non-commercial use and is
unaffiliated with F1/FIA. Its site links CC BY-NC-SA 4.0 while its FAQ says credit
is appreciated, not required. Preserve source attribution and the linked terms;
do not infer commercial data redistribution rights from an open-source code
license. Raw data stays local. [Access, FAQ and source-use statement](https://openf1.org/)
checked 2026-10-13; [linked license](https://creativecommons.org/licenses/by-nc-sa/4.0/).

## Evidence and completion

Every import creates a new snapshot directory; existing snapshots are never
overwritten. Each received response body is saved exactly as received, with a
SHA-256 hash. Manifest schema 1 records snapshot identity, source URL, configuration,
request endpoint/parameters, retrieval UTC, attempt/status/error information,
relative raw path, content hash, row count, resolved sessions and overall import
status. Failure bodies are evidence, not table inputs. An interrupted import has
no complete manifest. A failed or partial import remains visibly failed/partial,
even if some endpoints succeeded. An empty successful array is a valid response
with zero coverage, never proof of completeness. Download completion means every
expected request returned a valid array of objects; it does not mean quality passed.

Offline loading verifies manifest version, expected request set, paths, response
hashes, row counts and JSON structure. Corrupt evidence fails closed. Partial caches
can be rebuilt for diagnosis but cannot pass a readiness gate. Rebuild writes a new
output directory, typed Parquet plus JSON/Markdown reports and a build manifest
with source-manifest hash, config, schema/quality versions, dependency version,
row counts, logical-content hashes and output hashes. Same cache/config/toolchain
must reproduce content; output paths and wall clock are not report inputs.

## Normalized schemas and units

All tables retain original order and rows, including duplicates. Every row carries
`source_request` (request ID string), `source_row` (zero-based integer),
`raw_json` (canonical original object), and `validation_errors` (list of strings).
Unknown fields remain in raw JSON. Absent/null values become typed nulls; invalid
values become null plus an error, never zero or silent coercion. Integers reject
booleans; floats must be finite; booleans must be booleans. UTC timestamp columns
use Arrow timestamp microseconds with UTC timezone; naive/invalid timestamps are
flagged. Counts/keys are int64, seconds/measurements float64, text is UTF-8.
Raw objects distinguish absent fields from explicit null. Source spelling is kept.

| Table          | Logical key                                                              | Typed source columns beyond key                                                                                                            |
| -------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| sessions       | session_key                                                              | meeting_key, circuit_key, circuit_short_name, country_name, location, year, session_name, session_type, date_start, date_end, is_cancelled |
| meetings       | meeting_key                                                              | circuit_key, circuit_short_name, country_name, location, year, meeting_name, meeting_official_name, date_start, date_end                   |
| drivers        | session_key, driver_number                                               | meeting_key, full_name, name_acronym, team_name                                                                                            |
| laps           | session_key, driver_number, lap_number                                   | meeting_key, date_start, lap_duration, duration_sector_1/2/3, is_pit_out_lap                                                               |
| stints         | session_key, driver_number, stint_number                                 | meeting_key, lap_start, lap_end, compound, tyre_age_at_start                                                                               |
| pit            | session_key, driver_number, lap_number, date                             | meeting_key, lane_duration, pit_duration, stop_duration                                                                                    |
| race_control   | session_key, date, category, flag, scope, driver_number, sector, message | meeting_key, lap_number                                                                                                                    |
| weather        | session_key, date                                                        | meeting_key, rainfall, air_temperature, track_temperature, humidity, pressure, wind_direction, wind_speed                                  |
| session_result | session_key, driver_number                                               | meeting_key, number_of_laps, dnf, dns, dsq, position, duration                                                                             |

Keys, lap/stint numbers, date fields, names identifying sessions/meetings/drivers,
lap duration/pit-out flag, stint compound/bounds/start age, weather rainfall, and
result lap count/status are checked for missingness with purpose-specific impact.
Race-control optional scope/driver/sector/lap/flag fields remain nullable.
Durations are seconds; tire age is completed tire laps; temperature °C, humidity %,
pressure mbar, wind speed m/s, wind direction degrees. Rainfall is a 0/1 indicator,
not a rain amount. Full schema and required-field lists live in `schema.py`.

Pit derived columns are `effective_lane_duration` and `lane_duration_source`:
prefer observed `lane_duration`; explicitly fall back to deprecated `pit_duration`
only when the current field is unavailable. Preserve both and flag unequal values.
`stop_duration` remains null when unavailable (documented availability begins at
2024 US GP). Neither lane nor stationary time is incremental race-time pit loss.

## Joins, coverage and classifications

Join sessions to meetings on meeting key and validate circuit identity; each
session's child meeting key must agree. Join driver rows on BOTH session and driver.
Lap/stint join uses matching session/driver and inclusive lap_start <= lap_number
<= lap_end. No match or multiple distinct matches is unresolved; never pick a
conflicting row arbitrarily. Exact duplicates and conflicting logical keys are
counted separately and retained; downstream eligible views exclude ambiguous rows.

Expected completed laps come from a unique valid session_result per driver,
including retirements and lapped finishers; DNS expects zero. Count unique lap
numbers, positive timed laps, missing numbers within 1..completed laps, and extra
rows beyond that bound separately. A started but unfinished lap may explain an
extra row. Without result evidence report observed range/internal gaps only;
trailing coverage and retirement remain unknown, not a missing-to-winner penalty.
Include drivers found only in child tables and flag unmatched joins.

Retain a per-source-lap audit row with flags, exclusion reasons, joined source
references and derived tire age: tyre_age_at_start + lap_number - lap_start.
This is retrospective, requiring a unique valid stint; never fill a missing
starting age with zero or a future stint. Check inverted/overlapping/gapped stint
ranges, missing boundary laps and pit alignment. Source pit lap semantics are
not sufficient to guarantee an exact incoming/outgoing boundary: flag the reported
pit lap and following lap conservatively; compare the observed pit-out boolean,
stint starts and timestamps and expose disagreements/uncertainty.

Opening laps, observed pit-out laps, pit-associated laps, missing/invalid timing,
nonpositive or configured extreme durations, sector-total disagreement, overlapping
or discontinuous lap timing are flagged. The source says lap start is approximate;
configured tolerance is an audit assumption, not a physical calibration.
The configurable maximum lap number (1,000) bounds diagnostic gap enumeration;
larger source counts/indices remain evidence but coverage becomes unresolved.

Align weather with the latest sample AT OR BEFORE lap start, bounded by configured
maximum sample age; no future backfill. Positive rainfall or INTERMEDIATE/WET
compound is wet evidence. Zero rainfall plus a known dry compound is only
`dry_candidate`, never proof the track/session is dry; missing/stale weather is
unknown. Report gaps and uncertainty. Race-control uses UTC events, scope and
stateful SC/VSC/red intervals, plus overlapping yellow/local events conservatively.
Do not equate race-control lap number with each driver's lap. Missing/ambiguous
messages or ends propagate uncertainty; event timestamps are NOT necessarily
publication timestamps. No online/decision-time feature table is produced.

## Purpose-specific readiness and exclusions

Reports include counts by session AND driver; per-table required missing fields,
duplicates/conflicts/unmatched joins; stint/age/pit/timing/weather/control flags;
per-row exclusions with overlapping reason counts AND distinct excluded counts.
Original rows are never deleted. Criteria are versioned and thresholds are config.

- Descriptive lap/stint analysis: verified complete download, valid metadata and
  joins, independently supported lap coverage, unambiguous usable lap/stint rows,
  and no unresolved stint consistency flags, including endpoints outside the
  observed lap range. Individually usable laps remain eligible even when an
  inconsistent stint prevents session readiness.
- Dry pace investigation: above plus non-opening, non-pit, positive complete timing,
  known tire age/compound, contemporaneous dry-candidate weather and no known or
  uncertain neutralization. Report eligible counts and blockers; candidate rows
  do not certify causal tire wear or a calibrated model.
- Pit-lane description: valid unambiguous lane durations with alias conflict and
  join checks; report measured/eligible/missing counts. Stationary-stop description
  additionally needs observed stop_duration. Missing stationary time blocks that
  purpose only, not lap description by itself.
- Incremental pit-loss identification: blocked; these endpoints have no direct
  stay-on-track counterfactual measurement.
- Decision-time features: blocked; publication times/availability delays are not
  established and completed laps/stint outcomes are retrospective.

Every purpose reports `ready`, `limited`, or `blocked`, supporting counts and
explicit blockers. F1's circuit gate must not pass on partial access or unresolved
coverage; quality failures are a valid finding, not permission to invent data.
No tire fitting, simulator tuning, RL, live integration or arena calibration.

### F1.1 quality semantics change

Version `f1-audit-v2` adds `unresolved_stint_consistency` to descriptive lap/stint
and dry-pace blockers. Both purposes expose `counts.unresolved_stint_rows` and
overlapping `stint_blocking_reasons` counts; `stint_audit` retains source-row
references. All stint audit flags block these purposes except the informational
`pit_boundary_semantics_uncertain` and redundant `tyre_age_unavailable` (missing
age already blocks via `missing:tyre_age_at_start`). This covers missing endpoints,
invalid/gapped/overlapping ranges, pit-start disagreements, missing required
fields, invalid values, duplicates, conflicts and unmatched joins, even if no lap
lands on the problematic boundary. This does not alter lap eligibility, thresholds,
normalized schemas or raw evidence. It does not add a stint requirement to pit-lane
or stationary-duration description. The circuit gate still requires descriptive
readiness, so individually eligible 4/4 laps cannot override a stint ending at 5.

A legitimate unfinished retirement tail is not a missing completed stint endpoint:
the stint ends at the last completed lap. The extra untimed lap remains retained
and separately excluded under existing rules. Download completeness, row usability,
whole-stint consistency, and purpose readiness remain distinct. Supplemental FIA
evidence in the [F1.1 review](reports/f1-1-readiness-review.md) is a documented
reconciliation only; it is not merged into OpenF1 tables or used to relax this gate.

## Implementation interfaces

`cache.import_snapshot(cache_root: Path, config: dict, *, client=None) -> Path`
creates one raw snapshot and returns its path, including failed imports.
`cache.load_snapshot(snapshot: Path) -> tuple[dict, dict[str, list[dict]]]`
verifies evidence and returns manifest plus raw rows augmented with source_request
and source_row (original object preserved as raw_json by normalization).
`normalize.normalize_tables(raw_tables) -> dict[str, list[dict]]` preserves rows.
`quality.build_report(tables, manifest, config) -> dict` consumes typed Python
rows (timestamps are aware datetime) and returns JSON-safe deterministic audit.
`quality.render_markdown(report) -> str` is its readable counterpart.
`normalize.rebuild(snapshot, output, config=None) -> dict` writes only a fresh
output directory. CLI is `python -m pitwall_historical import --cache PATH
--config historical/config.json` and `rebuild SNAPSHOT --output PATH`.
