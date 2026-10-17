"use client";
import Link from "next/link";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { request } from "@/lib/api";
import type {
  Control,
  Controls,
  LabMetadata,
  LabResult,
  Point,
} from "@/lib/lab";
const controlNames: Control[] = [
  "pit_loss_s",
  "degradation_multiplier",
  "warmup_multiplier",
];
const seconds = (v: number) => v.toFixed(3);
const signed = (v: number) =>
  (v > 0 ? "+" : "") +
  (Math.abs(v) < 0.001 && v !== 0 ? v.toPrecision(6) : v.toFixed(3));
const pointLabel = (p: Point) =>
  "Pit " +
  p.pit_loss_s +
  " s, degradation " +
  p.degradation_multiplier +
  ", " +
  p.label +
  ", difference " +
  signed(p.delta_s) +
  " seconds";
function download(name: string, value: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2) + "\n"], {
      type: "application/json",
    }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function Lab({ metadata }: { metadata: LabMetadata }) {
  const defaults = () =>
    Object.fromEntries(
      controlNames.map((k) => [k, String(metadata.controls[k].default)]),
    ) as Record<Control, string>;
  const [inputs, setInputs] = useState(defaults);
  const [activeCell, setActiveCell] = useState(0);
  const cells = useRef<(HTMLButtonElement | null)[]>([]);
  const resetButton = useRef<HTMLButtonElement>(null);
  const [retry, setRetry] = useState(0);
  const [answer, setAnswer] = useState<{
    key: string;
    result?: LabResult;
    error?: string;
  } | null>(null);
  const [selected, setSelected] = useState<{
    key: string;
    point: Point;
  } | null>(null);
  const controls = Object.fromEntries(
    controlNames.map((k) => [k, Number(inputs[k])]),
  ) as Controls;
  const valid = controlNames.every(
    (k) =>
      inputs[k].trim() !== "" &&
      Number.isFinite(controls[k]) &&
      controls[k] >= metadata.controls[k].min &&
      controls[k] <= metadata.controls[k].max,
  );
  const currentKey = valid
    ? JSON.stringify({ ...controls, grid_size: metadata.grid_default })
    : null;
  // Hide stale data during render, even before effect cleanup or debounce.
  const visible = answer?.key === currentKey ? answer : null;
  const result = visible?.result;
  useEffect(() => {
    if (!currentKey) return;
    const controller = new AbortController();
    let active = true;
    const timer = setTimeout(() => {
      request<LabResult>(
        "/api/v1/lab",
        controller.signal,
        JSON.parse(currentKey),
      )
        .then((value) => {
          if (!active) return;
          const sent = JSON.parse(currentKey);
          if (
            value.lab_version !== 1 ||
            value.grid.size !== sent.grid_size ||
            controlNames.some((k) => value.controls[k] !== sent[k])
          )
            throw new Error(
              "The lab returned results for different inputs. Please retry.",
            );
          setAnswer({ key: currentKey, result: value });
        })
        .catch((error) => {
          if (active && !controller.signal.aborted)
            setAnswer({ key: currentKey, error: error.message });
        });
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [currentKey, retry]);
  function navigateMap(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
    size: number,
  ) {
    let row = Math.floor(index / size),
      column = index % size;
    switch (event.key) {
      case "ArrowLeft":
        column = Math.max(0, column - 1);
        break;
      case "ArrowRight":
        column = Math.min(size - 1, column + 1);
        break;
      case "ArrowUp":
        row = Math.max(0, row - 1);
        break;
      case "ArrowDown":
        row = Math.min(size - 1, row + 1);
        break;
      case "Home":
        column = 0;
        if (event.ctrlKey) row = 0;
        break;
      case "End":
        column = size - 1;
        if (event.ctrlKey) row = size - 1;
        break;
      default:
        return; // Native Tab / Shift+Tab leave the composite grid.
    }
    event.preventDefault();
    cells.current[row * size + column]?.focus();
  }
  function update(key: Control, value: string) {
    setInputs((old) => ({ ...old, [key]: value }));
    setAnswer(null);
    setSelected(null);
    setActiveCell(0);
    setRetry((n) => n + 1); // Re-request even if text changes from 18 to 18.0.
  }
  function reset() {
    setInputs(defaults());
    setAnswer(null);
    setSelected(null);
    setActiveCell(0);
    setRetry((n) => n + 1);
  }
  return (
    <>
      <section className="lab-controls" aria-label="Illustrative controls">
        {controlNames.map((k) => {
          const c = metadata.controls[k];
          return (
            <div className="lab-control" key={k}>
              <label htmlFor={k}>{c.label}</label>
              <div className="lab-control-inputs">
                <input
                  id={k}
                  type="number"
                  min={c.min}
                  max={c.max}
                  step={c.step}
                  value={inputs[k]}
                  onChange={(e) => update(k, e.target.value)}
                />
                <input
                  type="range"
                  aria-label={c.label + " slider"}
                  min={c.min}
                  max={c.max}
                  step={c.step}
                  value={inputs[k] || c.min}
                  onChange={(e) => update(k, e.target.value)}
                />
              </div>
              <span>
                {c.min}–{c.max} · illustrative range
              </span>
            </div>
          );
        })}
        <button className="lab-button" ref={resetButton} onClick={reset}>
          Reset assumptions
        </button>
      </section>
      <p className="lab-explanation">
        Degradation scales both slope and cap. Warm-up scales every entry,
        including the starting set. All other parameters, rules and schedules
        stay fixed.
      </p>
      {!valid ? (
        <p role="alert">
          Enter a number within each illustrative range. No results are shown
          for invalid inputs.
        </p>
      ) : visible?.error ? (
        <div role="alert">
          <p>{visible.error}</p>
          <button
            className="lab-button"
            onClick={() => {
              // The retry button unmounts while loading; retain a useful focus target.
              resetButton.current?.focus();
              setActiveCell(0);
              setAnswer(null);
              setRetry((n) => n + 1);
            }}
          >
            Retry comparison
          </button>
        </div>
      ) : !result ? (
        <p role="status" className="lab-loading">
          Simulating both schedules and the sampled map…
        </p>
      ) : (
        <>
          <section aria-labelledby="comparison-title" data-testid="lab-results">
            <div className="lab-section-heading">
              <h2 id="comparison-title">The two-schedule comparison</h2>
              <p>
                Resolved: pit {result.controls.pit_loss_s} s · degradation ×
                {result.controls.degradation_multiplier} · warm-up ×
                {result.controls.warmup_multiplier}
              </p>
            </div>
            <div className="lab-verdict" role="status">
              <strong>{result.comparison.label}</strong>
              <span data-testid="lab-delta">
                Δ {signed(result.comparison.delta_s)} s
              </span>
              <p>
                {result.comparison.sign_convention}. This is not a global
                optimum.
              </p>
            </div>
            <div className="lab-outcomes">
              {result.comparison.strategies.map((strategy) => (
                <article className="lab-outcome" key={strategy.name}>
                  <h3>{strategy.name}</h3>
                  <p
                    className="lab-total"
                    data-testid={strategy.name + "-total"}
                  >
                    {seconds(strategy.total_elapsed_s)} <small>s</small>
                  </p>
                  <p>
                    {strategy.legal ? "Legal finish" : "Illegal"} ·{" "}
                    {strategy.pit_count} stops · pit after lap{" "}
                    {strategy.pit_boundaries.join(", ")}
                  </p>
                  <div
                    className="lab-timeline"
                    aria-label={strategy.name + " tire-stint timeline"}
                  >
                    {strategy.stints.map((stint) => (
                      <div
                        className={"lab-stint lab-" + stint.compound}
                        key={stint.first_lap}
                        style={{ flex: stint.last_lap - stint.first_lap + 1 }}
                      >
                        <b>{stint.compound}</b>
                        <span>
                          laps {stint.first_lap}–{stint.last_lap}
                        </span>
                      </div>
                    ))}
                  </div>
                  <dl className="lab-costs">
                    {(
                      [
                        ["Base", "base_s"],
                        ["Compound pace offset", "pace_s"],
                        ["Pit loss", "pit_s"],
                        ["Degradation", "degradation_s"],
                        ["Warm-up", "warmup_s"],
                      ] as const
                    ).map(([label, k]) => (
                      <div key={k}>
                        <dt>{label}</dt>
                        <dd>{seconds(strategy.components[k])} s</dd>
                      </div>
                    ))}
                  </dl>
                </article>
              ))}
            </div>
            <p className="lab-note">
              Totals use full engine precision; display rounds to 0.001 s.
              Numerical tie within {result.tie_tolerance_s} s; below{" "}
              {result.near_tie_s} s a faster schedule is labelled near-tie. More
              digits appear for tiny signed differences. Component sums may
              differ at the last floating-point bit.
            </p>
          </section>
          <section aria-labelledby="map-title">
            <div className="lab-section-heading">
              <h2 id="map-title">Where the preference changes</h2>
              <p>
                {result.grid.size} × {result.grid.size} sampled points · warm-up
                fixed at ×{result.controls.warmup_multiplier}
              </p>
            </div>
            <p>
              Columns: pit loss (s/stop). Rows: degradation multiplier. <b>1</b>{" "}
              = one-stop faster; <b>2</b> = two-stop faster; <b>=</b> =
              numerical tie. Select or focus a cell for its exact sampled
              comparison.
            </p>
            <p id="map-keyboard-help" className="lab-note">
              Tab enters at one cell. Arrow keys move between samples; Home/End
              move to the row edges; Ctrl+Home/End move to the grid corners. Tab
              or Shift+Tab leaves the map. Scroll or swipe to explore; both axes
              stay visible. Changing assumptions resets the map entry to the
              top-left sample.
            </p>
            <div className="lab-map-scroll">
              <table
                className="lab-map"
                role="grid"
                aria-labelledby="map-title"
                aria-describedby="map-keyboard-help"
              >
                <caption>
                  Pit-loss × degradation sensitivity; each cell compares only
                  these two schedules
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Deg × / Pit s</th>
                    {result.grid.axes.pit_loss_s.map((p) => (
                      <th scope="col" key={p}>
                        {Number(p.toFixed(2))}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...result.grid.rows].reverse().map((row, rowIndex) => (
                    <tr key={row[0].degradation_multiplier}>
                      <th scope="row">
                        {Number(row[0].degradation_multiplier.toFixed(2))}
                      </th>
                      {row.map((point, columnIndex) => (
                        <td role="gridcell" key={point.pit_loss_s}>
                          <button
                            className={"lab-cell lab-winner-" + point.winner}
                            aria-label={pointLabel(point)}
                            tabIndex={
                              activeCell ===
                              rowIndex * result.grid.size + columnIndex
                                ? 0
                                : -1
                            }
                            ref={(element) => {
                              cells.current[
                                rowIndex * result.grid.size + columnIndex
                              ] = element;
                            }}
                            onKeyDown={(event) =>
                              navigateMap(
                                event,
                                rowIndex * result.grid.size + columnIndex,
                                result.grid.size,
                              )
                            }
                            onFocus={(event) => {
                              setActiveCell(
                                rowIndex * result.grid.size + columnIndex,
                              );
                              setSelected({ key: currentKey!, point });
                              event.currentTarget.scrollIntoView({
                                block: "nearest",
                                inline: "nearest",
                                behavior: "instant",
                              });
                            }}
                            onClick={(event) => {
                              event.currentTarget.focus();
                              setActiveCell(
                                rowIndex * result.grid.size + columnIndex,
                              );
                              setSelected({ key: currentKey!, point });
                            }}
                          >
                            {point.symbol}
                          </button>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p aria-live="polite" className="lab-point">
              {selected?.key === currentKey ? (
                <>
                  {pointLabel(selected.point)}. Warm-up ×
                  {selected.point.warmup_multiplier}. One-stop{" "}
                  {seconds(selected.point.one_stop_s)} s; two-stop{" "}
                  {seconds(selected.point.two_stop_s)} s.
                </>
              ) : (
                "Select a sampled cell to inspect its Python-computed result."
              )}
            </p>
            <p className="lab-note">
              A change between neighbouring cells is a sampled transition, not
              an exact crossover. No boundary interpolation is performed. This
              map is not a probability or confidence estimate.
            </p>
          </section>
          <section className="lab-export">
            <h2>Keep this experiment</h2>
            <p>
              Export the resolved loader-compatible scenario and the versioned
              result, including every sampled comparison. These are synthetic
              assumptions, not fitted historical parameters.
            </p>
            <div>
              <button
                className="lab-button"
                onClick={() => download("lab-scenario.json", result.scenario)}
              >
                Export scenario
              </button>
              <button
                className="lab-button"
                onClick={() => download("lab-result.json", result)}
              >
                Export result record
              </button>
            </div>
            <p>From the repository root, recompute the exported scenario:</p>
            <code>
              .venv-api/bin/python -m pitwall.sensitivity --scenario
              lab-scenario.json --output traces/lab-comparison.json
            </code>
            <p>
              Or verify the complete result:{" "}
              <code>
                .venv-api/bin/python -m pitwall.sensitivity --record
                lab-result.json --output traces/lab-verified.json
              </code>
            </p>
          </section>
        </>
      )}
    </>
  );
}
export default function SensitivityLab() {
  const heading = useRef<HTMLHeadingElement>(null);
  const [metadata, setMetadata] = useState<LabMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const c = new AbortController();
    let active = true;
    request<LabMetadata>("/api/v1/lab", c.signal)
      .then((v) => {
        if (active) setMetadata(v);
      })
      .catch((e) => {
        if (active && !c.signal.aborted) setError(e.message);
      });
    return () => {
      active = false;
      c.abort();
    };
  }, [retry]);
  return (
    <main className="lab-page">
      <header className="lab-header">
        <Link href="/">← PitWall Arena challenges</Link>
        <span>Synthetic lab · S1</span>
      </header>
      <div className="lab-intro">
        <h1 ref={heading} tabIndex={-1}>
          What changes the call?
        </h1>
        <p>
          Compare the fixed one-stop and two-stop schedules across illustrative
          pit-loss, tire degradation and warm-up assumptions.
        </p>
        <strong>12 laps. Two fixed schedules. One deterministic engine.</strong>
      </div>
      {metadata ? (
        <Lab metadata={metadata} />
      ) : error ? (
        <div role="alert">
          <p>{error}</p>
          <button
            className="lab-button"
            onClick={() => {
              heading.current?.focus();
              setError(null);
              setRetry((n) => n + 1);
            }}
          >
            Retry lab setup
          </button>
        </div>
      ) : (
        <p role="status">Loading lab assumptions…</p>
      )}
      <footer className="lab-footer">
        Synthetic product extension, not historical calibration or completion of
        F2. No traffic, fuel, weather, uncertainty model or adaptive planner.
        The historical quality gate remains blocked.
      </footer>
    </main>
  );
}
