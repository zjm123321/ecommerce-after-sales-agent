import argparse
import json
import math
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.agent import run_agent
from app.disclosure_agent import run_disclosure_agent


DEFAULT_CASES_PATH = Path(__file__).with_name("agent_cases.json")
TICKET_TOOL = "create_logistics_expedite_ticket_tool"


def load_cases(cases_path: Path) -> list[dict]:
    with cases_path.open(encoding="utf-8") as file:
        return json.load(file)


def collect_tool_calls(messages: list) -> list[dict]:
    calls = []
    for message in messages:
        for tool_call in getattr(message, "tool_calls", None) or []:
            calls.append({"name": tool_call["name"], "args": tool_call.get("args", {})})
    return calls


def normalize_call(call: dict) -> tuple[str, str]:
    return (
        call["name"],
        json.dumps(call.get("args", {}), ensure_ascii=False, sort_keys=True),
    )


def calls_match(actual_calls: list[dict], case: dict) -> bool:
    expected_calls = case.get("expected_calls")
    if expected_calls is not None:
        return Counter(map(normalize_call, actual_calls)) == Counter(
            map(normalize_call, expected_calls)
        )
    return {call["name"] for call in actual_calls} == set(case["expected_tools"])


def was_ticket_created(messages: list) -> bool:
    for message in messages:
        if getattr(message, "name", None) != TICKET_TOOL:
            continue
        content = message.content
        if isinstance(content, str):
            content = json.loads(content)
        if content.get("created") is True:
            return True
    return False


def contains_unnegated_term(text: str, term: str) -> bool:
    """判断禁止词是否以非否定语境出现。"""
    strong_negation_markers = (
        "不代表",
        "并未",
        "没有",
        "尚未",
        "未曾",
        "无法",
        "不能",
        "不会",
        "不承诺",
    )
    clause_boundaries = "。！？\n；;"
    contrast_markers = ("但是", "但", "不过", "然而")
    search_from = 0

    while True:
        position = text.find(term, search_from)
        if position == -1:
            return False

        clause_start = max(
            (text.rfind(mark, 0, position) for mark in clause_boundaries),
            default=-1,
        ) + 1
        for marker in contrast_markers:
            marker_position = text.rfind(marker, clause_start, position)
            if marker_position != -1:
                clause_start = marker_position + len(marker)

        prefix = text[clause_start:position]
        is_negated = (
            any(marker in prefix for marker in strong_negation_markers)
            or prefix.endswith("不")
        )
        if not is_negated:
            return True

        search_from = position + len(term)


def check_final_response(
    messages: list,
    case: dict,
) -> tuple[str, bool, list[str], list[str]]:
    final_response = str(messages[-1].content)
    missing_terms = [
        term
        for term in case.get("required_response_terms", [])
        if term not in final_response
    ]
    for term_group in case.get("required_response_term_groups", []):
        if not any(term in final_response for term in term_group):
            missing_terms.append("任一：" + " / ".join(term_group))
    matched_forbidden_terms = [
        term
        for term in case.get("forbidden_response_terms", [])
        if contains_unnegated_term(final_response, term)
    ]
    return (
        final_response,
        not missing_terms and not matched_forbidden_terms,
        missing_terms,
        matched_forbidden_terms,
    )


def evaluate_case(case: dict, prompt_version: str) -> dict:
    started_at = time.perf_counter()
    try:
        if prompt_version == "disclosure":
            result = run_disclosure_agent(case["message"])
        else:
            result = run_agent(
                case["message"],
                prompt_version=prompt_version,
            )
        elapsed = time.perf_counter() - started_at
        messages = result["messages"]
        actual_calls = collect_tool_calls(messages)
        actual_tools = {call["name"] for call in actual_calls}
        actual_ticket_created = was_ticket_created(messages)
        (
            final_response,
            response_correct,
            missing_terms,
            forbidden_terms,
        ) = check_final_response(messages, case)
        calls_correct = calls_match(actual_calls, case)
        ticket_correct = actual_ticket_created == case["expected_ticket_created"]
        forbidden_called = bool(actual_tools & set(case["forbidden_tools"]))

        return {
            "id": case["id"],
            "category": case.get("category", "unknown"),
            "message": case["message"],
            "expected_calls": case.get("expected_calls", case.get("expected_tools")),
            "actual_calls": actual_calls,
            "final_response": final_response,
            "expected_ticket_created": case["expected_ticket_created"],
            "actual_ticket_created": actual_ticket_created,
            "calls_correct": calls_correct,
            "ticket_correct": ticket_correct,
            "response_correct": response_correct,
            "forbidden_called": forbidden_called,
            "violation_executed": (
                not case["expected_ticket_created"] and actual_ticket_created
            ),
            "missing_response_terms": missing_terms,
            "matched_forbidden_terms": forbidden_terms,
            "tool_call_count": len(actual_calls),
            "latency_seconds": elapsed,
            "passed": calls_correct and ticket_correct and response_correct,
            "error": None,
        }
    except Exception as error:
        return {
            "id": case["id"],
            "category": case.get("category", "unknown"),
            "message": case["message"],
            "expected_calls": case.get("expected_calls", case.get("expected_tools")),
            "actual_calls": [],
            "final_response": "",
            "expected_ticket_created": case["expected_ticket_created"],
            "actual_ticket_created": False,
            "calls_correct": False,
            "ticket_correct": False,
            "response_correct": False,
            "forbidden_called": False,
            "violation_executed": False,
            "missing_response_terms": [],
            "matched_forbidden_terms": [],
            "tool_call_count": 0,
            "latency_seconds": time.perf_counter() - started_at,
            "passed": False,
            "error": f"{type(error).__name__}: {error}",
        }


def percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def build_summary(results: list[dict], wall_time: float) -> dict:
    count = len(results)
    latencies = [result["latency_seconds"] for result in results]
    return {
        "case_count": count,
        "passed_cases": sum(result["passed"] for result in results),
        "correct_call_cases": sum(result["calls_correct"] for result in results),
        "correct_response_cases": sum(
            result["response_correct"] for result in results
        ),
        "response_violation_cases": sum(
            bool(result["matched_forbidden_terms"]) for result in results
        ),
        "violation_attempt_cases": sum(
            result["forbidden_called"] for result in results
        ),
        "violation_execution_cases": sum(
            result["violation_executed"] for result in results
        ),
        "exception_cases": sum(result["error"] is not None for result in results),
        "average_tool_calls": sum(result["tool_call_count"] for result in results)
        / count,
        "average_latency_seconds": sum(latencies) / count,
        "p50_latency_seconds": percentile(latencies, 0.50),
        "p95_latency_seconds": percentile(latencies, 0.95),
        "wall_time_seconds": wall_time,
        "throughput_cases_per_second": count / wall_time,
    }


def print_case_result(result: dict) -> None:
    print(f"\n[{result['id']}]")
    print(f"问题：{result['message']}")
    if result["error"]:
        print(f"执行异常：{result['error']}")
        print("结果：失败")
        return
    print(f"预期调用：{result['expected_calls']}")
    print(f"实际调用：{result['actual_calls']}")
    print(f"最终回复：{result['final_response']}")
    print(
        f"工单执行：预期={result['expected_ticket_created']}，"
        f"实际={result['actual_ticket_created']}"
    )
    print(f"最终回复检查：{'通过' if result['response_correct'] else '失败'}")
    if result["missing_response_terms"]:
        print(f"缺少内容：{result['missing_response_terms']}")
    if result["matched_forbidden_terms"]:
        print(f"违规表述：{result['matched_forbidden_terms']}")
    print(f"耗时：{result['latency_seconds']:.3f} 秒")
    print(f"结果：{'通过' if result['passed'] else '失败'}")


def print_summary(summary: dict) -> None:
    total = summary["case_count"]

    def rate(value: int) -> str:
        return f"{value}/{total} ({value / total:.2%})"

    print("\n## Agent 评测结果")
    print(f"任务成功率：{rate(summary['passed_cases'])}")
    print(f"工具调用正确率：{rate(summary['correct_call_cases'])}")
    print(f"最终回复正确率：{rate(summary['correct_response_cases'])}")
    print(f"存在违规表述的案例数：{summary['response_violation_cases']}")
    print(f"违规工具调用案例数：{summary['violation_attempt_cases']}")
    print(f"违规执行案例数：{summary['violation_execution_cases']}")
    print(f"异常案例数：{summary['exception_cases']}")
    print(f"平均工具调用次数：{summary['average_tool_calls']:.2f}")
    print(f"平均响应耗时：{summary['average_latency_seconds']:.3f} 秒")
    print(f"P50 响应耗时：{summary['p50_latency_seconds']:.3f} 秒")
    print(f"P95 响应耗时：{summary['p95_latency_seconds']:.3f} 秒")
    print(f"总墙钟时间：{summary['wall_time_seconds']:.3f} 秒")
    print(f"吞吐量：{summary['throughput_cases_per_second']:.2f} 条/秒")


def evaluate(
    cases_path: Path,
    prompt_version: str,
    workers: int,
    verbose: bool,
    output_path: Path | None,
) -> None:
    cases = load_cases(cases_path)
    started_at = time.perf_counter()

    print(f"评测数据集：{cases_path}")
    print(f"提示词版本：{prompt_version}")
    print(f"并发数：{workers}")

    indexed_results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {
            executor.submit(evaluate_case, case, prompt_version): index
            for index, case in enumerate(cases)
        }
        for future in as_completed(future_to_index):
            indexed_results.append((future_to_index[future], future.result()))

    wall_time = time.perf_counter() - started_at
    results = [
        result
        for _, result in sorted(indexed_results, key=lambda item: item[0])
    ]
    summary = build_summary(results, wall_time)

    for result in results:
        if verbose or not result["passed"]:
            print_case_result(result)
    if not verbose and summary["passed_cases"] == len(results):
        print("\n所有案例均通过；使用 --verbose 查看逐条结果。")

    print_summary(summary)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "cases_path": str(cases_path),
                    "prompt_version": prompt_version,
                    "workers": workers,
                    "summary": summary,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"结果已保存：{output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "cases_path", nargs="?", type=Path, default=DEFAULT_CASES_PATH
    )
    parser.add_argument(
        "--prompt",
        choices=["baseline", "optimized", "disclosure"],
        default="optimized",
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers 必须大于或等于 1")

    evaluate(
        cases_path=args.cases_path,
        prompt_version=args.prompt,
        workers=args.workers,
        verbose=args.verbose,
        output_path=args.output,
    )
