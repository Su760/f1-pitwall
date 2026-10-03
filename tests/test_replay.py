import json
from copy import deepcopy
from dataclasses import asdict, replace

import pytest
from conftest import make_config

from pitwall.actions import Compound
from pitwall.engine import simulate
from pitwall.policies import FixedSchedule, PitStop
from pitwall.replay import load_trace, policy_from_actions, replay_document, trace_policy
from pitwall.trace import save_trace, trace_document


@pytest.fixture
def recorded():
    config = make_config(laps=6, degradation=0.37, warmup=(0.7, 0.2))
    policy = FixedSchedule(
        "fresh same compound then mandatory medium",
        (PitStop(2, Compound.SOFT), PitStop(4, Compound.MEDIUM)),
    )
    result = simulate(config, policy)
    return config, policy, result, trace_document(config, policy, result)


def test_replay_executes_saved_actions_without_asking_policy(recorded, monkeypatch, tmp_path):
    config, policy, result, document = recorded

    def policy_must_not_execute(*args):
        pytest.fail("Replay must execute the recorded actions, not rerun a named policy")

    monkeypatch.setattr(FixedSchedule, "choose_action", policy_must_not_execute)
    replayed = replay_document(document, expected_config=config)
    assert replayed.finished
    assert replayed.configuration == config
    assert replayed.result() == result
    assert trace_policy(document) == policy
    assert policy_from_actions(policy.name, result.actions) == policy
    path = tmp_path / "trace.json"
    save_trace(path, config, policy, result)
    assert load_trace(path).result() == result
    assert json.loads(path.read_text()) == document


def test_original_f0a_version_1_json_is_supported(recorded, tmp_path):
    config, policy, result, document = recorded
    # F0a used json.dumps on asdict tuples; this independent old writer retains its schema.
    summary = asdict(result)
    legacy = {
        "trace_version": 1,
        "model_version": "f0a-linear-capped-v1",
        "configuration": config.to_dict(),
        "strategy": asdict(policy),
        "actions": summary.pop("actions"),
        "laps": summary.pop("laps"),
        "result": summary,
    }
    path = tmp_path / "f0a.json"
    path.write_text(json.dumps(legacy))
    assert json.loads(path.read_text()) == document
    assert load_trace(path).result() == result


@pytest.mark.parametrize(
    "field,value",
    [
        ("lap", 2),
        ("compound", "hard"),
        ("tire_age_laps", 1),
        ("base_lap_time_s", 100.001),
        ("pace_offset_s", 0.001),
        ("degradation_s", 0.001),
        ("warmup_s", 0.701),
        ("pit_loss_s", 0.001),
        ("lap_time_s", 100.701),
        ("elapsed_s", 100.701),
    ],
)
def test_replay_checks_every_lap_component(recorded, field, value):
    document = recorded[3]
    document["laps"][0][field] = value
    with pytest.raises(ValueError, match=rf"laps\[0\].{field}"):
        replay_document(document)


@pytest.mark.parametrize(
    "field,value",
    [
        ("total_elapsed_s", 1.0),
        ("completed_laps", 5),
        ("pit_boundaries", [2, 3]),
        ("stints", [{"compound": "soft", "first_lap": 1, "last_lap": 6}]),
        ("legal", False),
        ("legality_errors", ["invented error"]),
    ],
)
def test_replay_checks_complete_result(recorded, field, value):
    document = recorded[3]
    document["result"][field] = value
    with pytest.raises(ValueError, match=f"result.{field}"):
        replay_document(document)


@pytest.mark.parametrize(
    "location,value,error",
    [
        (("trace_version",), True, "trace_version"),
        (("trace_version",), 2, "trace_version"),
        (("model_version",), "future-model", "model_version"),
        (("actions", 0, "after_lap"), False, r"actions\[0\].after_lap"),
        (("actions", 0, "after_lap"), 0.0, r"actions\[0\].after_lap"),
        (("actions", 1, "after_lap"), 3, r"actions\[1\].after_lap"),
        (("actions", 0, "action"), "unknown", r"actions\[0\].action"),
        (("actions", 0, "action"), "pit_medium", r"actions\[0\]"),
        (("actions", 5, "action"), "pit_hard", r"actions\[5\]"),
        (("actions", 2, "action"), "stay_out", r"laps\[2\]"),
        (("laps", 0, "lap"), 1.0, r"laps\[0\].lap"),
        (("laps", 0, "tire_age_laps"), False, r"laps\[0\].tire_age_laps"),
        (("laps", 0, "pit_loss_s"), False, r"laps\[0\].pit_loss_s"),
        (("laps", 0, "elapsed_s"), "100.7", r"laps\[0\].elapsed_s"),
        (("result", "legal"), 1, "result.legal"),
        (("strategy", "stops", 0, "after_lap"), 2.0, "after_lap"),
        (("strategy", "stops", 0, "compound"), "hard", "strategy.stops"),
        (("strategy", "stops", 1, "after_lap"), 5, "strategy.stops"),
        (("configuration", "laps"), True, "configuration"),
        (("configuration", "pit_loss_s"), float("inf"), "configuration.pit_loss_s"),
        (("laps", 0, "elapsed_s"), float("nan"), "elapsed_s"),
    ],
)
def test_replay_rejects_invalid_types_versions_boundaries_and_actions(
    recorded, location, value, error
):
    document = recorded[3]
    target = document
    for key in location[:-1]:
        target = target[key]
    target[location[-1]] = value
    with pytest.raises(ValueError, match=error):
        replay_document(document)


@pytest.mark.parametrize("section", [None, "result", "configuration"])
def test_unknown_fields_are_rejected(recorded, section):
    document = recorded[3]
    target = document if section is None else document[section]
    target["future_feature"] = None
    with pytest.raises(ValueError, match="fields"):
        replay_document(document)


def test_replay_requires_all_laps_and_no_post_finish_action(recorded):
    document = recorded[3]
    short = deepcopy(document)
    short["actions"].pop()
    short["laps"].pop()
    with pytest.raises(ValueError, match="complete trace requires"):
        replay_document(short)
    document["actions"].append({"after_lap": 6, "action": "stay_out"})
    document["laps"].append(document["laps"][-1])
    with pytest.raises(ValueError, match="at most 6"):
        replay_document(document)


def test_precision_and_config_compatibility_are_not_display_based(recorded):
    config, _, _, document = recorded
    with pytest.raises(ValueError, match="configuration.pit_loss_s"):
        replay_document(document, expected_config=replace(config, pit_loss_s=10.001))
    document["laps"][0]["lap_time_s"] += 1e-12
    with pytest.raises(ValueError, match=r"laps\[0\].lap_time_s"):
        replay_document(document)


@pytest.mark.parametrize(
    "content,error",
    [
        ('{"trace_version": 1, "trace_version": 1}', "Duplicate JSON field: trace_version"),
        ('{"nested": {"action": "stay_out", "action": "stay_out"}}', "Duplicate JSON field"),
        ('{"value": NaN}', "Nonfinite"),
        ('{"value": Infinity}', "Nonfinite"),
        ('{"value": -Infinity}', "Nonfinite"),
        ('{"value": 1e999}', "nonfinite"),
    ],
)
def test_trace_json_loader_rejects_duplicates_and_all_nonfinite_forms(tmp_path, content, error):
    path = tmp_path / "bad.json"
    path.write_text(content)
    with pytest.raises(ValueError, match=error):
        load_trace(path)


def test_in_memory_documents_require_json_arrays(recorded):
    document = recorded[3]
    document["actions"] = tuple(document["actions"])
    with pytest.raises(ValueError, match="actions.*unsupported JSON"):
        replay_document(document)
