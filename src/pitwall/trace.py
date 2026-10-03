"""Versioned audit traces. No timestamps, hidden state, or snapshot restoration."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pitwall.config import RaceConfig
from pitwall.policies import FixedSchedule
from pitwall.results import RaceResult


def trace_document(
    config: RaceConfig,
    strategy: FixedSchedule,
    result: RaceResult,
) -> dict[str, Any]:
    summary = asdict(result)
    actions = summary.pop("actions")
    laps = summary.pop("laps")
    return {
        "trace_version": 1,
        "model_version": "f0a-linear-capped-v1",
        "configuration": config.to_dict(),
        "strategy": asdict(strategy),
        "actions": actions,
        "laps": laps,
        "result": summary,
    }


def save_trace(path: Path, config: RaceConfig, strategy: FixedSchedule, result: RaceResult) -> None:
    text = json.dumps(trace_document(config, strategy, result), indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
