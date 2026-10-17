# F1.3 — frozen cohort descriptive visual report

Authorized 2026-10-17: implement, verify, document, commit/push and check CI.
Baseline d48dadee3b6f74bad14c692f5889509214eeaa66. Preserve unrelated
web/next-env.d.ts and the untracked downloaded spec. Approved spec unchanged.
No imports, eligibility changes, fitting, simulator calibration or new audit.

Scope: add src/pitwall_historical/descriptive.py,
historical/descriptive-2025.json, historical/tests/test_descriptive.py,
docs/reports/f1-3-descriptive-report.md and this task. Update README.md,
docs/status.md, docs/decisions.md and tasks/todo.md. All generated artifacts and
browser evidence stay under ignored historical-data/. Root owns edits; independent
reviewer reads only. Existing F1.2 code/config and core/API/web stay untouched.

- [x] Inspect Git and read guidance/spec/contract/F1.2 evidence/status.
- [x] Pin and validate retained F1.2 manifest/artifact hashes and source provenance;
      join frozen row identities to observed durations without reselection.
- [x] Build deterministic JSON statistics and self-contained HTML/SVG charts:
      driver/stint counts, exact lap coverage, median/Q1/Q3/IQR, explicit quantile
      convention and small samples. Preserve gaps, all primary rows and deletion
      annotations; separate sensitivity counts/statistics with 17 rows omitted.
- [x] Known-answer/corruption/reconciliation tests; independent numerical check;
      two new builds; rendered desktop/mobile/selection/export inspection.
- [x] Independent read-only review, documentation/status and scoped diff review.
- [x] Commit/push and verify hosted CI; close historical calibration avenue.

Design: no added dependencies. Inline SVG plots plus per-driver SVG exports,
HTML driver selection with accessible tables and no remote assets/fetches. Driver
order follows number, not pace. Shared axes preserve comparison context; lines
connect consecutive observed race laps only. Quantiles use linear interpolation
at zero-based (n-1)*p (Hyndman-Fan type 7); empty sensitivity is null, singleton
has zero IQR but visibly n=1. No inference or independence claim. Integrity failures
stop before output creation. Artifact completion is distinct from partial source
and blocked full circuit gate. Validate only the historical modules listed in the
frozen provenance so adding this generator does not rewrite the F1.2 evidence.

One next product proposal only: synthetic strategy sensitivity lab with explicitly
assumed parameters. No implementation of that task or further historical audit.

Visual plan (frontend-design skill): white #ffffff plot paper, slate #243746
text, cool #f1f5f8 surrounding page, teal #087e8b observations, amber #b45309
deletion diamonds, #cbd5df grid. System sans for readable offline body/axes,
Georgia headline for a restrained report title. Left-aligned report header,
full-width chart, compact selected-driver metrics, then the comparison table
and expandable provenance. Avoid decorative dashboards; the observation plot
is the primary visual. Browser checks cover both desktop and narrow screens.
The referenced ~/.Codex/rules/ui-ux-pro-max/AGENTS.md was absent; installed
frontend-design guidance was read instead. No UI dependencies added.

Local verification: both f1-3-a and f1-3-b return expected exit 2 and match all 22
files, including statistics/HTML/19 SVGs/manifest. 19 focused / 332 core-historical /
250 core-API tests, Ruff checks and wheel pass. Chromium desktop/mobile/selection/
downloads/no-JS checks pass with zero page errors or network requests. Visual
inspection confirms readable axes, real gaps and tagged diamonds; mobile charts
pan horizontally without document overflow. Evidence stays in historical-data/.

Root-cause correction before final builds: reading tags[key(lap)] from a
mutable defaultdict inserted untagged keys, causing inflated global tag counts
while per-group statistics remained correct. A non-mutating get fixes it; the
known-answer global reconciliation test catches it. Independent review reproduced
this defect and verified its correction. All 152 final summary quantities match
an independent Decimal/inclusive-quantile calculation within 1.50e-14 seconds.

Final independent read-only review passes: all 22 final files and published
hashes checked, all 152 statistics independently recalculated, Markdown counts/
rounded values checked, final screenshots inspected. No outstanding findings.
Publication and hosted CI verified below.

Implementation commit
[`edd96e68149efd03bf69249915f5dd744e3eff08`](https://github.com/Su760/f1-pitwall/commit/edd96e68149efd03bf69249915f5dd744e3eff08)
is pushed to origin/main without force. [CI 38999607994](https://github.com/Su760/f1-pitwall/actions/runs/38999607994)
passed historical, core Python 3.11/3.14 and production-browser arena jobs.
This documentation-only closure records those results; its exact commit/CI are
supplied in the final handoff. No generated datasets, environments, secrets or
unrelated files were staged. The approved spec and frozen F1.2 inputs are intact.

F1.3 and this bounded historical workstream are complete as descriptive work;
the circuit gate remains blocked and this cohort's calibration avenue is closed.
One next product proposal only: the explicitly synthetic strategy sensitivity
lab documented in the report. No implementation or further audit was started.
