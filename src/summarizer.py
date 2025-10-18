"""Simple text summarization tailored for earnings reports."""

from __future__ import annotations

import collections
import math
import re
from typing import Iterable, List, Sequence

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
TOKEN_RE = re.compile(r"[A-Za-z0-9$%]+")

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "we",
    "with",
    "will",
}


class Summary:
    """Structured output returned by :func:`summarize_text`."""

    def __init__(self, sentences: Sequence[str], keywords: Sequence[str]) -> None:
        self.sentences = list(sentences)
        self.keywords = list(keywords)

    def format_console(self) -> str:
        """Return a human-readable representation with bullet lists."""
        lines = ["Summary:", ""]
        for idx, sentence in enumerate(self.sentences, start=1):
            lines.append(f"{idx}. {sentence}")

        if self.keywords:
            lines.append("")
            lines.append("Key Terms: " + ", ".join(self.keywords))

        return "\n".join(lines)


def tokenize(text: str) -> List[str]:
    """Tokenize the input, emitting lowercase alphanumeric words."""
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def sentence_scores(sentences: Iterable[str]) -> List[float]:
    """Rank sentences via a naive TF-IDF heuristic."""
    sentence_list = list(sentences)
    tokenized = [tokenize(sentence) for sentence in sentence_list]

    doc_freq: collections.Counter[str] = collections.Counter()
    for tokens in tokenized:
        doc_freq.update(set(t for t in tokens if t not in STOPWORDS))

    total_docs = len(sentence_list) or 1
    scores: List[float] = []
    for tokens in tokenized:
        score = 0.0
        counts = collections.Counter(t for t in tokens if t not in STOPWORDS)
        for token, freq in counts.items():
            idf = math.log((total_docs + 1) / (1 + doc_freq[token])) + 1.0
            score += freq * idf
        scores.append(score)
    return scores


def top_keywords(text: str, *, limit: int = 8) -> List[str]:
    """Return frequently occurring tokens as keywords."""
    counts = collections.Counter(t for t in tokenize(text) if t not in STOPWORDS)
    most_common = [token for token, _ in counts.most_common(limit)]
    return most_common


def summarize_text(text: str, *, sentence_limit: int = 5) -> Summary:
    """Produce a bullet list summary of the provided text."""
    sentences = [
        sentence.strip()
        for sentence in SENTENCE_SPLIT_RE.split(text)
        if sentence and len(sentence.split()) > 3
    ]

    if not sentences:
        return Summary(sentences=[], keywords=[])

    scores = sentence_scores(sentences)
    ranked = sorted(
        zip(sentences, scores),
        key=lambda pair: pair[1],
        reverse=True,
    )
    top_sentences = [sentence for sentence, _ in ranked[:sentence_limit]]
    keywords = top_keywords(text)

    # Preserve original order for readability.
    sentence_order = {sentence: idx for idx, sentence in enumerate(sentences)}
    ordered_unique: List[str] = []
    for sentence in sorted(
        top_sentences, key=lambda s: sentence_order.get(s, float("inf"))
    ):
        if sentence not in ordered_unique:
            ordered_unique.append(sentence)

    return Summary(sentences=ordered_unique, keywords=keywords)
