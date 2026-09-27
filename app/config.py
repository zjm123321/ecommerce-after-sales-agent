from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """读取并校验本地环境配置。"""

    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_port: int = 5432
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dimension: int = 512
    embedding_cache_dir: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


SETTINGS = Settings()