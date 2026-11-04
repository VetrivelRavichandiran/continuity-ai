"""Shared text utilities."""
import re

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "by", "at", "is", "are", "was", "were", "be", "been", "it", "its", "as",
    "that", "this", "from", "not", "no", "but", "if", "then", "than", "so",
    "such", "into", "over", "under", "after", "before", "between", "during",
    "about", "up", "out", "we", "our", "their", "his", "her", "they",
    "status", "notes", "owner", "due", "date",
}


def significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words
            if w not in STOPWORDS and len(w) > 2 and not re.fullmatch(r"\d{4}", w)}