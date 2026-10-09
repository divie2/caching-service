"""cache-cli: send a payload to the caching service and print what comes back."""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Self

import httpx
from pydantic import Field, HttpUrl, PrivateAttr, ValidationError, model_validator
from pydantic_settings import BaseSettings, CliApp, CliSettingsSource, SettingsConfigDict

from app.schemas import PayloadCreate

STDIO = "-"


class CliOptions(BaseSettings):
    """Send a payload to the caching service, optionally several times."""

    model_config = SettingsConfigDict(
        # A prefix stops unrelated variables such as OUTPUT or HOST leaking into the options.
        env_prefix="CACHE_CLI_",
        cli_hide_none_type=True,
        cli_shortcuts={"host": "h", "repeat": "r", "input": "i", "json": "j", "output": "o"},
    )

    host: HttpUrl = Field(
        default=HttpUrl("http://localhost:8000"), description="Base URL of the caching service."
    )
    repeat: int = Field(default=1, ge=1, description="How many times to send the payload.")
    input: str | None = Field(
        default=None, description="File holding the payload JSON, or '-' for stdin."
    )
    json_text: str | None = Field(default=None, alias="json", description="Payload JSON inline.")
    output: str = Field(default=STDIO, description="File to write results to, or '-' for stdout.")

    _payload: PayloadCreate = PrivateAttr()

    @model_validator(mode="after")
    def load_payload(self) -> Self:
        if (self.input is None) == (self.json_text is None):
            raise ValueError("pass exactly one of --input/-i or --json/-j")
        self._payload = PayloadCreate.model_validate_json(self._read_payload_text())
        return self

    def _read_payload_text(self) -> str:
        if self.json_text is not None:
            return self.json_text
        if self.input == STDIO:
            return sys.stdin.read()
        try:
            return Path(str(self.input)).read_text(encoding="utf-8")
        except OSError as error:
            raise ValueError(f"cannot read --input file: {error}") from error

    @property
    def payload(self) -> PayloadCreate:
        return self._payload


def parse_options(argv: list[str]) -> CliOptions:
    # The brief gives -h to --host, so help is only offered as --help.
    parser = argparse.ArgumentParser(prog="cache-cli", add_help=False)
    parser.add_argument("--help", action="help", help="Show this help message and exit.")
    source: CliSettingsSource[argparse.ArgumentParser] = CliSettingsSource(
        CliOptions, root_parser=parser
    )
    return CliApp.run(CliOptions, cli_args=argv, cli_settings_source=source)


def send(options: CliOptions, client: httpx.Client) -> list[dict[str, object]]:
    """POST the payload `repeat` times and read back its output, so cache hits are visible."""
    body = options.payload.model_dump()
    results: list[dict[str, object]] = []
    for attempt in range(1, options.repeat + 1):
        started = time.perf_counter()
        created = client.post("/payload", json=body)
        created.raise_for_status()
        payload_id = created.json()["id"]
        fetched = client.get(f"/payload/{payload_id}")
        fetched.raise_for_status()
        results.append(
            {
                "attempt": attempt,
                "status": created.status_code,
                "id": payload_id,
                "seconds": round(time.perf_counter() - started, 3),
                "output": fetched.json()["output"],
            }
        )
    return results


def write_results(results: list[dict[str, object]], output: str) -> None:
    lines = "".join(json.dumps(result) + "\n" for result in results)
    if output == STDIO:
        sys.stdout.write(lines)
    else:
        Path(output).write_text(lines, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    try:
        options = parse_options(sys.argv[1:] if argv is None else argv)
    except ValidationError as error:
        print(f"cache-cli: invalid arguments\n{error}", file=sys.stderr)
        return 2
    try:
        with httpx.Client(base_url=str(options.host)) as client:
            results = send(options, client)
    except httpx.HTTPError as error:
        print(f"cache-cli: request failed: {error}", file=sys.stderr)
        return 1
    write_results(results, options.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
