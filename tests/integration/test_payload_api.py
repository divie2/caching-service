import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.fakes import CountingTransformer

BRIEF_REQUEST = {
    "list_1": ["first string", "second string", "third string"],
    "list_2": ["other string", "another string", "last string"],
}
BRIEF_OUTPUT = (
    "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
)


def test_post_then_get_returns_the_interleaved_output(client: TestClient) -> None:
    created = client.post("/payload", json=BRIEF_REQUEST)
    assert created.status_code == 201

    fetched = client.get(f"/payload/{created.json()['id']}")

    assert fetched.status_code == 200
    assert fetched.json() == {"output": BRIEF_OUTPUT}


def test_repeated_post_reuses_the_id_without_calling_the_transformer(
    client: TestClient, transformer: CountingTransformer
) -> None:
    first = client.post("/payload", json=BRIEF_REQUEST)
    transformer.calls.clear()

    second = client.post("/payload", json=BRIEF_REQUEST)

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert transformer.calls == []


def test_post_with_empty_lists_stores_an_empty_output(client: TestClient) -> None:
    created = client.post("/payload", json={"list_1": [], "list_2": []})
    assert created.status_code == 201

    fetched = client.get(f"/payload/{created.json()['id']}")

    assert fetched.json() == {"output": ""}


@pytest.mark.parametrize(
    "body",
    [
        {"list_1": ["a", "b"], "list_2": ["c"]},
        {"list_1": ["a"]},
        {"list_1": [1], "list_2": ["a"]},
    ],
    ids=["unequal-lengths", "missing-list", "non-string-item"],
)
def test_post_with_invalid_body_returns_422_without_calling_the_transformer(
    client: TestClient, transformer: CountingTransformer, body: dict[str, Any]
) -> None:
    response = client.post("/payload", json=body)

    assert response.status_code == 422
    assert transformer.calls == []


def test_get_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get(f"/payload/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Payload not found"}


def test_get_malformed_id_returns_422(client: TestClient) -> None:
    response = client.get("/payload/not-a-uuid")

    assert response.status_code == 422
