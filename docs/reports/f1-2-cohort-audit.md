# F1.2 — 2025 retrospective cohort suitability audit

Checked 2026-10-17 UTC against baseline `e191918eab7da6f6f8f25834bb42efca6d378705`.
This audit reproduces **382 included / 747 distinct excluded / 1,129 source laps**.
The cohort supports bounded description of recorded late-race elapsed laps. It
**cannot identify whole-race tire calibration or support strategy simulation**;
that calibration avenue is closed for this cohort. No model was fitted. The full
circuit gate remains **blocked**, with unchanged `f1-audit-v2` eligibility and
thresholds. The synthetic arena and approved specification are unchanged.

## Evidence and deterministic selection

Use retained OpenF1 snapshot `20261013T173926.193125Z-f1d80d3ff360`, schema 1,
and its embedded configuration. No source requests were made. All cached response
hashes and manifest relationships are validated before normalization. The complete
candidate snapshot remains partial: 26 successful requests / 27, including the
original 2023 pit HTTP 404. That failed response, every original value and null,
and the F1.1 supplemental evidence remain intact.

Selection is exactly **session 10014 AND existing `dry_pace_eligible` AND driver
number != 27**. The number 382 is an observed result, never an input or success
threshold. Session 10014 is the 2025-04-13 Bahrain Race, meeting 1257, circuit
63 / Sakhir. All nine requests for this session succeeded:

| Endpoint | Source rows |
| --- | ---: |
| sessions | 1 |
| meetings | 1 |
| drivers | 20 |
| laps | 1,129 |
| stints | 62 |
| pit | 42 |
| race_control | 93 |
| weather | 158 |
| session_result | 20 |

`audit.json.session_requests` retains each request's parameters, retrieval time,
response hash and status; provenance config retains the source base URL. The reconstructed quality JSON hashes to
the existing F1.1 report exactly; no new quality semantics or source repair is
hidden in this selection. Driver 27 remains excluded by explicit proposal scope:
his 57 physical laps and later technical DSQ are separate facts, and his OpenF1
completed-lap null is not filled from FIA evidence. See the
[F1.1 evidence review](f1-1-readiness-review.md).

The offline module writes four files into a new directory:

- `membership.json`: all selected quality rows, their original physical
  `source_request` / zero-based `source_row`, referenced stint/weather sources,
  and an empty cohort exclusion list.
- `exclusions.json`: every other physical session lap, original v2 flags/reasons
  plus the explicit driver exclusion; overlapping reasons remain visible.
- `audit.json`: reconciliation, endpoint and driver evidence, all included-driver
  stint audits, individual interval checks, control/weather evidence, deletion
  annotations, coverage, exact design ranks and separate suitability decisions.
- `manifest.json`: write status, provenance and hashes of the three artifacts.

Every document records snapshot/manifest, canonical config, selection file and
canonical selection, regenerated quality report, every historical Python module
and combined code hashes, plus Python version. Artifact write status `complete`
means the files were written; it does **not** promote the partial source snapshot
or blocked circuit gate. Outputs contain no run time or output-directory path.
They remain outside Git. The exact source row identity, rather than a driver/lap
natural key, partitions every original row without discarding duplicate evidence.

## Reconciliation and exclusions

V2 supplies 404 eligible and 725 ineligible rows. Driver 27 contributes 57 source
rows: 35 already ineligible and 22 additionally excluded. Thus
`1129 = 382 + (725 + 22) = 382 + 747`. The following counts overlap; their sum
is **not** the number of excluded rows:

| Reason | Rows |
| --- | ---: |
| neutralization_unknown | 621 |
| pit_associated_lap | 84 |
| pit_boundary_semantics_uncertain | 84 |
| neutralization_affected | 80 |
| excluded_driver:27 | 57 |
| observed_pit_out_lap | 42 |
| sector_timing_unavailable | 25 |
| opening_lap | 20 |
| lap_timing_overlap | 3 |
| compound_unavailable | 1 |
| invalid_lap_duration | 1 |
| lap_timing_gap | 1 |
| missing:lap_duration | 1 |
| tyre_age_unavailable | 1 |
| unmatched_stint | 1 |
| weather_unknown | 1 |

All 19 included drivers have complete independently assessed participation
coverage. Eighteen completed 57 laps. Sainz completed 45; his untimed started lap
46 is preserved as a retirement tail, not a missing completed lap. The source
contains 59 stints for these drivers, with zero unresolved stint consistency
flags under v2 (informational pit-boundary uncertainty is retained). The cohort
itself contains only 19 stints, exactly one per driver. Metadata have no missing
required fields, conflicts, duplicate records or unmatched joins; member stint
joins are unique and tire age follows the observed starting age and lap offset.

## Coverage and common conditions

Intervals below are inclusive. A range does not imply every interior age/lap is
present where the notes identify holes. Source stint rows refer to request
`stints-session_key-10014`; membership records retain each lap's own source row.

| Driver | Stint / source row | Compound | Rows | Race laps | Tire ages before lap |
| --- | --- | --- | ---: | --- | --- |
| 1 Verstappen | 3 / 40 | MEDIUM | 22 | 36–57 | 9–30 |
| 4 Norris | 3 / 50 | MEDIUM | 22 | 36–57 | 3–24 |
| 5 Bortoleto | 3 / 60 | MEDIUM | 22 | 36–57 | 3–24 |
| 6 Hadjar | 3 / 46 | HARD | 22 | 36–57 | 7–28 |
| 7 Doohan | 3 / 45 | HARD | 22 | 36–57 | 7–28 |
| 10 Gasly | 3 / 44 | HARD | 20 | 36–57 except 41,48 | 7–28 except 12,19 |
| 12 Antonelli | 4 / 55 | SOFT | 22 | 36–57 | 6–27 |
| 14 Alonso | 3 / 57 | HARD | 22 | 36–57 | 3–24 |
| 16 Leclerc | 3 / 49 | HARD | 22 | 36–57 | 3–24 |
| 18 Stroll | 3 / 59 | HARD | 22 | 36–57 | 3–24 |
| 22 Tsunoda | 3 / 53 | SOFT | 22 | 36–57 | 3–24 |
| 23 Albon | 3 / 56 | MEDIUM | 22 | 36–57 | 3–24 |
| 30 Lawson | 3 / 58 | SOFT | 22 | 36–57 | 3–24 |
| 31 Ocon | 3 / 42 | HARD | 22 | 36–57 | 8–29 |
| 44 Hamilton | 3 / 51 | HARD | 22 | 36–57 | 3–24 |
| 55 Sainz | 3 / 52 | HARD | 8 | 36–43 | 3–10 |
| 63 Russell | 3 / 48 | SOFT | 2 | 36–37 | 6–7 |
| 81 Piastri | 3 / 47 | MEDIUM | 22 | 36–57 | 3–24 |
| 87 Bearman | 3 / 54 | SOFT | 22 | 36–57 | 3–24 |

Compound totals: HARD 182 rows / 9 drivers, MEDIUM 110 / 5, SOFT 90 / 5.
Age counts are `3:12, 4:12, 5:12, 6:14, 7:17, 8:17, 9:18, 10:18, 11:17,
12:16, 13:17, 14:17, 15:17, 16:17, 17:17, 18:17, 19:16, 20:17, 21:17,
22:17, 23:17, 24:17, 25:6, 26:6, 27:6, 28:5, 29:2, 30:1`. Ages 0–2 and
warm-up are absent. Race-lap counts are `36:19, 37:19, 38:18, 39:18, 40:18,
41:17, 42:18, 43:18, 44:17, 45:17, 46:17, 47:17, 48:16`, then 17 each on
49–57. The artifact also supplies compound-by-age and compound-by-race-lap
counts; marginal overlap is not independent within-driver variation.

Gasly's laps 41/48 and Russell's 38–57 lack sector timing. Russell additionally
has a gap on 38 and overlaps on 39/45/49. Sainz's 44/45 are conservatively pit
associated and 46 is the untimed tail. These are data-dependent exclusions, not
random sampling. The cohort overrepresents surviving, well-recorded late stints
and excludes nearly all earlier race conditions. Compound choices are associated
with driver/car/team and strategy. All cars share race evolution, fuel burn,
traffic and the post-safety-car window; 382 rows are not 382 independent races.

Control references below use `race_control-session_key-10014`. Row 40 deploys
the safety car at 15:56:09 UTC. The simultaneous row 41 sector-3 CLEAR does not
end it; row 43's 16:02:20 IN THIS LAP also does not. Row 44 provides an explicit
TRACK CLEAR at **16:03:55**. The first selected interval starts **16:04:13.835**,
18.835 seconds later; the last ends **16:40:35.989**. The next hazard, row 89's
sector-1 double yellow at 16:52:34, is after all selected intervals. The leader's
16:39:28.840 session-finished message is not every following car's finish time.
Other-category infringement notices are not fresh safety-car deployments.
All 382 half-open `[start, end)` interval checks pass, with no unresolved state
transition since the prior explicit global clear. This audit conservatively
flags any such transition for review; it never silently changes membership.

Each selected lap uses the unique latest weather sample at or before its start:
34 distinct samples, all rainfall 0, ages **0.133–59.968 seconds**, within the
unchanged 120-second cap. Their air temperatures span 26.7–26.9°C, track
30.2–31.0°C, humidity 43–46%, pressure 1008.2–1008.5 mbar and wind 1–2.5 m/s.
These are sampled dry candidates, not proof of a uniformly dry surface or
independent weather experiments. No future sample is used.

### Retrospective deletion annotations

There are 36 control messages containing DELETED, all with explicit car/lap
references; zero ambiguous or unmatched explicit messages in this snapshot.
**17 selected rows across 11 drivers** carry deletion notices. Their car/lap
pairs are `4/36, 14/36, 55/36, 16/38, 44/42, 12/36, 1/45, 7/42, 1/48,
4/49, 22/50, 87/52, 22/52, 87/54, 1/55, 7/56, 18/57`.
The corresponding control source rows are
`47,49,50,53,61,62,64,65,68,72,74,76,77,79,80,84,87`.

V2 does not exclude these notices; F1.2 preserves the prescribed 382 members.
The target is **recorded elapsed lap intervals**, not legal clean-lap pace.
The annotation maps explicit message car/lap text, never the control stream's
leader lap number; ambiguous NEXT LAP text would remain unresolved. Later
notices, including notices after the leader finishes, are retrospective evidence
and cannot be backfilled as available decision-time features.

## Identifiability without fitting

For every selected stint g and lap i, the observed join gives
`A_i = L_i + c_g`, where `c_g = tyre_age_at_start - lap_start`.
Each driver has exactly one selected stint; each stint has one compound. The
module performs exact rational elimination of integer predictor matrices, using
an intercept and reference-coded categories. It never reads lap duration for
these diagnostics and estimates no pace coefficient.

| Design | Columns | Exact rank | Nullity |
| --- | ---: | ---: | ---: |
| Intercept + race lap + age + compound | 5 | 5 | 0 |
| Driver offsets + race lap | 20 | 20 | 0 |
| Stint offsets + race lap + age | 21 | 20 | 1 |
| Stint offsets + race lap + age + compound | 23 | 20 | 3 |
| Driver offsets + race lap + age + compound | 23 | 20 | 3 |
| Driver and stint offsets | 37 | 19 | 18 |

For a hypothetical additive expression `alpha_g + beta_L L + beta_A A`, change
`beta_A` by delta, `beta_L` by minus delta and `alpha_g` by `-delta*c_g`:
its value is identical on every selected row. Compound indicators are sums of
stint/driver indicators; compound effects can likewise be absorbed by offsets.
Driver and stint effects are inseparable here. The first matrix's full rank
merely omits driver/stint heterogeneity; it does not identify physical tire wear.
Adding flexible race-lap effects cannot solve this confounding. Association is
not causal degradation; no optimizer or regularizer would supply the missing
identification evidence. More stints alone also do not break age/lap dependence
when every stint is allowed an unconstrained offset.

## Separate suitability decisions

| Purpose | Decision | Limits / acceptance criteria |
| --- | --- | --- |
| Descriptive late-race elapsed pace | Suitable with limits | Describe the frozen members by driver/stint with counts, missingness and deletion annotations; no pure compound ranking, causal wear, legal-clean label or whole-race extrapolation. |
| Limited within-event prediction | Conditional proposal only | Predeclare target, features, horizon and validation before any separately authorized experiment. Use chronological blocks shared across cars, with a purge/gap justified by lookback/horizon. Report baseline comparisons and uncertainty; any unseen-driver check answers a different question. |
| Whole-race tire calibration and strategy simulation | Not supported; closed for this cohort | Missing early/young-tire regimes, inseparable offsets/age/lap/compound, uncontrolled fuel/traffic/track effects, no counterfactual incremental pit loss or independent-event validation. |

Random adjacent-lap train/test splitting would leak strongly dependent race
conditions and serial information. One event supplies **no held-out-event
performance estimate**. Time blocks still share an event and do not establish
transportability to other years, tracks, compounds or strategies. Retrospective
selection uses completed quality/stint evidence; it cannot establish a deployable
decision-time pipeline. Final stint outcomes and later deletion notices cannot
be used as if known before a predicted lap. No experiment or performance claim
is made here.

Missing stationary times (2 of 42 pit rows) do not block elapsed-lap description
or a suitably specified retrospective prediction target. They do block analyses
requiring those stop measurements. Event dates are not established publication
timestamps; this blocks decision-time availability claims, not retrospective
summaries. Lane duration, stationary duration and incremental race-time pit loss
remain distinct; none supplies the stay-on-track counterfactual.

## Reproduction and verification

From the repository root, with the locked historical environment installed as
in README, use unused output directories. No import command is required:

```sh
SNAPSHOT=historical-data/raw/20261013T173926.193125Z-f1d80d3ff360
for BUILD in historical-data/f1-2-a historical-data/f1-2-b; do
  CODE=0
  .venv-historical/bin/python -m pitwall_historical.cohort "$SNAPSHOT" \
    --selection historical/cohort-2025.json --output "$BUILD" || CODE=$?
  test "$CODE" -eq 2 || { echo "Unexpected exit: $CODE"; exit 1; }
done
diff -r historical-data/f1-2-a historical-data/f1-2-b
.venv-historical/bin/python -m pytest -q historical/tests/test_cohort.py
.venv-historical/bin/python -m pytest -q tests historical/tests
.venv-api/bin/python -m pytest -q tests apps/api/tests
.venv-api/bin/ruff check .
.venv-api/bin/ruff format --check .
```

Expected exit **2** explicitly preserves partial source status despite supported
cohort description. Exit 1 is an execution failure, including corrupt evidence
or an existing output directory. Use fresh suffixes when repeating. Reproduction
requires the retained local cache; generated datasets are intentionally not in Git.

Both final builds `historical-data/f1-2-a` and `f1-2-b` returned exit 2 and
match byte-for-byte across all four files on Python 3.11.14. The retained cache
was revalidated afterward. The regenerated quality hash equals the existing
`historical-data/f1-1-a/quality.json` exactly. SHA-256 evidence:

| Evidence | SHA-256 |
| --- | --- |
| Raw manifest | `22b92984adf14a904d3b3bfd924530dbcb903190a77f101c3280bd4ce6ffdc21` |
| Canonical configuration | `9babad255ada5b9c24134b229ae17183a79c938d4a70efa87d721646928fc6c2` |
| Selection file | `378b718fb25a6437cc4cfbb56e325d72b252a13c883dfdaa62a62f97774d4aac` |
| Canonical selection | `ba9f0dc7108e855bba0aa84ad81dd29ef58befaa3ccf377eceee4fe465abe20c` |
| Reproduced v2 quality JSON | `d6c2ac6c7958820df769703b81c42f61c4661253d4c18e67f328c2f02a50ed36` |
| Historical code bundle | `09b4d3da09effe887edf7016302c1ebc6d1d0561f0cb857c6236c4639cdbf457` |
| audit.json | `3dfe6564346d05260f7c4c8c89d3d36afc333aa90e6098819e8d584a2bf75b2b` |
| exclusions.json | `4ffb28f56880895e7e2c2d7771d8223313607d6cbc76a7eec051a1337c583e63` |
| manifest.json | `13bdfefe045cb9502ecc269932fd800dda4e7060fda95a690317ac15bdc2a6e4` |
| membership.json | `bde7ae1fcdb4a0020191992b9a0deae847ce8728b83c16f9a71bbcfc42ff79ce` |
| Unchanged approved spec | `518ebe5e9e6473266d36338c41975054233b3e4b2ab091c4ac772588834671b3` |

Code hashes identify the implementation independently of the later Git commit.

Local verification: 8 focused cohort tests, 313 combined core/historical tests
(110 historical), 250 core/API tests, Ruff lint/format and wheel packaging pass.
Independent read-only code review verified the selector, disjoint partition,
nine endpoints, unchanged gate and rank diagnostics with no actionable findings.
Independent final evidence review also verified the hashes, coverage tables,
weather/control values and deletion counts. Hosted CI is recorded in the
[task closure](../../tasks/f1-2-cohort-audit.md). No local
browser rerun was needed for unchanged UI code; the hosted arena job covers it.

## One concrete next task

Propose a separately authorized **descriptive late-race elapsed-lap report** on
these exact 382 members: per-driver/stint counts, medians and dispersion, with
race-lap-aligned plots, explicit missingness and the 17 deletion annotations.
Keep the primary cohort fixed and show a separately labelled deletion sensitivity
summary. Accept it only if every statistic reconciles to frozen source identities,
no future information is framed as a decision-time feature, and no compound
causal ranking, fitted degradation, simulator parameter or performance claim is
produced. F1.2 stops here; this proposal is not an implemented analysis or F2.
