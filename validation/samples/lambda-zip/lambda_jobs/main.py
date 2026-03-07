from __future__ import annotations

from lambda_jobs.handler import handler


def run() -> int:
    """Smoke-test entry point — invokes the Lambda handler with a mock event."""
    mock_event = {"message": "hello", "request_id": "test-123"}
    result = handler(mock_event, None)
    print(f"lambda ok: status={result['statusCode']} body={result['body']}")
    return 0
