# S2 — explicit bounded lab optimization

Baseline `6a0cf12`. Preserve local `web/next-env.d.ts` and untracked
`PitWall-Arena-Project-Spec (1).md`. User authorizes execution and commit/push.
See [bounded spec](../docs/s2-optimization-spec.md).

- [x] Inspect guidance, contracts, optimizer, S1.1 review and Git state; record spec.
- [x] Implement server-owned settings, lab optimization wrapper and strict API.
- [x] Implement explicit UI action, invalidation, results and existing-format exports.
- [x] Add focused Python/API/browser regressions and downloaded CLI reproduction.
- [x] Obtain distinct read-only backend/client reviews; validate and fix findings.
- [x] Inspect desktop/mobile; run relevant complete checks; update docs/status.
- [ ] Inspect staged scope, commit/push without force and verify hosted CI.

Edit scope: new `src/pitwall/lab_optimization.py`, `scenarios/lab-optimization.json`,
`tests/test_lab_optimization.py`, `apps/api/tests/test_optimization_api.py`,
`web/components/lab-optimizer.tsx`, `web/tests/optimization.spec.ts`; existing
`apps/api/app.py`, `web/lib/lab.ts`, `web/components/sensitivity-lab.tsx`,
`web/app/lab/lab.css` if needed; this task, todo, S2 spec, API contract, model
assumptions, README and status. No engine/optimizer, dependency, historical or
approved-spec edits. Any reproduced scoped review fix is documented here.

UI/UX Pro Max: installed skill at
`~/.claude/plugins/antigravity-skills/skills/ui-ux-pro-max/SKILL.md`, read and used
for targeted loading, focus and retry guidance. Ran its documented design-system,
UX and React searches; retain the existing identity. Carry forward S1.1 missing
Ponytail, PStack and Thermo Nuclear Code Review findings; none invoked.


Local delivery evidence: 327 core/API, 129 historical, 36 production browser
cases pass; 30 focused S2 Python/API cases also rerun after tightening acceptance
tolerances. Ordinary lint/typecheck/build, Ruff, wheel and original CLI demos
pass. Actual browser exports replay and two CLI searches produce identical
winning trace content. Root and client reviewer inspected desktop/mobile.
Backend reviewer independently checked 36 parameter combinations with Decimal
arithmetic; no outstanding finding from either distinct read-only review.
See [detailed evidence and tooling](../docs/s2-optimization-spec.md#delivery-evidence--2026-10-17).
Hosted verification pending the implementation push.
