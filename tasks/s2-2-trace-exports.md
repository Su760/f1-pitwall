# S2.2 — export any retained strategy trace

Baseline `3e513f7`. Preserve unrelated `web/next-env.d.ts` and untracked
`PitWall-Arena-Project-Spec (1).md`. User authorizes implementation, verification,
scoped commit/push and hosted CI. Stop after S2.2; next proposal is a short
end-to-end product playtest, with no automatic feature expansion.

- [x] Inspect Git, guidance, S2 contracts and local UI/UX Pro Max instructions.
- [x] Record contract; serialize each retained schedule/result with trace_document.
- [x] Add opaque TS trace field and accessible rank-specific card exports.
- [x] Test downloaded default/zero-pit traces against the correct rank, including
      valid wrong-rank rejection, ties, determinism, keyboard and stale/reset cases.
- [x] Obtain distinct read-only backend/client reviews; inspect desktop/mobile.
- [x] Run applicable gates; update API/export docs, S2 spec and status with evidence.
- [x] Inspect staged scope, commit/push without force, verify hosted CI.

Allowed edits: `src/pitwall/lab_optimization.py`, `tests/test_lab_optimization.py`,
`apps/api/tests/test_optimization_api.py`, `web/lib/lab.ts`,
`web/components/lab-optimizer.tsx`, `web/app/lab/lab.css`,
`web/tests/optimization.spec.ts`, `web/tests/ranked-strategies.spec.ts`, new
`web/tests/ranked-exports.spec.ts`, `README.md`, `docs/api-contract.md`,
`docs/s2-optimization-spec.md`, `docs/status.md`, this task and `tasks/todo.md`.
No engine, optimizer, trace/replay format, scenario/configuration, dependency,
historical or approved-project-spec changes. No new export endpoint.

Contract: add `trace` to each `search.ranked` entry using the existing
`trace_document(resolved configuration, entry.schedule, entry.result)`. Reuse
retained engine data; no extra search or simulation. Version 1 remains unchanged.
Rank 1's trace equals top-level `trace`; scenario/winner exports keep their names.
Each card offers native “Export rank N trace”, filename `lab-rank-N-trace.json`,
with its pit-decision list as accessible description. Download the opaque server
object through the existing mechanism. All ranks replay with the same accompanying
`lab-optimized-scenario.json`; explain and show an accurate rank-2 CLI command.

Cards gain one aligned row/button. Tab order follows visible server order, then
existing exports; buttons remain focused after download. Existing input-revision
lifetime removes all exports on every edit/reset and ignores late responses.
Rank binding is tested against schedule, actions, stints, elapsed and full trace:
a legal trace from another rank must fail even if elapsed time is equal.

UI/UX Pro Max read at
`~/.claude/plugins/antigravity-skills/skills/ui-ux-pro-max/SKILL.md`; used documented
design-system, UX focus/touch and React semantic-button searches. Preserve existing
identity and 44px targets. Previously unavailable reviewer-tool findings carry
forward; no unavailable tool is claimed to have run.


Local evidence: 36 focused backend/API, 333 complete core/API, 129 historical and
46 desktop/mobile browser cases pass. Ruff, ordinary lint/typecheck/build, wheel
and actual downloaded CLI replay pass. Direct expected-engine trace equality
covers all records; valid wrong-rank/equal-time substitutions fail identity checks.
Repeated rank exports and legacy winner bytes match, with no added search/sims.
Independent backend review checked 20 controls/60 traces versus baseline; client
review inspected four rendered screenshots and independently replayed six actual
browser downloads. Neither review has an outstanding finding. See detailed
[S2.2 evidence](../docs/s2-optimization-spec.md#s22-verification-evidence--2026-10-18).
Initial missing-trace regression failures were expected before implementation.
Full-suite startup cleared first-run artifacts; regenerated files were inspected
and replayed for final evidence. Implementation
[`d3abc58`](https://github.com/Su760/f1-pitwall/commit/d3abc58e42d5952e404f506bf151772e99efae90)
is pushed; [CI 39102114593](https://github.com/Su760/f1-pitwall/actions/runs/39102114593)
passes all four jobs (Python 3.11/3.14, historical and production arena/browser).
S2.2 is complete; final documentation-closure commit/CI is supplied in the handoff.
