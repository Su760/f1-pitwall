"""Strict JSON and exact, path-aware comparisons shared by saved race artifacts."""

import json
import math
from enum import Enum
from pathlib import Path
from typing import Any

MODEL_VERSION = "f0a-linear-capped-v1"


def json_value(value: Any) -> Any:
    """Normalize dataclass output to ordinary JSON arrays, objects, and scalars."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def validate_json(value: Any, path: str = "document") -> None:
    """Also validate in-memory documents, which need not originate in json.loads."""
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{path}: JSON object keys must be strings")
            validate_json(item, f"{path}.{key}")
    elif type(value) is list:
        for index, item in enumerate(value):
            validate_json(item, f"{path}[{index}]")
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path}: nonfinite JSON number")
    elif value is not None and type(value) not in (str, int, bool):
        raise ValueError(f"{path}: unsupported JSON value type {type(value).__name__}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Nonfinite JSON number: {value}")


def load_document(path: Path) -> Any:
    data = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )
    validate_json(data)
    return data


def write_document(path: Path, data: dict[str, Any]) -> None:
    text = json.dumps(data, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def verify_equal(saved: Any, expected: Any, path: str) -> None:
    """Compare a strict schema inferred from engine output, without display rounding.

    Seconds may be JSON integers or floats; counters must remain integers. Equality
    is exact because verification repeats the same model and addition order.
    """
    if type(expected) is dict:
        if type(saved) is not dict or set(saved) != set(expected):
            raise ValueError(f"{path}: expected exactly these fields: {sorted(expected)}")
        for key, item in expected.items():
            verify_equal(saved[key], item, f"{path}.{key}")
        return
    if type(expected) is list:
        if type(saved) is not list or len(saved) != len(expected):
            raise ValueError(f"{path}: expected an array of {len(expected)} items")
        for index, item in enumerate(expected):
            verify_equal(saved[index], item, f"{path}[{index}]")
        return
    seconds = path.endswith("_s") or ".warmup_s[" in path
    if type(expected) is float or (type(expected) is int and seconds):
        if type(saved) not in (int, float):
            raise ValueError(f"{path}: expected finite numeric seconds")
        try:
            finite = math.isfinite(saved)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError(f"{path}: expected finite numeric seconds")
    elif type(saved) is not type(expected):
        raise ValueError(f"{path}: expected {type(expected).__name__}")
    if saved != expected:
        raise ValueError(f"{path}: expected {expected!r}, found {saved!r}")
