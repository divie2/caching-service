import pytest
from pydantic import ValidationError

from app.schemas import PayloadCreate


def test_payload_create_accepts_lists_of_equal_length() -> None:
    payload = PayloadCreate(list_1=["a", "b"], list_2=["c", "d"])

    assert payload.list_1 == ["a", "b"]
    assert payload.list_2 == ["c", "d"]


def test_payload_create_rejects_lists_of_different_lengths() -> None:
    with pytest.raises(ValidationError, match="same length"):
        PayloadCreate(list_1=["a", "b"], list_2=["c"])


def test_payload_create_rejects_non_string_items() -> None:
    with pytest.raises(ValidationError):
        PayloadCreate.model_validate({"list_1": [1], "list_2": ["a"]})


def test_payload_create_accepts_empty_lists() -> None:
    payload = PayloadCreate(list_1=[], list_2=[])

    assert payload.list_1 == []
    assert payload.list_2 == []
