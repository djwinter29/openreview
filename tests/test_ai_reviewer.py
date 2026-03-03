from openreview.ai_reviewer import _fp


def test_fingerprint_stable() -> None:
    a = _fp('/a.c', 12, 'Null pointer risk')
    b = _fp('/a.c', 12, 'null pointer risk')
    assert a == b
