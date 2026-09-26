import json
import sys
import time
from collections import Counter
from pathlib import Path

from app.agent import run_agent


DEFAULT_CASES_PATH = Path(__file__).with_name("agent_cases.json")
TICKET_TOOL = "create_logistics_expedite_ticket_tool"


def load_cases(cases_path: Path) -> list[dict]:
    """读取指定的 Agent 评测数据。"""
    with cases_path.open(encoding="utf-8") as file:
        return json.load(file)


def collect_tool_calls(messages: list) -> list[dict]:
    """提取模型请求调用的工具名称和参数。"""
    calls = []

    for message in messages:
        tool_calls = getattr(message, "tool_calls", None) or []

        for tool_call in tool_calls:
            calls.append(
                {
                    "name": tool_call["name"],
                    "args": tool_call.get("args", {}),
                }
            )

    return calls


def normalize_call(call: dict) -> tuple[str, str]:
    """将工具调用转换为可比较的格式。"""
    return (
        call["name"],
        json.dumps(
            call.get("args", {}),
            ensure_ascii=False,
            sort_keys=True,
        ),
    )


def calls_match(actual_calls: list[dict], case: dict) -> bool:
    """比较工具名称、参数及调用次数。"""
    expected_calls = case.get("expected_calls")

    # 新数据集：严格比较名称、参数和调用次数。
    if expected_calls is not None:
        return Counter(map(normalize_call, actual_calls)) == Counter(
            map(normalize_call, expected_calls)
        )

    # 兼容旧数据集：只比较工具名称集合。
    expected_tools = set(case["expected_tools"])
    actual_tools = {call["name"] for call in actual_calls}
    return actual_tools == expected_tools


def was_ticket_created(messages: list) -> bool:
    """检查工单工具是否返回 created=true。"""
    for message in messages:
        if getattr(message, "name", None) != TICKET_TOOL:
            continue

        content = message.content

        if isinstance(content, str):
            content = json.loads(content)

        if content.get("created") is True:
            return True

    return False


def check_final_response(
    messages: list,
    case: dict,
) -> tuple[bool, list[str], list[str]]:
    """检查最终回复是否包含必需内容和违规表述。"""
    final_response = str(messages[-1].content)
    required_terms = case.get("required_response_terms", [])
    forbidden_terms = case.get("forbidden_response_terms", [])

    missing_terms = [
        term
        for term in required_terms
        if term not in final_response
    ]
    matched_forbidden_terms = [
        term
        for term in forbidden_terms
        if term in final_response
    ]

    response_correct = not missing_terms and not matched_forbidden_terms
    return response_correct, missing_terms, matched_forbidden_terms


def evaluate(cases_path: Path) -> None:
    cases = load_cases(cases_path)

    passed_cases = 0
    correct_call_cases = 0
    correct_response_cases = 0
    response_violation_cases = 0
    violation_attempts = 0
    violation_executions = 0
    total_tool_calls = 0
    total_latency = 0.0

    print(f"评测数据集：{cases_path}")

    for case in cases:
        started_at = time.perf_counter()

        try:
            result = run_agent(case["message"])
            elapsed = time.perf_counter() - started_at

            messages = result["messages"]
            actual_calls = collect_tool_calls(messages)
            actual_tools = {
                call["name"]
                for call in actual_calls
            }
            actual_ticket_created = was_ticket_created(messages)
            (
                response_correct,
                missing_response_terms,
                matched_forbidden_terms,
            ) = check_final_response(messages, case)

            forbidden_tools = set(case["forbidden_tools"])
            calls_correct = calls_match(actual_calls, case)
            forbidden_called = bool(
                actual_tools & forbidden_tools
            )
            ticket_correct = (
                actual_ticket_created
                == case["expected_ticket_created"]
            )
            case_passed = (
                calls_correct
                and ticket_correct
                and response_correct
            )

            correct_call_cases += int(calls_correct)
            correct_response_cases += int(response_correct)
            response_violation_cases += int(
                bool(matched_forbidden_terms)
            )
            violation_attempts += int(forbidden_called)

            if (
                not case["expected_ticket_created"]
                and actual_ticket_created
            ):
                violation_executions += 1

            passed_cases += int(case_passed)
            total_tool_calls += len(actual_calls)
            total_latency += elapsed

            expected = case.get(
                "expected_calls",
                case.get("expected_tools"),
            )

            print(f"\n[{case['id']}]")
            print(f"问题：{case['message']}")
            print(f"预期调用：{expected}")
            print(f"实际调用：{actual_calls}")
            print(
                "工单执行："
                f"预期={case['expected_ticket_created']}，"
                f"实际={actual_ticket_created}"
            )
            print(
                "最终回复检查："
                f"{'通过' if response_correct else '失败'}"
            )
            if missing_response_terms:
                print(f"缺少内容：{missing_response_terms}")
            if matched_forbidden_terms:
                print(f"违规表述：{matched_forbidden_terms}")
            print(f"耗时：{elapsed:.3f} 秒")
            print(
                f"结果：{'通过' if case_passed else '失败'}"
            )

        except Exception as error:
            elapsed = time.perf_counter() - started_at
            total_latency += elapsed

            print(f"\n[{case['id']}]")
            print(
                f"执行异常：{type(error).__name__}: {error}"
            )
            print("结果：失败")

    case_count = len(cases)

    print("\n## Agent 评测结果")
    print(
        f"任务成功率：{passed_cases}/{case_count} "
        f"({passed_cases / case_count:.2%})"
    )
    print(
        f"工具调用正确率：{correct_call_cases}/{case_count} "
        f"({correct_call_cases / case_count:.2%})"
    )
    print(
        f"最终回复正确率：{correct_response_cases}/{case_count} "
        f"({correct_response_cases / case_count:.2%})"
    )
    print(f"存在违规表述的案例数：{response_violation_cases}")
    print(f"违规工具调用次数：{violation_attempts}")
    print(f"违规执行次数：{violation_executions}")
    print(
        "平均工具调用次数："
        f"{total_tool_calls / case_count:.2f}"
    )
    print(
        f"平均响应耗时："
        f"{total_latency / case_count:.3f} 秒"
    )


if __name__ == "__main__":
    cases_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else DEFAULT_CASES_PATH
    )
    evaluate(cases_path)
