# F1.3 — frozen cohort descriptive visual report

Completed locally 2026-10-17 UTC from baseline
`d48dadee3b6f74bad14c692f5889509214eeaa66`. The historical workstream now has a
self-contained local HTML report, machine-readable statistics and 19 exportable
SVG charts. It describes the **382 frozen F1.2 observations**; the separately
labelled deletion-omission sensitivity has **365 observations**. All 17 tagged
members remain in the primary view. No source import, eligibility change, model
fit or simulator calibration was performed. The full circuit gate remains blocked.

## Open and reproduce

The verified artifact already exists locally. From the repository root on macOS:

```sh
open historical-data/f1-3-a/report.html
```

Absolute output:
`/Users/supashramesha/Desktop/F1/Pitwall/historical-data/f1-3-a/report.html`.
It opens directly without a server, remote assets or network requests. Choose a
driver/stint or all drivers; inspect the coverage lists and source-row table.
The chart and statistics export links work even when this HTML is copied alone.
There are also separate SVG and JSON files alongside it. Charts keep readable
axes on narrow screens by allowing horizontal scrolling; tables scroll separately.
Without JavaScript all driver sections remain visible.

Use the existing locked historical environment (README setup), retained raw
snapshot and verified F1.2 artifacts. A new directory is mandatory:

```sh
CODE=0
.venv-historical/bin/python -m pitwall_historical.descriptive \
  historical-data/raw/20261013T173926.193125Z-f1d80d3ff360 \
  --cohort historical-data/f1-2-a \
  --config historical/descriptive-2025.json \
  --output historical-data/f1-3-new || CODE=$?
test "$CODE" -eq 2 && open historical-data/f1-3-new/report.html
```

Exit **2** is expected: the report is complete, while the retained source snapshot
is partial and the full circuit gate blocked. Exit **1** means generation failed;
do not treat it as expected partial. Existing output directories are refused.
No generated data or reports are distributed in Git. These commands require the
retained local inputs; they do not download replacements.

## Integrity and reconciliation

`historical/descriptive-2025.json` pins the verified F1.2 manifest SHA-256. Before
analysis, the generator verifies that pin, its complete artifact-write status,
the exact three artifact names and each content hash, and identical provenance
across membership, exclusions and audit. It validates the raw manifest hash,
snapshot identity, embedded config/hash, cached response bodies and the recorded
F1.2 code bundle. It checks the individual historical modules listed in the
frozen provenance; adding this separate generator does not change that evidence.

It regenerates the unchanged v2 quality report and verifies its original hash,
then requires exact equality with frozen membership/exclusions. This verification
cannot silently select a new primary cohort. The versioned pin is a local trust
anchor, not a cryptographic signature. Changing that pin would select different
evidence and requires an explicit reviewed task.

Observed lap duration comes only from the raw normalized lap at the frozen
`source_request` / zero-based `source_row`; session, driver and lap must match.
The unique referenced stint and driver name are checked. Missing/invalid durations
fail explicitly, never become zero. Descriptive output retains all primary row
identities, elapsed seconds, lap starts, stint identity and deletion notices;
all 747 excluded identities remain in its reconciliation. The copied full gate
and partial source status remain explicit:

`1129 source laps = 382 primary + 747 distinct exclusions`

`382 primary = 365 sensitivity + 17 deletion-tagged members`

The original 2023 failed pit request and 2025 driver 27's null result are untouched.
See [F1.2](f1-2-cohort-audit.md) for the source suitability limits and membership.

## Definitions and reading the report

Statistics are per driver/stint, ordered by driver number, never by performance.
Quantiles use **Hyndman–Fan type 7**: sort n values, set `h=(n−1)*p`, and linearly
interpolate between the floor/ceiling zero-based indices. Median uses p=0.5;
Q1/Q3 use p=0.25/0.75; IQR is Q3−Q1. Empty sensitivity groups have null statistics.
A singleton has its observed time for all quantiles and IQR zero, not evidence
of stable pace. `n<5` is a display caution only, not a new eligibility rule.
IQR describes spread, not uncertainty or a confidence interval.

JSON stores full numerical precision. HTML/SVG display seconds to three decimals
where appropriate; ordinary binary floating-point rounding is retained. Every
summary lists its source rows and exact observed lap numbers. Race-lap alignment
is **not simultaneous clock time**. Lines connect only consecutive observed laps;
no line bridges a missing lap, and no value is interpolated into a coverage gap.
All driver charts share the same labelled nonzero y-axis. SVG metadata includes
session identity, frozen-manifest hash and generator hash.

Amber diamonds and an explicit tagged-lap list annotate retrospective deletion
notices. Omitting them is only a sensitivity comparison: it is **not certified
clean**, and notices alone do not determine final legal status. Primary counts
never change. The following table is a compact transcription of the JSON; seconds
are rounded to three decimals. It is not a compound or driver-performance ranking.

| Driver / stint | Primary n | Median (s) | IQR (s) | Omitted tags | Sensitivity n | Median (s) | IQR (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 Max VERSTAPPEN / 3 | 22 | 97.434 | 0.941 | 3 | 19 | 97.369 | 0.964 |
| 4 Lando NORRIS / 3 | 22 | 96.587 | 1.014 | 2 | 20 | 96.587 | 0.921 |
| 5 Gabriel BORTOLETO / 3 | 22 | 98.647 | 0.459 | 0 | 22 | 98.647 | 0.459 |
| 6 Isack HADJAR / 3 | 22 | 98.313 | 0.525 | 0 | 22 | 98.313 | 0.525 |
| 7 Jack DOOHAN / 3 | 22 | 98.415 | 0.951 | 2 | 20 | 98.415 | 0.808 |
| 10 Pierre GASLY / 3 | 20 | 97.465 | 0.992 | 0 | 20 | 97.465 | 0.992 |
| 12 Kimi ANTONELLI / 4 | 22 | 97.739 | 0.984 | 1 | 21 | 97.738 | 0.801 |
| 14 Fernando ALONSO / 3 | 22 | 98.486 | 0.362 | 1 | 21 | 98.442 | 0.376 |
| 16 Charles LECLERC / 3 | 22 | 96.834 | 1.219 | 1 | 21 | 96.894 | 1.093 |
| 18 Lance STROLL / 3 | 22 | 98.651 | 0.496 | 1 | 21 | 98.648 | 0.459 |
| 22 Yuki TSUNODA / 3 | 22 | 97.833 | 0.719 | 2 | 20 | 97.822 | 0.702 |
| 23 Alexander ALBON / 3 | 22 | 97.837 | 0.971 | 0 | 22 | 97.837 | 0.971 |
| 30 Liam LAWSON / 3 | 22 | 97.915 | 0.630 | 0 | 22 | 97.915 | 0.630 |
| 31 Esteban OCON / 3 | 22 | 97.915 | 0.709 | 0 | 22 | 97.915 | 0.709 |
| 44 Lewis HAMILTON / 3 | 22 | 97.156 | 1.044 | 1 | 21 | 97.198 | 1.144 |
| 55 Carlos SAINZ / 3 | 8 | 98.539 | 1.255 | 1 | 7 | 98.454 | 0.762 |
| 63 George RUSSELL / 3 | 2 | 95.680 | 0.162 | 0 | 2 | 95.680 | 0.162 |
| 81 Oscar PIASTRI / 3 | 22 | 96.236 | 0.268 | 0 | 22 | 96.236 | 0.268 |
| 87 Oliver BEARMAN / 3 | 22 | 97.860 | 0.722 | 2 | 20 | 97.819 | 0.646 |

The observed window is laps 36–57. Gasly lacks 41 and 48; Sainz's primary window
ends at 43 (8 rows); Russell has only 36–37 (2 rows, explicitly marked small).
The other 16 drivers have all 22 laps. Absence from this cohort window is not a
claim of missing physical participation; pit/timing exclusions and retirement
remain distinct in the retained F1.2 audit. The sensitivity count changes are
visible for every driver, including those unaffected by notices.

## Verification

- **19 focused tests** cover known quartiles (empty, singleton, two/even/odd
  samples), invalid measurements, sensitivity/source reconciliation, exact gap
  segmentation, annotations, escaping, corrupt evidence, code/provenance drift,
  overwrite refusal and deterministic outputs. Tests use artificial source-shaped
  fixtures and forbid network access. The mock cache fixture tests downstream
  verification; a separate case checks actual cache-corruption rejection.
- An independent read-only reviewer calculated all **152 Q1/median/Q3/IQR values**
  from retained raw durations using Decimal and `statistics.quantiles` with
  `method="inclusive"`, without importing the generator. Every primary/sensitivity
  count and lap list agrees; the largest numerical difference is **1.50e−14 s**.
  They independently verified 382 source identities and all 17 annotations.
- The first focused test and reviewer caught a mutable-defaultdict lookup that
  inflated the global deletion count while leaving group statistics correct.
  Non-mutating reads fix the causal defect; the reconciliation regression passes.
- New builds `historical-data/f1-3-a` and `f1-3-b` both return expected exit 2.
  **All 22 files are byte-identical**, including JSON, HTML, 19 SVGs and manifest.
  The frozen inputs and approved spec remain unchanged. Output manifest completion
  certifies artifact writes, not historical quality or analysis readiness.
- Chromium inspection at 1365×1050 and 390×844 verified readable shared axes,
  horizontal chart panning without page overflow, selection among all 19 driver/
  stints, Gasly's two gaps, Russell's small-sample label, and 365 ordinary markers
  plus 17 deletion diamonds. All-driver and JavaScript-disabled views work.
  Downloaded SVG/JSON bytes match the separate exports; SVG opens standalone.
  No page errors or HTTP(S) requests occurred. Screenshots and browser-check
  evidence are retained under ignored `historical-data/f1-3-*` paths.
- **332 core/historical tests** (129 historical) and **250 core/API tests** pass;
  Ruff lint/format and wheel packaging pass. Hosted CI and final review closure
  are recorded in [the scoped task](../../tasks/f1-3-descriptive-report.md).

Recheck numerical/visual artifact determinism using new output suffixes:

```sh
diff -r historical-data/f1-3-a historical-data/f1-3-b
.venv-historical/bin/python -m pytest -q historical/tests/test_descriptive.py
.venv-historical/bin/python -m pytest -q tests historical/tests
.venv-api/bin/python -m pytest -q tests apps/api/tests
.venv-api/bin/ruff check .
.venv-api/bin/ruff format --check .
```

SHA-256 evidence, Python 3.11.14:

| Artifact | SHA-256 |
| --- | --- |
| Frozen F1.2 manifest | `13bdfefe045cb9502ecc269932fd800dda4e7060fda95a690317ac15bdc2a6e4` |
| Generator | `21c800429eb21b850b31fae8a9c40efc9592fdabac6727af73aea7802169368d` |
| statistics.json | `91365114a5ab97a9e048ec538319e8d9b9decfdefbe65074c427fd055e0146c5` |
| report.html | `100bc51bf42c8d986288d41d3ed8b5492a6efec6398bb5940d1a3b396bcf47ab` |
| Output manifest | `6947bd7df61324778e5cc1040e7792062e5a927d1eb9303a47b7f0b14019d24c` |
| Approved spec (unchanged) | `518ebe5e9e6473266d36338c41975054233b3e4b2ab091c4ac772588834671b3` |

## Historical closure and one next product task

This artifact completes the bounded historical workstream with an honest
observational description. **This cohort's calibration avenue is closed.**
One late-race sample cannot separate tire age, race lap, compound and driver/stint
offsets, establish causal degradation, validate a whole-race simulator, or supply
counterfactual pit losses. Shared race conditions and serially dependent laps are
not independent experiments. Neither the sensitivity subset nor the HTML report
weakens the blocked full circuit gate. Missing stationary/publication timestamps
retain their purpose-specific limits. No predictive experiment was run.

Propose one separately authorized product task: a **synthetic strategy sensitivity
lab** using explicitly assumed parameters. Compare two legal strategies under
bounded user-selected pit-loss, degradation and warm-up assumptions; show which
assumptions reverse the preference and preserve a reproducible scenario record.
Use the existing synthetic engine and label every result simulated. Historical
lap statistics must not populate these parameters. This task is only proposed;
no lab implementation, further audit, fitting or RL starts in F1.3.
