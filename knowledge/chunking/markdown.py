"""Bounded Markdown chunks with stable offsets and section labels."""

import re
from dataclasses import dataclass


HEADING = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class MarkdownChunk:
    index: int
    start: int
    end: int
    heading: str
    text: str


def chunk_markdown(content: str, *, size: int = 1200, overlap: int = 120) -> tuple[MarkdownChunk, ...]:
    if not 1 <= size <= 4000 or not 0 <= overlap < size:
        raise ValueError("invalid chunk size or overlap")
    headings = list(HEADING.finditer(content))
    chunks: list[MarkdownChunk] = []
    start = 0
    while start < len(content):
        end = min(start + size, len(content))
        heading = next((match.group(1).strip() for match in reversed(headings)
                        if match.start() <= start), "Document")
        chunks.append(MarkdownChunk(len(chunks), start, end, heading, content[start:end]))
        if end == len(content):
            break
        start = end - overlap
    return tuple(chunks)
