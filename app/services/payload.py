"""Builds payload outputs while calling the expensive transformer as little as possible."""

from sqlmodel import Session, col, select

from app.models import TransformCache
from app.transformer import Transformer


def interleave(first: list[str], second: list[str]) -> list[str]:
    """Alternate items: first[0], second[0], first[1], second[1], ..."""
    result: list[str] = []
    for left, right in zip(first, second, strict=True):
        result.append(left)
        result.append(right)
    return result


def transform_with_cache(
    session: Session, values: list[str], transformer: Transformer
) -> dict[str, str]:
    """Return each distinct value's output, calling the transformer only for cache misses."""
    distinct = list(dict.fromkeys(values))

    cached_rows = session.exec(
        select(TransformCache).where(col(TransformCache.input).in_(distinct))
    ).all()
    outputs = {row.input: row.output for row in cached_rows}

    misses = [value for value in distinct if value not in outputs]
    for value in misses:
        output = transformer(value)
        session.add(TransformCache(input=value, output=output))
        outputs[value] = output

    session.commit()
    return outputs
