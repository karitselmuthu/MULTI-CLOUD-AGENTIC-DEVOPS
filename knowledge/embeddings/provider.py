"""Embedding interface and deterministic offline implementation."""

import hashlib
import math
import re
from typing import Protocol


VECTOR_SIZE = 128
WORDS = re.compile(r"[a-z0-9][a-z0-9_-]*")


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed(self, text: str) -> list[float]: ...


class LocalHashEmbedding:
    """Repeatable lexical vector for local tests; not a semantic model."""

    dimensions = VECTOR_SIZE

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in WORDS.findall(text.lower()):
            digest = hashlib.sha256(word.encode()).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            vector[index] += 1.0
        length = math.sqrt(sum(item * item for item in vector))
        return [item / length for item in vector] if length else vector
