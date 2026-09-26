from typing import Literal

from pydantic import BaseModel

from app.classifier import IssueType, classify_message


AgentRoute = Literal[
    "logistics",
    "refund",
    "return_exchange",
    "human_handoff",
]


class TriageDecision(BaseModel):
    """Triage Agent 的结构化路由结果。"""

    issue_type: IssueType
    route: AgentRoute


ROUTE_BY_ISSUE_TYPE: dict[IssueType, AgentRoute] = {
    "delivery_delay": "logistics",
    "refund_request": "refund",
    "return_exchange": "return_exchange",
    "unknown": "human_handoff",
}


def triage_message(message: str) -> TriageDecision:
    """识别业务类型并选择对应的专家 Agent。"""
    issue_type = classify_message(message)

    return TriageDecision(
        issue_type=issue_type,
        route=ROUTE_BY_ISSUE_TYPE[issue_type],
    )