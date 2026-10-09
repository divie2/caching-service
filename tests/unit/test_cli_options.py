import io
from pathlib import Path

import pytest
from pydantic import ValidationError

from cli.main import parse_options

VALID_JSON = '{"list_1": ["a"], "list_2": ["b"]}'


def test_short_flags_set_host_repeat_and_payload() -> None:
    options = parse_options(["-h", "http://api:9000", "-r", "3", "-j", VALID_JSON])

    assert str(options.host) == "http://api:9000/"
    assert options.repeat == 3
    assert options.payload.list_1 == ["a"]
    assert options.payload.list_2 == ["b"]


def test_payload_can_be_read_from_a_file(tmp_path: Path) -> None:
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(VALID_JSON, encoding="utf-8")

    options = parse_options(["--input", str(payload_file)])

    assert options.payload.list_2 == ["b"]


def test_payload_can_be_read_from_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(VALID_JSON))

    options = parse_options(["-i", "-"])

    assert options.payload.list_1 == ["a"]


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["-i", "payload.json", "-j", VALID_JSON],
        ["-r", "0", "-j", VALID_JSON],
        ["-h", "not a url", "-j", VALID_JSON],
        ["-j", "{not json"],
        ["-j", '{"list_1": ["a"], "list_2": []}'],
        ["-i", "missing-file.json"],
    ],
    ids=[
        "no-payload",
        "both-input-and-json",
        "repeat-below-one",
        "invalid-url",
        "invalid-json",
        "unequal-lists",
        "missing-file",
    ],
)
def test_invalid_arguments_are_rejected(argv: list[str]) -> None:
    with pytest.raises(ValidationError):
        parse_options(argv)
