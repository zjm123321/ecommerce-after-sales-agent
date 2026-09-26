import argparse
import json
import time
from pathlib import Path

from app.multi_agent import run_multi_agent
from evaluation.evaluate_agent import (
    calls_match,
    collect_tool_calls,
    contains_unnegated_term,
)


DEFAULT_CASES_PATH = Path(__file__).with_name(
    "multi_agent_cases.json"
)


def load_cases(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def evaluate_case(case: dict) -> dict:
    started_at = time.perf_counter()

    try:
        result = run_multi_agent(case["message"])
        messages = result["messages"]
        actual_calls = collect_tool_calls(messages)
        actual_tools = {
            call["name"]
            for call in actual_calls
        }
        final_response = str(messages[-1].content)

        route_correct = (
            result["route"] == case["expected_route"]
        )
        tool_calls_correct = calls_match(
            actual_calls,
            case,
        )

        forbidden_called = sorted(
            actual_tools & set(case["forbidden_tools"])
        )

        forbidden_phrases = [
            phrase
            for phrase in case["forbidden_phrases"]
            if contains_unnegated_term(
                final_response,
                phrase,
            )
        ]

        passed = (
            route_correct
            and tool_calls_correct
            and not forbidden_called
            and not forbidden_phrases
        )

        return {
            "id": case["id"],
            "message": case["message"],
            "expected_route": case["expected_route"],
            "actual_route": result["route"],
            "expected_calls": case["expected_calls"],
            "actual_calls": actual_calls,
            "route_correct": route_correct,
            "tool_calls_correct": tool_calls_correct,
            "forbidden_called": forbidden_called,
            "forbidden_phrases": forbidden_phrases,
            "final_response": final_response,
            "latency_seconds": (
                time.perf_counter() - started_at
            ),
            "passed": passed,
            "error": None,
        }
    except Exception as error:
        return {
            "id": case["id"],
            "message": case["message"],
            "expected_route": case["expected_route"],
            "actual_route": None,
            "expected_calls": case["expected_calls"],
            "actual_calls": [],
            "route_correct": False,
            "tool_calls_correct": False,
            "forbidden_called": [],
            "forbidden_phrases": [],
            "final_response": "",
            "latency_seconds": (
                time.perf_counter() - started_at
            ),
            "passed": False,
            "error": repr(error),
        }


def print_result(result: dict) -> None:
    print(f"\n[{result['id']}]")
    print(f"问题：{result['message']}")
    print(
        "路由："
        f"预期={result['expected_route']}，"
        f"实际={result['actual_route']}"
    )
    print(f"预期调用：{result['expected_calls']}")
    print(f"实际调用：{result['actual_calls']}")

    if result["forbidden_called"]:
        print(
            "越权工具："
            f"{result['forbidden_called']}"
        )

    if result["forbidden_phrases"]:
        print(
            "违规表述："
            f"{result['forbidden_phrases']}"
        )

    if result["error"]:
        print(f"异常：{result['error']}")

    print(
        f"耗时：{result['latency_seconds']:.3f} 秒"
    )
    print(
        f"结果：{'通过' if result['passed'] else '失败'}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "cases_path",
        nargs="?",
        default=str(DEFAULT_CASES_PATH),
    )
    args = parser.parse_args()

    cases_path = Path(args.cases_path)
    cases = load_cases(cases_path)

    print(f"评测数据集：{cases_path}")

    started_at = time.perf_counter()
    results = [
        evaluate_case(case)
        for case in cases
    ]
    wall_time = time.perf_counter() - started_at

    for result in results:
        print_result(result)

    total = len(results)
    passed = sum(
        result["passed"]
        for result in results
    )
    route_correct = sum(
        result["route_correct"]
        for result in results
    )
    calls_correct = sum(
        result["tool_calls_correct"]
        for result in results
    )
    forbidden_calls = sum(
        bool(result["forbidden_called"])
        for result in results
    )
    forbidden_responses = sum(
        bool(result["forbidden_phrases"])
        for result in results
    )
    average_latency = sum(
        result["latency_seconds"]
        for result in results
    ) / total

    print("\n## 多智能体评测结果")
    print(
        f"任务成功率：{passed}/{total} "
        f"({passed / total:.2%})"
    )
    print(
        f"路由正确率：{route_correct}/{total} "
        f"({route_correct / total:.2%})"
    )
    print(
        f"工具调用正确率：{calls_correct}/{total} "
        f"({calls_correct / total:.2%})"
    )
    print(f"越权工具调用案例数：{forbidden_calls}")
    print(f"违规回复案例数：{forbidden_responses}")
    print(f"平均响应耗时：{average_latency:.3f} 秒")
    print(f"总墙钟时间：{wall_time:.3f} 秒")


if __name__ == "__main__":
    main()