from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.api import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_returns_agent_result(monkeypatch):
    fake_result = {
        "issue_type": "refund_request",
        "route": "refund",
        "messages": [
            AIMessage(
                content="正在查询订单",
                tool_calls=[
                    {
                        "name": "get_order_tool",
                        "args": {"order_id": "ORD-1001"},
                        "id": "call-test-001",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="内部退款审核工单已创建。"),
        ],
    }

    monkeypatch.setattr(
        "app.api.run_multi_agent",
        lambda message: fake_result,
    )

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "订单 ORD-1001 帮我退款",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["issue_type"] == "refund_request"
    assert body["route"] == "refund"
    assert body["response"] == "内部退款审核工单已创建。"
    assert body["tool_calls"] == [
        {
            "name": "get_order_tool",
            "args": {"order_id": "ORD-1001"},
        }
    ]


def test_chat_rejects_empty_message():
    response = client.post(
        "/api/v1/chat",
        json={"message": ""},
    )

    assert response.status_code == 422


def test_chat_hides_internal_error(monkeypatch):
    def raise_error(message):
        raise RuntimeError("模拟内部异常")

    monkeypatch.setattr(
        "app.api.run_multi_agent",
        raise_error,
    )

    response = client.post(
        "/api/v1/chat",
        json={"message": "测试请求"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Agent 处理请求失败"
    }