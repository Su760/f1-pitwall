"""Server-owned synthetic challenges, evaluated by independent authoritative forks."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pitwall.actions import Action, Compound
from pitwall.engine import Race
from pitwall.results import LapResult
from pitwall.serialization import MODEL_VERSION, json_value, load_document
from pitwall.snapshots import fork, restore_snapshot

_DIRECTORY = Path(__file__).parent
SETTINGS = load_document(_DIRECTORY / "settings.json")
CONTINUATION = {
    "id": "stay-out-v1",
    "description": "Make this call for the next lap, then stay out until the finish.",
}
SCORE_LABEL = "Excess time within this synthetic model and stay-out continuation"


class ChallengeError(ValueError):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass(frozen=True)
class Challenge:
    metadata: dict[str, Any]
    race: Race


def load_challenge(challenge_id: str, version: int) -> Challenge:
    # Identity is selected from a server-owned allowlist, never interpolated unchecked.
    if challenge_id not in SETTINGS["fixtures"]:
        raise ChallengeError(404, "unknown_challenge", "Unknown challenge identity.")
    data = load_document(_DIRECTORY / "fixtures" / f"{challenge_id}.json")
    if type(version) is not int or version != data["version"]:
        raise ChallengeError(409, "unsupported_version", "Challenge version is not supported.")
    if (
        data["id"] != challenge_id
        or data["snapshot"]["configuration"]["laps"] > SETTINGS["max_race_laps"]
    ):
        raise ValueError("Server fixture identity or lap bound is inconsistent")
    race = restore_snapshot(data["snapshot"])
    if not 1 <= race.state.completed_laps < race.configuration.laps:
        raise ValueError("Server fixture must be at an unfinished decision boundary")
    return Challenge({key: value for key, value in data.items() if key != "snapshot"}, race)


def _summary(challenge: Challenge) -> dict[str, Any]:
    return {
        **{key: challenge.metadata[key] for key in ("id", "version", "title", "summary")},
        "remaining_laps": challenge.race.configuration.laps - challenge.race.state.completed_laps,
    }


def challenge_summaries() -> list[dict[str, Any]]:
    return [_summary(load_challenge(identity, 1)) for identity in SETTINGS["fixtures"]]


def unavailable_reason(race: Race, action: Action) -> str | None:
    """Explain the engine's mask; never replace it with a separately computed mask."""
    if race.observe().allows(action):
        return None
    state, config = race.state, race.configuration
    if race.finished:
        return "The race has finished."
    if action is not Action.STAY_OUT:
        if state.completed_laps == 0:
            return "A pit call is available only after lap one."
        if len(state.pit_boundaries) >= config.rules.max_pit_stops:
            return "No pit stops remain."
        if state.remaining_sets[tuple(Compound).index(action.compound)] == 0:
            return f"No fresh {action.compound.value} sets remain."
    return "This call leaves no legal finish meeting the distinct-compound requirement."


def challenge_detail(challenge_id: str, version: int) -> dict[str, Any]:
    challenge = load_challenge(challenge_id, version)
    race = challenge.race
    state, config, observation = race.state, race.configuration, race.observe()
    return {
        "api_version": 1,
        **_summary(challenge),
        "briefing": challenge.metadata["briefing"],
        "objective": challenge.metadata["objective"],
        "continuation": dict(CONTINUATION),
        "situation": {
            "completed_laps": state.completed_laps,
            "total_laps": config.laps,
            "remaining_laps": config.laps - state.completed_laps,
            "current_compound": state.current_compound.value,
            "tire_age_laps": state.tire_age_laps,
            "remaining_sets": dict(
                zip((c.value for c in Compound), state.remaining_sets, strict=True)
            ),
            "used_compounds": [c.value for c in Compound if c in state.used_compounds],
            "stops_remaining": observation.stops_remaining,
            "elapsed_s": state.elapsed_s,
            "stints": json_value([asdict(stint) for stint in race.result().stints]),
        },
        "actions": [
            {
                "action": a.value,
                "available": observation.allows(a),
                "reason": unavailable_reason(race, a),
            }
            for a in Action
        ],
        "assumptions": {
            "label": "Synthetic teaching parameters; no real-world F1 calibration.",
            "base_lap_time_s": config.base_lap_time_s,
            "pit_loss_s": config.pit_loss_s,
            "max_pit_stops": config.rules.max_pit_stops,
            "min_distinct_compounds": config.rules.min_distinct_compounds,
            "noise": "disabled",
            "tires": [
                {
                    "compound": tire.compound.value,
                    "pace_offset_s": tire.pace_offset_s,
                    "degradation_s_per_lap": tire.degradation_s_per_lap,
                    "degradation_cap_s": tire.degradation_cap_s,
                    "warmup_s": list(tire.warmup_s),
                }
                for tire in config.tires
            ],
        },
    }


def _costs(laps: tuple[LapResult, ...]) -> dict[str, float]:
    return {
        "base_s": sum(lap.base_lap_time_s for lap in laps),
        "pace_s": sum(lap.pace_offset_s for lap in laps),
        "degradation_s": sum(lap.degradation_s for lap in laps),
        "warmup_s": sum(lap.warmup_s for lap in laps),
        "pit_s": sum(lap.pit_loss_s for lap in laps),
    }


def _difference(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    return {key: value - right[key] for key, value in left.items()}


def _rollout(parent: Race, action: Action) -> dict[str, Any]:
    child = fork(parent)
    child.step(action)
    while not child.finished:
        child.step(Action.STAY_OUT)
    result = child.result()
    if not result.legal:
        raise ValueError("Server fixture does not permit the documented continuation")
    laps = result.laps[parent.state.completed_laps :]
    return {
        "action": action.value,
        "remaining_elapsed_s": result.total_elapsed_s - parent.state.elapsed_s,
        "total_elapsed_s": result.total_elapsed_s,
        "legal": result.legal,
        "components": _costs(laps),
        "laps": json_value([asdict(lap) for lap in laps]),
        "stints": json_value([asdict(stint) for stint in result.stints]),
    }


def evaluate_boundary(
    parent: Race, action: Action, compare_action: Action | None = None
) -> dict[str, Any]:
    """Bounded internal evaluator. No arbitrary boundary is accepted over HTTP."""
    if parent.configuration.laps > SETTINGS["max_race_laps"] or parent.finished:
        raise ValueError("Unsupported challenge boundary")
    for call in (action, compare_action):
        if call is None:
            continue
        if not isinstance(call, Action):
            raise ChallengeError(422, "invalid_action", "Action must be a typed pit call.")
        reason = unavailable_reason(parent, call)
        if reason is not None:
            raise ChallengeError(422, "illegal_action", reason)
    if action is None:
        raise ChallengeError(422, "invalid_action", "An action is required.")
    outcomes = [_rollout(parent, call) for call in Action if parent.observe().allows(call)]
    # Stable sort retains declared Action order for exact full-precision ties.
    outcomes.sort(key=lambda result: result["remaining_elapsed_s"])
    best = outcomes[0]
    boundary = parent.state.completed_laps
    for outcome in outcomes:
        outcome["excess_s"] = outcome["remaining_elapsed_s"] - best["remaining_elapsed_s"]
        outcome["cumulative"] = [
            {"lap": boundary, "remaining_elapsed_s": 0.0, "gap_to_best_s": 0.0}
        ]
        for lap, reference in zip(outcome["laps"], best["laps"], strict=True):
            outcome["cumulative"].append(
                {
                    "lap": lap["lap"],
                    "remaining_elapsed_s": lap["elapsed_s"] - parent.state.elapsed_s,
                    "gap_to_best_s": lap["elapsed_s"] - reference["elapsed_s"],
                }
            )
    selected = next(outcome for outcome in outcomes if outcome["action"] == action.value)
    comparison = None
    if compare_action is not None:
        original = next(
            outcome for outcome in outcomes if outcome["action"] == compare_action.value
        )
        comparison = {
            "original_action": compare_action.value,
            "alternative_action": action.value,
            "delta_remaining_s": selected["remaining_elapsed_s"] - original["remaining_elapsed_s"],
            "components_delta": _difference(selected["components"], original["components"]),
            "gap_series": [{"lap": boundary, "gap_s": 0.0}]
            + [
                {"lap": lap["lap"], "gap_s": lap["elapsed_s"] - reference["elapsed_s"]}
                for lap, reference in zip(selected["laps"], original["laps"], strict=True)
            ],
        }
    return {
        "model_version": MODEL_VERSION,
        "continuation": dict(CONTINUATION),
        "decision_after_lap": boundary,
        "selected_action": action.value,
        "score_s": selected["excess_s"],
        "score_label": SCORE_LABEL,
        "best_action": best["action"],
        "best_remaining_elapsed_s": best["remaining_elapsed_s"],
        "selected": selected,
        "alternatives": outcomes,
        "debrief": {
            "summary": (
                f"Your call used {selected['remaining_elapsed_s']:.3f} s for the remaining laps: "
                f"{selected['excess_s']:.3f} s above the fastest legal call evaluated here. "
                "The component differences below compare your call with that reference under "
                "the same stay-out continuation. This is not a global strategy optimum."
            ),
            "reference_action": best["action"],
            "delta_components": _difference(selected["components"], best["components"]),
        },
        "comparison": comparison,
    }


def evaluate(
    challenge_id: str, version: int, action: Action, compare_action: Action | None = None
) -> dict[str, Any]:
    challenge = load_challenge(challenge_id, version)
    return {
        "api_version": 1,
        "challenge_id": challenge_id,
        "challenge_version": version,
        **evaluate_boundary(challenge.race, action, compare_action),
    }
