import pytest

from app.triage import triage_message


@pytest.mark.parametrize(
    ("issue_type", "expected_route"),
    [
        ("delivery_delay", "logistics"),
        ("refund_request", "refund"),
        ("return_exchange", "return_exchange"),
        ("unknown", "human_handoff"),
    ],
)
def test_triage_routes_issue_to_expected_agent(
    monkeypatch,
    issue_type,
    expected_route,
):
    monkeypatch.setattr(
        "app.triage.classify_message",
        lambda message: issue_type,
    )

    result = triage_message("测试问题")

    assert result.issue_type == issue_type
    assert result.route == expected_route