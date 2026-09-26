from uuid import uuid4

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Ticket

def create_ticket(
    order_id: str,
    issue_type: str,
    action: str,
) -> Ticket:
    """创建工单；相同订单已有待处理工单时直接返回原工单。"""

    with SessionLocal() as session:
        existing_ticket = session.scalar(
            select(Ticket)
            .where(
                Ticket.order_id == order_id,
                Ticket.action == action,
                Ticket.status == "pending",
            )
            .order_by(Ticket.created_at.desc())
        )

        if existing_ticket is not None:
            return existing_ticket

        ticket = Ticket(
            ticket_id=f"TICKET-{uuid4().hex[:12].upper()}",
            order_id=order_id,
            issue_type=issue_type,
            action=action,
            status="pending",
        )

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