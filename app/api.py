from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from uuid import uuid4

from app.persistent_multi_agent import run_persistent_multi_agent

from time import perf_counter

from app.observability import record_agent_run

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
    user_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description=(
            "用户编号；用于跨不同 thread_id 检索长期记忆"
        ),
    )

class ToolCallRecord(BaseModel):
    name: str
    args: dict[str, Any]


class ChatResponse(BaseModel):
    request_id: str
    thread_id: str
    user_id: str
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
def chat(
    payload: ChatRequest,
    http_request: Request,
    http_response: Response,
) -> ChatResponse:
    incoming_request_id = http_request.headers.get(
        "X-Request-ID"
    )
    request_id = (
        incoming_request_id
        if incoming_request_id
        and len(incoming_request_id) <= 100
        else str(uuid4())
    )
    thread_id = payload.thread_id or str(uuid4())
    user_id = payload.user_id or thread_id
    started_at = perf_counter()

    try:
        result = run_persistent_multi_agent(
            message=payload.message,
            thread_id=thread_id,
            user_id=user_id,
        )
        turn_messages = result["turn_messages"]
        tool_calls = collect_tool_calls(turn_messages)

        duration_ms = (
            perf_counter() - started_at
        ) * 1000

        record_agent_run(
            request_id=request_id,
            thread_id=thread_id,
            duration_ms=duration_ms,
            status="success",
            route=str(result["route"]),
            issue_type=str(result["issue_type"]),
            tool_names=[
                tool_call.name
                for tool_call in tool_calls
            ],
        )

        http_response.headers[
            "X-Request-ID"
        ] = request_id

        return ChatResponse(
            request_id=request_id,
            thread_id=thread_id,
            user_id=user_id,
            issue_type=str(result["issue_type"]),
            route=str(result["route"]),
            response=str(turn_messages[-1].content),
            tool_calls=tool_calls,
        )
    except Exception as exc:
        duration_ms = (
            perf_counter() - started_at
        ) * 1000

        record_agent_run(
            request_id=request_id,
            thread_id=thread_id,
            duration_ms=duration_ms,
            status="error",
            error_type=type(exc).__name__,
        )

        raise HTTPException(
            status_code=500,
            detail="Agent 处理请求失败",
            headers={
                "X-Request-ID": request_id,
            },
        ) from exc
