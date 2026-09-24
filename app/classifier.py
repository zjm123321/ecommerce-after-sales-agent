from typing import Literal

from openai import OpenAI
from pydantic import BaseModel

from app.local_config import DEEPSEEK_API_KEY


# 限制模型只能返回以下四种问题类型。
IssueType = Literal[
    "delivery_delay",
    "refund_request",
    "return_exchange",
    "unknown",
]


# 定义并校验 DeepSeek 返回的 JSON 结构。
class ClassificationResult(BaseModel):
    issue_type: IssueType


def classify_message(message: str) -> IssueType:
    """使用 DeepSeek 判断售后问题类型。"""

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
        timeout=10.0,
        max_retries=2,
    )   

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": (
                    "你是电商售后问题分类器。"
                    "请将用户问题分类为 delivery_delay、refund_request、"
                    "return_exchange 或 unknown。"
                    '只返回 JSON，例如：{"issue_type": "delivery_delay"}。'
                ),
            },
            {
                "role": "user",
                "content": message,
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=100,
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("DeepSeek 返回了空内容")

    result = ClassificationResult.model_validate_json(content)
    return result.issue_type