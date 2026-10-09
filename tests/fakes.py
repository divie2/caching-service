"""Test doubles shared by unit and integration tests."""


class CountingTransformer:
    """Fake external service that records every value it is asked to transform."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, value: str) -> str:
        self.calls.append(value)
        return value.upper()
