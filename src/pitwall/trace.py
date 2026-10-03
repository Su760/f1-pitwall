"""Version-1 audit traces, compatible with the original F0a JSON representation."""

from dataclasses import asdict
from pathlib import Path
from typing import Any

from pitwall.config import RaceConfig
from pitwall.policies import FixedSchedule
from pitwall.results import RaceResult
from pitwall.serialization import MODEL_VERSION, json_value, write_document


def trace_document(
    config: RaceConfig,
    strategy: FixedSchedule,
    result: RaceResult,
) -> dict[str, Any]:
    summary = asdict(result)
    actions = summary.pop("actions")
    laps = summary.pop("laps")
    return json_value(
        {
            "trace_version": 1,
            "model_version": MODEL_VERSION,
            "configuration": config.to_dict(),
            "strategy": asdict(strategy),
            "actions": actions,
            "laps": laps,
            "result": summary,
        }
    )


def save_trace(path: Path, config: RaceConfig, strategy: FixedSchedule, result: RaceResult) -> None:
    write_document(path, trace_document(config, strategy, result))
