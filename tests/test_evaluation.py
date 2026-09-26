import pytest

from evaluation.evaluate_agent import contains_unnegated_term


@pytest.mark.parametrize(
    ("text", "term", "expected"),
    [
        ("我们已联系顺丰处理。", "已联系顺丰", True),
        ("不代表已联系顺丰。", "已联系顺丰", False),
        ("我们保证送达。", "保证送达", True),
        ("目前无法保证送达时间。", "保证送达", False),
    ],
)
def test_contains_unnegated_term(text, term, expected):
    assert contains_unnegated_term(text, term) is expected
