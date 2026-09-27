import json
from pathlib import Path

from app.policy_service import upsert_policy_documents


POLICY_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "policies.json"
)


def main() -> None:
    """读取政策文件并写入向量数据库。"""
    with POLICY_FILE.open(encoding="utf-8") as file:
        documents = json.load(file)

    count = upsert_policy_documents(documents)

    print(f"政策文档入库完成：{count} 条")


if __name__ == "__main__":
    main()