from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.api import app


client = TestClient(app)


def build_fake_result():
    messages = [
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
    ]

    return {
        "issue_type": "refund_request",
        "route": "refund",
        "messages": messages,
        "turn_messages": messages,
    }


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert (
        response.headers["content-type"]
        == "application/json; charset=utf-8"
    )


def test_chat_returns_agent_result(monkeypatch):
    monkeypatch.setattr(
        "app.api.run_persistent_multi_agent",
        lambda message, thread_id: build_fake_result(),
    )

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "订单 ORD-1001 帮我退款",
            "thread_id": "api-test-001",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["thread_id"] == "api-test-001"
    assert body["issue_type"] == "refund_request"
    assert body["route"] == "refund"
    assert body["response"] == "内部退款审核工单已创建。"
    assert body["tool_calls"] == [
        {
            "name": "get_order_tool",
            "args": {"order_id": "ORD-1001"},
        }
    ]


def test_chat_generates_thread_id(monkeypatch):
    captured = {}

    def fake_agent(message, thread_id):
        captured["thread_id"] = thread_id
        return build_fake_result()

    monkeypatch.setattr(
        "app.api.run_persistent_multi_agent",
        fake_agent,
    )

    response = client.post(
        "/api/v1/chat",
        json={"message": "测试自动生成会话编号"},
    )

    assert response.status_code == 200
    assert response.json()["thread_id"]
    assert response.json()["thread_id"] == captured["thread_id"]


def test_chat_rejects_empty_message():
    response = client.post(
        "/api/v1/chat",
        json={"message": ""},
    )

    assert response.status_code == 422


def test_chat_hides_internal_error(monkeypatch):
    def raise_error(message, thread_id):
        raise RuntimeError("模拟内部异常")

    monkeypatch.setattr(
        "app.api.run_persistent_multi_agent",
        raise_error,
    )

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "测试请求",
            "thread_id": "api-test-error",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Agent 处理请求失败"
    }