from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Ticket(Base):
    """售后工单数据库模型。"""

    __tablename__ = "tickets"

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