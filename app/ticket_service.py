from uuid import uuid4

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Ticket


def create_ticket(
    order_id: str,
    issue_type: str,
    action: str,
) -> Ticket:
    """创建售后工单并写入数据库。"""
    ticket = Ticket(
        ticket_id=f"TICKET-{uuid4().hex[:12].upper()}",
        order_id=order_id,
        issue_type=issue_type,
        action=action,
        status="pending",
    )

    with SessionLocal() as session:
        session.add(ticket)
        session.commit()
        session.refresh(ticket)

    return ticket


def get_ticket(ticket_id: str) -> Ticket | None:
    """根据工单编号查询工单。"""
    with SessionLocal() as session:
        return session.get(Ticket, ticket_id)


def get_tickets_by_order(order_id: str) -> list[Ticket]:
    """查询指定订单的全部工单。"""
    with SessionLocal() as session:
        statement = (
            select(Ticket)
            .where(Ticket.order_id == order_id)
            .order_by(Ticket.created_at.desc())
        )
        return list(session.scalars(statement))