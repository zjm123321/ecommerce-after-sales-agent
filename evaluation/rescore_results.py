import argparse
import json
from pathlib import Path

from evaluation.evaluate_agent import (
    build_summary,
    calls_match,
    contains_unnegated_term,
)


def check_response_text(text: str, case: dict) -> tuple[bool, list[str], list[str]]:
    missing_terms = [
        term
        for term in case.get("required_response_terms", [])
        if term not in text
    ]
    for term_group in case.get("required_response_term_groups", []):
        if not any(term in text for term in term_group):
            missing_terms.append("任一：" + " / ".join(term_group))

    forbidden_terms = [
        term
        for term in case.get("forbidden_response_terms", [])
        if contains_unnegated_term(text, term)
    ]
    return not missing_terms and not forbidden_terms, missing_terms, forbidden_terms


def rescore(cases_path: Path, results_path: Path, output_path: Path) -> None:
    with cases_path.open(encoding="utf-8") as file:
        cases = {case["id"]: case for case in json.load(file)}
    with results_path.open(encoding="utf-8") as file:
        report = json.load(file)

    rescored_results = []
    for old_result in report["results"]:
        result = dict(old_result)
        case = cases[result["id"]]
        response_correct, missing_terms, forbidden_terms = check_response_text(
            result.get("final_response", ""),
            case,
        )
        calls_correct = calls_match(result["actual_calls"], case)
        ticket_correct = (
            result["actual_ticket_created"]
            == case["expected_ticket_created"]
        )

        result["calls_correct"] = calls_correct
        result["ticket_correct"] = ticket_correct
        result["response_correct"] = response_correct
        result["missing_response_terms"] = missing_terms
        result["matched_forbidden_terms"] = forbidden_terms
        result["passed"] = calls_correct and ticket_correct and response_correct
        rescored_results.append(result)

    wall_time = report["summary"]["wall_time_seconds"]
    report["summary"] = build_summary(rescored_results, wall_time)
    report["results"] = rescored_results
    report["rescored_from"] = str(results_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = report["summary"]
    total = summary["case_count"]
    print(f"重新评分完成：{output_path}")
    print(f"任务成功率：{summary['passed_cases']}/{total}")
    print(f"工具调用正确率：{summary['correct_call_cases']}/{total}")
    print(f"最终回复正确率：{summary['correct_response_cases']}/{total}")
    print(f"违规表述案例数：{summary['response_violation_cases']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cases_path", type=Path)
    parser.add_argument("results_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rescore(args.cases_path, args.results_path, args.output)
