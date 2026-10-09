from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_transformer
from app.config import Settings
from app.main import create_app
from tests.fakes import CountingTransformer


@pytest.fixture
def transformer() -> CountingTransformer:
    return CountingTransformer()


@pytest.fixture
def client(transformer: CountingTransformer) -> Iterator[TestClient]:
    app = create_app(Settings(database_url="sqlite://"))
    # Swap the real transformer for the counting fake, so tests can see every call.
    app.dependency_overrides[get_transformer] = lambda: transformer
    with TestClient(app) as client:
        yield client
