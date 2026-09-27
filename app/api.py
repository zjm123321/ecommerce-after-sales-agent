from typing import Any

from fastapi import FastAPI, HTTPException, Request
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from uuid import uuid4

from app.persistent_multi_agent import run_persistent_multi_agent


app = FastAPI(
    title="电商售后 Agent API",
    description="支持物流催办、退款审核和政策 RAG 的多智能体接口",
    version="1.0.0",
)

@app.middleware("http")
async def add_utf8_charset(request: Request, call_next):
    """明确声明 JSON 使用 UTF-8，兼容旧版 PowerShell 客户端。"""
    response = await call_next(request)
    content_type = response.headers.get(
        "content-type",
        "",
    )

    if (
        content_type.startswith("application/json")
        and "charset=" not in content_type
    ):
        response.headers["content-type"] = (
            f"{content_type}; charset=utf-8"
        )

    return response


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="用户的售后问题",
    )
    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="会话编号；不提供时自动生成",
    )

class ToolCallRecord(BaseModel):
    name: str
    args: dict[str, Any]


class ChatResponse(BaseModel):
    thread_id: str
    issue_type: str
    route: str
    response: str
    tool_calls: list[ToolCallRecord]


def collect_tool_calls(messages: list[Any]) -> list[ToolCallRecord]:
    """从 Agent 消息中提取 Function Calling 轨迹。"""
    records: list[ToolCallRecord] = []

    for message in messages:
        if not isinstance(message, AIMessage):
            continue

        for tool_call in message.tool_calls:
            records.append(
                ToolCallRecord(
                    name=tool_call["name"],
                    args=tool_call.get("args", {}),
                )
            )

    return records


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    thread_id = request.thread_id or str(uuid4())

    try:
        result = run_persistent_multi_agent(
            message=request.message,
            thread_id=thread_id,
        )
        turn_messages = result["turn_messages"]

        return ChatResponse(
            thread_id=thread_id,
            issue_type=str(result["issue_type"]),
            route=str(result["route"]),
            response=str(turn_messages[-1].content),
            tool_calls=collect_tool_calls(turn_messages),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Agent 处理请求失败",
        ) from exc