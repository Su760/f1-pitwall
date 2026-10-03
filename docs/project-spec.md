# PitWall Arena Project Specification

Build an interactive race-strategy simulator where a human, simple strategy rules, and a trained reinforcement-learning agent compete under the same scenario. Use historical F1 data to inform the simulator and make every strategic comparison reproducible.

The first release is a dry-race pit and tire strategy game with an honest benchmark. More realistic traffic, safety cars, weather, and a race-engineer interface follow after the simulator is validated. These are proposed requirements, not claims of completed analysis or real-world predictive accuracy. Version 2.1, October 2, 2026. Repository: https://github.com/Su760/f1-pitwall. Status: F0a implementation and a synthetic demo have been reported from terminal Codex; source and test results have not yet been independently reviewed. The remote repository was still empty at the October 2 review checkpoint.

## Product goal

Choose a circuit scenario and starting tires, make pit decisions, and watch your result alongside a baseline and a trained agent. Inspect where the strategies diverged and how sensitive the outcome is to uncertain tire wear and pit losses.

The central question is whether an agent can make useful sequential strategy decisions inside a documented model. Performance inside that model must stay separate from claims about what a real F1 team should have done.

The product hook is a decision lab: pause before a pit call, make a choice, compare plausible alternatives, and learn what would change the recommendation. A complete game and a credible planner are useful releases even before a learned agent exists.

## Additions adopted in version 2

| Addition                                | User value                                                                              | First delivery                                    |
| --------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------- |
| Pit-call challenges and debriefs        | Practice short strategy decisions and understand the tradeoffs                          | F0.5 with synthetic scenarios                     |
| Forkable replay                         | Rewind to a decision, change the call, and compare the simulated branches               | Snapshot contract in F0; interface in F0.5        |
| Adaptive tire estimates and replanning  | React when completed laps reveal different degradation than expected                    | F2, before RL                                     |
| Strategy confidence and risk comparison | See how close the alternatives are and which assumptions reverse the choice             | F2; optional risk objectives in F3                |
| Rival strategy archetypes               | Race against an early stopper, a stint extender, and a rival that covers observed stops | F4 with traffic                                   |
| Two-car team strategy                   | Explore shared pit service, double-stack delays, and split strategies                   | Optional F6 after field and safety-car validation |

Move the first playable synthetic demo ahead of historical calibration so data cleanup does not block the core experience. Keep features behind the milestones below; this table does not expand the first coding task.

## Scope and release sequence

| Release           | Deliverable                                                                            | Completion condition                                                                    |
| ----------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Synthetic preview | Pure simulator plus short pit-call challenges and replay branches                      | A complete playable loop works with clearly labeled assumed parameters                  |
| Strategy MVP      | One circuit, dry conditions, tire wear, warm-up, pit losses, and a playable comparison | Human and deterministic baselines complete identical configured scenarios               |
| Data calibration  | Historical-data importer, quality report, fitted pace components, and held-out checks  | Observed and assumed quantities are separated and validation results are reproducible   |
| Adaptive strategy | Observation-based tire estimates and a planner that replans                            | Different observed histories can justify different decisions without future information |
| RL release        | A trained pit-and-tire policy with baseline comparisons                                | Candidate completes a frozen benchmark with uncertainty and stress tests                |
| Race interaction  | Simulated field, traffic, and reactive rivals                                          | Altered actions change the simulated future consistently                                |
| Advanced strategy | Safety cars, uncertain weather, tire inventory, and broader circuit support            | Each addition passes its own calibration and evaluation gates                           |

Use a generic parameterized circuit for the first runnable core. Bahrain is the proposed first historical case study, subject to a completeness audit. Select actual sessions from source metadata during implementation; no dataset has been downloaded or certified by this specification.

## Three clearly labeled modes

Historical replay shows what happened in recorded data. It has no strategic control and cannot establish a counterfactual outcome.

Strategy sandbox runs a model forward from a configured starting state. If the player changes a pit decision, subsequent pace, tire state, and race interactions come from simulation. Label the result as simulated.

Benchmark mode runs policies headlessly over a frozen scenario suite. Every candidate receives the same information rules and matched exogenous randomness. Include simulator version and scenario identity with all results.

## First simulation model

Use lap-level decisions and a single controlled car in the first core. Compare strategies as independent runs under the same conditions. A visual track marker can show approximate progress, but interpolation must not imply high-resolution vehicle physics.

The proposed lap-time model adds circuit base pace, a driver or car pace offset, a fuel trend, tire-compound offset, tire-age degradation, warm-up loss, a pit transition loss when applicable, and bounded random variation. Traffic and neutralization terms belong to later versions. Store seconds, laps, and tire age with explicit units.

Document which terms can change strategy rankings. In the initial single-car model, action-independent base pace and fuel terms summed over the same laps cancel between strategies. They help reproduce timing but do not by themselves make the strategy problem richer. Similarly, shared additive noise that is independent of tire choice can change race times without changing paired strategy rankings. Meaningful adaptation needs uncertainty that changes the relative consequences of the available actions.

Begin with transparent, bounded tire curves and documented assumptions. More flexible learned components must earn their place through held-out predictive checks. Public lap times mix fuel, traffic, driver management, track evolution, and tire condition; fitting a curve does not isolate causal tire degradation.

A pit action occurs at a defined decision boundary before the next simulated lap. The transition includes the pit visit exactly once, consumes the selected tire set, updates compound history, and resets tire age. Write down whether pit loss is charged to the incoming or outgoing interval and use that convention everywhere.

F0 convention: the initial compound is selected during reset and consumes a fresh set. No pit action is allowed before lap 1; later pits occur between completed laps and the next lap, including before the final lap. Charge the entire incremental pit loss to that next interval. A fresh tire has age zero when its first lap is calculated, then age one after that lap. Each set can be fitted once; reused-set handling is deferred. Save both the completed-lap boundary and the next lap number to avoid ambiguous pit labels.

Keep lane transit, stationary service, and total incremental race-time loss distinct. OpenF1 documents lane duration separately from stationary stop duration. Total pit loss relative to staying on track must be estimated; it is not automatically equal to either field. [S2]

For the first arena configuration, provide two sets of each compound, consume one at the start, allow at most two pit stops, and require at least two distinct dry compounds by the finish. These are explicit simplifying arena rules. They also keep exhaustive comparison of one-stop and two-stop schedules practical. Version event rules separately before claiming historical race-rule fidelity, including exceptions and event-specific requirements.

## Decision contract

At each boundary, the policy sees completed lap count, laps remaining, current compound, current tire age, remaining inventory, compounds used, recent observed pace, and its current pit-loss estimate. Later observations can include public gaps, observed rival stints, current flags, and noisy forecasts.

Actions are stay out, pit for soft, pit for medium, or pit for hard. A legal-action mask reflects inventory, the stop cap, and decision timing. For each step, validate the action, apply any pit transition, simulate the next lap, increment tire age, accumulate time, and expose the updated observation. No action occurs after the race has finished. The configuration defines what happens if a mandatory compound requirement remains unmet; invalid finishes are recorded as violations and receive a terminal cost large enough to prevent an apparent gain from skipping the rule.

Use one published legality convention for every policy: mask actions that leave no possible rule-compliant finish, in addition to immediately unavailable actions. Reject configurations with no legal completion at reset. An invalid submitted action raises a structured error without advancing state; it is never silently changed to stay out. Retain terminal rule checks as a backstop. Rank invalid or incomplete races outside the valid leaderboard, regardless of any training penalty; store physical elapsed time and penalties separately.

The policy never sees future race-control events, future weather, upcoming random draws, exact hidden model parameters, unseen rival plans, or historical final results. It may use estimates derived from past observations. Simulator truth and analyst-only plots remain outside its observation payload.

Use separate random streams keyed by scenario, lap, and event type so different action paths do not accidentally change unrelated weather or incident draws. Derive behavior-dependent outcomes from the new simulated state; shared randomness does not mean preserving a historical future that the decision has invalidated.

Seeds, RNG state, future event streams, and latent parameters belong to trusted simulator/evaluator state. Keep them out of policy payloads, training features, and pre-decision challenge responses. An observation-only function signature is an interface boundary, not a security sandbox for arbitrary third-party code; untrusted bot uploads are out of scope.

## Decision lab and replay

Begin with three hand-authored challenges: whether a second stop pays for itself, which available compound best balances warm-up and degradation over the remaining stint, and how the remaining compound requirement constrains the final stint. Verify that changing the decision changes the relevant cost terms: an identical fixed warm-up cost may cancel between two schedules with the same stops. Use names and parameter ranges that do not reveal a challenge's concealed answer. Each challenge defines its observation cutoff, legal actions, objective, and scoring model. Add undercut, pit-rejoin traffic, and safety-car challenges only after those mechanisms exist.

The player inspects a short briefing, commits a pit call, watches the result, and opens a debrief. Offer a short glossary and optional hints. A local history records scenario version, choice, and feedback so progress can be measured on new scenarios; repeated attempts at the same scenario are practice, not independent evidence of improvement.

The debrief includes what was known at the decision, legal alternatives, projected remaining time, an uncertainty range when applicable, and the eventual result. Grade choices using the information available at the time. A plausible choice can lose to a lucky alternative. When alternatives are close relative to model uncertainty, say the recommendation is weak instead of manufacturing a precise winning lap.

Support two explicitly labeled analyses:

- **Same-world replay:** restore a trusted snapshot, replace an action, and rerun with matched external randomness. All consequences of the changed action are recomputed. This is a model counterfactual for that world, not proof of what would have happened in the actual race.
- **Decision-time comparison:** sample plausible hidden conditions consistent with past observations and new possible futures. Compare every legal action with the same frozen continuation policy and paired rollout draws. Never condition this score on the original realized future or hidden true parameter. Report estimated excess remaining time relative to the best evaluated action, rollout count, and uncertainty. This is a model-based local comparison, not a global optimality claim; local losses should not simply be summed across a race.

F0 needs serializable snapshots and restore/continue operations. A snapshot captures scenario/config identity, simulator state, observation history, policy memory where relevant, and random-stream position or keys. Identical continuation must reproduce the original run; a fork must not mutate its parent. F0.5 adds the interface for branching. F2 adds uncertainty-aware decision scoring. Deterministic F0.5 challenges disclose their relevant assumed parameters and can use exact deterministic comparisons.

Explanations initially come from structured rollout results and templates: for example, whether saved degradation exceeds pit and warm-up costs. A later radio-style assistant may verbalize those results, with evidence links and no invented numbers. It is not responsible for simulation, scoring, or policy decisions.

## Data inputs and preparation

Use OpenF1 as the primary historical source. Its documentation describes historical access from 2023 onward, plus lap, stint, pit, weather, and race-control endpoints. Live data is a separate paid capability and is unnecessary for this project. [S1, S2]

| Dataset              | Purpose                                             | Required handling                                                           |
| -------------------- | --------------------------------------------------- | --------------------------------------------------------------------------- |
| Sessions and drivers | Resolve event identity and competitors              | Use actual returned keys; record source and retrieval time                  |
| Laps                 | Estimate pace and compare predictions               | Flag missing laps, outliers, pit transitions, and neutralized periods       |
| Stints               | Associate compound and tire age                     | Validate joins; retain missing values and starting tire-age uncertainty     |
| Pit records          | Inform pit transitions                              | Distinguish transit and service time from estimated race-time loss          |
| Race control         | Identify flags and interruptions                    | Respect event time; exclude future events from observations                 |
| Weather              | Filter initial dry scenarios and support later work | Separate realized measurements from information available before a decision |

Cache raw responses immutably and write normalized Parquet tables with a provenance manifest. Respect published rate limits, use bounded retries, and run simulation and training entirely from the cache. An unavailable source should produce a visible data-quality failure, not fabricated rows.

Prefer the current `lane_duration` field; the documented `pit_duration` alias is deprecated. Stationary `stop_duration` is documented only from the 2024 US Grand Prix onward. A Bahrain session earlier than that cannot be assumed to include this measurement. Missing stationary duration does not automatically disqualify a session for pace calibration; identify which analysis it blocks and keep any replacement assumption explicit. [S2]

Lap duration is available only after the lap finishes. Completed stint length and a later pit stop must not be treated as features known at the start of that stint. If historical publication timestamps are unavailable, state the availability assumption and apply a conservative delay. Never backfill missing observations with future measurements.

FastF1 is an optional later adapter for cross-checks or extra telemetry, not an MVP dependency. If two sources disagree, preserve provenance and resolve the mismatch; do not silently combine identifiers or duplicate events. [S5]

## Calibration and simulator validation

Fit components on chronological training events and tune on a separate validation set. Keep final evaluation events untouched. Split entire events or stints rather than random adjacent laps, which share conditions and would leak information across the split.

Audit which compounds, tire ages, conditions, and drivers are actually represented. Report lap-time mean absolute error and signed error on held-out clean laps, broken down by compound and tire age. Compare with a simple constant or rolling-pace baseline. Show residuals and uncertainty around poorly supported parameters.

A single circuit provides only a small number of independent historical races. Generated scenarios broaden simulator testing but do not create new real-world evidence. Document the event count and scope any claims accordingly.

Before RL, verify synthetic cases with known answers: zero degradation with equal compound pace and nonnegative warm-up should favor avoiding optional pit costs; sufficiently steep degradation in a constructed case should make an extra stop worthwhile; increasing pit loss should not improve the same fixed strategy's time. Account for mandatory rules when constructing these tests. Check tire transitions, inventory use, and total-time accounting against hand calculations.

When no clean historical measurement identifies a parameter, use a labeled assumption with a sensitivity range. Passing simulator consistency tests is necessary but does not prove realism.

## Baselines and learning

Implement fixed one-stop and two-stop schedules, a tire-age threshold, and a simple model-based planner before training. Tune baseline parameters on the same validation budget and allowed information as the learner. In the small deterministic core, enumerate legal schedules to obtain a useful reference optimum.

For fixed known parameters, the initial strategy problem may largely reduce to choosing a schedule before the start. Treat exhaustive search as a reference for that restricted deterministic model. Do not add a neural network merely to rediscover its answer. Establish useful adaptation in F2: draw hidden degradation from a bounded scenario distribution, expose noisy completed-lap observations, and let every online strategy use the same observation-derived estimate and uncertainty summary.

Start the estimator with a small grid or ensemble of plausible tire models, updated from completed clean laps under explicit fuel and warm-up assumptions. Its uncertainty is conditional on those assumptions; it does not identify real tire wear independently of confounding effects. Skip missing observations without future imputation. Track estimator error in synthetic tests separately from strategy performance, and test recovery from a plausible but wrong initial estimate.

Add an adaptive model-based planner that evaluates feasible remaining schedules across those plausible models, executes only its next decision, and replans after the next observation. Compare it against a static planner, heuristics, and later RL. Put a rollout/time budget on planning and record the hardware and latency. Fair online planners sample from their observation-derived beliefs; they do not clone evaluator-only simulator truth. In small known deterministic cases, the planner should agree with exhaustive search within a documented tolerance.

Show expected time, outcome percentiles, and how often each option wins in the sampled model scenarios. These quantities depend on the assumed scenario distribution. Distinguish outcome variability from a confidence interval on estimated mean improvement and from unsupported model uncertainty. Keep expected elapsed time as the primary objective. Optional conservative profiles can minimize the average of the worst 10 percent of times, with a separately versioned objective and leaderboard.

Keep a hindsight planner that knows the whole simulated future in a separately labeled diagnostic category. It is not a fair online competitor. Once latent parameters and random future events exist, any deployable planner must use the same observable estimates as the agent.

Wrap the simulator as a Gymnasium environment. A proposed first learner is MaskablePPO with a small feedforward network and discrete actions; use the library's mask-aware evaluator. This is a starting experiment, not a claim that PPO will beat planning for this problem. [S3, S4]

Supply recent observation history or the shared estimator summary to the first feedforward policy. MaskablePPO currently does not support recurrent policies; do not assume an LSTM policy is a drop-in option. Revisit a recurrent implementation only if history-based baselines show a concrete need. [S4]

Use negative elapsed seconds per transition as the first reward, with an undiscounted episodic objective so total return tracks total race time. Add explicit terminal rule penalties. Avoid extra rewards for pit stops, position changes, or lap completion until their effect on the objective is understood. Interrupted runs are invalid, not successful short races.

Randomize tire degradation, pit loss, warm-up, and pace noise within documented ranges during training. Keep observation-visible estimates separate from hidden true parameters. Begin with a bounded CPU smoke run, measure simulation throughput, and estimate the next run before allocating it. Paid compute is opt-in.

## Field interaction and realism

Add a simulated field only after the single-car time objective works. Update all policies from the same pre-step snapshot and resolve the lap together, so update order cannot leak another car's new decision.

Traffic, passing, and pit rejoin costs must depend on the simulated order and gaps. Begin with a simple published model and expose its assumptions. Do not combine a changed ego strategy with unchanged future opponent lap times and then describe the result as a faithful replay.

Later, make race position or points an explicitly versioned objective. Keep objective definitions and leaderboards separate; minimizing isolated elapsed time is not equivalent to maximizing finishing position in traffic. Add safety cars before wet-weather tire physics, and evaluate each feature independently before combining them.

Introduce interpretable rival strategies: early stopper, long-stint runner, reactive cover strategy, and opportunistic stopper once neutralization exists. These are synthetic policies, not claims about real drivers or teams. Rivals react only to observations available at the decision boundary; a simultaneous rival pit call cannot be observed before acting. Freeze development rivals separately from held-out rival mixtures. Show undercut/overcut and pit-rejoin effects only when the traffic model can generate them.

Optional F6 expands control to two teammates with a shared pit-service resource. Service occupancy and arrival order must determine double-stack delay; model split strategies and a team-level objective separately from the single-car leaderboard. First test a deterministic simultaneous-arrival case. If lap-level timing cannot resolve service order credibly, add a small event-based pit-service component before releasing this feature.

## Application screens

| Screen              | Main interaction                                       | Required output                                                            |
| ------------------- | ------------------------------------------------------ | -------------------------------------------------------------------------- |
| Race control        | Advance a lap, change speed, make pit calls            | Current observations, legal choices, inventory, running time               |
| Strategy comparison | Select human, heuristic, planner, and learned policies | Tire timelines, cumulative gaps, total time, rule violations               |
| Decision replay     | Inspect a specific pit decision                        | What was known then, selected action, action probabilities if available    |
| Pit-call challenge  | Read a briefing, choose an action, open a debrief      | Decision-time feedback, glossary, local practice history                   |
| What-if lab         | Fork a decision and change one action                  | Paired branch comparison, assumptions, uncertainty, and a sensitivity view |
| Training            | Run or stop a bounded experiment                       | Job state, throughput, checkpoints, independent validation results         |
| Benchmarks          | Compare frozen policy versions                         | Paired performance differences, intervals, worst cases, scenario coverage  |
| Data quality        | Inspect event readiness                                | Missing fields, exclusions, source metadata, calibration diagnostics       |

Use an F1-inspired timing tower and tire colors, with text labels for accessibility. Start with 2D visuals and readable charts. Display historical, assumed, and simulated values distinctly. A rule-based explanation can describe why a baseline acted; a neural agent's attribution should not invent an internal chain of reasoning.

## Evaluation and acceptance

Freeze training, validation, and final-test scenario manifests. Use held-out parameter combinations and seeds, then later held-out events and circuits. Evaluate at least three training seeds, and report both the selected checkpoint and variability across runs.

Proposed final-test starting budget: 1,000 matched simulated races per policy. Record mean and median total-time difference against the strongest validation-selected fair baseline, a paired 95 percent confidence interval, 90th-percentile time loss, rule violations, incomplete runs, and inference latency. These are proposed sample sizes, not promises of precision or real-world validity.

Define time improvement as baseline seconds minus candidate seconds, so positive means faster. Report intervals per training seed plus variability across seeds; laps from one race are not independent samples. When scenarios share an event or parameter family, preserve that grouping in resampling and describe the scope of the interval. Compute physical-time comparisons only for completed, legal matched pairs and report all exclusions prominently; invalid runs still fail promotion. Final test results are read once for the frozen candidate; further tuning requires a new test suite or an explicit disclosure that it is now development data.

Promotion requires zero legality failures, reproducible checkpoint replay, positive mean improvement with the paired confidence interval above zero, and acceptable tail performance under a regression limit fixed before final testing. If the planner remains stronger, retain it as the default strategist and report that outcome. A well-tested negative RL result still fulfills the research objective.

Stress tests vary pit loss, tire-curve shape, warm-up, observation noise, missing recent timing, and later incident timing. Include a second tire model family to test whether the policy only exploits the exact functional form used in training. Interpret all gains as simulator-specific until independently supported.

Maintain a named development suite: high pit cost, steep degradation, slow warm-up, last-chance compound compliance, noisy pace, missing timing, and an unseen tire-curve family. Enable each case only when its mechanism exists. Every case states an expected qualitative relationship and the assumptions supporting it. Keep this visible teaching/debugging suite separate from final-test seeds and settings. Before promotion, inspect the largest apparent gains for accounting exploits, impossible tire resets, future leakage, or rewards for premature termination.

## Architecture and saved artifacts

Use Python 3.11 or later, NumPy, pandas or Polars, Parquet, Gymnasium, PyTorch, and sb3-contrib. Serve the application with FastAPI and Next.js with TypeScript. Store experiment metadata in SQLite initially and keep datasets, episode logs, and checkpoints as local artifacts. A separate training process publishes progress over SSE; the race API remains responsive.

Keep data ingestion, calibration, pure simulation, observation construction, policies, evaluation, API, and visualization separate. The simulator must run headlessly. Each saved episode includes its scenario, simulator version, parameter source, event seed references, observation and action schema versions, policy hash, and decision log. Privileged future-event data is evaluator-only.

Use one policy interface for a human adapter, heuristics, planner, and learned policy: reset episode memory, then select an action from an observation and legal-action mask. Keep snapshots and evaluator secrets outside that interface. Separate the full local replay artifact from the redacted pre-decision API payload. Record code commit, dependency lockfile identity, objective/rule versions, and estimator version with benchmarks. Pin a supported Python version and resolved dependency set during implementation; add data, RL, and web dependencies only when their milestone requires them.

Store raw-data manifests, normalized event tables, calibration reports, scenario suites, policy checkpoints, episode replays, and benchmark summaries. A checkpoint includes preprocessing and rejects incompatible simulator versions. Do not build shared infrastructure with Poker Arena until a concrete duplication justifies it.

## Milestones

| Milestone        | Build                                                                                      | Exit gate                                                                                                                        |
| ---------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| F0               | Pure simulator, scenario schema, reference schedules, and snapshots                        | Deterministic replay, independent forks, and analytically checkable pit and tire cases                                           |
| F0a, first pass  | Deterministic engine, fixed schedules, CLI, versioned trace, and core tests                | Accounting and legality checks pass; source and verification results are available for review                                    |
| F0b, second pass | Exhaustive legal schedule optimizer, replay verification, snapshots, and independent forks | Tiny known-answer optimum verified; restore/continue matches original trace; forks cannot mutate parent                          |
| F0.5             | Minimal playable synthetic arena, three challenges, and debriefs                           | A user completes a challenge and compares a fork using disclosed assumed parameters                                              |
| F1               | Historical importer and quality report                                                     | One proposed circuit passes the completeness audit; unsupported fields are explicit                                              |
| F2               | Calibration, uncertain tire models, adaptive planner, and decision-time debriefs           | No future leakage; observation changes can change the recommended action; estimates and strategy results are reported separately |
| F3               | Gymnasium wrapper and RL experiment                                                        | Bounded training, checkpoint recovery, frozen matched-scenario evaluation                                                        |
| F4               | Simulated field, traffic, and rival archetypes                                             | Position and gaps respond consistently; simultaneous decisions do not leak                                                       |
| F5               | Safety cars, then weather and additional circuits                                          | Each feature passes new data, physics-assumption, and generalization checks                                                      |
| F6, optional     | Two-car team strategy and shared pit service                                               | Service conflicts are accounted for and the team objective is benchmarked separately                                             |

The first demo ends at F0.5. The first data-informed strategy release ends at F2. F3 is the first learned-policy research release. Avoid calendar promises until F0 provides actual implementation and simulation-throughput evidence.

## Research direction and scope boundaries

Race simulation, Monte Carlo strategy evaluation, and learned pit policies already have public research precedents. TUM's simulator provides a lap-level research reference; RSRL explores learned strategy with explanation methods. Use them to understand assumptions and evaluation design, without claiming PitWall invents F1 strategy RL. PitWall's proposed distinction is the integrated challenge, fork, and decision-quality experience with auditable comparisons. [S6, S7]

A later research experiment can compare a learned policy with a planner-assisted policy, or distill the planner into a fast policy. Published work also explores combining RL and model predictive control for an F1 strategy problem. This supports investigating the direction; it does not establish gains for PitWall. Attempt it only after a standalone planner and RL policy have credible baselines, and hold information and compute budgets explicit. [S8]

Defer live race ingestion, voice radio, multiplayer, full vehicle dynamics, arbitrary bot uploads, and production account systems. Add a feature when it improves a demonstrated decision or user loop. Keep raw datasets and checkpoints out of normal Git history; commit small synthetic fixtures and provenance/config files.

## Collaboration and terminal workflow

Use this chat for product choices, milestone planning, research, and reviewing terminal output. The user created `Su760/f1-pitwall`; terminal Codex runs in `~/Desktop/F1/Pitwall`. Implementation happens in that checkout. Save this specification in the repository as `docs/project-spec.md`; Codex cannot assume the chat attachment is already on the user's computer.

At the start of each terminal task, inspect the current files, Git status, and applicable repository instructions. Work on one milestone at a time, preserve unrelated work, and verify behavior before claiming completion. At the end, return changed files, checks run, exact demo commands, known limitations, and the next milestone. After implementation begins, the repository's current spec and status files are authoritative; bring back the diff or handoff when this chat needs to review them.

F0 should create a concise `README.md`, `docs/model-assumptions.md`, and `docs/status.md`. The status file tracks completed gates, unresolved assumptions, evidence, and the next bounded task. Keep a short decision log for changes to the simulator, rules, observations, or objective; those changes can invalidate old benchmark comparisons.

Add a short repository-root `AGENTS.md` with verified setup/test/lint commands, the observation boundary, deterministic accounting conventions, and the requirement to update status after a milestone. Link to this spec and the model assumptions instead of duplicating their full text. Inspect existing instructions before editing them and preserve unrelated requirements. Record consequential choices and research links with access dates in `docs/decisions.md`.

At the start of a milestone, check official documentation for unfamiliar or changed dependency APIs and tool behavior. Research relevant modeling choices before implementing them. Record what the evidence changed; avoid tool upgrades or extra infrastructure without a concrete benefit. Use scoped tasks, meaningful checks, and a separate review pass. Delegate independent read-only analysis where useful; coordinate file ownership for parallel edits. These are project workflow decisions informed by current official Codex guidance. [S9, S10]

After verification, publish a reviewable Git checkpoint to the intended repository branch and report its exact commit. Keep local test outcomes, remote CI outcomes, and independent review status separate. If the code has not been pushed or supplied as files, a chat review can assess pasted output but cannot certify the implementation. Never force-push or overwrite unrelated work as part of routine milestone handoff.

October 2 checkpoint: the terminal reported 1,113.850 seconds for a fixed one-stop schedule and 1,124.700 seconds for a fixed two-stop schedule, both labeled legal, with JSON traces. The 10.850-second difference applies only to that synthetic comparison and is not evidence of an optimum. The pasted handoff omitted test results and reported a missing project spec. Next step is F0a verification, documentation, and repository synchronization; then review F0b readiness.

The reported `invalid stop hook JSON output` is a separate tooling issue. Current docs require successful Stop-hook output to be JSON. Locate the actual hook and compare its exit status and sanitized output against behavior supported by the installed version before proposing a fix; preserve the hook's intended checks and do not disable it to make the warning disappear. [S11]

## First implementation task

Complete F0 in two passes. F0a builds the deterministic pure Python engine, fixed schedules, CLI, versioned trace, and core tests. F0b adds exhaustive legal schedule search, replay verification, snapshot restore, and independent forks after the engine is reviewed. The full F0 definition below describes both passes; it does not authorize skipping the current F0a verification checkpoint. Stop after F0 with a documented simulator and an F0.5 checklist; do not begin neural training or historical/live-data integration yet.

Original full-F0 implementation reference (use only the subset authorized by the current task):

```text
Read docs/project-spec.md and all applicable repository instructions. Inspect
the current files and Git status, preserve existing work, and implement F0
only. This is a local research project called PitWall Arena.

Build a pure Python lap-level dry-race simulator with a versioned scenario
schema, explicit units, soft/medium/hard compounds, age-based degradation,
warm-up, finite tire inventory, pit loss, and the documented arena rules.
Follow the spec's decision boundary and tire-age conventions exactly.
Keep simulator truth separate from policy observations.

Implement fixed one-stop/two-stop schedules and exhaustive enumeration of
legal schedules for the small deterministic model. Support deterministic
replay, snapshot restore, and independent forks. Add a CLI that runs and
compares policies and writes a versioned replay plus a readable summary.
Clearly label all initial circuit/tire parameters as synthetic assumptions.

Verify hand-calculated lap/pit accounting, inventory and legal-finish
handling, no mutation on invalid actions, zero/steep degradation cases,
fixed-strategy pit-cost monotonicity, and snapshot/fork reproducibility.
Confirm the exhaustive-search result on a tiny manually checkable case.

Use a small src/pitwall package with tests and synthetic scenarios. Keep
dependencies minimal; do not add the web UI, historical importer, database,
Gymnasium, PyTorch, paid services, or training yet. Add a dependency lockfile
and lightweight CI for the core checks. Document setup and exact CLI commands
in README.md, assumptions in docs/model-assumptions.md, and milestone status
in docs/status.md. Report what works, verification results, limitations, and
the next F0.5 task. Finish F0 and stop at that milestone boundary.
```

## Sources and design status

The proposed model, stack, budgets, milestones, and acceptance gates are engineering decisions. Source documentation supports access and library capabilities, not counterfactual race outcomes. Checked October 2, 2026.

- [S1 OpenF1 access and project scope](https://openf1.org/)
- [S2 OpenF1 API documentation](https://openf1.org/docs/)
- [S3 Gymnasium custom environments](https://gymnasium.farama.org/introduction/create_custom_env/)
- [S4 MaskablePPO documentation](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html)
- [S5 FastF1 project](https://github.com/theOehrly/Fast-F1)
- [S6 TUM race-simulation research repository](https://github.com/TUMFTM/race-simulation)
- [S7 Explainable Reinforcement Learning for Formula One Race Strategy](https://arxiv.org/abs/2501.04068)
- [S8 Bridging RL and MPC for mixed-integer optimal control with application to Formula 1 race strategies](https://arxiv.org/abs/2604.00826)
- [S9 Official Codex best practices](https://learn.chatgpt.com/guides/best-practices)
- [S10 Official AGENTS.md guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [S11 Official Codex hooks documentation](https://learn.chatgpt.com/docs/hooks)
