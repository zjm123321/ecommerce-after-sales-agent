from typing import Any

from fastapi import FastAPI, HTTPException
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from app.multi_agent import run_multi_agent


app = FastAPI(
    title="电商售后 Agent API",
    description="支持物流催办、退款审核和政策 RAG 的多智能体接口",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="用户的售后问题",
    )


class ToolCallRecord(BaseModel):
    name: str
    args: dict[str, Any]


class ChatResponse(BaseModel):
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
    try:
        result = run_multi_agent(request.message)
        messages = result["messages"]

        return ChatResponse(
            issue_type=str(result["issue_type"]),
            route=str(result["route"]),
            response=str(messages[-1].content),
            tool_calls=collect_tool_calls(messages),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Agent 处理请求失败",
        ) from exc