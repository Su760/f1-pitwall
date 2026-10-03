"""HTTP validation, bounded work, and pre-submit information boundaries."""

import json

import pytest
from fastapi.testclient import TestClient

from apps.api.app import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def payload(**changes):
    return {"challenge_id": "closing-laps", "challenge_version": 1, "action": "stay_out", **changes}


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    assert set(response.json()) == {"detail"}
    assert set(response.json()["detail"]) == {"code", "message"}
    assert response.json()["detail"]["code"] == code
    assert response.headers["cache-control"] == "no-store"


def test_health_list_detail_and_evaluation(client):
    assert client.get("/health").json() == {"status": "ready", "api_version": 1}
    listing = client.get("/api/v1/challenges")
    assert listing.status_code == 200
    assert listing.headers["cache-control"] == "no-store"
    assert len(listing.json()["challenges"]) == 3
    detail = client.get("/api/v1/challenges/closing-laps?version=1")
    assert detail.status_code == 200
    assert "best_action" not in detail.json()
    response = client.post("/api/v1/evaluate", json=payload())
    assert response.status_code == 200
    assert response.json()["score_s"] > 0
    assert response.json()["selected_action"] == "stay_out"
    assert response.json() == client.post("/api/v1/evaluate", json=payload()).json()
    compared = client.post(
        "/api/v1/evaluate", json=payload(action="pit_hard", compare_action="stay_out")
    )
    assert compared.json()["comparison"]["original_action"] == "stay_out"
    assert compared.json()["comparison"]["delta_remaining_s"] < 0
    assert detail.json() == client.get("/api/v1/challenges/closing-laps?version=1").json()


@pytest.mark.parametrize(
    "patch",
    [
        {"snapshot": {}},
        {"configuration": {}},
        {"score_s": 0},
        {"challenge_version": True},
        {"challenge_version": "1"},
        {"challenge_version": 1.0},
        {"challenge_version": None},
        {"challenge_id": 1},
        {"action": "pit_wet"},
        {"action": 0},
        {"action": None},
        {"compare_action": None},
        {"compare_action": 1},
        {"compare_action": "pit_wet"},
    ],
)
def test_strict_request_types_and_extra_fields(client, patch):
    assert_error(client.post("/api/v1/evaluate", json=payload(**patch)), 422, "invalid_request")


@pytest.mark.parametrize(
    "body",
    [
        '{"challenge_id":"closing-laps","challenge_version":1,"action":"stay_out","action":"pit_soft"}',
        '{"challenge_id":"closing-laps","challenge_version":NaN,"action":"stay_out"}',
        '{"challenge_id":"closing-laps","challenge_version":Infinity,"action":"stay_out"}',
        '{"challenge_id":"closing-laps","challenge_version":1e999,"action":"stay_out"}',
        "{}",
        "null",
        "[]",
        "{",
        '["' + "x" * 100 + '"',
    ],
)
def test_invalid_json_and_nonfinite_numbers(client, body):
    assert_error(
        client.post("/api/v1/evaluate", content=body, headers={"content-type": "application/json"}),
        422,
        "invalid_request",
    )


def test_body_size_bound_with_and_without_content_length(client):
    assert_error(
        client.post(
            "/api/v1/evaluate", content=" " * 1025, headers={"content-type": "application/json"}
        ),
        413,
        "body_too_large",
    )

    def chunks():
        yield b" " * 600
        yield b" " * 600

    assert_error(
        client.post(
            "/api/v1/evaluate", content=chunks(), headers={"content-type": "application/json"}
        ),
        413,
        "body_too_large",
    )
    exact = json.dumps(payload()).ljust(1024)
    assert (
        client.post(
            "/api/v1/evaluate", content=exact, headers={"content-type": "application/json"}
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "path",
    [
        "/health?x=1",
        "/api/v1/challenges?version=1",
        "/api/v1/challenges/closing-laps",
        "/api/v1/challenges/closing-laps?version=1&x=1",
        "/api/v1/challenges/closing-laps?version=1&version=1",
        "/api/v1/challenges/closing-laps?version=true",
        "/api/v1/challenges/closing-laps?version=1.0",
    ],
)
def test_missing_duplicate_and_unknown_queries(client, path):
    assert_error(client.get(path), 422, "invalid_request")


def test_post_unknown_query_and_content_type(client):
    assert_error(client.post("/api/v1/evaluate?version=1", json=payload()), 422, "invalid_request")
    assert_error(
        client.post("/api/v1/evaluate", content=json.dumps(payload())), 422, "invalid_request"
    )


def test_id_version_legality_and_route_boundaries(client):
    assert_error(
        client.post("/api/v1/evaluate", json=payload(challenge_id="unknown")),
        404,
        "unknown_challenge",
    )
    assert_error(
        client.post("/api/v1/evaluate", json=payload(challenge_version=2)),
        409,
        "unsupported_version",
    )
    assert_error(
        client.get("/api/v1/challenges/closing-laps?version=2"), 409, "unsupported_version"
    )
    for action in ("stay_out", "pit_soft"):
        assert_error(
            client.post(
                "/api/v1/evaluate", json=payload(challenge_id="final-stint", action=action)
            ),
            422,
            "illegal_action",
        )
    assert_error(
        client.post(
            "/api/v1/evaluate",
            json=payload(
                challenge_id="final-stint", action="pit_medium", compare_action="stay_out"
            ),
        ),
        422,
        "illegal_action",
    )
    for path in ("/api/v1/optimize", "/api/v1/snapshots", "/docs", "/openapi.json"):
        assert_error(client.get(path), 404, "not_found")


def test_only_four_rollouts_even_when_comparing(client, monkeypatch):
    from apps.api import challenges

    original = challenges._rollout
    actions = []

    def counted(parent, action):
        actions.append(action)
        return original(parent, action)

    monkeypatch.setattr(challenges, "_rollout", counted)
    assert (
        client.post("/api/v1/evaluate", json=payload(compare_action="pit_hard")).status_code == 200
    )
    assert len(actions) == len(set(actions)) == 4
