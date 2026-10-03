"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  actionLabels,
  compounds,
  request,
  type Action,
  type ChallengeDetail,
  type ChallengeSummary,
  type Compound,
  type Costs,
  type Evaluation,
  type Outcome,
  type Stint,
} from "@/lib/api";
import { readHistory, savePractice, type Practice } from "@/lib/history";

const seconds = (value: number) => value.toFixed(3);
const signed = (value: number) => (value > 0 ? "+" : "") + seconds(value);

function Tire({
  compound,
  small = false,
}: {
  compound: Compound;
  small?: boolean;
}) {
  return (
    <span
      className={"tire tire-" + compound + (small ? " tire-small" : "")}
      aria-label={compound}
    >
      {compound[0].toUpperCase()}
    </span>
  );
}

function Stints({
  stints,
  totalLaps,
  label,
}: {
  stints: Stint[];
  totalLaps: number;
  label: string;
}) {
  return (
    <div className="stint-block">
      <div
        className="stint-bar"
        role="img"
        aria-label={
          label +
          ": " +
          stints
            .map(
              (s) => s.compound + ", laps " + s.first_lap + " to " + s.last_lap,
            )
            .join("; ")
        }
      >
        {stints.map((s) => (
          <span
            key={s.first_lap}
            className={"stint stint-" + s.compound}
            style={{ flex: (s.last_lap - s.first_lap + 1) / totalLaps }}
          >
            <b>{s.compound[0].toUpperCase()}</b>
            <span>
              {s.first_lap}–{s.last_lap}
            </span>
          </span>
        ))}
      </div>
      <p className="stint-caption">
        {stints
          .map(
            (s) =>
              s.compound[0].toUpperCase() +
              " laps " +
              s.first_lap +
              "–" +
              s.last_lap,
          )
          .join(" / ")}
      </p>
    </div>
  );
}

function Assumptions({ detail }: { detail: ChallengeDetail }) {
  const a = detail.assumptions;
  return (
    <details className="disclosure assumptions">
      <summary>
        Inspect model assumptions <span>Synthetic, dry race</span>
      </summary>
      <div className="disclosure-body">
        <p>{a.label}</p>
        <div className="assumption-facts">
          <span>
            Base lap <b>{seconds(a.base_lap_time_s)} s</b>
          </span>
          <span>
            Pit loss <b>{seconds(a.pit_loss_s)} s</b>
          </span>
          <span>
            Noise <b>{a.noise}</b>
          </span>
        </div>
        <div
          className="table-scroll"
          tabIndex={0}
          aria-label="Tire assumptions, scroll horizontally if needed"
        >
          <table>
            <caption>Public tire curves, all time values in seconds</caption>
            <thead>
              <tr>
                <th>Compound</th>
                <th>Pace offset</th>
                <th>Degradation / age lap</th>
                <th>Degradation cap</th>
                <th>Warm-up by age</th>
              </tr>
            </thead>
            <tbody>
              {a.tires.map((t) => (
                <tr key={t.compound}>
                  <th>
                    <Tire compound={t.compound} small /> {t.compound}
                  </th>
                  <td>{signed(t.pace_offset_s)}</td>
                  <td>{seconds(t.degradation_s_per_lap)}</td>
                  <td>{seconds(t.degradation_cap_s)}</td>
                  <td>
                    {t.warmup_s.length
                      ? t.warmup_s.map(seconds).join(", ")
                      : "0.000"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fine-print">
          Lap time = base + compound pace + min(tire age × degradation rate,
          cap) + warm-up + any pit loss. A fresh set starts at age 0. Warm-up
          entries apply at ages 0, 1, …; later ages cost zero.
        </p>
        <p className="fine-print">
          Up to {a.max_pit_stops} pit stops; at least {a.min_distinct_compounds}{" "}
          distinct compounds by the finish. Each set can be fitted once. A pit
          after lap {detail.situation.completed_laps} fits new tires for lap{" "}
          {detail.situation.completed_laps + 1} and charges its loss once.
        </p>
      </div>
    </details>
  );
}

function Situation({ detail }: { detail: ChallengeDetail }) {
  const s = detail.situation;
  return (
    <section className="situation" aria-label="Current race situation">
      <div className="boundary-display">
        <span>Decision boundary</span>
        <div>
          <strong>{s.completed_laps.toString().padStart(2, "0")}</strong>
          <span>
            /{s.total_laps.toString().padStart(2, "0")}
            <small>laps complete</small>
          </span>
        </div>
      </div>
      <div className="situation-detail">
        <div
          className="lap-strip"
          aria-label={
            s.completed_laps +
            " laps complete, " +
            s.remaining_laps +
            " remaining"
          }
          role="img"
        >
          {Array.from({ length: s.total_laps }, (_, i) => (
            <span
              key={i}
              className={i < s.completed_laps ? "lap-done" : "lap-ahead"}
            />
          ))}
        </div>
        <div className="situation-metrics">
          <div>
            <span>On the car</span>
            <strong>
              <Tire compound={s.current_compound} small />
              {s.current_compound}
            </strong>
          </div>
          <div>
            <span>Tire age</span>
            <strong>
              {s.tire_age_laps} <small>laps</small>
            </strong>
          </div>
          <div>
            <span>To the flag</span>
            <strong>
              {s.remaining_laps} <small>laps</small>
            </strong>
          </div>
          <div>
            <span>Stops available</span>
            <strong>{s.stops_remaining}</strong>
          </div>
        </div>
        <div className="inventory">
          <span>Fresh sets left</span>
          {compounds.map((c) => (
            <span key={c}>
              <Tire compound={c} small />
              <b>{s.remaining_sets[c]}</b>
              <span className="sr-only">{c} sets remaining</span>
            </span>
          ))}
          <span className="used-compounds">
            Used: {s.used_compounds.map((c) => c[0].toUpperCase()).join(" / ")}
            <span className="sr-only"> compounds</span>
          </span>
        </div>
      </div>
    </section>
  );
}

function Playback({
  outcome,
  boundary,
}: {
  outcome: Outcome;
  boundary: number;
}) {
  const [count, setCount] = useState(0);
  const [running, setRunning] = useState(true);
  const done = count >= outcome.laps.length;
  const current = count ? outcome.laps[count - 1] : null;
  useEffect(() => {
    if (!running || done) return;
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const timer = window.setTimeout(
      () => setCount((c) => (reduced ? outcome.laps.length : c + 1)),
      reduced ? 0 : 650,
    );
    return () => window.clearTimeout(timer);
  }, [count, running, done, outcome.laps.length]);
  return (
    <section className="playback" aria-label="Result playback">
      <div className="section-heading">
        <div>
          <span className="status-dot" />
          {done ? "Chequered flag" : "Lap-by-lap playback"}
        </div>
        <div className="playback-controls">
          {!done && (
            <button
              className="text-button"
              onClick={() => setRunning((v) => !v)}
            >
              {running ? "Pause playback" : "Resume playback"}
            </button>
          )}
          {!done ? (
            <button
              className="text-button"
              onClick={() => {
                setCount(outcome.laps.length);
                setRunning(false);
              }}
            >
              Skip playback
            </button>
          ) : (
            <button
              className="text-button"
              onClick={() => {
                setCount(0);
                setRunning(true);
              }}
            >
              Replay result
            </button>
          )}
        </div>
      </div>
      <div className="playback-timing">
        <div>
          <span>Lap</span>
          <strong>
            {current?.lap ?? boundary}
            <small> / {outcome.laps.at(-1)?.lap}</small>
          </strong>
        </div>
        <div>
          <span>Lap time</span>
          <strong>
            {current ? seconds(current.lap_time_s) : "—"}
            <small> s</small>
          </strong>
        </div>
        <div>
          <span>Tire / age</span>
          <strong>
            {current ? (
              <>
                <Tire compound={current.compound} small />
                {current.tire_age_laps}
                <small> laps</small>
              </>
            ) : (
              "Ready"
            )}
          </strong>
        </div>
      </div>
      <div
        className="playback-progress"
        role="progressbar"
        aria-label="Simulated laps revealed"
        aria-valuemin={0}
        aria-valuemax={outcome.laps.length}
        aria-valuenow={count}
      >
        <span style={{ width: (count / outcome.laps.length) * 100 + "%" }} />
      </div>
      <p className="fine-print">
        {done
          ? "All remaining laps shown. The engine result is deterministic."
          : "Revealing the simulated lap records. Playback speed does not change the result."}
      </p>
      <details className="lap-records">
        <summary>Inspect lap timing</summary>
        <div
          className="table-scroll"
          tabIndex={0}
          aria-label="Recorded lap components"
        >
          <table>
            <thead>
              <tr>
                <th>Lap</th>
                <th>Tire</th>
                <th>Age</th>
                <th>Pace</th>
                <th>Wear</th>
                <th>Warm-up</th>
                <th>Pit</th>
                <th>Lap total</th>
              </tr>
            </thead>
            <tbody>
              {outcome.laps.slice(0, count).map((lap) => (
                <tr key={lap.lap}>
                  <th>{lap.lap}</th>
                  <td>
                    <Tire compound={lap.compound} small />
                  </td>
                  <td>{lap.tire_age_laps}</td>
                  <td>{signed(lap.pace_offset_s)}</td>
                  <td>{seconds(lap.degradation_s)}</td>
                  <td>{seconds(lap.warmup_s)}</td>
                  <td>{seconds(lap.pit_loss_s)}</td>
                  <td>{seconds(lap.lap_time_s)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}

const costNames: [keyof Costs, string][] = [
  ["pit_s", "Pit loss"],
  ["pace_s", "Compound pace"],
  ["warmup_s", "Warm-up"],
  ["degradation_s", "Degradation"],
  ["base_s", "Base running"],
];
function CostTable({
  selected,
  delta,
  reference,
}: {
  selected: Costs;
  delta: Costs;
  reference: string;
}) {
  return (
    <div className="table-scroll">
      <table className="cost-table">
        <caption>Measured costs over the remaining laps</caption>
        <thead>
          <tr>
            <th>Time component</th>
            <th>Your call (s)</th>
            <th>Δ vs {reference} (s)</th>
          </tr>
        </thead>
        <tbody>
          {costNames.map(([key, title]) => (
            <tr key={key}>
              <th>{title}</th>
              <td>{seconds(selected[key])}</td>
              <td
                className={
                  delta[key] < 0 ? "gain" : delta[key] > 0 ? "loss" : ""
                }
              >
                {signed(delta[key])}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GapChart({ evaluation }: { evaluation: Evaluation }) {
  const series =
    evaluation.comparison?.gap_series ??
    evaluation.selected.cumulative.map((p) => ({
      lap: p.lap,
      gap_s: p.gap_to_best_s,
    }));
  const points =
    series[0]?.lap === evaluation.decision_after_lap
      ? series
      : [{ lap: evaluation.decision_after_lap, gap_s: 0 }, ...series];
  const maxMagnitude = Math.max(...points.map((p) => Math.abs(p.gap_s)), 0.1);
  const x = (lap: number) =>
    56 +
    ((lap - points[0].lap) /
      Math.max(points[points.length - 1].lap - points[0].lap, 1)) *
      584;
  const y = (gap: number) => 116 - (gap / maxMagnitude) * 74;
  const title = evaluation.comparison
    ? "Alternative minus original"
    : "Your call minus best evaluated call";
  return (
    <section className="gap-panel" data-testid="gap-chart">
      <div className="section-heading">
        <h3>Cumulative time gap</h3>
        <span>Seconds at each lap boundary</span>
      </div>
      <p>{title}. Negative is faster; positive is slower.</p>
      <svg
        className="gap-chart"
        viewBox="0 0 680 244"
        role="img"
        aria-label={
          title +
          ". Final gap " +
          signed(points.at(-1)?.gap_s ?? 0) +
          " seconds. See the exact lap gaps below."
        }
      >
        {[maxMagnitude, 0, -maxMagnitude].map((v, i) => (
          <g key={i}>
            <line
              x1="56"
              x2="640"
              y1={y(v)}
              y2={y(v)}
              className={v === 0 ? "chart-zero" : "chart-grid"}
            />
            <text x="46" y={y(v) + 4} textAnchor="end">
              {v === 0 ? "0" : (v > 0 ? "+" : "−") + Math.abs(v).toFixed(1)}
            </text>
          </g>
        ))}
        <polyline
          points={points.map((p) => x(p.lap) + "," + y(p.gap_s)).join(" ")}
          className="chart-line"
        />
        {points.map((p) => (
          <g key={p.lap}>
            <circle cx={x(p.lap)} cy={y(p.gap_s)} r="4" />
            <text x={x(p.lap)} y="218" textAnchor="middle">
              {p.lap}
            </text>
          </g>
        ))}
        <text x="348" y="241" textAnchor="middle">
          Completed lap
        </text>
      </svg>
      <details className="lap-records">
        <summary>Exact gap values</summary>
        <table>
          <thead>
            <tr>
              <th>After lap</th>
              <th>Signed gap (s)</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.lap}>
                <th>{p.lap}</th>
                <td>{signed(p.gap_s)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}

function RunCard({
  outcome,
  title,
  totalLaps,
  original = false,
}: {
  outcome: Outcome;
  title: string;
  totalLaps: number;
  original?: boolean;
}) {
  return (
    <div
      className="run-card"
      data-testid={original ? "original-result" : "alternative-result"}
    >
      <span className="run-label">{title}</span>
      <h3>{actionLabels[outcome.action]}</h3>
      <div className="run-time">
        {seconds(outcome.remaining_elapsed_s)} <small>s remaining</small>
      </div>
      <Stints stints={outcome.stints} totalLaps={totalLaps} label={title} />
      <p className="fine-print">
        Full race: {seconds(outcome.total_elapsed_s)} s ·{" "}
        {outcome.legal ? "Legal finish" : "Illegal finish"}
      </p>
    </div>
  );
}

function Results({
  original,
  alternative,
  totalLaps,
  attempt,
  onRewind,
  headingRef,
}: {
  original: Evaluation;
  alternative: Evaluation | null;
  totalLaps: number;
  attempt: number;
  onRewind: () => void;
  headingRef: React.RefObject<HTMLHeadingElement | null>;
}) {
  const evaluation = alternative ?? original;
  return (
    <div className="results">
      <Playback
        key={attempt}
        outcome={evaluation.selected}
        boundary={evaluation.decision_after_lap}
      />
      <section className="debrief">
        <div className="section-heading">
          <h2 ref={headingRef} tabIndex={-1}>
            Debrief
          </h2>
          <span className="legal-label">Legal finish</span>
        </div>
        <div className="score-row">
          <div>
            <span>Excess remaining time</span>
            <strong data-testid="score">
              {signed(evaluation.score_s)}
              <small> s</small>
            </strong>
          </div>
          <p>{evaluation.score_label}</p>
        </div>
        <p className="debrief-summary">{evaluation.debrief.summary}</p>
        <p className="fine-print">
          Compared with {actionLabels[evaluation.best_action].toLowerCase()} at{" "}
          {seconds(evaluation.best_remaining_elapsed_s)} s. Every legal call
          uses the same continuation: {evaluation.continuation.description}
        </p>
        <CostTable
          selected={evaluation.selected.components}
          delta={evaluation.debrief.delta_components}
          reference="best call"
        />
        <details className="lap-records">
          <summary>Compare all legal calls</summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Call</th>
                  <th>Remaining (s)</th>
                  <th>Excess (s)</th>
                </tr>
              </thead>
              <tbody>
                {evaluation.alternatives.map((outcome) => (
                  <tr key={outcome.action}>
                    <th>
                      {actionLabels[outcome.action]}
                      {outcome.action === evaluation.selected_action
                        ? " (selected)"
                        : ""}
                    </th>
                    <td>{seconds(outcome.remaining_elapsed_s)}</td>
                    <td>{signed(outcome.excess_s)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>
      <section className="fork-results" aria-label="Independent run comparison">
        <div className="section-heading">
          <h3>
            {alternative
              ? "Same boundary. Two different calls."
              : "Your completed run"}
          </h3>
          <span>Stints across the full race</span>
        </div>
        <div className={"run-grid" + (alternative ? " has-alternative" : "")}>
          <RunCard
            outcome={original.selected}
            title="Original call"
            totalLaps={totalLaps}
            original
          />
          {alternative && (
            <RunCard
              outcome={alternative.selected}
              title="Independent alternative"
              totalLaps={totalLaps}
            />
          )}
        </div>
        {alternative?.comparison && (
          <p className="comparison-result">
            Alternative minus original:{" "}
            <strong>
              {signed(alternative.comparison.delta_remaining_s)} s
            </strong>
            .{" "}
            {alternative.comparison.delta_remaining_s < 0
              ? "The alternative is faster."
              : alternative.comparison.delta_remaining_s > 0
                ? "The original is faster."
                : "Both calls have equal remaining time."}
          </p>
        )}
      </section>
      <GapChart evaluation={evaluation} />
      <div className="rewind-bar">
        <div>
          <h3>Try the other call.</h3>
          <p>
            Return to this exact decision boundary. Your original run stays
            intact.
          </p>
        </div>
        <button className="secondary-button" onClick={onRewind}>
          <span aria-hidden="true">↶</span> Rewind this call
        </button>
      </div>
    </div>
  );
}

function PracticeHistory({
  history,
  challenge,
}: {
  history: Practice[];
  challenge: ChallengeSummary;
}) {
  return (
    <details className="disclosure practice-history">
      <summary>
        Local practice history{" "}
        <span>
          {history.length} {history.length === 1 ? "attempt" : "attempts"}
        </span>
      </summary>
      <div className="disclosure-body">
        <p className="fine-print">
          For {challenge.title}, version {challenge.version}. Stored only in
          this browser, up to 20 attempts. Repeated calls are practice; local
          records are user-editable.
        </p>
        {history.length ? (
          <ol>
            {history.map((p, i) => (
              <li key={p.recorded_at + "-" + i} data-testid="history-entry">
                <span>
                  {actionLabels[p.action]}
                  {p.fork ? " · alternative" : ""}
                  <small>{new Date(p.recorded_at).toLocaleString()}</small>
                </span>
                <b>
                  {signed(p.score_s)} s <small>excess</small>
                </b>
              </li>
            ))}
          </ol>
        ) : (
          <p>Make a call to start your practice history.</p>
        )}
      </div>
    </details>
  );
}

export default function Arena() {
  const [challenges, setChallenges] = useState<ChallengeSummary[]>([]);
  const [detail, setDetail] = useState<ChallengeDetail | null>(null);
  const [activeId, setActiveId] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Action | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<{
    source: "catalog" | "challenge" | "submit";
    message: string;
  } | null>(null);
  const [original, setOriginal] = useState<Evaluation | null>(null);
  const [alternative, setAlternative] = useState<Evaluation | null>(null);
  const [choosing, setChoosing] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [history, setHistory] = useState<Practice[]>([]);
  const requestId = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const submitGuard = useRef(false);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const callHeading = useRef<HTMLHeadingElement>(null);

  const loadDetail = useCallback(async (challenge: ChallengeSummary) => {
    controller.current?.abort();
    const pending = new AbortController();
    controller.current = pending;
    const id = ++requestId.current;
    submitGuard.current = false;
    setActiveId(challenge.id);
    setLoading(true);
    setDetail(null);
    setError(null);
    setSelected(null);
    setOriginal(null);
    setAlternative(null);
    setChoosing(true);
    setSubmitting(false);
    setHistory(readHistory(challenge));
    try {
      const data = await request<ChallengeDetail>(
        "/api/v1/challenges/" +
          encodeURIComponent(challenge.id) +
          "?version=" +
          challenge.version,
        pending.signal,
      );
      if (id === requestId.current) setDetail(data);
    } catch (e) {
      if (!pending.signal.aborted && id === requestId.current)
        setError({
          source: "challenge",
          message:
            e instanceof Error
              ? e.message
              : "The challenge could not be loaded.",
        });
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  const loadCatalog = useCallback(() => {
    controller.current?.abort();
    const pending = new AbortController();
    controller.current = pending;
    const id = ++requestId.current;
    return request<{
      api_version: 1;
      challenges: ChallengeSummary[];
    }>("/api/v1/challenges", pending.signal)
      .then((data) => {
        if (id !== requestId.current) return;
        if (!data.challenges.length)
          throw new Error(
            "There are no challenges available. Retry after checking the API.",
          );
        setChallenges(data.challenges);
        return loadDetail(data.challenges[0]);
      })
      .catch((e: unknown) => {
        if (!pending.signal.aborted && id === requestId.current) {
          setError({
            source: "catalog",
            message:
              e instanceof Error
                ? e.message
                : "Challenges could not be loaded.",
          });
          setLoading(false);
        }
      });
  }, [loadDetail]);

  useEffect(() => {
    void loadCatalog();
    return () => {
      controller.current?.abort();
    };
  }, [loadCatalog]);
  useEffect(() => {
    if (!choosing && original)
      resultHeading.current?.focus({ preventScroll: true });
  }, [choosing, original, alternative]);

  async function submit() {
    if (!detail || !selected || submitGuard.current) return;
    submitGuard.current = true;
    controller.current?.abort();
    const pending = new AbortController();
    controller.current = pending;
    const id = ++requestId.current;
    setSubmitting(true);
    setError(null);
    try {
      const evaluation = await request<Evaluation>(
        "/api/v1/evaluate",
        pending.signal,
        {
          challenge_id: detail.id,
          challenge_version: detail.version,
          action: selected,
          ...(original ? { compare_action: original.selected_action } : {}),
        },
      );
      if (id !== requestId.current) return;
      if (original) setAlternative(evaluation);
      else setOriginal(evaluation);
      setChoosing(false);
      setAttempt((v) => v + 1);
      setHistory(
        savePractice(detail, {
          action: evaluation.selected_action,
          score_s: evaluation.score_s,
          remaining_s: evaluation.selected.remaining_elapsed_s,
          recorded_at: new Date().toISOString(),
          fork: original !== null,
        }),
      );
    } catch (e) {
      if (!pending.signal.aborted && id === requestId.current)
        setError({
          source: "submit",
          message:
            e instanceof Error
              ? e.message
              : "This call could not be evaluated.",
        });
    } finally {
      if (id === requestId.current) {
        setSubmitting(false);
        submitGuard.current = false;
      }
    }
  }

  function rewind() {
    setChoosing(true);
    setSelected(null);
    setError(null);
    window.requestAnimationFrame(() => {
      callHeading.current?.focus();
      callHeading.current?.scrollIntoView({
        behavior: "instant",
        block: "center",
      });
    });
  }

  function retry() {
    if (error?.source === "submit") void submit();
    else if (error?.source === "challenge") {
      const challenge = challenges.find((c) => c.id === activeId);
      if (challenge) void loadDetail(challenge);
    } else {
      setLoading(true);
      setError(null);
      void loadCatalog();
    }
  }

  return (
    <>
      <a className="skip-link" href="#arena-main">
        Skip to arena
      </a>
      <header className="site-header">
        <Link className="wordmark" href="/" aria-label="PitWall Arena home">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          PitWall<span>Arena</span>
        </Link>
        <div className="header-meta">
          <span className="status-dot" />
          Synthetic practice<span className="header-version">F0.5</span>
        </div>
      </header>
      <div className="arena-layout">
        <aside className="challenge-rail" aria-label="Challenge selection">
          <div className="rail-intro">
            <p className="section-kicker">The strategy desk</p>
            <h1>
              Make <br />
              the call.
            </h1>
            <p>
              One boundary. One decision. <br />
              Find the time you leave behind.
            </p>
          </div>
          <nav aria-label="Challenges">
            <h2>Choose a situation</h2>
            {challenges.map((c) => (
              <button
                key={c.id + "-" + c.version}
                data-testid={"challenge-" + c.id}
                aria-label={c.title}
                aria-current={activeId === c.id ? "true" : undefined}
                className={
                  "challenge-button " + (activeId === c.id ? "is-active" : "")
                }
                onClick={() => void loadDetail(c)}
              >
                <span className="challenge-title">
                  {c.title}
                  <span aria-hidden="true">↗</span>
                </span>
                <span>{c.summary}</span>
                <small>{c.remaining_laps} laps to resolve</small>
              </button>
            ))}
          </nav>
          <div className="rail-note">
            <span aria-hidden="true">◇</span>
            <p>
              No reflexes required.
              <br />
              Read the situation. Inspect the assumptions. Then commit.
            </p>
          </div>
          <a className="glossary-link" href="#glossary">
            New to pit strategy? Read the glossary
          </a>
        </aside>
        <main id="arena-main" className="main-board">
          {loading && (
            <div className="loading-state" role="status">
              <span className="loading-line" />
              <h2>Preparing the pit wall</h2>
              <p>Loading the trusted decision boundary.</p>
            </div>
          )}
          {error && (
            <div className="error-banner" role="alert">
              <div>
                <h2>
                  {error.source === "submit"
                    ? "Your call has not been recorded"
                    : "The pit wall is unavailable"}
                </h2>
                <p>{error.message}</p>
              </div>
              <button
                className="secondary-button"
                onClick={retry}
                disabled={submitting}
              >
                Retry
              </button>
            </div>
          )}
          {detail && !loading && (
            <>
              <div className="challenge-heading">
                <div>
                  <p className="section-kicker">
                    Synthetic challenge / version {detail.version}
                  </p>
                  <h2>{detail.title}</h2>
                  <p>{detail.briefing}</p>
                </div>
                <div className="dry-tag">
                  Dry
                  <br />
                  <span>conditions</span>
                </div>
              </div>
              <Situation detail={detail} />
              <Assumptions detail={detail} />
              {choosing ? (
                <section className="call-panel" aria-label="Make your pit call">
                  <div className="section-heading">
                    <h2 ref={callHeading} tabIndex={-1}>
                      {original ? "Rewind: make another call" : "Your call"}
                    </h2>
                    <span>
                      Before lap {detail.situation.completed_laps + 1}
                    </span>
                  </div>
                  <p>{detail.objective}</p>
                  {original && (
                    <div
                      className="original-preserved"
                      data-testid="original-result"
                    >
                      <span>Original preserved</span>
                      <strong>{actionLabels[original.selected_action]}</strong>
                      <b>
                        {seconds(original.selected.remaining_elapsed_s)} s
                        remaining
                      </b>
                    </div>
                  )}
                  <div
                    className="action-grid"
                    role="group"
                    aria-label="Legal pit calls"
                  >
                    {detail.actions.map((a) => (
                      <div key={a.action} className="action-option">
                        <button
                          data-testid={"action-" + a.action}
                          aria-label={actionLabels[a.action]}
                          aria-pressed={selected === a.action}
                          aria-describedby={
                            a.reason ? "reason-" + a.action : undefined
                          }
                          disabled={!a.available || submitting}
                          onClick={() => setSelected(a.action)}
                          className={
                            "action-button" +
                            (selected === a.action ? " is-selected" : "")
                          }
                        >
                          {a.action === "stay_out" ? (
                            <span className="stay-icon" aria-hidden="true">
                              ↗
                            </span>
                          ) : (
                            <Tire compound={a.action.slice(4) as Compound} />
                          )}
                          <strong>{actionLabels[a.action]}</strong>
                          <small>
                            {a.available
                              ? a.action === "stay_out"
                                ? "Keep current tires"
                                : "Fit one fresh set"
                              : "Unavailable"}
                          </small>
                          <span className="selection-mark" aria-hidden="true">
                            {selected === a.action ? "✓" : "+"}
                          </span>
                        </button>
                        {a.reason && (
                          <p
                            id={"reason-" + a.action}
                            className="unavailable-reason"
                          >
                            {a.reason}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                  <div className="commit-row">
                    <p>
                      <strong>After this call: no more stops.</strong>
                      <br />
                      {detail.continuation.description}
                    </p>
                    <button
                      className="primary-button"
                      disabled={!selected || submitting}
                      onClick={() => void submit()}
                    >
                      {submitting
                        ? "Simulating call…"
                        : original
                          ? "Compare alternative"
                          : "Commit pit call"}
                      <span aria-hidden="true">↗</span>
                    </button>
                  </div>
                  <p className="scoring-note">
                    Your score is excess remaining time against the best legal
                    call at this boundary, within the disclosed synthetic model
                    and continuation. It is not a global optimum or real-world
                    F1 performance.
                  </p>
                </section>
              ) : (
                original && (
                  <Results
                    original={original}
                    alternative={alternative}
                    totalLaps={detail.situation.total_laps}
                    attempt={attempt}
                    onRewind={rewind}
                    headingRef={resultHeading}
                  />
                )
              )}
              <PracticeHistory history={history} challenge={detail} />
            </>
          )}
          <section id="glossary" className="glossary">
            <h2>The short glossary</h2>
            <dl>
              <div>
                <dt>Stint</dt>
                <dd>
                  A sequence of laps on one tire set. S / M / H mean soft /
                  medium / hard.
                </dd>
              </div>
              <div>
                <dt>Pit loss</dt>
                <dd>
                  The extra time for a stop, charged once on the next lap
                  interval.
                </dd>
              </div>
              <div>
                <dt>Degradation</dt>
                <dd>
                  The age-related lap-time cost, bounded by the assumed tire
                  curve.
                </dd>
              </div>
              <div>
                <dt>Warm-up</dt>
                <dd>A separate cost on the first laps of a fresh set.</dd>
              </div>
              <div>
                <dt>Excess time</dt>
                <dd>
                  Your remaining time minus the fastest legal call under the
                  same continuation.
                </dd>
              </div>
              <div>
                <dt>Rewind</dt>
                <dd>
                  An independent alternative from the original boundary. The
                  original stays intact.
                </dd>
              </div>
            </dl>
          </section>
          <footer className="board-footer">
            <span>PitWall Arena</span>
            <p>
              Synthetic circuit. Deterministic model. A place to practice the
              decision.
            </p>
          </footer>
        </main>
      </div>
    </>
  );
}
