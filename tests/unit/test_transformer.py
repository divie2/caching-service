import time

from app.transformer import make_transformer


def test_transformer_upper_cases_input() -> None:
    transform = make_transformer()

    assert transform("first string") == "FIRST STRING"


def test_transformer_waits_for_configured_delay() -> None:
    transform = make_transformer(delay_seconds=0.05)

    start = time.perf_counter()
    transform("x")

    assert time.perf_counter() - start >= 0.05
