# 模拟物流系统返回的数据。
LOGISTICS = {
    "ORD-1001": {
        "company": "顺丰速运",
        "tracking_number": "SF10010001",
        "status": "delayed",
        "latest_event": "包裹停留在上海分拨中心，物流信息长时间未更新",
        "updated_at": "2026-09-22 14:30:00",
    },
    "ORD-1002": {
        "company": "京东物流",
        "tracking_number": "JD10020001",
        "status": "delivered",
        "latest_event": "包裹已由本人签收",
        "updated_at": "2026-09-18 16:20:00",
    },
}


def get_logistics(order_id: str) -> dict | None:
    """根据订单号查询物流信息。"""
    return LOGISTICS.get(order_id)