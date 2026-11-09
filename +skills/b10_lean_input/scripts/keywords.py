"""Frequency keywords for extracted page text.

This is a deterministic count, not a semantic model. It uses the English
stopword list beside this file and the standard library only.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
TITLE_BOOST = 1
MAX_KEYWORDS = 10
MIN_TOKEN_LENGTH = 3

_STOPWORDS = None


def load_stopwords():
    global _STOPWORDS
    if _STOPWORDS is None:
        path = Path(__file__).resolve().parent / "stopwords_en.txt"
        words = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            word = line.split("#", 1)[0].strip().lower()
            if word:
                words.add(word)
        _STOPWORDS = frozenset(words)
    return _STOPWORDS


def tokenize(text):
    if not isinstance(text, str):
        return []
    stopwords = load_stopwords()
    tokens = []
    for match in TOKEN_RE.findall(text.lower()):
        if len(match) < MIN_TOKEN_LENGTH or match in stopwords:
            continue
        tokens.append(match)
    return tokens


def top_keywords(text, title=None, limit=MAX_KEYWORDS):
    """Return up to ``limit`` keywords, highest score first.

    Score is the token count in ``text``, plus ``TITLE_BOOST`` when the same
    token also appears in ``title``. Ties break by keyword, alphabetically.
    An empty or missing text returns an empty list.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    counts = Counter(tokenize(text))
    if not counts:
        return []
    title_tokens = set(tokenize(title or ""))
    ranked = []
    for token, count in counts.items():
        score = count + (TITLE_BOOST if token in title_tokens else 0)
        ranked.append((score, token))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [{"keyword": token, "score": score} for score, token in ranked[:limit]]
