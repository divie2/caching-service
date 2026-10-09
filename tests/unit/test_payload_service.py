from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel

from app.db import build_engine
from app.services.payload import transform_with_cache


class CountingTransformer:
    """Fake external service that records every value it is asked to transform."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, value: str) -> str:
        self.calls.append(value)
        return value.upper()


@pytest.fixture
def session() -> Iterator[Session]:
    engine = build_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_duplicates_in_one_request_are_transformed_once(session: Session) -> None:
    transformer = CountingTransformer()

    outputs = transform_with_cache(session, ["a", "a", "b"], transformer)

    assert outputs == {"a": "A", "b": "B"}
    assert transformer.calls == ["a", "b"]


def test_cached_values_are_not_transformed_again(session: Session) -> None:
    transform_with_cache(session, ["a", "b"], CountingTransformer())
    transformer = CountingTransformer()

    outputs = transform_with_cache(session, ["a", "b"], transformer)

    assert outputs == {"a": "A", "b": "B"}
    assert transformer.calls == []


def test_cache_values_are_not_transformed_again(session: Session) -> None:
    transform_with_cache(session, ["a", "b"], CountingTransformer())
    transformer = CountingTransformer()

    outputs = transform_with_cache(session, ["a", "b", "c"], transformer)

    assert outputs == {"a": "A", "b": "B", "c": "C"}
    assert transformer.calls == ["c"]
