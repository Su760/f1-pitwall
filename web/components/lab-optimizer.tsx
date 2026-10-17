"use client";
import { useEffect, useRef, useState } from "react";
import { request } from "@/lib/api";
import type { Controls, OptimizationResult, SearchSettings } from "@/lib/lab";

export default function LabOptimizer({
  controls,
  valid,
  settings,
  download,
}: {
  controls: Controls;
  valid: boolean;
  settings: SearchSettings;
  download: (name: string, value: unknown) => void;
}) {
  // Parent keys this component by every edit/reset, even equivalent numeric edits.
  // Cleanup cancels transport; the lifetime guard also rejects late resolutions.
  const active = useRef(true);
  const inFlight = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OptimizationResult | null>(null);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      controller.current?.abort();
    };
  }, []);
  async function search() {
    if (!valid || inFlight.current) return;
    inFlight.current = true;
    controller.current = new AbortController();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const value = await request<OptimizationResult>(
        "/api/v1/lab/optimize",
        controller.current.signal,
        controls,
      );
      if (!active.current) return;
      if (
        value.optimization_version !== 1 ||
        !value.search.search_complete ||
        !value.best.legal ||
        (Object.keys(controls) as (keyof Controls)[]).some(
          (key) => value.controls[key] !== controls[key],
        )
      )
        throw new Error("No complete result for these assumptions. Please retry.");
      setResult(value);
    } catch (failure) {
      if (active.current && !controller.current.signal.aborted)
        setError(failure instanceof Error ? failure.message : "Search failed. Please retry.");
    } finally {
      if (active.current) {
        inFlight.current = false;
        setLoading(false);
      }
    }
  }
  return (
    <section className="lab-optimization" aria-labelledby="optimization-heading">
      <div className="lab-section-heading">
        <h2 id="optimization-heading">Find the best legal fixed schedule</h2>
        <p>
          Search all 0–2 stop schedules over 12 laps with a soft start, two sets
          of each compound and at least two compounds used. The same engine
          checks every candidate. This runs only when you activate the button.
        </p>
        <p>
          Server limits: {settings.max_candidates} candidates and{" "}
          {settings.max_lap_evaluations.toLocaleString("en-US")} potential search
          lap evaluations, plus 24 for benchmarks. Retain the top {settings.top_k};
          evaluate the entire candidate space.
        </p>
      </div>
      <button
        className="lab-button lab-search-button"
        aria-disabled={!valid || loading}
        aria-describedby="search-status"
        onClick={search}
      >
        {loading ? "Searching legal schedules…" : error ? "Retry strategy search" : "Find best legal strategy"}
      </button>
      <p id="search-status" role="status" className="lab-note">
        {!valid
          ? "Enter valid assumptions above before searching."
          : loading
            ? "Evaluating the complete bounded search. Changing assumptions cancels this result."
            : result
              ? "Search complete. All candidates evaluated."
              : "Uses the selected assumptions. Edits or reset clear results and exports; search again explicitly."}
      </p>
      {error && <p role="alert">{error}</p>}
      {result && (
        <div data-testid="optimization-result">
          <article className="lab-outcome">
            <h3>{result.label}</h3>
            <p>
              Resolved: pit {result.controls.pit_loss_s} s · degradation ×{result.controls.degradation_multiplier}
              {" "}· warm-up ×{result.controls.warmup_multiplier}
            </p>
            <p className="lab-total" data-testid="optimized-total">
              {result.best.total_elapsed_s.toFixed(3)} <small>s</small>
            </p>
            <p>
              Complete search · {result.search.candidate_count} candidates ·{" "}
              {result.search.legal_count} legal · legal finish
            </p>
            <ul className="lab-pit-schedule">
              {result.best.schedule.stops.map((stop) => (
                <li key={stop.after_lap}>Pit after lap {stop.after_lap} → {stop.compound}</li>
              ))}
            </ul>
            <div className="lab-timeline" aria-label="Best schedule tire-stint timeline">
              {result.best.stints.map((stint) => (
                <div
                  className={"lab-stint lab-" + stint.compound}
                  key={stint.first_lap}
                  style={{ flex: stint.last_lap - stint.first_lap + 1 }}
                >
                  <b>{stint.compound}</b>
                  <span>laps {stint.first_lap}–{stint.last_lap}</span>
                </div>
              ))}
            </div>
            <dl className="lab-costs">
              {result.benchmarks.map((benchmark) => (
                <div key={benchmark.name}>
                  <dt>Improvement over {benchmark.name}</dt>
                  <dd data-testid={"gain-" + benchmark.name}>{benchmark.improvement_s.toFixed(3)} s</dd>
                </div>
              ))}
            </dl>
            <p className="lab-note">
              Improvement = benchmark time minus best time; positive means faster.
              Display rounded to 0.001 s; 0.000 can hide a smaller difference.
              Ranking and exports retain full precision. {result.search.tie_break}.
              This optimum applies only to the configured synthetic fixed-schedule search.
            </p>
          </article>
          <div className="lab-export">
            <h3>Reproduce this search</h3>
            <p>Download all three files. The search record includes controls, source hashes, limits, counts and the top three schedules.</p>
            <div>
              <button className="lab-button" onClick={() => download("lab-optimized-scenario.json", result.scenario)}>Export optimized scenario</button>
              <button className="lab-button" onClick={() => download("lab-winning-trace.json", result.trace)}>Export winning trace</button>
              <button className="lab-button" onClick={() => download("lab-search.json", result)}>Export search record</button>
            </div>
            <p>From the repository root, replay the downloaded trace:</p>
            <code>.venv-api/bin/python -m pitwall replay lab-winning-trace.json --scenario lab-optimized-scenario.json</code>
            <p>Recompute the search with the recorded limits:</p>
            <code>
              .venv-api/bin/python -m pitwall optimize lab-optimized-scenario.json --top {result.search.top_k}
              {" "}--max-candidates {result.search.limits.max_candidates}
              {" "}--max-lap-evaluations {result.search.limits.max_lap_evaluations}
              {" "}--output traces/lab-recomputed-winner.json
            </code>
          </div>
        </div>
      )}
    </section>
  );
}
