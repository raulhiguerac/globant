from collections.abc import Iterator
from typing import TypeVar

T = TypeVar("T")


def iter_chunks(items: list[T], size: int) -> Iterator[list[T]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]
