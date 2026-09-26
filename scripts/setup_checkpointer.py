from langgraph.checkpoint.postgres import PostgresSaver

from app.database import CHECKPOINT_DATABASE_URL


def main() -> None:
    """初始化 LangGraph PostgreSQL Checkpoint 表。"""
    with PostgresSaver.from_conn_string(
        CHECKPOINT_DATABASE_URL
    ) as checkpointer:
        checkpointer.setup()

    print("LangGraph Checkpoint 表初始化成功")


if __name__ == "__main__":
    main()