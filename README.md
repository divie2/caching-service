# Caching Service

A FastAPI microservice that builds an interleaved output from two lists of strings, passing every
string through a slow, costly **transformer**. The transformer stands in for an external service.
The service is designed to **call the transformer as few times as possible**. It ships with a
command-line client, `cache-cli`.

```
POST /payload  {"list_1": ["first string", "second string"], "list_2": ["other string", "another string"]}
→ 201 {"id": "1d13a539-..."}

GET /payload/1d13a539-...
→ 200 {"output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING"}
```

## How the transformer calls are kept to a minimum

There are three levels of saving, and each is covered by tests that count transformer calls with
a fake:

1. **Within a request:** strings are deduplicated across both lists, so `["a", "a"]` + `["a", "b"]`
   makes two calls, not four.
2. **Across requests:** every result is cached in the `transformcache` table (`input → output`,
   with `input` as the primary key). Each request does **one** bulk `WHERE input IN (...)` lookup
   and calls the transformer only for the misses.
3. **Identical requests:** each payload stores a SHA-256 hash of its inputs in a unique column.
   A repeated request returns the existing id with **zero** transformer calls and no new row.

**Concurrent requests** are handled with the unique constraints, not check-then-insert:

- If two requests insert the same **payload** hash, the loser catches `IntegrityError`, rolls back,
  and returns the winner's row, so both callers get the same id.
- If two requests insert the same **cache** row, the loser rolls back and carries on with its own
  result. That result is identical, because the transformer is deterministic.
- Cache rows are committed one at a time, so a conflict on one string never discards the others.

This was checked against Postgres with ten simultaneous identical requests: one `201`, nine `200`,
a single id, and no errors.

## Running it

Requirements: Python 3.12 and [uv](https://docs.astral.sh/uv/), or Docker.

### Locally

```bash
uv sync
TRANSFORMER_DELAY_SECONDS=1 uv run uvicorn app.main:app
```

Interactive API docs are served at http://localhost:8000/docs.

### With Docker (SQLite)

```bash
docker compose up --build
```

The SQLite file is kept in a named volume, so cached results survive restarts.

### With Docker (Postgres)

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

The override file adds a Postgres container and changes **only** `DATABASE_URL` for the API.

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./cache.db` (Docker: `sqlite:////data/cache.db`) | Any SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@host/db` |
| `TRANSFORMER_DELAY_SECONDS` | `0` locally, `1` in docker-compose | Simulated latency per transformer call |

## API

| Method | Path | Success | Errors |
|---|---|---|---|
| `POST` | `/payload` | `201 {"id"}` for a new payload, `200 {"id"}` when the same inputs were sent before | `422` invalid body (missing list, non-string item, lists of different lengths) |
| `GET` | `/payload/{id}` | `200 {"output"}` | `404` unknown id, `422` malformed id |

## CLI: `cache-cli`

```
cache-cli [-h|--host URL] [-r|--repeat N] [-i|--input FILE|-] [-j|--json JSON] [-o|--output FILE|-] [--help]
```

```bash
# Send the same payload three times: the first call is slow (201), the rest hit the cache (200, same id).
uv run cache-cli -r 3 -j '{"list_1": ["first string", "second string"], "list_2": ["other string", "another string"]}'

# Read the payload from a file or stdin, and write the results to a file.
uv run cache-cli -i payload.json -o results.jsonl
echo '{"list_1": ["a"], "list_2": ["b"]}' | uv run cache-cli -i -
```

The CLI prints one JSON line per attempt: `attempt`, `status`, `id`, `seconds` and `output`.
All arguments are parsed and validated by a pydantic-settings model before anything is sent:
`--repeat` must be at least 1, `--host` must be a valid URL, exactly one of `--input`/`--json` is
required, and the JSON must parse into two lists of equal length. The exit code is `2` for invalid
arguments and `1` for HTTP errors.

**`-h` is host, not help.** The brief lists `-h` for both `--host` and `--help`. I kept `-h` for
`--host`, as specified, and offer help only as `--help`. pydantic-settings adds `-h/--help`
automatically, which conflicts with `-h` for host. So the CLI gives pydantic-settings a root parser
that only defines `--help`. pydantic-settings still defines, parses and validates every option.

## Design decisions

- **Transformer = `str.upper()`**, inferred from the sample output. It is injected as a dependency
  (`Callable[[str], str]`), so tests swap in a fake that counts calls. A configurable delay
  simulates the external service.
- **The payload id is a random UUID**, and the input hash is used only for deduplication. The id
  then reveals nothing about the input, and the hashing could change without changing ids. Using
  the hash itself as the id would also work.
- **The hash is SHA-256 of `json.dumps([list_1, list_2])`.** JSON quotes every string, so
  `["a, b"] + ["c"]` and `["a"] + ["b, c"]` can't collide, as they would with a comma join. The
  lists are not sorted, because order changes the output.
- **The output is stored, not recomputed,** so `GET` never touches the transformer.
- **Empty lists are allowed** and produce an empty output `""`. They meet the brief's only rule
  (equal lengths), and the result is well defined.
- **The business logic lives in `app/services/payload.py`.** Routes only translate between HTTP
  and the service (`created` → `201`/`200`, `None` → `404`).
- **The CLI reuses the API's `PayloadCreate` schema** for validation, so the equal-length rule
  lives in one place. A CLI distributed separately would carry its own copy.

## Shortcuts and what I would do next

- **No migrations:** tables are created at startup with `create_all`. A real deployment would use
  Alembic.
- **No authentication or rate limiting.**
- **Per-row cache commits** cost one round-trip per new string. In production I would use
  `INSERT ... ON CONFLICT DO NOTHING`, which is dialect-specific in SQLAlchemy, so I avoided it to
  keep SQLite and Postgres on the same code path.
- **The transformer is called once per string, sequentially.** A real remote service would
  benefit from batching or concurrent calls for the misses.
- **No size limits** on the lists or strings.
- If two requests race on a new payload, the loser may already have paid for transformer calls.
  That is rare, the results stay in the cache, and avoiding it would need locking on every request.

## Development

```bash
uv run pytest                                      # unit + integration tests
uv run ruff check . && uv run ruff format --check .
uv run mypy app cli                                # strict mode
```

```
app/
  main.py              app factory + lifespan (engine, tables, transformer)
  config.py            settings from environment variables
  db.py                engine construction
  models.py            TransformCache and Payload tables
  schemas.py           request/response bodies and validation
  transformer.py       the stand-in external service
  services/payload.py  dedupe → cache lookup → transform misses → interleave → store
  api/                 dependencies and routes (thin HTTP layer)
cli/main.py            cache-cli
tests/unit/            pure logic, the service with a call-counting fake, schemas, CLI options
tests/integration/     HTTP round trips with TestClient, and the CLI end to end
```
