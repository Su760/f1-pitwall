"""Strict explicit-only S2 API and failure semantics."""

import importlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.api.app import app
from pitwall.optimizer import SearchTooLarge

MODULE = importlib.import_module("apps.api.app")
URL = "/api/v1/lab/optimize"
CONTROLS = dict(pit_loss_s=18, degradation_multiplier=1, warmup_multiplier=1)


def test_explicit_only_success_and_unchanged_challenges():
    with TestClient(app) as client:
        challenges = client.get("/api/v1/challenges").json()
        with patch.object(MODULE, "optimize_lab") as search:
            assert client.get("/api/v1/lab").json()["optimization"]["top_k"] == 3
            assert client.post("/api/v1/lab", json={**CONTROLS, "grid_size": 2}).status_code == 200
            search.assert_not_called()
        response = client.post(URL, json=CONTROLS)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["best"]["total_elapsed_s"] == pytest.approx(1113.55)
        ranked = response.json()["search"]["ranked"]
        assert [entry["rank"] for entry in ranked] == [1, 2, 3]
        assert ranked[0]["stints"] == response.json()["best"]["stints"]
        assert ranked[1]["stints"] == [
            {"compound": "soft", "first_lap": 1, "last_lap": 6},
            {"compound": "medium", "first_lap": 7, "last_lap": 12},
        ]
        assert all(entry["exact_tie_ranks"] == [] for entry in ranked)
        assert ranked[0]["trace"] == response.json()["trace"]
        for entry in ranked:
            assert entry["trace"]["trace_version"] == 1
            assert entry["trace"]["strategy"] == entry["schedule"]
            assert entry["trace"]["result"]["stints"] == entry["stints"]
            assert entry["trace"]["result"]["total_elapsed_s"] == entry["total_elapsed_s"]
        assert client.get("/api/v1/challenges").json() == challenges


@pytest.mark.parametrize(
    "extra",
    [
        {"pit_loss_s": True},
        {"pit_loss_s": "18"},
        {"pit_loss_s": None},
        {"pit_loss_s": 40.1},
        {"pit_loss_s": -0.1},
        {"degradation_multiplier": 3.1},
        {"warmup_multiplier": -0.1},
        {"top_k": 100},
        {"max_candidates": 999999},
        {"grid_size": 21},
        {"scenario": {}},
        {"schedule": []},
    ],
)
def test_invalid_controls_and_client_budget_overrides(extra):
    with TestClient(app) as client:
        response = client.post(URL, json={**CONTROLS, **extra})
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "invalid_request"


@pytest.mark.parametrize(
    "body",
    [
        "null",
        "{}",
        "[]",
        "{",
        '{"pit_loss_s":NaN}',
        '{"pit_loss_s":1e999}',
        '{"pit_loss_s":18,"pit_loss_s":0}',
    ],
)
def test_invalid_json(body):
    with TestClient(app) as client:
        assert (
            client.post(URL, content=body, headers={"content-type": "application/json"}).status_code
            == 422
        )


def test_body_query_and_content_type():
    with TestClient(app) as client:
        assert (
            client.post(
                URL, content=" " * 1025, headers={"content-type": "application/json"}
            ).status_code
            == 413
        )
        assert client.post(URL, content="{}").status_code == 422
        assert client.post(URL + "?top_k=100", json=CONTROLS).status_code == 422


@pytest.mark.parametrize(
    "failure,status,code",
    [
        (SearchTooLarge("private config"), 422, "search_too_large"),
        (RuntimeError("private state"), 503, "search_unavailable"),
    ],
)
def test_no_success_or_internal_details_on_failed_search(failure, status, code):
    with patch.object(MODULE, "optimize_lab", side_effect=failure), TestClient(app) as client:
        response = client.post(URL, json=CONTROLS)
        assert response.status_code == status
        assert response.json()["detail"]["code"] == code
        assert "private" not in response.text
        assert "best" not in response.json()
