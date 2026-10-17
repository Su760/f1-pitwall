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
          <section className="lab-ranked" aria-labelledby="ranked-heading">
            <div className="lab-section-heading">
              <h3 id="ranked-heading">Compare the top three schedules</h3>
              <p>
                Shared race-lap scale, 1–12; this is not simultaneous clock time.
                S = soft, M = medium, H = hard. Each segment is a separate tire set.
              </p>
              <p>
                Times and gaps round to 0.001 s. Equal displayed values do not
                establish an exact tie: only the explicit tie labels below do.
                Exact ties keep this deterministic order: fewer stops, earlier
                pit-boundary tuple, then soft/medium/hard compound order.
                Small gaps do not establish robustness, confidence or real-world superiority.
              </p>
            </div>
            <ol className="lab-ranked-cards" aria-label="Top three legal fixed schedules">
              {result.search.ranked.map((entry) => (
                <li className="lab-ranked-card" key={entry.schedule.name}>
                  <h4>Rank {entry.rank}</h4>
                  <div className="lab-ranked-metrics">
                    <p className="lab-total" data-testid={"rank-" + entry.rank + "-total"}>
                      {entry.total_elapsed_s.toFixed(3)} <small>s</small>
                    </p>
                    <p data-testid={"rank-" + entry.rank + "-gap"}>
                      Gap to fastest: {entry.gap_s.toFixed(3)} s
                    </p>
                  </div>
                  <p className="lab-ranked-tie" data-testid={"rank-" + entry.rank + "-tie"}>
                    {entry.exact_tie_ranks.length
                      ? "Exact elapsed-time tie with rank " + entry.exact_tie_ranks.join(", ") + "."
                      : "No exact elapsed-time tie among these three."}
                  </p>
                  <ul className="lab-pit-schedule">
                    {entry.schedule.stops.map((stop) => (
                      <li key={stop.after_lap}>
                        Pit after lap {stop.after_lap} → {stop.compound}
                      </li>
                    ))}
                  </ul>
                  <div
                    className="lab-ranked-timeline"
                    role="img"
                    aria-label={"Rank " + entry.rank + " race-lap timeline: " + entry.stints.map(
                      (stint) => stint.compound + " laps " + stint.first_lap + "–" + stint.last_lap,
                    ).join("; ")}
                  >
                    <p className="lab-ranked-axis-label">Race lap</p>
                    <div className="lab-ranked-axis" aria-hidden="true">
                      {Array.from({ length: 12 }, (_, i) => <span key={i}>{i + 1}</span>)}
                    </div>
                    <div className="lab-ranked-track" aria-hidden="true">
                      {entry.stints.map((stint) => (
                        <span
                          className={"lab-ranked-segment lab-" + stint.compound}
                          key={stint.first_lap}
                          style={{ gridColumn: stint.first_lap + " / " + (stint.last_lap + 1) }}
                        >
                          {stint.compound[0].toUpperCase()}
                        </span>
                      ))}
                    </div>
                  </div>
                  <ul className="lab-ranked-stints" aria-label={"Rank " + entry.rank + " tire stints"}>
                    {entry.stints.map((stint) => (
                      <li key={stint.first_lap}>
                        <strong>{stint.compound}</strong>: laps {stint.first_lap}–{stint.last_lap}
                      </li>
                    ))}
                  </ul>
                  <p className="lab-ranked-precision">
                    Full precision: elapsed {String(entry.total_elapsed_s)} s;
                    gap {String(entry.gap_s)} s.
                  </p>
                </li>
              ))}
            </ol>
          </section>
          <div className="lab-export">
            <h3>Reproduce this search</h3>
            <p>Download all three files. The search record includes all three schedules and stints. The winning trace belongs to rank 1 only; it does not contain alternative traces.</p>
            <div>
              <button className="lab-button" onClick={() => download("lab-optimized-scenario.json", result.scenario)}>Export optimized scenario</button>
              <button className="lab-button" onClick={() => download("lab-winning-trace.json", result.trace)}>Export rank 1 winning trace</button>
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
