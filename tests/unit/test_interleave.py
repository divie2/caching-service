import pytest

from app.services.payload import interleave


def test_interleave_alternates_items_from_both_lists() -> None:
    first = ["first string", "second string", "third string"]
    second = ["other string", "another string", "last string"]

    assert interleave(first, second) == [
        "first string",
        "other string",
        "second string",
        "another string",
        "third string",
        "last string",
    ]


def test_interleave_rejects_lists_of_different_lengths() -> None:
    with pytest.raises(ValueError):
        interleave(["a", "b"], ["c"])


def test_interleave_of_empty_lists_is_empty() -> None:
    assert interleave([], []) == []
