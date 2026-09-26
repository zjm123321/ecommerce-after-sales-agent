from types import SimpleNamespace

from app.workflow import handle_ticket


def test_valid_order_and_delivery_question_returns_expedite_action(
    monkeypatch,
):
    # 模拟 DeepSeek 分类结果。
    monkeypatch.setattr(
        "app.workflow.classify_message",
        lambda message: "delivery_delay",
    )

    # 模拟数据库创建工单，避免单元测试写入真实数据库。
    monkeypatch.setattr(
        "app.workflow.create_ticket",
        lambda **kwargs: SimpleNamespace(
            ticket_id="TICKET-TEST-001"
        ),
    )

    result = handle_ticket(
        "ORD-1001",
        "我的蓝牙耳机啥时候到？",
    )

    assert result["issue_type"] == "delivery_delay"
    assert result["action"] == "expedite_logistics"
    assert result["order"]["product"] == "蓝牙耳机"
    assert result["ticket_id"] == "TICKET-TEST-001"
    assert "物流催办" in result["response"]
    assert "TICKET-TEST-001" in result["response"]


def test_missing_order_returns_manual_service(monkeypatch):
    # 固定分类结果，专门测试订单不存在。
    monkeypatch.setattr(
        "app.workflow.classify_message",
        lambda message: "delivery_delay",
    )

    result = handle_ticket(
        "ORD-9999",
        "我的物流还没到",
    )

    assert result["action"] == "manual_service"
    assert result["error_code"] == "order_not_found"
    assert result["error_message"] == "订单不存在"


def test_classifier_failure_returns_manual_service(monkeypatch):
    def raise_api_error(message):
        raise RuntimeError("模拟 DeepSeek API 连接失败")

    monkeypatch.setattr(
        "app.workflow.classify_message",
        raise_api_error,
    )

    result = handle_ticket(
        "ORD-1001",
        "我的耳机什么时候到？",
    )

    assert result["issue_type"] == "unknown"
    assert result["error_code"] == "classification_failed"
    assert result["action"] == "manual_service"
    assert (
        result["response"]
        == "问题识别服务暂时不可用，请联系人工客服。"
    )


def test_ticket_creation_failure_returns_manual_service(monkeypatch):
    # 模拟DeepSeek正常识别为物流问题。
    monkeypatch.setattr(
        "app.workflow.classify_message",
        lambda message: "delivery_delay",
    )

    # 模拟数据库创建工单失败。
    def raise_database_error(**kwargs):
        raise RuntimeError("模拟数据库连接失败")

    monkeypatch.setattr(
        "app.workflow.create_ticket",
        raise_database_error,
    )

    result = handle_ticket(
        "ORD-1001",
        "我的耳机还没到",
    )

    assert result["action"] == "manual_service"
    assert result["error_code"] == "ticket_creation_failed"
    assert (
        result["response"]
        == "物流催办工单创建失败，请联系人工客服。"
    )