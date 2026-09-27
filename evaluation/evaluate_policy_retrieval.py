import json
import time
from pathlib import Path

from app.policy_service import search_policy_documents

import argparse

CASES_PATH = Path(__file__).with_name(
    "policy_retrieval_cases.json"
)


def load_cases(cases_path: Path) -> list[dict]:
    with cases_path.open(encoding="utf-8") as file:
        return json.load(file)


def evaluate_case(case: dict) -> dict:
    started_at = time.perf_counter()

    results = search_policy_documents(
        query=case["query"],
        category=case["category"],
        order_status=case.get("order_status"),
        limit=3,
    )

    latency = time.perf_counter() - started_at
    ranked_policy_ids = [
        result["policy_id"]
        for result in results
    ]

    expected_policy_id = case["expected_policy_id"]

    try:
        rank = (
            ranked_policy_ids.index(expected_policy_id)
            + 1
        )
    except ValueError:
        rank = None

    return {
        "id": case["id"],
        "query": case["query"],
        "order_status": case.get("order_status"),
        "expected_policy_id": expected_policy_id,
        "ranked_policy_ids": ranked_policy_ids,
        "rank": rank,
        "hit_at_1": rank == 1,
        "hit_at_3": rank is not None and rank <= 3,
        "reciprocal_rank": (
            1.0 / rank
            if rank is not None
            else 0.0
        ),
        "latency_seconds": latency,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "cases_path",
        nargs="?",
        default=str(CASES_PATH),
    )
    args = parser.parse_args()

    cases_path = Path(args.cases_path)
    cases = load_cases(cases_path)

    print(f"评测数据集：{cases_path}")

    # 预热模型，避免首次加载时间污染平均检索耗时。
    search_policy_documents(
        query="预热查询",
        limit=1,
    )

    results = [
        evaluate_case(case)
        for case in cases
    ]

    for result in results:
        print(f"\n[{result['id']}]")
        print(f"问题：{result['query']}")
        print(
            f"订单状态：{result['order_status']}"
        )
        print(
            f"预期政策：{result['expected_policy_id']}"
        )
        print(
            f"实际排序：{result['ranked_policy_ids']}"
        )
        print(f"目标排名：{result['rank']}")
        print(
            "结果："
            f"{'通过' if result['hit_at_1'] else '失败'}"
        )

    total = len(results)
    hit_at_1 = sum(
        result["hit_at_1"]
        for result in results
    )
    hit_at_3 = sum(
        result["hit_at_3"]
        for result in results
    )
    mrr = sum(
        result["reciprocal_rank"]
        for result in results
    ) / total
    average_latency = sum(
        result["latency_seconds"]
        for result in results
    ) / total

    print("\n## 政策检索评测结果")
    print(
        f"Hit@1：{hit_at_1}/{total} "
        f"({hit_at_1 / total:.2%})"
    )
    print(
        f"Hit@3：{hit_at_3}/{total} "
        f"({hit_at_3 / total:.2%})"
    )
    print(f"MRR：{mrr:.4f}")
    print(
        f"平均检索耗时：{average_latency:.4f} 秒"
    )


if __name__ == "__main__":
    main()