from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import SETTINGS


QUERY_INSTRUCTION = (
    "为这个句子生成表示以用于检索相关文章："
)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """加载并缓存本地 Embedding 模型。"""
    return SentenceTransformer(
        SETTINGS.embedding_model,
        cache_folder=SETTINGS.embedding_cache_dir,
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    """生成文档向量。"""
    model = get_embedding_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
    )
    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    """生成带检索指令的查询向量。"""
    model = get_embedding_model()
    vector = model.encode(
        QUERY_INSTRUCTION + query,
        normalize_embeddings=True,
    )
    return vector.tolist()