from types import SimpleNamespace

from app.tools import (
    create_logistics_expedite_ticket_tool,
    get_logistics_tool,
    get_order_tool,
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

    monkeypatch.setattr("app.tools.create_ticket", fail_if_called)

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