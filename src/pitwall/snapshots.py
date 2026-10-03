"""Versioned decision-boundary snapshots restored by verified action-prefix replay."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pitwall.actions import Compound
from pitwall.config import RaceConfig, fields
from pitwall.engine import Race
from pitwall.replay import read_configuration, replay_prefix, result_summary
from pitwall.serialization import (
    MODEL_VERSION,
    json_value,
    load_document,
    validate_json,
    verify_equal,
    write_document,
)


def configuration_id(config: RaceConfig) -> str:
    """Fingerprint the model plus canonical, lossless JSON configuration."""
    encoded = json.dumps(
        {"model_version": MODEL_VERSION, "configuration": config.to_dict()},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def state_document(race: Race) -> dict[str, Any]:
    state = asdict(race.state)
    state["used_compounds"] = [c.value for c in Compound if c in race.state.used_compounds]
    return json_value(state)


def snapshot_document(race: Race) -> dict[str, Any]:
    """Capture complete history without serializing arbitrary Python objects or policies."""
    result = race.result()
    return {
        "snapshot_version": 1,
        "model_version": MODEL_VERSION,
        "configuration_id": configuration_id(race.configuration),
        "configuration": race.configuration.to_dict(),
        "state": state_document(race),
        "actions": json_value([asdict(action) for action in result.actions]),
        "laps": json_value([asdict(lap) for lap in result.laps]),
        "result": result_summary(race),
    }


def restore_snapshot(data: Any, *, expected_config: RaceConfig | None = None) -> Race:
    validate_json(data)
    fields(
        data,
        {
            "snapshot_version",
            "model_version",
            "configuration_id",
            "configuration",
            "state",
            "actions",
            "laps",
            "result",
        },
        "snapshot",
    )
    verify_equal(data["snapshot_version"], 1, "snapshot_version")
    verify_equal(data["model_version"], MODEL_VERSION, "model_version")
    config = read_configuration(data["configuration"], expected_config)
    verify_equal(data["configuration_id"], configuration_id(config), "configuration_id")
    race = replay_prefix(config, data["actions"], data["laps"])
    verify_equal(data["state"], state_document(race), "state")
    verify_equal(data["result"], result_summary(race), "result")
    return race


def save_snapshot(path: Path, race: Race) -> None:
    write_document(path, snapshot_document(race))


def load_snapshot(path: Path, *, expected_config: RaceConfig | None = None) -> Race:
    return restore_snapshot(load_document(path), expected_config=expected_config)


def fork(race: Race) -> Race:
    """Validate a boundary and replay into new state/history owned only by the child."""
    return restore_snapshot(snapshot_document(race), expected_config=race.configuration)
