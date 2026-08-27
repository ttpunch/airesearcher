"""Splits extracted document text into overlapping passages for embedding.

Paragraph-aware: prefers to break on blank lines (and falls back to
sentence boundaries for an over-long paragraph) rather than slicing at a
fixed character offset mid-word, since the resulting chunk is what a
citation actually points to and quotes — it should read like a real
passage, not an arbitrary substring.
"""

import re

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 150

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _split_oversized(paragraph: str, chunk_size: int) -> list[str]:
    """A single paragraph longer than chunk_size gets split on sentence
    boundaries; a single sentence longer than chunk_size is hard-sliced
    as a last resort.
    """
    if len(paragraph) <= chunk_size:
        return [paragraph]

    pieces: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(paragraph):
        if len(sentence) <= chunk_size:
            pieces.append(sentence)
        else:
            pieces.extend(sentence[i : i + chunk_size] for i in range(0, len(sentence), chunk_size))
    return pieces


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[str]:
    """Returns non-empty, order-preserved chunks, each carrying `overlap`
    characters of context from the tail of the previous chunk (chunks
    after the first only).
    """
    if not text or not text.strip():
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    segments: list[str] = []
    for paragraph in _split_paragraphs(text):
        segments.extend(_split_oversized(paragraph, chunk_size))

    chunks: list[str] = []
    current = ""
    for segment in segments:
        candidate = f"{current}\n\n{segment}" if current else segment
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        chunks.append(current)
        tail = current[-overlap:] if overlap else ""
        # Every segment is already <= chunk_size (via _split_oversized), so
        # this is the only place a chunk could exceed chunk_size — only
        # keep the overlap tail if it still fits, to keep chunk_size a
        # real hard cap rather than a rough target.
        current = f"{tail}\n\n{segment}" if tail and len(tail) + 2 + len(segment) <= chunk_size else segment

    if current:
        chunks.append(current)

    return chunks
