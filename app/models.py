from datetime import datetime

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from sqlalchemy import DateTime, Index, String, Text, func, text
from pgvector.sqlalchemy import Vector

class Ticket(Base):
    """售后工单数据库模型。"""

    __tablename__ = "tickets"
    __table_args__ = (
        Index(
            "uq_tickets_pending_order_action",
            "order_id",
            "action",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    ticket_id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
    )
    order_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    issue_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

class PolicyDocument(Base):
    """售后政策知识库文档块。"""

    __tablename__ = "policy_documents"

    policy_id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(512),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )