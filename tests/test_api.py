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
    events = []

    monkeypatch.setattr(
        "app.api.run_persistent_multi_agent",
        lambda message, thread_id, user_id: build_fake_result(),
    )
    monkeypatch.setattr(
        "app.api.record_agent_run",
        lambda **kwargs: events.append(kwargs),
    )

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "订单 ORD-1001 帮我退款",
            "thread_id": "api-test-001",
        },
        headers={
            "X-Request-ID": "request-test-001",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["request_id"] == "request-test-001"
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
    assert (
        response.headers["X-Request-ID"]
        == "request-test-001"
    )

    assert len(events) == 1
    assert events[0]["status"] == "success"
    assert events[0]["route"] == "refund"
    assert events[0]["tool_names"] == [
        "get_order_tool"
    ]
    assert events[0]["duration_ms"] >= 0


def test_chat_generates_thread_id(monkeypatch):
    captured = {}

    def fake_agent(message, thread_id, user_id):
        captured["thread_id"] = thread_id
        captured["user_id"] = user_id
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
    assert response.json()["request_id"]
    assert response.headers["X-Request-ID"]
    assert (
        response.json()["request_id"]
        == response.headers["X-Request-ID"]
    )


def test_chat_rejects_empty_message():
    response = client.post(
        "/api/v1/chat",
        json={"message": ""},
    )

    assert response.status_code == 422


def test_chat_hides_internal_error(monkeypatch):
    events = []

    def raise_error(message, thread_id, user_id):
        raise RuntimeError("模拟内部异常")

    monkeypatch.setattr(
        "app.api.run_persistent_multi_agent",
        raise_error,
    )
    monkeypatch.setattr(
        "app.api.record_agent_run",
        lambda **kwargs: events.append(kwargs),
    )

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "测试请求",
            "thread_id": "api-test-error",
        },
        headers={
            "X-Request-ID": "request-test-error",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Agent 处理请求失败"
    }
    assert (
        response.headers["X-Request-ID"]
        == "request-test-error"
    )

    assert len(events) == 1
    assert events[0]["status"] == "error"
    assert events[0]["error_type"] == "RuntimeError"
    assert events[0]["duration_ms"] >= 0

def test_chat_passes_user_id_to_agent(monkeypatch):
    captured = {}

    def fake_agent(message, thread_id, user_id):
        captured["message"] = message
        captured["thread_id"] = thread_id
        captured["user_id"] = user_id
        return build_fake_result()

    monkeypatch.setattr(
        "app.api.run_persistent_multi_agent",
        fake_agent,
    )

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "查询之前的工单",
            "thread_id": "api-thread-001",
            "user_id": "api-user-001",
        },
    )

    assert response.status_code == 200
    assert captured == {
        "message": "查询之前的工单",
        "thread_id": "api-thread-001",
        "user_id": "api-user-001",
    }
    assert response.json()["user_id"] == "api-user-001"
