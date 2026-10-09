import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

from app.db import build_engine
from app.models import Payload, TransformCache


@pytest.fixture
def engine() -> Engine:
    engine = build_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return engine


def test_cache_rejects_a_second_row_for_the_same_input(engine: Engine) -> None:
    with Session(engine) as first:
        first.add(TransformCache(input="hello", output="HELLO"))
        first.commit()

    with Session(engine) as second:
        second.add(TransformCache(input="hello", output="HELLO"))
        with pytest.raises(IntegrityError):
            second.commit()


def test_payload_rejects_a_second_row_with_the_same_hash(engine: Engine) -> None:
    with Session(engine) as first:
        first.add(Payload(input_hash="abc123", output="A, B"))
        first.commit()

    with Session(engine) as second:
        second.add(Payload(input_hash="abc123", output="A, B"))
        with pytest.raises(IntegrityError):
            second.commit()
