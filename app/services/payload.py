"""Builds payload outputs while calling the expensive transformer as little as possible."""


def interleave(first: list[str], second: list[str]) -> list[str]:
    """Alternate items: first[0], second[0], first[1], second[1], ..."""
    result: list[str] = []
    for left, right in zip(first, second, strict=True):
        result.append(left)
        result.append(right)
    return result
