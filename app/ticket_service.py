from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Ticket

def _find_pending_ticket(
    session: Session,
    order_id: str,
    action: str,
) -> Ticket | None:
    """查询同一订单和动作的待处理工单。"""
    return session.scalar(
        select(Ticket)
        .where(
            Ticket.order_id == order_id,
            Ticket.action == action,
            Ticket.status == "pending",
        )
        .order_by(Ticket.created_at.desc())
    )

def create_ticket(
    order_id: str,
    issue_type: str,
    action: str,
) -> Ticket:
    """创建工单；重复请求返回已有待处理工单。"""

    with SessionLocal() as session:
        existing_ticket = _find_pending_ticket(
            session,
            order_id,
            action,
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

        try:
            session.commit()
        except IntegrityError:
            # 另一个并发请求可能已经创建了相同工单。
            session.rollback()

            existing_ticket = _find_pending_ticket(
                session,
                order_id,
                action,
            )

            if existing_ticket is None:
                raise

            return existing_ticket

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