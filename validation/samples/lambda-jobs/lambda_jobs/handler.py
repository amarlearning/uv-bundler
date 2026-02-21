from __future__ import annotations

from typing import Any

from lambda_jobs.utils import normalize_event


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    payload = normalize_event(event)
    body = f"{payload['request_id']}:{payload['message']}"
    return {"statusCode": 200, "body": body}
