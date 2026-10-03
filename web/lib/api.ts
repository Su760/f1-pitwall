export type Action = "stay_out" | "pit_soft" | "pit_medium" | "pit_hard";
export type Compound = "soft" | "medium" | "hard";
export type Stint = { compound: Compound; first_lap: number; last_lap: number };
export type Costs = {
  base_s: number;
  pace_s: number;
  degradation_s: number;
  warmup_s: number;
  pit_s: number;
};
export type Continuation = { id: "stay-out-v1"; description: string };
export type ChallengeSummary = {
  id: string;
  version: number;
  title: string;
  summary: string;
  remaining_laps: number;
};
export type ChallengeDetail = ChallengeSummary & {
  api_version: 1;
  briefing: string;
  objective: string;
  continuation: Continuation;
  situation: {
    completed_laps: number;
    total_laps: number;
    remaining_laps: number;
    current_compound: Compound;
    tire_age_laps: number;
    remaining_sets: Record<Compound, number>;
    used_compounds: Compound[];
    stops_remaining: number;
    elapsed_s: number;
    stints: Stint[];
  };
  actions: { action: Action; available: boolean; reason: string | null }[];
  assumptions: {
    label: string;
    base_lap_time_s: number;
    pit_loss_s: number;
    max_pit_stops: number;
    min_distinct_compounds: number;
    noise: "disabled";
    tires: {
      compound: Compound;
      pace_offset_s: number;
      degradation_s_per_lap: number;
      degradation_cap_s: number;
      warmup_s: number[];
    }[];
  };
};
export type Lap = {
  lap: number;
  compound: Compound;
  tire_age_laps: number;
  base_lap_time_s: number;
  pace_offset_s: number;
  degradation_s: number;
  warmup_s: number;
  pit_loss_s: number;
  lap_time_s: number;
  elapsed_s: number;
};
export type Outcome = {
  action: Action;
  remaining_elapsed_s: number;
  total_elapsed_s: number;
  excess_s: number;
  legal: boolean;
  components: Costs;
  laps: Lap[];
  stints: Stint[];
  cumulative: {
    lap: number;
    remaining_elapsed_s: number;
    gap_to_best_s: number;
  }[];
};
export type Evaluation = {
  api_version: 1;
  challenge_id: string;
  challenge_version: number;
  model_version: string;
  continuation: Continuation;
  decision_after_lap: number;
  selected_action: Action;
  score_s: number;
  score_label: string;
  best_action: Action;
  best_remaining_elapsed_s: number;
  selected: Outcome;
  alternatives: Outcome[];
  debrief: {
    summary: string;
    reference_action: Action;
    delta_components: Costs;
  };
  comparison: null | {
    original_action: Action;
    alternative_action: Action;
    delta_remaining_s: number;
    components_delta: Costs;
    gap_series: { lap: number; gap_s: number }[];
  };
};

export const actionLabels: Record<Action, string> = {
  stay_out: "Stay out",
  pit_soft: "Pit for soft",
  pit_medium: "Pit for medium",
  pit_hard: "Pit for hard",
};
export const compounds: Compound[] = ["soft", "medium", "hard"];

export async function request<T>(
  url: string,
  signal: AbortSignal,
  body?: unknown,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: body === undefined ? "GET" : "POST",
      headers:
        body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
      cache: "no-store",
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error(
      "The arena service could not be reached. Check that the API is running, then retry.",
    );
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(
      typeof data?.detail?.message === "string"
        ? data.detail.message
        : "The arena service could not complete this call. Retry when the API is available.",
    );
  }
  if (!data || data.api_version !== 1)
    throw new Error(
      "This arena response is not supported. Refresh and try again.",
    );
  return data as T;
}
