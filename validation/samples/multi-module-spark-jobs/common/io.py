from __future__ import annotations

from typing import Any


def format_result(job_name: str, payload: dict[str, Any]) -> str:
    parts = [f"job={job_name}"]
    for key in sorted(payload):
        parts.append(f"{key}={payload[key]}")
    return " ".join(parts)
