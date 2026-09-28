from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

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
    applicable_order_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
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

class UserMemory(Base):
    """跨会话保存的用户长期记忆。"""

    __tablename__ = "user_memories"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "memory_type",
            "source_id",
            name="uq_user_memories_user_type_source",
        ),
        Index(
            "ix_user_memories_user_type",
            "user_id",
            "memory_type",
        ),
    )

    memory_id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    source_thread_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(512),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )