from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.multi_agent import build_multi_agent


def fake_logistics_agent(state) -> dict:
    """代替真实物流 Agent，避免单元测试调用 API。"""
    return {
        "messages": [
            AIMessage(content="物流 Agent 已处理")
        ]
    }


@pytest.mark.parametrize(
    ("issue_type", "route", "expected_text"),
    [
        (
            "delivery_delay",
            "logistics",
            "物流 Agent 已处理",
        ),
        (
            "refund_request",
            "refund",
            "退款 Agent 尚未接入",
        ),
        (
            "return_exchange",
            "return_exchange",
            "退换货 Agent 尚未接入",
        ),
        (
            "unknown",
            "human_handoff",
            "人工客服",
        ),
    ],
)
def test_multi_agent_routes_to_expected_specialist(
    monkeypatch,
    issue_type,
    route,
    expected_text,
):
    monkeypatch.setattr(
        "app.multi_agent.triage_message",
        lambda message: SimpleNamespace(
            issue_type=issue_type,
            route=route,
        ),
    )

    agent = build_multi_agent(
        logistics_agent=fake_logistics_agent,
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "测试问题",
                }
            ]
        }
    )

    assert result["issue_type"] == issue_type
    assert result["route"] == route
    assert expected_text in result["messages"][-1].content