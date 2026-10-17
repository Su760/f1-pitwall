# S1.1 — bounded code-quality and UX pass

Baseline 78c1ac0b5c62f1ce0cf9324cdd6363ccc8a54b53. Preserve modified
web/next-env.d.ts and untracked downloaded spec; no S2, calibration or RL.

Scoped edits: web/components/sensitivity-lab.tsx, web/app/lab/lab.css,
web/tests/lab.spec.ts, web/eslint.config.mjs, docs/sensitivity-lab-spec.md,
docs/reports/s1-1-review.md, docs/status.md, tasks/todo.md, this task,
tasks/lessons.md. AGENTS.md only if a concise reusable rule is warranted.
Expand this plan before any other file edit, based on demonstrated findings.
Root owns implementation; reviewers read only with distinct backend / client focus.

- [x] Inspect status, guidance/contracts; discover requested tools/read instructions.
- [x] Reproduce tab-stop/lint defects and review rendered desktop/mobile UI.
- [x] Implement one grid Tab stop, directional navigation, visible focus and exit;
      verify refresh behavior and all sampled descriptions. Narrow generated ignores.
- [x] Validate/consolidate independent numerical/API and client-state reviews;
      fix only reproduced scoped issues. Apply UI UX Pro targeted recommendations.
- [x] Run focused/full checks, acceptance/export replay, normal lint and UI inspection.
- [x] Record actual tool paths/use/findings/evidence; stage scoped files, commit/push,
      verify hosted CI and stop. S2 is proposed, never implemented.

Interaction choice: WAI data-grid semantics on the existing table, roving button
focus, arrows without wrapping, Home/End within row and Ctrl+Home/End across grid.
Tab/Shift+Tab exit normally. A refreshed result resets the entry cell to top-left;
focus stays on the edited control/reset button, never jumps into new results.
Any additional UX change must have a rendered, measurable cause.

Confirmed rendered UX findings: mobile sample targets measure 36.375×28 px;
row-axis labels scroll out of view at rightmost columns. Keep the existing table,
enlarge sample buttons to 44×44 minimum, and pin row headers while scrolling.
Retry comparison also removes its focused button during loading; restore focus
to the persistent Reset assumptions button before removal, with a regression.

The same disappearing-focus defect was independently reproduced for Retry lab
setup (BODY immediately and after response). Move focus to the persistent lab
heading before removing that button; next Tab reaches the first control.

Final rendered review found the enlarged grid puts pit-loss column headers above
the viewport at lower rows (root and independent screenshot review agree).
Keep the same grid, bound its scrolling viewport, pin column headers too, and
regress focused-cell visibility below/alongside both pinned axes.

Final local checks: 297 core/API +129 historical pass; Ruff, ordinary npm lint,
typecheck and production build pass. 28 browser cases pass (including preserved
18 challenge cases), all acceptance points, 441-keyboard-cell traversal, both retry
paths and actual downloaded JSON replay twice. Rendered 375/768/1024/1440 checks
show no page overflow, persistent axes and focused samples not hidden by headers.
No backend numerical/API change. UI UX Pro actual commands and missing requested
tools are recorded in docs/reports/s1-1-review.md. Independent reviewers read only.

Publication: scoped implementation `34126a8468e5b3ed5499d20e2079a65dd527d14c`
is pushed without force; [CI 39012839475](https://github.com/Su760/f1-pitwall/actions/runs/39012839475)
passed all four jobs. Final independent review closes the pinned-axis finding.
This docs-only closure records the result; its exact commit/CI is in the handoff.
Stop at S1.1; no other feature started. All unrelated local work remains intact.
