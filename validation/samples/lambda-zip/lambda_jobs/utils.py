from __future__ import annotations

from typing import Any


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    message = event.get("message") or "ok"
    request_id = event.get("request_id") or "unknown"
    return {"message": message, "request_id": request_id}
