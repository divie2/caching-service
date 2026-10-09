import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_read_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db/cache")
    monkeypatch.setenv("TRANSFORMER_DELAY_SECONDS", "0.5")

    settings = Settings()

    assert settings.database_url == "postgresql://user:pass@db/cache"
    assert settings.transformer_delay_seconds == 0.5


def test_settings_reject_negative_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSFORMER_DELAY_SECONDS", "-1")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_reject_non_numeric_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSFORMER_DELAY_SECONDS", "abc")

    with pytest.raises(ValidationError):
        Settings()
