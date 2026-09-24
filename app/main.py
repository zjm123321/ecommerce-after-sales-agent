from app.workflow import handle_ticket


def main() -> None:
    print("电商售后最小原型")
    order_id = input("请输入订单号：").strip()
    message = input("请输入售后问题：").strip()
    result = handle_ticket(order_id, message)
    print(f"\n问题类型：{result['issue_type']}")
    print(f"处理动作：{result['action']}")
    print(f"处理结果：{result['response']}")


if __name__ == "__main__":
    main()

