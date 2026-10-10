import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from cli.main import REQUEST_TIMEOUT_SECONDS, main, parse_options, send, write_results
from tests.fakes import CountingTransformer


def test_repeated_requests_hit_the_cache_and_reuse_the_id(
    client: TestClient, transformer: CountingTransformer
) -> None:
    options = parse_options(["-r", "3", "-j", '{"list_1": ["a", "b"], "list_2": ["c", "a"]}'])

    results = send(options, client)

    assert [result["status"] for result in results] == [201, 200, 200]
    assert len({result["id"] for result in results}) == 1
    assert all(result["output"] == "A, C, B, A" for result in results)
    assert transformer.calls == ["a", "b", "c"]


def test_results_are_written_as_json_lines_to_a_file(tmp_path: Path) -> None:
    output_file = tmp_path / "results.jsonl"

    write_results([{"attempt": 1, "status": 201}], str(output_file))

    lines = output_file.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [{"attempt": 1, "status": 201}]


def test_main_reports_invalid_arguments_with_exit_code_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["-r", "0", "-j", '{"list_1": [], "list_2": []}'])

    assert exit_code == 2
    assert "invalid arguments" in capsys.readouterr().err


def test_main_waits_longer_than_the_httpx_default_for_slow_transforms(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_server(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": "abc"})
        return httpx.Response(200, json={"output": "A, B"})

    created_clients: list[httpx.Client] = []
    real_client = httpx.Client

    def client_with_fake_server(**kwargs: Any) -> httpx.Client:
        client = real_client(transport=httpx.MockTransport(fake_server), **kwargs)
        created_clients.append(client)
        return client

    monkeypatch.setattr(httpx, "Client", client_with_fake_server)
    output_file = tmp_path / "results.jsonl"

    exit_code = main(["-j", '{"list_1": ["a"], "list_2": ["b"]}', "-o", str(output_file)])

    assert exit_code == 0
    assert created_clients[0].timeout.read == REQUEST_TIMEOUT_SECONDS
    assert json.loads(output_file.read_text(encoding="utf-8"))["output"] == "A, B"
