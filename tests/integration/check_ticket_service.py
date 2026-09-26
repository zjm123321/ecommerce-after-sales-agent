from sqlalchemy import delete

from app.database import SessionLocal
from app.models import Ticket
from app.ticket_service import (
    create_ticket,
    get_ticket,
    get_tickets_by_order,
)


def test_create_and_query_ticket():
    ticket = create_ticket(
        order_id="ORD-TEST-001",
        issue_type="delivery_delay",
        action="expedite_logistics",
    )

    try:
        loaded_ticket = get_ticket(ticket.ticket_id)

        assert loaded_ticket is not None
        assert loaded_ticket.ticket_id == ticket.ticket_id
        assert loaded_ticket.order_id == "ORD-TEST-001"
        assert loaded_ticket.issue_type == "delivery_delay"
        assert loaded_ticket.action == "expedite_logistics"
        assert loaded_ticket.status == "pending"

        order_tickets = get_tickets_by_order("ORD-TEST-001")

        assert any(
            item.ticket_id == ticket.ticket_id
            for item in order_tickets
        )
    finally:
        # 测试完成后删除测试数据，避免污染开发数据库。
        with SessionLocal() as session:
            session.execute(
                delete(Ticket).where(
                    Ticket.ticket_id == ticket.ticket_id
                )
            )
            session.commit()