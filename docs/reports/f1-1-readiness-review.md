# F1.1 readiness review

Reviewed 2026-10-16 America/Chicago (source retrievals 2026-10-17 UTC), against
`c503441a2eefaf83a5dc19f2b3ebdef26bd5aafb`. **The gate defect is repaired;
the full Bahrain candidate set remains blocked.** No calibration, cohort export,
simulator tuning, or RL was performed. The approved specification is unchanged.

## Repair and changed semantics

The supplied classified finisher has four completed, timed laps and a sole stint
covering 1–5. Version `f1-audit-v1` flags `missing_boundary_lap` but reports
descriptive readiness **ready, 4/4** and a **passed** circuit gate. At baseline,
`quality.py:282` detects the missing endpoint, but `:525` only propagates selected
start-boundary inconsistencies to observed laps, and `:745–775` does not consume
the stint audit. There is no fifth lap on which to attach an exclusion.

Version **`f1-audit-v2`** passes every session's stint audit into readiness.
Unresolved stint flags now limit descriptive lap/stint and dry-pace readiness,
with affected-row counts and overlapping reason counts. The example now reports
**limited, 4/4 eligible laps, one unresolved stint**, and **blocked** circuit gate.
The four valid lap observations are retained. Pit-lane and stationary-duration
description do not inherit this stint blocker. Schema/manifest version remains 1;
thresholds and per-lap eligibility are unchanged. See the
[versioned contract](../data-contract.md#f11-quality-semantics-change).

A completed retirement stint ending at lap 3 plus an untimed started lap 4 still
has no missing stint endpoint and supported completed-lap coverage. The tail is
retained and excluded by the existing lap rules; it does not create a new stint
inconsistency. Informational pit-boundary uncertainty alone also does not block
stint consistency. Missing tire age continues to block through its required-field
flag. Regression tests distinguish these cases from a contradictory finisher.

## Cache verification and reproduction

Both retained snapshots pass `load_snapshot`: manifest/request-set validation,
response hashes/lengths, JSON shapes, row counts and source scopes. Each contains
27 requests: 26 successful and one failed. No source refresh or repair was made.

| Snapshot                               | Manifest SHA-256                                                   |
| -------------------------------------- | ------------------------------------------------------------------ |
| `20261013T173313.808650Z-78aa081d6315` | `cb72336d2c365fcdb96c560b3112c7880cbe6151187c45d6870f4f525d814033` |
| `20261013T173926.193125Z-f1d80d3ff360` | `22b92984adf14a904d3b3bfd924530dbcb903190a77f101c3280bd4ce6ffdc21` |

Before changing code, `historical-data/f1-1-baseline` reproduced all **12/12** files
of `historical-data/f1-final-a` byte-for-byte. The original JSON hash remains
`1b148ae5006e01adc79f85bb9f47e43b79b370c4ef6af7bb6e06b413f79e5792`.
After the repair, fresh `f1-1-a` and `f1-1-b` builds reproduce **12/12** files
byte-for-byte, including the build manifest. All **nine Parquet files** are also
byte-identical to the original build. All 3,316 lap rows and original nulls remain.
Toolchain: Python 3.11.14 / PyArrow 25.0.0. New hashes:

| Artifact              | SHA-256                                                            |
| --------------------- | ------------------------------------------------------------------ |
| `quality.json`        | `d6c2ac6c7958820df769703b81c42f61c4661253d4c18e67f328c2f02a50ed36` |
| `quality.md`          | `41b46560496b4637734e4469f876bd31b93b1247cc220859e8c1aab361083075` |
| `build-manifest.json` | `f58aae8011245f95b1df753533b1db47551366c5ac206adbf302256f00b442af` |

All three rebuilds returned **exit 2 / partial**, not a failed rebuild and not a
passed quality gate. The retained failure is `pit?session_key=7953`, HTTP 404,
retrieved `2026-10-13T17:39:30.507905+00:00`. Its 30-byte body has SHA-256
`79e458c7f1cd32213fb418a50acca1646db353c29a8775154e0fbf8bc6ebd79d`.
The error body, attempt record and failed status are preserved.

## Targeted external evidence

These are supplemental observations and reconciliation notes, not replacements
for OpenF1 rows. Official documents were downloaded with HTTP 200 and PDF content
verified; relevant table pages were rendered and inspected. Originals, extracted
text and retrieval manifests remain ignored under `historical-data/f1-1-evidence/`.
The 2024 PDF failed in the browser retrieval tool but succeeded via direct HTTP;
this was a tool-specific failure, not a missing source. FIA timing sheets carry
Formula One World Championship Limited copyright/reuse restrictions; this report
links and summarizes them, without adding their datasets to Git or assuming
OpenF1's terms apply to them.

### 2023 pit-stop records

The [FIA race pit-stop PDF, v01, pp. 1–2](https://www.fia.com/sites/default/files/2023_01_brn_f1_r0_timing_racepitstopsummary_v01.pdf)
contains **50 records for 19 drivers**. Audit comparison found 50 unique driver/lap
keys and exactly one match for each of OpenF1's 50 non-opening stint starts:
FIA lap = OpenF1 stint start minus one, with no unmatched records. This supports
retrospective pit-boundary corroboration, not silently completing the failed API.

Columns identify car, driver, entrant, lap, time of day, stop ordinal, duration
and cumulative duration. The PDF does not define the duration's timing lines or
timestamp's entry/exit meaning. Treat it as the published pit-event duration;
pit-lane interpretation is plausible, not a verified mapping to `lane_duration`.
It is not a stationary measurement or incremental race-time loss. No UTC timestamp
or duration field was imported from this sheet.

There is a source conflict: the [FIA HTML classification page](https://www.fia.com/events/fia-formula-one-world-championship/season-2023/bahrain-grand-prix/race-classification)
has **48** detail records and summarizes Norris with four stops, omitting the
PDF's fifth and sixth stops at laps 47 and 54. Retain both versions; the PDF
supplies the fuller corroboration. A future adapter needs explicit revision and
field-mapping rules, not a silent preference masquerading as identical evidence.

### 2024 initial track-control baseline

The [FIA race-control sheet, v01, pp. 1–2](https://www.fia.com/sites/default/files/2024_01_brn_f1_r0_timing_raceracecontrolmessages_v01.pdf)
shows pit-exit opening at 18:03, sector-2 double-yellow/clear sequences around
18:03–18:04, and sector-4 slippery/clear messages at 18:05. No explicit initial
global-clear, SC or VSC message appears. A rain-risk forecast is not observed
dryness. The sheet uses minute-level time of day; matching messages align with
OpenF1 at a +3-hour offset, an observed alignment, not publication-time proof.

OpenF1 request `race_control-session_key-9472`, rows 5–10 (zero-based), records
pit-exit green at 15:03:42 UTC, session started at 15:03:42.341, then local
yellow/clear events. Its Track scope on the pit-exit message does not erase the
message's narrower meaning. A normal-start global-clear baseline would be an
additional modeling assumption. Neither the sheet's silence nor local clear
messages establish it. The parser and gate remain unchanged: **1,087 unknown +
42 affected lap intervals, zero clear; 0/1,129 dry-pace eligible**. This is
classification uncertainty, not evidence that the whole race was neutralized.

### 2025 car 27: participation and disqualification

[FIA provisional classification, document 45, p. 2](https://www.fia.com/system/files/decision-document/2025_bahrain_grand_prix_-_provisional_race_classification.pdf)
records Hulkenberg with **57 laps**, provisionally 13th. That independently
corroborates OpenF1's 57 observed positive-timed laps as physical participation.
[Document 55, p. 1](https://www.fia.com/system/files/decision-document/2025_bahrain_grand_prix_-_infringement_-_car_27_-_technical_non-compliance_plank_assembly.pdf)
subsequently disqualifies car 27 for an under-thickness plank assembly.
[Final classification, document 57, p. 2](https://www.fia.com/system/files/decision-document/2025_bahrain_grand_prix_-_final_race_classification.pdf)
lists DQ with no lap total. Document 57's cover time is 22:26 while its timing
sheet says 22:25; these are document labels, not guaranteed publication times.

The results express different facts, not a reason to erase participation or undo
DSQ. OpenF1 `session_result-session_key-10014`, row 19, retains `dsq=true`,
`dnf=false`, `dns=false`, `number_of_laps=null`, `position=null`, `duration=null`.
Coverage remains unresolved in the **OpenF1-only automated gate**; the external
participation corroboration is recorded separately here. A future evidence layer
could distinguish physical completed laps from final classification with source
references. It must not overwrite the null or promote provisional position to
the final result. Technical noncompliance also warrants excluding this driver
from any proposed representative pace cohort, even when physical coverage is known.

### Retrieval identity

All times below are 2026-10-17 UTC. The links above are the requested and resolved
URLs. `retrieval.json` and `web-retrieval.json` retain exact timestamps, URLs,
HTTP status, content type, byte count and SHA-256; filenames below are local.

| File                            | Retrieved UTC   |  Bytes | SHA-256                                                            |
| ------------------------------- | --------------- | -----: | ------------------------------------------------------------------ |
| `2023-pit-summary.pdf`          | 02:52:42.717349 | 491517 | `cfba93b6b17dab6032617c67bd5a571ed6b9d1a16aa2bf8e83317e193d64dc26` |
| `2024-race-control.pdf`         | 02:52:43.307269 | 483456 | `b55092a47c6ace2110ce54c00c61e91012c5d6ac9d1874c1ec5d811908be4842` |
| `2025-provisional.pdf`          | 02:52:44.278117 | 536667 | `f8d8932aeabd254227c1cb2b67fd0390549a790a2b39d69c2eadbe30ba617e02` |
| `2025-dsq.pdf`                  | 02:52:44.947583 | 335327 | `cd30dac05884fe5302880d8545820f1f1ccfcf2caa5a002371fa5e2e895c083a` |
| `2025-final.pdf`                | 02:52:45.451921 | 536643 | `af14c5f0bd75b2df730d6bf35beab587baaa6fb223ba2a3d7ce6ee9b57ae23b7` |
| `2023-classification-page.html` | 02:54:47.434857 | 117696 | `543a6bf8262af15afbff5282cead2c82751caf1a54cfc062d410b5fc60fd243d` |

[OpenF1 endpoint definitions](https://openf1.org/docs/) rechecked 2026-10-17 UTC:
stint end is the last completed lap; result lap count describes completed laps;
lane duration and stationary duration are separate. The deprecated `pit_duration`
alias is not a third measurement. Earlier stationary values remain unavailable;
none of these fields is incremental pit loss. Historical timestamps remain
event evidence, not verified decision-time availability.

## Retained readiness and proposed narrower scope

Sessions remain Bahrain Race / circuit 63: **7953/1141 (2023), 9472/1229 (2024),
10014/1257 (2025)**, expressed as session/meeting keys. Driver completed-lap
coverage remains 20/20, 20/20 and 19/20 in the automated report.

| Purpose / evidence          | 2023                     | 2024              | 2025              |
| --------------------------- | ------------------------ | ----------------- | ----------------- |
| Descriptive eligible laps   | limited 955/1058         | limited 1129/1129 | limited 1128/1129 |
| Unresolved stint rows, v2   | 50, missing pit evidence | 0                 | 0                 |
| Dry-pace eligible laps      | limited 258/1058         | blocked 0/1129    | limited 404/1129  |
| Distinct dry exclusions     | 800                      | 1129              | 725               |
| Pit-lane eligible records   | blocked, unavailable     | limited 43/43     | limited 42/42     |
| Stationary eligible records | blocked, unavailable     | blocked 0/43      | limited 40/42     |

Incremental pit loss and decision-time feature readiness remain blocked in all
three sessions. All non-blocked purposes retain the partial-candidate-source
blocker. FIA corroboration has not changed these statuses. The absence of wet
evidence does not certify a dry session or model suitability.

**Proposal only: a 2025 retrospective, post-neutralization descriptive pace
cohort.** Select existing `dry_pace_eligible` laps from session 10014, excluding
driver 27. This yields **382 rows, 19 drivers, 19 joined stints**, spanning observed
lap numbers 36–57. It removes 22 otherwise eligible car-27 rows from the 404
candidates; total exclusion from the 1,129 source rows is 747 (725 existing plus
22 DSQ candidates, disjoint). No eligibility threshold or parser assumption
changes. It excludes all 2023/2024 sessions, opening/pit transitions, unknown or
affected control intervals, missing/stale weather, invalid timing, unresolved
joins/age and unfinished tails through the existing rules.

Acceptance criteria for a separately authorized cohort audit:

1. Keep the full circuit gate blocked and label this subset's purpose explicitly;
   record exact snapshot, quality/config/implementation hashes and source-row IDs.
2. Verify the selected session's nine endpoints independently and every included
   driver's completed-lap coverage and stint consistency; retain all exclusions.
3. Independently inspect control interval boundaries and weather alignment for
   every included interval. Retain dry-candidate uncertainty and retrospective-only
   use; no decision-time backfill or inferred 2024 initial global-clear state.
4. Publish per-driver/stint/compound/age coverage and selection bias. These late
   race rows cannot establish whole-race, fuel, traffic, tire-wear or pit-loss
   effects, nor guarantee sufficient variation for fitting.
5. Reproduce the same membership offline and review it independently before
   accepting even descriptive cohort suitability. No model fitting is authorized.

This proposal is supportable for further audit, **not an accepted calibration
dataset**. It does not resolve missing 2023 API data, 2024 control initialization,
stationary-time gaps, counterfactual loss, or publication timing.

## Verification and exact commands

The supplied defect first failed its readiness regression (`ready` versus expected
`limited`). After repair: **37 quality tests**, **102 historical tests**, **305
combined core/historical tests**, and **250 core/API tests** pass. Ruff lint/format
and wheel build pass. The historical environment lacks pip (`No module named
pip`); packaging passed using the existing API environment instead. PDF inspection
used PyMuPDF 1.28.2 in an ignored temporary environment, not a project dependency.
Synthetic CLI comparison retains 1113.850/1124.700 seconds; exhaustive optimization
evaluates 529 candidates/462 legal and replays the 1113.550-second winner.
No local browser rerun was needed for this historical-only change; hosted arena
CI remains a separate publication check. Independent read-only code and final
documentation/evidence reviews passed, including an unobserved extra stint, an
informational-only valid pit boundary, cache/provenance hashes, source conflicts
and proposal counts. No substantive review finding remains.

Run from the repository root after the README's locked historical/API setup.
Output directories must be new; expected exit 2 is handled explicitly:

```sh
.venv-historical/bin/python -m pytest -q historical/tests/test_quality.py
.venv-historical/bin/python -m pytest -q tests historical/tests
.venv-api/bin/python -m pytest -q tests apps/api/tests
.venv-historical/bin/ruff check .
.venv-historical/bin/ruff format --check .
.venv-api/bin/python -m pip wheel --no-build-isolation --no-deps . --wheel-dir dist

SNAPSHOT=historical-data/raw/20261013T173926.193125Z-f1d80d3ff360
for BUILD in historical-data/f1-1-reproduce-a historical-data/f1-1-reproduce-b; do
  if .venv-historical/bin/python -m pitwall_historical rebuild "$SNAPSHOT" \
      --output "$BUILD" --config historical/config.json; then
    echo "Unexpected complete source status"; exit 1
  else
    RESULT=$?
    test "$RESULT" -eq 2 || exit "$RESULT"
  fi
done
diff -r historical-data/f1-1-reproduce-a historical-data/f1-1-reproduce-b
```

To reproduce only the proposal's count, without exporting a cohort or changing
any readiness result:

```sh
.venv-historical/bin/python - <<'PY'
import json
from pathlib import Path
report = json.loads(Path('historical-data/f1-1-reproduce-a/quality.json').read_text())
rows = [r for r in report['lap_audit'] if r['session_key'] == 10014
        and r['driver_number'] != 27 and r['dry_pace_eligible']]
print(len(rows), len({r['driver_number'] for r in rows}))  # 382 rows, 19 drivers
PY
```

The cache is local and ignored. Another checkout needs the retained snapshot or
a new identifiable import; a changed upstream snapshot need not match these hashes.
Expected output: partial import, `f1-audit-v2`, blocked circuit gate and the counts
above. A corrupt cache must fail, not produce a replacement observation.

Implementation [`880f11a`](https://github.com/Su760/f1-pitwall/commit/880f11aaf0db603676dc877dbe432abf5901b0da)
was pushed to origin/main without force. [Hosted CI 38997040963](https://github.com/Su760/f1-pitwall/actions/runs/38997040963)
passed all four jobs: historical, core Python 3.11/3.14 and arena (API, web checks,
production browser tests). This documentation follow-up records that observed
result; its own commit/CI are reported in the final handoff. Software CI success
does not establish historical completeness or calibration suitability.

Remaining blockers are explicit above. **One next task:** separately authorize
the proposed 2025 cohort audit, delivering only provenance-backed membership,
exclusions and suitability review. F2 calibration and RL remain deferred.
