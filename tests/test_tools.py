from datetime import datetime, timezone
from types import SimpleNamespace

from app.tools import (
    create_logistics_expedite_ticket_tool,
    get_logistics_tool,
    get_order_tool,
    get_ticket_status_tool,
    create_refund_review_ticket_tool,
    search_refund_policy_tool,
    create_return_exchange_review_ticket_tool,
    search_return_exchange_policy_tool,
)


def test_get_order_tool_returns_existing_order():
    result = get_order_tool.invoke({"order_id": "ORD-1001"})

    assert result["found"] is True
    assert result["product"] == "蓝牙耳机"
    assert result["status"] == "shipped"


def test_get_logistics_tool_returns_delayed_status():
    result = get_logistics_tool.invoke({"order_id": "ORD-1001"})

    assert result["found"] is True
    assert result["status"] == "delayed"


def test_delivered_order_cannot_create_expedite_ticket(monkeypatch):
    # 如果护栏正确，这个假函数不应该被调用。
    def fail_if_called(**kwargs):
        raise AssertionError("已签收订单不应调用 create_ticket")

    monkeypatch.setattr(
        "app.tools.create_ticket",
        fail_if_called,
    )

    result = create_logistics_expedite_ticket_tool.invoke(
        {"order_id": "ORD-1002"}
    )

    assert result["created"] is False
    assert result["reason"] == "物流状态不是延迟，不能创建催办工单"


def test_delayed_order_can_create_expedite_ticket(monkeypatch):
    fake_ticket = SimpleNamespace(
        ticket_id="TICKET-TEST-001",
        order_id="ORD-1001",
        issue_type="delivery_delay",
        action="expedite_logistics",
        status="pending",
    )

    monkeypatch.setattr(
        "app.tools.create_ticket",
        lambda **kwargs: fake_ticket,
    )

    result = create_logistics_expedite_ticket_tool.invoke(
        {"order_id": "ORD-1001"}
    )

    assert result["created"] is True
    assert result["ticket_id"] == "TICKET-TEST-001"
    assert result["action"] == "expedite_logistics"


def test_get_ticket_status_tool_returns_ticket(monkeypatch):
    fake_ticket = SimpleNamespace(
        ticket_id="TICKET-TEST-001",
        order_id="ORD-1001",
        issue_type="delivery_delay",
        action="expedite_logistics",
        status="pending",
        created_at=datetime(
            2026,
            9,
            27,
            tzinfo=timezone.utc,
        ),
    )

    monkeypatch.setattr(
        "app.tools.get_ticket",
        lambda ticket_id: fake_ticket,
    )

    result = get_ticket_status_tool.invoke(
        {"ticket_id": "TICKET-TEST-001"}
    )

    assert result["found"] is True
    assert result["ticket_id"] == "TICKET-TEST-001"
    assert result["order_id"] == "ORD-1001"
    assert result["status"] == "pending"
    assert result["created_at"] == "2026-09-27T00:00:00+00:00"


def test_get_ticket_status_tool_returns_not_found(monkeypatch):
    monkeypatch.setattr(
        "app.tools.get_ticket",
        lambda ticket_id: None,
    )

    result = get_ticket_status_tool.invoke(
        {"ticket_id": "TICKET-NOT-FOUND"}
    )

    assert result == {
        "found": False,
        "ticket_id": "TICKET-NOT-FOUND",
        "message": "工单不存在",
    }

def test_missing_order_cannot_create_refund_review(monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("无效订单不应调用 create_ticket")

    monkeypatch.setattr(
        "app.tools.create_ticket",
        fail_if_called,
    )

    result = create_refund_review_ticket_tool.invoke(
        {"order_id": "ORD-9999"}
    )

    assert result["created"] is False
    assert result["reason"] == "订单不存在"


def test_existing_order_can_create_refund_review(monkeypatch):
    fake_ticket = SimpleNamespace(
        ticket_id="TICKET-REFUND-001",
        order_id="ORD-1001",
        issue_type="refund_request",
        action="refund_review",
        status="pending",
    )

    monkeypatch.setattr(
        "app.tools.create_ticket",
        lambda **kwargs: fake_ticket,
    )

    result = create_refund_review_ticket_tool.invoke(
        {"order_id": "ORD-1001"}
    )

    assert result["created"] is True
    assert result["ticket_id"] == "TICKET-REFUND-001"
    assert result["issue_type"] == "refund_request"
    assert result["action"] == "refund_review"
    assert result["status"] == "pending"

def test_refund_policy_tool_uses_real_order_status(
    monkeypatch,
):
    captured = {}

    def fake_search(
        query,
        category,
        order_status,
        limit,
    ):
        captured["query"] = query
        captured["category"] = category
        captured["order_status"] = order_status
        captured["limit"] = limit

        return [
            {
                "policy_id": "POLICY-REFUND-002",
                "category": "refund",
                "applicable_order_status": "shipped",
                "title": "已发货订单退款申请",
                "content": "测试政策",
                "source": "mock://policy",
                "score": 0.9,
            }
        ]

    monkeypatch.setattr(
        "app.tools.search_policy_documents",
        fake_search,
    )

    result = search_refund_policy_tool.invoke(
        {
            "order_id": "ORD-1001",
            "query": "这个订单可以退款吗？",
        }
    )

    assert result["found"] is True
    assert result["order_status"] == "shipped"
    assert captured == {
        "query": "这个订单可以退款吗？",
        "category": "refund",
        "order_status": "shipped",
        "limit": 2,
    }
    assert (
        result["policies"][0]["policy_id"]
        == "POLICY-REFUND-002"
    )


def test_refund_policy_tool_rejects_missing_order(
    monkeypatch,
):
    def fail_if_called(**kwargs):
        raise AssertionError(
            "订单不存在时不应执行政策检索"
        )

    monkeypatch.setattr(
        "app.tools.search_policy_documents",
        fail_if_called,
    )

    result = search_refund_policy_tool.invoke(
        {
            "order_id": "ORD-9999",
            "query": "帮我退款",
        }
    )

    assert result["found"] is False
    assert result["reason"] == "订单不存在"

def test_search_return_exchange_policy_uses_real_order_status(
    monkeypatch,
):
    captured = {}

    def fake_search(
        query,
        category,
        order_status,
        limit,
    ):
        captured.update(
            {
                "query": query,
                "category": category,
                "order_status": order_status,
                "limit": limit,
            }
        )
        return [
            {
                "policy_id": "POLICY-RETURN-001",
                "title": "商品质量问题退换货",
            }
        ]

    monkeypatch.setattr(
        "app.tools.search_policy_documents",
        fake_search,
    )

    result = search_return_exchange_policy_tool.invoke(
        {
            "order_id": "ORD-1002",
            "query": "键盘按键坏了，想换货",
        }
    )

    assert result["found"] is True
    assert result["order_status"] == "delivered"
    assert captured == {
        "query": "键盘按键坏了，想换货",
        "category": "return_exchange",
        "order_status": "delivered",
        "limit": 2,
    }


def test_unshipped_order_cannot_create_return_ticket(
    monkeypatch,
):
    def fail_if_called(**kwargs):
        raise AssertionError(
            "未签收订单不应创建退换货审核工单"
        )

    monkeypatch.setattr(
        "app.tools.create_ticket",
        fail_if_called,
    )

    result = (
        create_return_exchange_review_ticket_tool.invoke(
            {"order_id": "ORD-1001"}
        )
    )

    assert result == {
        "created": False,
        "order_id": "ORD-1001",
        "reason": "订单尚未签收，不能创建退换货审核工单",
    }


def test_delivered_order_can_create_return_ticket(
    monkeypatch,
):
    fake_ticket = SimpleNamespace(
        ticket_id="TICKET-RETURN-001",
        order_id="ORD-1002",
        issue_type="return_exchange",
        action="return_exchange_review",
        status="pending",
    )

    monkeypatch.setattr(
        "app.tools.create_ticket",
        lambda **kwargs: fake_ticket,
    )

    result = (
        create_return_exchange_review_ticket_tool.invoke(
            {"order_id": "ORD-1002"}
        )
    )

    assert result["created"] is True
    assert result["ticket_id"] == "TICKET-RETURN-001"
    assert result["issue_type"] == "return_exchange"
    assert result["action"] == "return_exchange_review"