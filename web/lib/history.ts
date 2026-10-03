import { actionLabels, type Action, type ChallengeSummary } from "./api";

export type Practice = {
  action: Action;
  score_s: number;
  remaining_s: number;
  recorded_at: string;
  fork: boolean;
};
const LIMIT = 20;
const key = (challenge: ChallengeSummary) =>
  `pitwall.practice.v1:${challenge.id}:${challenge.version}`;

export function readHistory(challenge: ChallengeSummary): Practice[] {
  try {
    const saved: unknown = JSON.parse(
      localStorage.getItem(key(challenge)) ?? "[]",
    );
    if (!Array.isArray(saved)) return [];
    return saved
      .filter(
        (item): item is Practice =>
          item !== null &&
          typeof item === "object" &&
          typeof item.action === "string" &&
          Object.hasOwn(actionLabels, item.action) &&
          typeof item.score_s === "number" &&
          Number.isFinite(item.score_s) &&
          item.score_s >= 0 &&
          typeof item.remaining_s === "number" &&
          Number.isFinite(item.remaining_s) &&
          item.remaining_s > 0 &&
          typeof item.recorded_at === "string" &&
          Number.isFinite(Date.parse(item.recorded_at)) &&
          typeof item.fork === "boolean",
      )
      .slice(0, LIMIT);
  } catch {
    return [];
  }
}

export function savePractice(
  challenge: ChallengeSummary,
  practice: Practice,
): Practice[] {
  const items = [practice, ...readHistory(challenge)].slice(0, LIMIT);
  try {
    localStorage.setItem(key(challenge), JSON.stringify(items));
  } catch {
    /* Play remains available when storage is blocked. */
  }
  return items;
}
