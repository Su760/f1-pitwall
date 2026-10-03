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
schedule-only proposal; no F0b code is included in this checkpoint.

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
