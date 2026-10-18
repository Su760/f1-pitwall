import type { Costs, Stint } from "./api";
export type Control =
  "pit_loss_s" | "degradation_multiplier" | "warmup_multiplier";
export type Controls = Record<Control, number>;
export type LabMetadata = {
  api_version: 1;
  lab_version: 1;
  controls: Record<
    Control,
    { label: string; min: number; max: number; default: number; step: number }
  >;
  optimization: SearchSettings;
  grid_default: number;
  grid_max: number;
};
export type Classification = {
  delta_s: number;
  winner: "one-stop" | "two-stop" | "tie";
  label: string;
  symbol: string;
  near_tie: boolean;
};
export type Point = Classification &
  Controls & { one_stop_s: number; two_stop_s: number };
export type LabResult = {
  api_version: 1;
  lab_version: 1;
  controls: Controls;
  scenario: { configuration: { laps: number }; [key: string]: unknown };
  comparison: Classification & {
    sign_convention: string;
    strategies: {
      name: string;
      total_elapsed_s: number;
      legal: boolean;
      pit_count: number;
      pit_boundaries: number[];
      stints: Stint[];
      components: Costs;
    }[];
  };
  tie_tolerance_s: number;
  near_tie_s: number;
  grid: {
    size: number;
    axes: { pit_loss_s: number[]; degradation_multiplier: number[] };
    rows: Point[][];
  };
};

export type SearchSettings = {
  optimization_version: 1;
  top_k: number;
  max_candidates: number;
  max_lap_evaluations: number;
};
export type RankedStrategy = {
  rank: number;
  schedule: { name: string; stops: { after_lap: number; compound: string }[] };
  total_elapsed_s: number;
  gap_s: number;
  stints: Stint[];
  exact_tie_ranks: number[];
  trace: unknown;
};
export type OptimizationResult = {
  api_version: 1;
  optimization_version: 1;
  controls: Controls;
  label: string;
  search: {
    search_complete: boolean;
    candidate_count: number;
    legal_count: number;
    limits: { max_candidates: number; max_lap_evaluations: number };
    top_k: number;
    tie_break: string;
    ranked: RankedStrategy[];
  };
  best: {
    schedule: { name: string; stops: { after_lap: number; compound: string }[] };
    total_elapsed_s: number;
    legal: boolean;
    stints: Stint[];
  };
  benchmarks: { name: string; total_elapsed_s: number; improvement_s: number }[];
  scenario: unknown;
  trace: unknown;
};
