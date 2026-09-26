from sqlalchemy import delete

from app.database import SessionLocal
from app.models import Ticket
from app.ticket_service import (
    create_ticket,
    get_ticket,
    get_tickets_by_order,
)


TEST_ORDER_ID = "ORD-TEST-001"


def test_create_and_query_ticket():
    # 第一次调用：应该创建一张新工单。
    ticket = create_ticket(
        order_id=TEST_ORDER_ID,
        issue_type="delivery_delay",
        action="expedite_logistics",
    )

    try:
        # 第二次相同调用：应该返回已有工单，不应重复创建。
        duplicate_ticket = create_ticket(
            order_id=TEST_ORDER_ID,
            issue_type="delivery_delay",
            action="expedite_logistics",
        )

        assert duplicate_ticket.ticket_id == ticket.ticket_id

        # 根据工单编号查询。
        loaded_ticket = get_ticket(ticket.ticket_id)

        assert loaded_ticket is not None
        assert loaded_ticket.ticket_id == ticket.ticket_id
        assert loaded_ticket.order_id == TEST_ORDER_ID
        assert loaded_ticket.issue_type == "delivery_delay"
        assert loaded_ticket.action == "expedite_logistics"
        assert loaded_ticket.status == "pending"

        # 根据订单号查询。
        order_tickets = get_tickets_by_order(TEST_ORDER_ID)

        matching_tickets = [
            item
            for item in order_tickets
            if (
                item.action == "expedite_logistics"
                and item.status == "pending"
            )
        ]

        # 相同请求执行两次，数据库中仍然只能有一张待处理工单。
        assert len(matching_tickets) == 1
        assert matching_tickets[0].ticket_id == ticket.ticket_id

    finally:
        # 即使测试失败，也删除该测试订单产生的全部工单。
        with SessionLocal() as session:
            session.execute(
                delete(Ticket).where(
                    Ticket.order_id == TEST_ORDER_ID
                )
            )
            session.commit()