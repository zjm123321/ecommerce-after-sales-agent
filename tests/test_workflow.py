from app.workflow import handle_ticket


def test_valid_order_and_delivery_question_returns_expedite_action(monkeypatch):
    # 用假函数代替真实 DeepSeek 分类器。
    monkeypatch.setattr(
        "app.workflow.classify_message",
        lambda message: "delivery_delay",
    )

    result = handle_ticket("ORD-1001", "我的蓝牙耳机啥时候到？")

    assert result["issue_type"] == "delivery_delay"
    assert result["action"] == "expedite_logistics"
    assert result["order"]["product"] == "蓝牙耳机"
    assert "物流催办" in result["response"]


def test_missing_order_returns_manual_service(monkeypatch):
    # 同样固定分类结果，专门测试订单不存在的处理逻辑。
    monkeypatch.setattr(
        "app.workflow.classify_message",
        lambda message: "delivery_delay",
    )

    result = handle_ticket("ORD-9999", "我的物流还没到")

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

    result = handle_ticket("ORD-1001", "我的耳机什么时候到？")

    assert result["issue_type"] == "unknown"
    assert result["error_code"] == "classification_failed"
    assert result["action"] == "manual_service"
    assert result["response"] == "问题识别服务暂时不可用，请联系人工客服。"