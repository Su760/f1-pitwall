# S1 — synthetic strategy sensitivity lab

User authorizes implementation, verification, commit/push and hosted CI.
Baseline 4a40fe28defd214a521dc24db16ade51b2c9eb10. Preserve unrelated modified
web/next-env.d.ts and untracked downloaded spec. No F2, calibration, imports or RL.

Scope: new docs/sensitivity-lab-spec.md, this task, scenarios/sensitivity-lab.json,
src/pitwall/sensitivity.py, tests/test_sensitivity.py, apps/api/tests/test_lab.py,
web/app/lab/page.tsx, web/components/sensitivity-lab.tsx, web/lib/lab.ts,
web/app/lab/lab.css, web/tests/lab.spec.ts. Update apps/api/app.py,
web/components/arena.tsx (navigation only), README.md, docs/api-contract.md,
docs/model-assumptions.md, docs/decisions.md, docs/status.md, tasks/todo.md.
Generated test/export/browser evidence remains in ignored traces/ or web reports.
Root owns edits; independent reviewer reads only.

- [x] Read guidance/contracts, inspect Git, record concise S1 spec.
- [x] Implement bounded Python comparison/grid/scenario/result exports and replay.
- [x] Add strict API and discoverable responsive lab with stale-response protection.
- [x] Focused math/API/browser tests; visible reversal/reset/rapid changes, exports.
- [x] Independent read-only review; repository checks; documentation/status.
- [x] Inspect staging, commit/push, check hosted CI; stop at usable S1.

Implementation choices: standard library core; reuse existing request-size parser,
Next proxy and UI styles where suitable. Dedicated scoped lab CSS. Teal/amber
sample grid with explicit 1/2/= symbols, shared axes and keyboard cell details.
No charting dependencies. Backend owns all numeric comparisons and labels.

Verification notes: 297 core/API and 356 core/historical tests pass; Ruff and wheel
pass. Web lint/typecheck/build pass with `npm run lint -- --ignore-pattern
'artifacts/**'`: default local lint encounters pre-existing ignored
`web/artifacts/f1-playwright.config.ts:4` (`Unexpected any`); preserved that artifact.
Clean CI does not contain it. Next-generated next-env.d.ts will be restored to its
original local content before staging.

Initial browser run: 22 passed / 2 failed, both the error-test locator matching
Next's route announcer in addition to the lab alert. Scoped the test to main;
no product workaround. Independent review found equivalent numeric edits could
clear the response without changing the effect key; request revision now changes
on every edit. Regression explicitly covers 18 → 18.0. Independent arithmetic
matches 1,323 sampled comparisons (maximum difference 4.55e-13 s).

Final local evidence: all 24 production browser cases pass (18 existing + 6 S1).
Root/reviewer inspected desktop/mobile screenshots for readable controls, axes,
text symbols, timelines/components and contained horizontal map scrolling. Real
browser-downloaded scenario comparison equals the result's comparison; full record
replays exactly and two canonical outputs are byte-identical. Ignored evidence:
traces/lab-{scenario,result,comparison,verified,verified-second}.json and web test
results. Existing next-env.d.ts restored byte-for-byte; approved spec SHA-256
518ebe5e9e6473266d36338c41975054233b3e4b2ab091c4ac772588834671b3 unchanged.
Final independent review has no outstanding findings.

Publication: implementation commit `83636f7ff6911c33de32fa09e3c40e259ee97d5a`
pushed to origin/main without force. [CI 39009001641](https://github.com/Su760/f1-pitwall/actions/runs/39009001641)
passed historical, core Python 3.11/3.14 and arena (including production-browser)
jobs. This docs-only closure records observed evidence; final handoff reports its
own commit/CI. No further task started. Unrelated local work remains preserved.
