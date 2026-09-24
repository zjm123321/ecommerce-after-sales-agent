import json
import time
from pathlib import Path
from typing import Callable

from app.baseline_classifier import classify_message_by_rules
from app.classifier import classify_message


DATA_PATH = Path(__file__).with_name("classification_cases.json")


def load_cases() -> list[dict]:
    """读取分类评测数据。"""
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def evaluate_classifier(
    name: str,
    classifier: Callable[[str], str],
    cases: list[dict],
) -> None:
    """运行一个分类器并输出准确率、耗时和错误案例。"""
    correct_count = 0
    total_time = 0.0

    print(f"\n{name}")
    print("-" * 50)

    for index, case in enumerate(cases, start=1):
        message = case["message"]
        expected = case["expected"]

        start_time = time.perf_counter()

        try:
            predicted = classifier(message)
        except Exception as exc:
            predicted = "error"
            print(f"[{index}] 调用失败：{exc}")

        elapsed = time.perf_counter() - start_time
        total_time += elapsed

        if predicted == expected:
            correct_count += 1
        else:
            print(
                f"[{index}] 分类错误\n"
                f"  问题：{message}\n"
                f"  预期：{expected}\n"
                f"  实际：{predicted}"
            )

    total_count = len(cases)
    accuracy = correct_count / total_count
    average_time = total_time / total_count

    print(f"\n正确数量：{correct_count}/{total_count}")
    print(f"准确率：{accuracy:.2%}")
    print(f"平均耗时：{average_time:.3f} 秒")


def main() -> None:
    cases = load_cases()

    evaluate_classifier(
        "关键词基线分类器",
        classify_message_by_rules,
        cases,
    )

    evaluate_classifier(
        "DeepSeek 语义分类器",
        classify_message,
        cases,
    )


if __name__ == "__main__":
    main()