"""Stand-in for the slow, costly external service that transforms strings."""

import time
from collections.abc import Callable

# Any function from str to str can act as the transformer, so tests can inject a fake.
Transformer = Callable[[str], str]


def make_transformer(delay_seconds: float = 0.0) -> Transformer:
    """Build the transformer; the delay simulates the latency of a real remote call."""

    def transform(value: str) -> str:
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        return value.upper()

    return transform
