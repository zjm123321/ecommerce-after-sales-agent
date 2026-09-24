# 模拟订单数据库：订单号是 key，订单信息是 value。
ORDERS = {
    "ORD-1001": {
        "product": "蓝牙耳机",
        "status": "shipped",  # 已发货，尚未送达
        "expected_delivery": "2026-09-20",
    },
    "ORD-1002": {
        "product": "机械键盘",
        "status": "delivered",  # 已送达
        "expected_delivery": "2026-09-18",
    },
}


def get_order(order_id: str) -> dict | None:
    """根据订单号查询订单；不存在时返回 None。"""
    return ORDERS.get(order_id)
