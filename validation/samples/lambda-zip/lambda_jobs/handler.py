from __future__ import annotations

from typing import Any

import orjson

from lambda_jobs.utils import normalize_event


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler — set the function's handler to ``lambda_jobs.handler.handler``."""
    payload = normalize_event(event)
    return {"statusCode": 200, "body": orjson.dumps(payload).decode()}
