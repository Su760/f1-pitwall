# S2.1 — compare the three retained legal schedules

Baseline `b02a670`. Preserve unrelated `web/next-env.d.ts` and untracked
`PitWall-Arena-Project-Spec (1).md`. User authorizes implementation, verification,
commit/push and hosted CI. Stop after S2.1. No search/model/historical changes.

- [x] Inspect Git, guidance, S2 contracts and installed UI/UX Pro Max instructions.
- [x] Add scoped contract/spec; expose retained engine stints and exact tie ranks.
- [x] Extend TS contract and render ordered cards with shared 1–12 lap scale.
- [x] Verify default/tie/rounded-alike cases, engine correspondence, no extra work,
      invalidation, keyboard and downloaded winner replay; inspect desktop/mobile.
- [x] Obtain separate read-only backend/client reviews, resolve reproduced findings.
- [x] Run applicable gates; record evidence in S2 spec and status.
- [x] Inspect scoped staged changes, commit/push without force, verify hosted CI.

Allowed edits: `src/pitwall/lab_optimization.py`, `tests/test_lab_optimization.py`,
`apps/api/tests/test_optimization_api.py`, `web/lib/lab.ts`,
`web/components/lab-optimizer.tsx`, `web/app/lab/lab.css`,
`web/tests/optimization.spec.ts`, new `web/tests/ranked-strategies.spec.ts`,
`docs/s2-optimization-spec.md`, `docs/api-contract.md`, `docs/status.md`,
this task, `tasks/todo.md`, and the README export-button label (changed by this UI). No engine/optimizer, configuration, dependency,
S1 controls/map, approved-spec or historical edits.

Design/contract: retain existing server order and existing formats/version 1;
add `rank`, engine `stints`, and `exact_tie_ranks` (other retained ranks with
exactly equal full-precision elapsed time) to each ranked entry. Exact equality
uses no tolerance and never compares formatted strings. No additional simulations.
Cards use semantic ordered-list structure, three equal columns on desktop,
stack on mobile, common aligned rows and a 12-column race-lap timeline with
numbers 1–12, compound letters plus full compound names/lap ranges separately.
No minimum segment width may distort the shared scale. Every card shows elapsed,
Python gap, exact-tie status and full-precision values; rounded matches are not
labelled ties. Explain deterministic order and no robustness/confidence claims.
Label the unchanged winning trace as rank 1 only. No new focusable card controls;
preserve search→export Tab flow and existing revision/abort handling.

UI/UX Pro Max: read installed
`~/.claude/plugins/antigravity-skills/skills/ui-ux-pro-max/SKILL.md`; ran documented
`search.py --design-system`, UX color/labels and React semantic-list searches.
Apply existing theme, responsive layout and textual non-color cues. Previously
unavailable Ponytail/PStack/Thermo Nuclear findings carry forward; none invoked.


Local evidence: 331 core/API, 129 offline historical and 42 production browser
cases pass. The final capture-only harness adjustment was additionally verified
with the targeted one-lap/responsive case. Ordinary lint/typecheck/build, Ruff
lint/format, wheel and actual downloaded winning-trace CLI replay pass. Two
independent CLI searches reproduce the downloaded trace exactly. Root inspected
375/768/1024/1440px; reviews have no outstanding findings. No additional engine
or optimizer work, altered search scope, numerical rules or historical changes.

One supplementary 1024px image was blank after rapid viewport changes despite
passing geometry. Stabilized test capture with instant positioning plus two
paint frames, then regenerated and visually inspected it; no application change.
Valid responsive captures are under ignored `web/test-results/s21-responsive/`.
Before-implementation regression output was expected `KeyError: 'rank'` (four
new cases); all now pass. Implementation
[`1920319`](https://github.com/Su760/f1-pitwall/commit/1920319b39758fef1b1cb3a3256a6bc40a10f8ec)
is pushed; [CI 39056718773](https://github.com/Su760/f1-pitwall/actions/runs/39056718773)
passes all four jobs (Python 3.11/3.14, historical and production arena/browser).
S2.1 is complete; final documentation-closure commit/CI is supplied in the handoff.
