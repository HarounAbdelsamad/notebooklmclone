"""Token counting / splitting via tiktoken (cl100k_base is a good generic proxy)."""

from functools import lru_cache

import tiktoken


@lru_cache
def _encoding() -> "tiktoken.Encoding":
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoding().encode(text))


def encode(text: str) -> list[int]:
    return _encoding().encode(text)


def decode(tokens: list[int]) -> str:
    return _encoding().decode(tokens)
