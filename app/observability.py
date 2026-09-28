import json
import logging
from datetime import datetime, timezone
from typing import Any


LOGGER = logging.getLogger("ecommerce_agent.runs")

LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False

if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(message)s")
    )
    LOGGER.addHandler(handler)


def record_agent_run(
    *,
    request_id: str,
    thread_id: str,
    duration_ms: float,
    status: str,
    route: str | None = None,
    issue_type: str | None = None,
    tool_names: list[str] | None = None,
    error_type: str | None = None,
) -> dict[str, Any]:
    """记录一次 Agent 请求的结构化运行信息。"""
    event = {
        "event": "agent_run",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "request_id": request_id,
        "thread_id": thread_id,
        "status": status,
        "route": route,
        "issue_type": issue_type,
        "tool_names": tool_names or [],
        "tool_call_count": len(tool_names or []),
        "duration_ms": round(duration_ms, 2),
        "error_type": error_type,
    }

    LOGGER.info(
        json.dumps(
            event,
            ensure_ascii=False,
        )
    )

    return event
