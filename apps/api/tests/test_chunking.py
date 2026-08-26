from itertools import pairwise

import pytest

from app.processing.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_returns_single_chunk():
    text = "This is a short BHEL document."
    chunks = chunk_text(text, chunk_size=1000, overlap=150)
    assert chunks == [text]


def test_long_text_splits_into_multiple_chunks_with_overlap():
    paragraphs = [f"Paragraph {i}. " + ("BHEL manufactures heavy electrical equipment. " * 5) for i in range(20)]
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, chunk_size=500, overlap=100)

    assert len(chunks) > 1
    # every chunk after the first should share a real overlap with the
    # tail of the previous chunk, not just coincidentally similar text
    for prev, curr in pairwise(chunks):
        tail = prev[-100:]
        assert tail in curr or tail[:50] in curr


def test_no_chunk_exceeds_chunk_size():
    text = "\n\n".join(f"Sentence number {i} in a BHEL technical report about turbines and boilers." for i in range(200))
    chunks = chunk_text(text, chunk_size=300, overlap=80)
    assert all(len(c) <= 300 for c in chunks)


def test_oversized_single_paragraph_is_split():
    huge_paragraph = "BHEL " * 5000  # one giant "paragraph", no blank lines at all
    chunks = chunk_text(huge_paragraph, chunk_size=1000, overlap=100)
    assert len(chunks) > 1
    assert all(len(c) <= 1000 for c in chunks)
    # reassembling should not lose the actual words (allowing for the
    # overlap duplication and our whitespace joins)
    assert "".join(chunks).count("BHEL") >= 5000


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=100, overlap=100)
