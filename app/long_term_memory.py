from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.embedding import embed_documents, embed_query
from app.models import UserMemory


def upsert_user_memory(
    *,
    user_id: str,
    memory_type: str,
    source_id: str,
    source_thread_id: str,
    content: str,
    expires_at: datetime | None = None,
) -> dict:
    """写入或更新一条经过验证的用户长期记忆。"""
    embedding = embed_documents([content])[0]
    memory_id = f"MEM-{uuid4().hex[:12].upper()}"

    statement = (
        insert(UserMemory)
        .values(
            memory_id=memory_id,
            user_id=user_id,
            memory_type=memory_type,
            source_id=source_id,
            source_thread_id=source_thread_id,
            content=content,
            embedding=embedding,
            expires_at=expires_at,
        )
        .on_conflict_do_update(
            constraint=(
                "uq_user_memories_user_type_source"
            ),
            set_={
                "source_thread_id": source_thread_id,
                "content": content,
                "embedding": embedding,
                "expires_at": expires_at,
                "updated_at": func.now(),
            },
        )
        .returning(UserMemory)
    )

    with SessionLocal() as session:
        memory = session.scalar(statement)
        session.commit()

        if memory is None:
            raise RuntimeError("长期记忆写入失败")

        return {
            "memory_id": memory.memory_id,
            "user_id": memory.user_id,
            "memory_type": memory.memory_type,
            "source_id": memory.source_id,
            "source_thread_id": memory.source_thread_id,
            "content": memory.content,
            "expires_at": (
                memory.expires_at.isoformat()
                if memory.expires_at is not None
                else None
            ),
        }


def search_user_memories(
    *,
    user_id: str,
    query: str,
    memory_type: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """检索指定用户尚未过期的相关长期记忆。"""
    query_embedding = embed_query(query)
    distance = UserMemory.embedding.cosine_distance(
        query_embedding
    )

    statement = (
        select(
            UserMemory,
            distance.label("distance"),
        )
        .where(
            UserMemory.user_id == user_id,
            or_(
                UserMemory.expires_at.is_(None),
                UserMemory.expires_at > func.now(),
            ),
        )
    )

    if memory_type is not None:
        statement = statement.where(
            UserMemory.memory_type == memory_type
        )

    statement = (
        statement
        .order_by(distance)
        .limit(limit)
    )

    with SessionLocal() as session:
        rows = session.execute(statement).all()

    return [
        {
            "memory_id": memory.memory_id,
            "user_id": memory.user_id,
            "memory_type": memory.memory_type,
            "source_id": memory.source_id,
            "source_thread_id": memory.source_thread_id,
            "content": memory.content,
            "score": 1.0 - float(distance_value),
        }
        for memory, distance_value in rows
    ]


def delete_user_memory(
    *,
    user_id: str,
    memory_id: str,
) -> bool:
    """删除属于指定用户的一条长期记忆。"""
    statement = (
        delete(UserMemory)
        .where(
            UserMemory.user_id == user_id,
            UserMemory.memory_id == memory_id,
        )
        .returning(UserMemory.memory_id)
    )

    with SessionLocal() as session:
        deleted_memory_id = session.scalar(statement)
        session.commit()

    return deleted_memory_id is not None