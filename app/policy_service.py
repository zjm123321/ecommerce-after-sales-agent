from sqlalchemy import or_, select

from app.database import SessionLocal
from app.embedding import embed_documents, embed_query
from app.models import PolicyDocument


def upsert_policy_documents(
    documents: list[dict],
) -> int:
    """生成政策向量并写入或更新数据库。"""
    if not documents:
        return 0

    contents = [
        f"{document['title']}。{document['content']}"
        for document in documents
    ]
    embeddings = embed_documents(contents)

    with SessionLocal() as session:
        for document, embedding in zip(
            documents,
            embeddings,
            strict=True,
        ):
            policy = PolicyDocument(
                policy_id=document["policy_id"],
                category=document["category"],
                applicable_order_status=document.get(
                    "applicable_order_status"
                ),
                title=document["title"],
                content=document["content"],
                source=document["source"],
                embedding=embedding,
            )
            session.merge(policy)

        session.commit()

    return len(documents)


def search_policy_documents(
    query: str,
    category: str | None = None,
    order_status: str | None = None,
    limit: int = 3,
) -> list[dict]:
    """使用结构化过滤和余弦距离检索政策。"""
    query_embedding = embed_query(query)

    distance = PolicyDocument.embedding.cosine_distance(
        query_embedding
    )

    statement = select(
        PolicyDocument,
        distance.label("distance"),
    )

    if category is not None:
        statement = statement.where(
            PolicyDocument.category == category
        )

    if order_status is not None:
        statement = statement.where(
            or_(
                PolicyDocument.applicable_order_status
                == order_status,
                PolicyDocument.applicable_order_status
                .is_(None),
            )
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
            "policy_id": document.policy_id,
            "category": document.category,
            "applicable_order_status": (
                document.applicable_order_status
            ),
            "title": document.title,
            "content": document.content,
            "source": document.source,
            "score": 1.0 - float(distance_value),
        }
        for document, distance_value in rows
    ]