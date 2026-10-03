"""Small stateless FastAPI boundary; clients choose a challenge and a typed action."""

import json
import re
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.exceptions import HTTPException
from starlette.requests import ClientDisconnect

from apps.api.challenges import (
    SETTINGS,
    ChallengeError,
    challenge_detail,
    challenge_summaries,
    evaluate,
)
from pitwall.actions import Action
from pitwall.serialization import validate_json

ActionName = Literal["stay_out", "pit_soft", "pit_medium", "pit_hard"]


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    challenge_id: str = Field(min_length=1, max_length=64)
    challenge_version: int
    action: ActionName
    compare_action: ActionName | None = None


app = FastAPI(title="PitWall Arena", docs_url=None, redoc_url=None, openapi_url=None)


def _invalid(message: str) -> ChallengeError:
    return ChallengeError(422, "invalid_request", message)


@app.middleware("http")
async def no_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ChallengeError)
async def challenge_error_handler(request: Request, exc: ChallengeError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status, content={"detail": {"code": exc.code, "message": str(exc)}}
    )


@app.exception_handler(HTTPException)
async def route_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": {
                "code": "not_found" if exc.status_code == 404 else "http_error",
                "message": "Unknown endpoint."
                if exc.status_code == 404
                else "Request is not supported.",
            }
        },
    )


def _query(request: Request, *, version: bool = False) -> int | None:
    pairs = list(request.query_params.multi_items())
    if not version:
        if pairs:
            raise _invalid("This endpoint does not accept query fields.")
        return None
    if len(pairs) != 1 or pairs[0][0] != "version":
        raise _invalid("Exactly one version query field is required.")
    value = pairs[0][1]
    if len(value) > 10 or re.fullmatch(r"[1-9][0-9]*", value) is None:
        raise _invalid("Version must be a positive integer.")
    return int(value)


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON fields are not accepted.")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError("Nonfinite JSON numbers are not accepted.")


async def _read_request(request: Request) -> EvaluationRequest:
    if (
        request.headers.get("content-type", "").split(";", 1)[0].lower().strip()
        != "application/json"
    ):
        raise _invalid("Content-Type must be application/json.")
    limit = SETTINGS["max_request_bytes"]
    body = bytearray()
    try:
        async for chunk in request.stream():
            if len(body) + len(chunk) > limit:
                raise ChallengeError(413, "body_too_large", f"Request body exceeds {limit} bytes.")
            body.extend(chunk)
        data = json.loads(body, object_pairs_hook=_unique_fields, parse_constant=_nonfinite)
        validate_json(data)
        if type(data) is dict and "compare_action" in data and data["compare_action"] is None:
            raise ValueError("Omit compare_action unless it names an action.")
        return EvaluationRequest.model_validate(data)
    except (ValueError, UnicodeError, RecursionError, ValidationError, ClientDisconnect) as exc:
        # Never echo an untrusted body, model inputs, or server snapshot in errors.
        if isinstance(exc, ChallengeError):
            raise
        raise _invalid(
            "Expected a valid challenge identity, integer version, and typed action."
        ) from exc


@app.get("/health")
def health(request: Request) -> dict[str, Any]:
    _query(request)
    challenge_summaries()  # Readiness includes validated server fixtures.
    return {"status": "ready", "api_version": 1}


@app.get("/api/v1/challenges")
def challenges(request: Request) -> dict[str, Any]:
    _query(request)
    return {"api_version": 1, "challenges": challenge_summaries()}


@app.get("/api/v1/challenges/{challenge_id}")
def detail(challenge_id: str, request: Request) -> dict[str, Any]:
    version = _query(request, version=True)
    assert version is not None
    return challenge_detail(challenge_id, version)


@app.post("/api/v1/evaluate")
async def evaluation(request: Request) -> dict[str, Any]:
    _query(request)
    body = await _read_request(request)
    return evaluate(
        body.challenge_id,
        body.challenge_version,
        Action(body.action),
        Action(body.compare_action) if body.compare_action is not None else None,
    )
