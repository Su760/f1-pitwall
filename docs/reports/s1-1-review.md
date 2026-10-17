# S1.1 — bounded lab quality and usability review

Reviewed 2026-10-17. Baseline `78c1ac0b5c62f1ce0cf9324cdd6363ccc8a54b53`;
S1 implementation `83636f7`. Scope is the existing synthetic `/lab`, not F2.
The approved project spec, numerical engine, API, export schema, fixed schedules,
challenge fixtures and historical evidence remain unchanged.

## Actual tool discovery and use

Searched installed skill/plugin/command filenames and instruction contents under
`~/.agents`, `~/.codex/skills`, `~/.codex/plugins`, `~/.codex/prompts`,
`~/.claude/skills`, `~/.claude/commands`, `~/.claude/plugins`, `~/.Codex/rules`,
plus filenames under `~/.config` and `~/.local/bin`. Followed skill symlinks and
checked shell startup/config files for the missing tool names (filename-only
matching, without printing unrelated settings). Queried shell PATH with
`command -v ponytail pstack thermo-nuclear-code-review ui-ux-pro uipro`.
No tools were installed or global configuration changed during this task.

| Requested tool | Actual availability / identity | Work performed |
| --- | --- | --- |
| Ponytail | Not found in inspected installed instructions, commands or PATH | Not invoked; backend fallback review below |
| PStack | Not found in inspected installed instructions, commands or PATH | Not invoked; client fallback review below; did not assume it means gstack |
| Thermo Nuclear Code Review | No matching instruction/command found, including thermonuclear spelling | Not invoked; findings consolidated from independent fallback reviews |
| UI UX Pro | Available as community **UI/UX Pro Max** in Antigravity skills | Actual search CLI plus targeted rendered touch/focus/label review; not a separately executed autonomous UI reviewer |

UI skill read before use:
`/Users/supashramesha/.claude/plugins/antigravity-skills/skills/ui-ux-pro-max/SKILL.md`.
No standalone semantic version is declared. Bundle Git revision:
`d25d06c29b32148be51505c5c9b84b3e38e0e2b1`; SKILL SHA-256:
`6aad875f675e5909272c78ed2b9011115566233059ea2b71ba4d4a5c3a5d78f7`.
The older referenced `~/.Codex/rules/ui-ux-pro-max/AGENTS.md` is still absent;
this installed skill is the available implementation, not that missing file.

Executed its documented Python CLI (Python 3.14.2):

```sh
python3 /Users/supashramesha/.claude/plugins/antigravity-skills/skills/ui-ux-pro-max/scripts/search.py 'motorsport analytical dashboard dark compact accessible existing design' --design-system -p 'PitWall S1.1'
python3 /Users/supashramesha/.claude/plugins/antigravity-skills/skills/ui-ux-pro-max/scripts/search.py 'keyboard focus touch target horizontal scroll' --domain ux -n 5
python3 /Users/supashramesha/.claude/plugins/antigravity-skills/skills/ui-ux-pro-max/scripts/search.py 'focus keyboard accessibility' --stack react
```

Applied its visible-focus, 44px touch-target and labelled-control guidance.
Preserved the existing palette/fonts and contained map scrolling; rejected generic
palette/font/landing-page recommendations as outside this targeted review. Tool
recommendations alone are not evidence of accessibility conformance.

Other actual capabilities: Superpowers 7.0.0 instruction files under
`~/.codex/plugins/cache/claude-plugins-official/superpowers/7.0.0/skills/`
(`using-superpowers`, `systematic-debugging`, `verification-before-completion`)
were read for evidence-first workflow. Playwright 1.63.0 / Chromium 153.0.8010.12 inspects the
real production app; ESLint 9.39.5 checks the retained local filesystem.

Independent read-only fallback reviewers had distinct ownership:

- `/root/s11_backend_review`: Python numerical accounting, legality, API validation,
  work bounds, provenance and exact export replay. No rendered UI claim.
- `/root/s11_client_review`: request races, equivalent inputs, reset/retry, exports,
  grid semantics and focus code/tests. No independent browser execution claim.
- Root: actual UI UX Pro commands, defect reproduction, code fixes, live rendered
  desktop/mobile inspection, browser checks, report consolidation and publication.

## Validated findings and fixes

References to original lines below are at baseline `78c1ac0`.

1. **441 sequential map Tab stops** —
   `web/components/sensitivity-lab.tsx:306` rendered every sample as an ordinary
   button, plus a focusable scrolling wrapper at line 282. Browser counted 441
   buttons with nonnegative tabIndex; Tab from the first moved to the second.
   The table now has data-grid semantics, labelled headers, one roving Tab stop,
   bounded arrow navigation, Home/End and Ctrl+Home/End. Tab exits to Export scenario;
   Shift+Tab exits to Reset assumptions. Re-entry remembers the inspected point.
   All 441 samples retain button descriptions and text winner symbols.

2. **Normal local lint failed on generated evidence** —
   `web/eslint.config.mjs:8` omitted the already Git-ignored `web/artifacts/`.
   That directory contains four captured PNGs and a temporary F1 alternate-port
   Playwright config, documented in the F1 task history. `npm run lint` reproduced
   `f1-playwright.config.ts:4:35 Unexpected any` and the line-5 anonymous-export
   warning. Added only `artifacts/**` to the web-local global ignores. No files
   removed/rewritten. ESLint's `isPathIgnored` confirms app/component/test source
   and the real Playwright config remain included; `lintText` confirms the
   no-explicit-any rule still fires for component and test paths.

3. **Mobile targets and axis context** — `web/app/lab/lab.css:206` set 28px cell
   height; browser measured 36.375×28px at 375px viewport. Original row headers
   scrolled off-screen when inspecting rightmost columns. Sample targets now have
   a 44×44px minimum, pinned row/column headers and scroll padding that keeps focused
   cells unobscured. Final root/reviewer screenshots caught lost column context at
   lower rows after enlargement; a bounded scrolling viewport repairs that too. The white-only focus outline on pale cells is replaced by
   a dark inset outline with white edge. Visible instructions explain keyboard
   navigation and map scrolling/swiping. No page-wide overflow or palette redesign.

4. **Keyboard focus lost after retry** — conditional error buttons at
   `web/components/sensitivity-lab.tsx:172` and `:424` were removed by their own
   handlers. Injected POST and GET failures reproduced `document.activeElement`
   becoming BODY immediately and remaining BODY after successful response.
   Comparison retry now focuses the persistent Reset assumptions button; setup
   retry focuses the persistent lab heading. Next Tab reaches the map / first
   control respectively after the response. Neither response steals focus.

Duplicate known-map findings from root/client review are consolidated in item 1;
both retry variants share item 4. No speculative refactors or backend changes.
The original API's per-request work bound remains a documented local-tool limit,
not a global concurrency quota. No new blocker was found in state/export handling.

## Interaction contract and references

A changed/equivalent control edit or reset removes stale results and resets the
map's next entry to top-left (pit0, degradation3). Focus stays on the control/reset
button; new results do not auto-focus the map. No wrapping at row/grid boundaries.
Pointers can inspect any point and establish the next keyboard entry. Header cells
have no actions and are not additional Tab stops. No aria-selected state is claimed:
focus inspects a sample, not a selectable strategy or input change.

Primary references checked 2026-10-17:
[WAI data-grid pattern](https://www.w3.org/WAI/ARIA/apg/patterns/grid/) supports a
single tab-sequence element and author-managed movement;
[WAI keyboard interface guidance](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/)
informs visible, persistent focus and roving tabindex;
[ESLint global ignores](https://eslint.org/docs/latest/use/configure/ignore)
provides the directory-scoped exclusion mechanism.

## Verification

- 297 core/API tests and 129 offline historical tests pass. Ruff lint/format pass.
- Independent backend reviewer: 47 focused tests; all 2,646 engine totals from
  441 points × 3 warm-up values × 2 schedules agree with separate Decimal
  arithmetic (maximum difference 2.274e-13 s). A reduced work budget fails before
  any simulation; 500-digit numeric fields return structured 422 responses.
- Three default-multiplier cases remain one/two-stop:
  pit18 → 1113.850/1124.700; pit7.15 → 1103.000/1103.000;
  pit0 → 1095.850/1088.700 seconds.
- Ordinary `npm run lint`, TypeScript and production build pass with artifacts
  present. No special lint CLI exclusion is needed.
- Browser checks include the three cases, all 441 points reached by directional
  keys, single Tab entry, boundaries, remembered exit/re-entry, reset/refresh focus,
  equivalent edits, stale responses, both retry paths and original challenges.
  Downloaded scenario comparison equals the exported comparison; full record replay
  equals the download; two canonical replay outputs match byte-for-byte.
- Final production browser run: **28 passed** (18 preserved challenge cases and
  10 lab cases across desktop/mobile), with no retries. Root inspected real
  Chromium at 375, 768, 1024 and 1440px: no page overflow, one grid Tab stop, visible
  focus, pinned coordinates and unobscured first/last sample. Client reviewer also
  independently inspected the root-generated desktop/mobile screenshots.
  Latest visual evidence: `traces/s11-fixed-axes-{375,768,1024,1440}.png`;
  controls: `traces/s11-final-controls-{375,768,1024,1440}.png`.
- Implementation [`34126a8`](https://github.com/Su760/f1-pitwall/commit/34126a8468e5b3ed5499d20e2079a65dd527d14c)
  is pushed. [CI 39012839475](https://github.com/Su760/f1-pitwall/actions/runs/39012839475)
  passes all four jobs: historical, Python 3.11/3.14, and production arena/browser.
  The docs-only closure commit/CI is supplied in the final handoff.

Generated screenshots/results/exports remain ignored under `traces/` and
`web/test-results/`. Preserved artifact config SHA-256:
`14d7d3ddafb985bf44c0fa22f48bb3851cda01f5eaacb06f8ae0fcff9a738436`.
Approved spec SHA-256 remains
`518ebe5e9e6473266d36338c41975054233b3e4b2ab091c4ac772588834671b3`.
The unrelated next-env.d.ts edit and downloaded original spec remain local.

## Remaining limits and stopping point

This is a two-fixed-schedule synthetic comparison, not global optimization or
historical calibration. Sampled transitions are not exact crossovers. Full circuit
gate stays blocked and historical cohort calibration stays closed. Chromium
keyboard/semantics checks do not certify all screen-reader/browser combinations;
VoiceOver/NVDA manual testing is not claimed. The wide map still needs horizontal
scrolling on small screens, with persistent row/column labels and accessible cell text.

S1.1 stops here. Proposed **S2** is one explicit “Find best legal strategy” action
using the existing bounded optimizer at selected settings. It is not implemented
or authorized by this task. No adaptive planning, calibration or RL.
