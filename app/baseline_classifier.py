def classify_message_by_rules(message: str) -> str:
    """使用第一版关键词规则识别物流问题。"""
    delivery_words = ("物流", "快递", "没到", "延迟", "晚了", "送到")

    if any(word in message for word in delivery_words):
        return "delivery_delay"

    return "unknown"