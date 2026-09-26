from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import SETTINGS


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=SETTINGS.postgres_user,
    password=SETTINGS.postgres_password,
    host="127.0.0.1",
    port=SETTINGS.postgres_port,
    database=SETTINGS.postgres_db,
)

ENGINE = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=ENGINE,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """所有数据库模型的基类。"""


def check_database_connection() -> bool:
    """执行简单SQL，确认数据库连接可用。"""
    with ENGINE.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return result.scalar_one() == 1