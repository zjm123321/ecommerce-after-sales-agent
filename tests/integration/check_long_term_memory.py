from uuid import uuid4

from sqlalchemy import delete

from app.database import SessionLocal
from app.long_term_memory import (
    delete_user_memory,
    search_user_memories,
    upsert_user_memory,
)
from app.models import UserMemory


def test_long_term_memory_persistence_and_isolation():
    suffix = uuid4().hex[:8]
    user_id = f"integration-user-{suffix}"
    other_user_id = f"integration-other-{suffix}"
    source_id = f"TICKET-{suffix.upper()}"

    try:
        first = upsert_user_memory(
            user_id=user_id,
            memory_type="ticket",
            source_id=source_id,
            source_thread_id="thread-old",
            content=(
                f"订单 ORD-TEST 的内部工单 {source_id}，"
                "当前状态为 pending。"
            ),
        )

        second = upsert_user_memory(
            user_id=user_id,
            memory_type="ticket",
            source_id=source_id,
            source_thread_id="thread-new",
            content=(
                f"订单 ORD-TEST 的内部工单 {source_id}，"
                "当前状态仍为 pending。"
            ),
        )

        assert second["memory_id"] == first["memory_id"]
        assert second["source_thread_id"] == "thread-new"

        results = search_user_memories(
            user_id=user_id,
            query="我之前的工单现在怎么样了？",
        )

        assert len(results) == 1
        assert results[0]["source_id"] == source_id

        other_results = search_user_memories(
            user_id=other_user_id,
            query="我之前的工单现在怎么样了？",
        )

        assert other_results == []

        deleted = delete_user_memory(
            user_id=user_id,
            memory_id=first["memory_id"],
        )

        assert deleted is True

        remaining = search_user_memories(
            user_id=user_id,
            query="之前的工单",
        )

        assert remaining == []
    finally:
        with SessionLocal() as session:
            session.execute(
                delete(UserMemory).where(
                    UserMemory.user_id.in_(
                        [user_id, other_user_id]
                    )
                )
            )
            session.commit()