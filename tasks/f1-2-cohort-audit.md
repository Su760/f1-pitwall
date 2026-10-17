# F1.2 — 2025 retrospective cohort suitability audit

Authorized 2026-10-16: implement, verify, document, commit/push and inspect CI.
Baseline `e191918eab7da6f6f8f25834bb42efca6d378705`; preserve unrelated
`web/next-env.d.ts` and untracked downloaded spec. No new source imports, model
fitting, calibration, RL, v2 eligibility changes or threshold changes.

Scope: new `src/pitwall_historical/cohort.py`, `historical/cohort-2025.json`,
`historical/tests/test_cohort.py`, `docs/reports/f1-2-cohort-audit.md`, this task;
update `README.md`, `docs/{data-contract,status,decisions}.md`, `tasks/todo.md`.
Generated membership/exclusions/audits remain in ignored `historical-data/`.
The approved specification, quality v2 implementation and arena remain unchanged.

- [x] Read guidance/contracts, inspect Git, reproduce proposed membership count.
- [x] Implement offline deterministic selection/audit with focused tests and hashes.
- [x] Validate nine session endpoints, driver/stint coverage, control/weather joins;
      reconcile every source lap and report marginal/joint coverage and exclusions.
- [x] Diagnose identifiability algebraically without fitting; distinguish three
      analysis purposes and validation/selection limits; retain the full blocked gate.
- [x] Reproduce outputs twice; run relevant repository checks and independent review.
- [ ] Write final report/status/decisions, inspect staged diff, commit/push, verify CI.

Selection is exactly session 10014 AND existing `dry_pace_eligible` AND driver !=27.
382 is a result to verify, never a selector limit or hardcoded success criterion.
Audit raw cache integrity, regenerate v2 quality in memory with the snapshot's
unchanged config, preserve every source identity, and expose additional audit
failures separately without changing cohort membership. Use exact rational rank
and within-stint identities; no lap-duration regression or learned coefficients.
Separate descriptive suitability, conditional within-event prediction and whole-
race calibration. Unknown stationary/publication times affect only purposes that
need them. A successful cohort audit cannot promote the full circuit gate.

Initial read-only evidence: 382 rows / 19 drivers / 19 stints, laps 36–57;
182 HARD, 110 MEDIUM, 90 SOFT. Every driver's included tire age minus race lap
is constant. Independent read-only evidence/mathematical review requested.

Control review found retrospective lap-deletion messages on some selected laps.
Include a separate explicit car/lap annotation and unmatched/ambiguous message
ledger in this suitability audit. Do not alter v2 eligibility or prescribed
membership, infer a driver's lap from the control stream's leader lap, or use
later notices as decision-time inputs. Distinguish observed elapsed pace from
legal/clean-lap performance in suitability decisions.

Final local evidence (2026-10-17 UTC): 382 members + 747 distinct exclusions;
17 deletion-tagged members annotated without reselection; all 382 interval joins
pass; all nine session requests complete while the original snapshot is partial.
Exact ranks show 20/23 with driver/stint offsets: whole-race calibration is closed
for this cohort. Separate retrospective description is supported with limits;
prediction remains a conditional proposal. No model, import or threshold change.

Two new builds f1-2-a/f1-2-b returned expected exit 2 and match all four JSON files;
cache revalidation and regenerated v2 quality hash match the retained evidence.
8 focused / 313 core-historical (110 historical) / 250 core-API tests, Ruff checks
and wheel packaging pass. An initial stale-weather-reference fixture exposed a
KeyError while collecting weather samples after correctly flagging the bad join;
the artifact now collects checked prior-sample references and the regression
passes. No v2 implementation or source evidence changed. Independent read-only
code and final docs/evidence reviews found no actionable blocker. Reviewer
independently verified every reported SHA, both artifact sets, the baseline v2
report/spec hashes, coverage tables, interval/weather evidence, deletion counts
and rank proof. Publication/CI remains the final pending step.
