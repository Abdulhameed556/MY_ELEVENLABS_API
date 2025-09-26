"""
Text Chunking Utilities for TTS Processing
Enhanced and optimized version of chunk_text
"""

import re
from typing import List


def chunk_text(text: str, max_length: int = 2500) -> List[str]:
    """
    Chunk text into manageable pieces for TTS, respecting sentence boundaries.
    Falls back to word-level or character-level splitting if needed.

    Args:
        text (str): Input text to split
        max_length (int): Maximum characters per chunk

    Returns:
        List[str]: List of text chunks
    """
    if not text:
        return []

    text = text.strip()
    if len(text) <= max_length:
        return [text]

    sentences = split_sentences(text)
    chunks, current = [], ""

    for sentence in sentences:
        if not sentence.strip():
            continue

        if len(current) + len(sentence) + 1 > max_length:
            if current:
                chunks.append(current.strip())
                current = sentence
            else:
                # Handle oversized sentence
                chunks.extend(chunk_by_words(sentence, max_length))
                current = ""
        else:
            current = f"{current} {sentence}".strip()

    if current:
        chunks.append(current.strip())

    return chunks


def split_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex with abbreviation awareness.

    Args:
        text (str): Input text

    Returns:
        List[str]: Sentences
    """
    # Avoid variable-length lookbehind (not supported):
    # iterate and decide splits
    abbreviations = {
        "dr.", "mr.", "mrs.", "ms.", "prof.", "inc.", "ltd.",
        "etc.", "vs.", "e.g.", "i.e.",
    }

    sentences: List[str] = []
    start = 0

    for match in re.finditer(r"([.!?])\s+", text):
        punct_pos = match.start(1)
        punct_char = text[punct_pos]

        # Determine the word immediately before the punctuation
        before = text[start:punct_pos]
        word_match = re.search(r"([A-Za-z]+(?:\.[A-Za-z]+)*)$", before)
        prev_word = word_match.group(0) if word_match else ""
        if punct_char == ".":
            token = (prev_word + ".").lower()
        else:
            token = prev_word.lower()

        # Skip splitting if preceding token is a known abbreviation
        if token in abbreviations:
            continue

        # Commit a sentence ending here
        sentences.append(text[start:punct_pos + 1].strip())
        start = match.end()

    # Remainder
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)

    return sentences


def chunk_by_words(text: str, max_length: int) -> List[str]:
    """
    Split text by words when sentence-based chunking exceeds max_length.

    Args:
        text (str): Input text
        max_length (int): Max allowed chunk size

    Returns:
        List[str]: Word-based chunks
    """
    words = text.split()
    chunks, current = [], ""

    for word in words:
        if len(current) + len(word) + 1 > max_length:
            if current:
                chunks.append(current.strip())
                current = word
            elif len(word) > max_length:
                # Extremely long word fallback
                chunks.extend(force_split_text(word, max_length))
        else:
            current = f"{current} {word}".strip()

    if current:
        chunks.append(current.strip())

    return chunks


def force_split_text(text: str, max_length: int) -> List[str]:
    """
    Force split long words or strings at character-level.

    Args:
        text (str): Input text
        max_length (int): Max allowed chunk size

    Returns:
        List[str]: Character-based chunks
    """
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


def estimate_audio_duration(text: str, words_per_minute: int = 180) -> float:
    """
    Estimate audio duration from text length and reading speed.

    Args:
        text (str): Input text
        words_per_minute (int): Average speaking rate

    Returns:
        float: Duration in seconds
    """
    words = len(text.split())
    return (words / words_per_minute) * 60


def validate_text_for_tts(text: str, max_length: int = 10000) -> bool:
    """
    Validate text suitability for TTS processing.

    Args:
        text (str): Input text
        max_length (int): Maximum allowed length

    Returns:
        bool: Whether text is valid
    """
    if not text or not text.strip():
        return False

    if len(text) > max_length:
        return False

    # Reject if >30% of characters are non-alphanumeric
    special_ratio = sum(
        1 for c in text if not c.isalnum() and not c.isspace()
    ) / len(text)

    return special_ratio <= 0.3
