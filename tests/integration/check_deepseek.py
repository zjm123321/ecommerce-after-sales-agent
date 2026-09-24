from app.classifier import classify_message


def test_deepseek_classifies_delivery_question():
    result = classify_message("我的蓝牙耳机啥时候到？")

    assert result == "delivery_delay"
