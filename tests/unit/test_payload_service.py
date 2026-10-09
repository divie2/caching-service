from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, select

from app.db import build_engine
from app.models import Payload, TransformCache
from app.services.payload import build_output, create_payload, hash_inputs, transform_with_cache
from tests.fakes import CountingTransformer


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


def test_create_payload_stores_a_new_payload(session: Session) -> None:
    payload, created = create_payload(session, ["a"], ["b"], CountingTransformer())

    assert created is True
    assert payload.output == "A, B"


def test_create_payload_reuses_the_id_for_a_repeated_request(session: Session) -> None:
    first, _ = create_payload(session, ["a"], ["b"], CountingTransformer())
    transformer = CountingTransformer()

    second, created = create_payload(session, ["a"], ["b"], transformer)

    assert second.id == first.id
    assert created is False
    assert transformer.calls == []


def test_create_payload_returns_the_winner_when_it_loses_an_insert_race(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'race.db'}")
    SQLModel.metadata.create_all(engine)
    input_hash = hash_inputs(["a"], ["a"])

    def transformer_racing_another_request(value: str) -> str:
        # While we wait on the slow service, another request saves the same payload.
        with Session(engine) as other_request:
            other_request.add(Payload(input_hash=input_hash, output="A, A"))
            other_request.commit()
        return value.upper()

    with Session(engine) as session:
        payload, created = create_payload(session, ["a"], ["a"], transformer_racing_another_request)

    assert created is False
    assert payload.input_hash == input_hash


def test_transform_with_cache_survives_another_request_caching_the_same_value(
    tmp_path: Path,
) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'race.db'}")
    SQLModel.metadata.create_all(engine)

    def transformer_racing_another_request(value: str) -> str:
        # While we wait on the slow service, another request caches the same value.
        with Session(engine) as other_request:
            other_request.add(TransformCache(input=value, output=value.upper()))
            other_request.commit()
        return value.upper()

    with Session(engine) as session:
        outputs = transform_with_cache(session, ["a", "b"], transformer_racing_another_request)
        cached_inputs = [row.input for row in session.exec(select(TransformCache)).all()]

    assert outputs == {"a": "A", "b": "B"}
    assert sorted(cached_inputs) == ["a", "b"]
