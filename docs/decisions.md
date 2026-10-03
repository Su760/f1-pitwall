# Decisions and evidence

Dates below are check dates, not claims that future work has been implemented.

## 2026-10-02 — scope and specification

The approved version-2.1 specification was downloaded as
`PitWall-Arena-Project-Spec (1).md`. `docs/project-spec.md` was absent; it now holds
the complete, byte-identical contents. SHA-256:
`518ebe5e9e6473266d36338c41975054233b3e4b2ab091c4ac772588834671b3`.
Preserve the downloaded original locally; the canonical committed spec is in
`docs/`. Its historical checkpoint statements remain intact; current evidence
belongs in [status](status.md).

F0a remains fixed schedules, deterministic simulation, CLI, audit traces, and
core verification. F0b means exhaustive legal schedule optimization, verified
replay, snapshot restoration, and independent forks. Corrected the earlier
schedule-only proposal; no F0b code was included in the reviewed F0a checkpoint
`68b99c5d5dd79d470497ab8a8c942854503eecfb`. F0b implementation is recorded below.

## 2026-10-02 — transparent model and policy boundary

Keep the implemented capped linear degradation and additive age-indexed warm-up.
They permit hand calculations and express the intended cost tradeoffs without
calibration claims. Model parameters and arena rules live in scenario input.
The independent five-lap check totals 412.1 s; details are in
[assumptions](model-assumptions.md#independent-accounting-check-2026-10-02).
This decision follows the [approved F0 conventions](project-spec.md#first-simulation-model),
not an inference that public lap timing identifies causal tire wear.

Keep observations separate from state and configuration. F0a fixed policies need
only the current public race summary and legal-action mask. The spec's richer
recent-pace/estimated-pit-loss observations, policy-memory reset, and uncertainty
handling are not present and must be designed with their consuming milestone.
The observation interface is not a sandbox for untrusted Python code.

## 2026-10-02 — trace precision and focused verification

Keep schema/model versions separate and retain full float values. Actions carry
the completed boundary; aligned lap records carry the next lap number. No
snapshot state is implied. CLI formatting must not alter trace/state values.

The read-only reviewer found no confirmed engine bugs. It identified missing
explicit coverage of cumulative/final trace totals and submillisecond display
precision. Extend the existing trace test and add one two-lap precision case;
do not rewrite working engine code or pin demo totals as a replacement for math.
Use tight tolerances when comparing different floating-point accumulation orders.
Primary references checked: [Python floating-point behavior](https://docs.python.org/3/tutorial/floatingpoint.html)
and [sum](https://docs.python.org/3/library/functions.html#sum).

## 2026-10-02 — dependencies and CI

Retain the zero-dependency runtime, resolved hash-checked development lock, and
Python 3.11/3.14 CI matrix. No dependency upgrade is justified by this review.
Installation/build commands use the pinned setuptools already installed from
the lock, with build isolation disabled to avoid silently resolving another
backend. Check the wheel as well as the editable install.

Primary tooling references: [pip hash-checking mode](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode),
[uv dependency compilation](https://docs.astral.sh/uv/pip/compile/),
[pytest assertions](https://docs.pytest.org/en/stable/how-to/assert.html), and
[Ruff configuration](https://docs.astral.sh/ruff/configuration/). Check dates:
2026-10-02. Future milestones must verify unfamiliar/current APIs and record
findings that actually change a choice; avoid speculative upgrades.

## 2026-10-02 — global Stop-hook diagnosis (unresolved outside project)

Installed CLI/package metadata reports `codex-cli 0.160.0`. Responsible
reproducible configuration: `~/.codex/hooks.json:41`, `hooks.Stop[0].hooks[0]`.
It runs an `echo` reminder rather than returning an object. Executing only this
inspected echo command produced exit **0**, empty stderr, and sanitized stdout:

```text
Session complete. Update <workspace>/MEMORY.md with what changed this session.
Mark any completed <other-project> phases. Remove resolved blockers.
```

Parsing stdout as JSON fails at line 1, column 1. The installed-version
[Stop handler source](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/hooks/src/events/stop.rs)
accepts empty successful output, but emits the reported error for invalid nonempty
JSON from a normal synchronous hook. Its
[output schema](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/hooks/schema/generated/stop.command.output.schema.json)
supports `systemMessage`. This matches the
[official hooks contract](https://learn.chatgpt.com/docs/hooks#stop).

Proposed owner-applied fix: preserve the exact reminder text, but serialize it
as a JSON object's `systemMessage`, followed by a newline, and keep exit 0.
That retains the advisory reminder without creating a blocking continuation loop.
For example, the output shape is `{"systemMessage":"<unchanged reminder>"}`.
Do not use `continue: false`, delete the hook, suppress its output, or disable checks.

Read-only searches covered `~/.codex/logs_2.sqlite`, the app-server daemon stderr
log, and this session's prior-turn transcript. They did not retain the original
warning event, so original-event attribution is not log-confirmed. Attribution
rests on the active configuration, exact-command reproduction, installed binary
error string, and matching 0.160.0 source. The separate `on-stop.js` exits silently
on its no-transcript path, which that version accepts; it was not invoked against
real transcripts because it writes learning data and can spawn background work.

No project hook exists. No global or plugin-managed files were modified. The
formatting fault therefore remains for the global hook owner to fix; it is
separate from simulator test status.

## 2026-10-02 — F0b exhaustive reference and resource bounds

Keep the engine as the only scorer. Enumerate increasing boundary combinations
and compound Cartesian products for every permitted stop count, including zero
and fresh same-compound replacements. This makes the small reference exhaustive
without introducing another physics/rules implementation. The supplied arena
derives 529 candidates, 462 legal schedules, and medium after lap 5 at 1113.550 s.
A separate six-strategy hand calculation verifies a 406 s optimum.

Preflight explicit limits on candidates and candidate-count × laps before any
scoring; default limits are 100,000 and 2,000,000 respectively. Reject unsupported
spaces and propagate interrupts; do not return a truncated result as exhaustive.
Rank exact elapsed times, stop count, boundary tuple, then soft/medium/hard order.
Retain only requested top results in a bounded heap. Use the existing min-heap
API with negated keys, retaining Python 3.11 support without new dependencies or
Python 3.14-only max-heap APIs. Search budgets are operational limits, not physical
model parameters; they do not alter scores.

Primary docs checked 2026-10-02: [itertools combinations and product](https://docs.python.org/3/library/itertools.html)
and [heapq API/version additions](https://docs.python.org/3/library/heapq.html).
An independent read-only reviewer also matched the full ranking/counts against
legal action-tree enumeration across 60 small configurations. No substantive
implementation finding required a fix.

## 2026-10-02 — strict replay and compatible storage

Retain trace schema 1 and model `f0a-linear-capped-v1`: the equations, action
boundaries, and storage semantics did not change. Load accepted actions directly,
execute them through Race.step, and compare every lap and final field. Named
FixedSchedule metadata is validated against accepted history but does not drive
replay. Exact numeric equality is intentional because replay repeats the same
operation order; independently reordered arithmetic tests use tolerances.

Python's JSON decoder permits repeated keys and nonstandard nonfinite constants
by default. Use duplicate-key and parse-constant hooks plus recursive finite/type
validation (also catches `1e999`) instead of treating JSON parsing as validation.
Reject unknown fields, unsupported versions, and inconsistent records with field
paths. Primary docs checked 2026-10-02:
[JSON decoder compliance and hooks](https://docs.python.org/3/library/json.html#standard-compliance-and-interoperability).

Snapshot schema 1 is separate from complete trace schema 1. Store full config,
model/config fingerprint, state, and accepted action/lap prefix. Restore by replay
and verify the imported state/result, never by assigning imported state or using
check_finish alone. SHA-256 identifies serialized input; it is not an authenticity
check. This deliberately trades linear restoration work for one authoritative
transition implementation. Fixed policies are stateless; memory-bearing policies
will require a separately designed contract. Fork reuses this validation and owns
new history lists, leaving all evaluator data outside policy observations.

## 2026-10-02 — compatible CLI and delivery

Keep the original `pitwall SCENARIO` comparison command, also available as
`pitwall compare SCENARIO`. Add optimize/replay/snapshot/restore/fork subcommands.
Restore/fork takes future pit decisions and derives complete trace metadata from
actual accepted actions. Refuse output paths that alias input artifacts. Keep
runtime dependency and lock files unchanged. Add all F0b CLI demos to the existing
Python 3.11/3.14 CI matrix; preserve Git history and the original spec download.
Primary docs checked: [argparse subcommands](https://docs.python.org/3/library/argparse.html#sub-commands).

The specification has no intentional design changes in F0b and remains unchanged.
Next is the separate F0.5 playable synthetic arena, three challenges, and debriefs.

## 2026-10-03 — F0.5 contract, scoring, and state ownership

Use the approved FastAPI + Next.js/TypeScript stack with a small stateless API.
Keep the Python engine authoritative and its Observation unchanged. The written
[API contract](api-contract.md) was agreed before backend/frontend delegation;
separate file ownership keeps the core and original spec intact.

Each server-owned versioned fixture is a trusted saved decision boundary, restored
through the existing verified prefix-replay path. Evaluate every original-mask
legal action on an independent fork under one frozen stay-out continuation.
Fixtures must permit that continuation for all legal choices; the mandatory
compound fixture therefore uses the boundary before the last lap. This avoids
an implicit future decision changing the meaning of the player's one-call score.

Score selected remaining elapsed seconds minus the best evaluated remaining
seconds. Keep exact ranking and report model/continuation scope; neither the UI
nor API calls this global optimality or real F1 performance. Component totals and
signed cumulative differences come from Python lap results. Tests include an
independent hand calculation and parameter interventions that change the cost
tradeoff, not just an assertion that the fixtures run.

Disclose relevant assumed tire curves, pit loss and rules in a separate public
payload. Do not disclose answers or future traces before a call. Reconstruct
canonical state for every request; reject uploaded state/config/score and expose
no optimizer endpoint. At most four rollouts over a 20-lap fixture, and a 1024-byte
request cap, bound work. Versioned browser history is local practice, never
server authority. No persistence service or external API is needed.

## 2026-10-03 — isolated web tooling and reproducible browser checks

The core dependency file remains unchanged. Pin Python web dependencies under
`apps/api/requirements.in` and a hash-checked lock; install into `.venv-api`.
Pin Next.js/React/TypeScript/ESLint/Playwright under `web/package.json`, committing
npm's resolved lock and using `npm ci`. Use existing Node 22.20.0 for local/CI
checks. Runtime UI fonts are local/system fonts, avoiding a remote font fetch
requirement during production builds.

FastAPI uses typed request validation with forbidden extra fields, plus strict
JSON parsing and bounded body reads. Strict validation matters because normal
coercion can reinterpret a boolean/string as a version number. Primary docs
checked: [FastAPI request bodies](https://fastapi.tiangolo.com/tutorial/body/),
[Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), and
[Starlette request streams](https://starlette.dev/requests/).

Next.js external rewrites keep browser requests on one origin and route to the
local Python service. No permissive CORS or browser-visible backend secrets are
needed. Current Next.js requires explicit linting separate from production builds;
run ESLint, TypeScript, and build individually. Primary docs checked:
[Next.js installation](https://nextjs.org/docs/app/getting-started/installation)
and [rewrites](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites).

Playwright starts both real servers and exercises the production build at desktop
and mobile sizes. Tests use role/name locators and API-returned values, and check
keyboard focus, errors/retry, duplicate submission, stale responses, and history.
Screenshots are inspected as separate visual evidence; passing tests alone is not
visual approval. Primary docs checked: [Playwright web servers](https://playwright.dev/docs/test-webserver)
and [CI setup](https://playwright.dev/docs/ci-intro). GitHub Actions setup-node v7
and upload-artifact v7 were verified against their official repository releases.

The referenced global UI rules path was absent and no moved copy was found under
the installed rule/agent directories. Repository guidance, the approved spec,
and the requested accessible timing-board design remain the design basis.
No global hooks or configuration were modified.

The installed Starlette 1.7.0 TestClient deprecated its HTTPX integration; that
warning was reproduced during backend tests. Follow the current
[Starlette TestClient documentation](https://starlette.dev/testclient/) and pin
HTTPX2 2.13.1 for API tests. FastAPI 0.142.2, Pydantic 2.13.5, and Uvicorn 0.54.0
are separately pinned; no core dependency upgrade was required. This choice was
verified 2026-10-03 against the installed API behavior and official documentation.

Next's bundled React lint plugin calls context.getFilename, which ESLint 10
removed. The initial lint run reproduced that exception. Pin ESLint 9.39.5,
compatible with the plugin, and retain all configured rules. See the official
[ESLint 10 migration guide](https://eslint.org/docs/latest/use/migrate-to-10.0.0).
The mount fetch was expressed with an explicit response callback so asynchronous
state updates satisfy the React effect rule while immediate challenge-switch
resets remain in the user-event path. Lint and production build then passed.

The full npm audit reports five development-dependency entries from the same
unpatched braces<=3.0.3 issue in the Next lint dependency chain. The
[upstream advisory GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
reports no patched release; registry latest is 3.0.3 (checked 2026-10-03). The offered
automatic fix downgrades the Next lint configuration to a different major; do not
apply it or disable linting. `npm audit --omit=dev` reports zero production
vulnerabilities. Record the concrete development-tool limitation until an
upstream compatible patch exists.

Final browser verification found that hiding a desktop `<br>` on mobile joined
adjacent JSX words. Add explicit whitespace and test rendered heading/intro text
at both viewports. Fresh production-app checks then passed all 18 cases, with
desktop/mobile screenshots inspected separately. The independent reviewer found
no substantive scoring, state isolation, request-boundary, or completed-flow
issue; a test-only ambiguous paragraph locator was narrowed to its intended text.
