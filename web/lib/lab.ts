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
