from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel

from app.db import build_engine
from app.services.payload import build_output, hash_inputs, transform_with_cache


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


def test_only_uncached_values_are_transformed(session: Session) -> None:
    transform_with_cache(session, ["a", "b"], CountingTransformer())
    transformer = CountingTransformer()

    outputs = transform_with_cache(session, ["b", "c", "c"], transformer)

    assert outputs == {"b": "B", "c": "C"}
    assert transformer.calls == ["c"]


def test_build_output_matches_the_example_from_the_brief(session: Session) -> None:
    output = build_output(
        session,
        ["first string", "second string", "third string"],
        ["other string", "another string", "last string"],
        CountingTransformer(),
    )

    assert output == (
        "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
    )


def test_build_output_transforms_values_shared_by_both_lists_once(session: Session) -> None:
    transformer = CountingTransformer()

    output = build_output(session, ["a", "b"], ["b", "a"], transformer)

    assert output == "A, B, B, A"
    assert transformer.calls == ["a", "b"]


def test_hash_inputs_is_the_same_for_identical_requests() -> None:
    first = hash_inputs(["a", "b"], ["c", "d"])
    second = hash_inputs(["a", "b"], ["c", "d"])

    assert first == second
    assert len(first) == 64


def test_hash_inputs_cannot_be_fooled_by_commas_inside_strings() -> None:
    assert hash_inputs(["a, b"], ["c"]) != hash_inputs(["a"], ["b, c"])


def test_hash_inputs_changes_when_the_lists_are_swapped() -> None:
    assert hash_inputs(["a"], ["b"]) != hash_inputs(["b"], ["a"])

