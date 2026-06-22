"""Text cleaning and spam filtering."""

from __future__ import annotations

import html
import re

MIN_TEXT_LENGTH = 10
MAX_REPEAT_CHAR_RUN = 8

URL_ONLY_PATTERN = re.compile(r"^https?://\S+$", re.IGNORECASE)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
REPEAT_CHAR_PATTERN = re.compile(r"(.)\1{" + str(MAX_REPEAT_CHAR_RUN) + r",}")


def strip_html(text: str) -> str:
    unescaped = html.unescape(text)
    without_tags = HTML_TAG_PATTERN.sub(" ", unescaped)
    return re.sub(r"\s+", " ", without_tags).strip()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def is_spam(text: str) -> bool:
    cleaned = normalize_whitespace(text)
    if len(cleaned) < MIN_TEXT_LENGTH:
        return True
    if URL_ONLY_PATTERN.match(cleaned):
        return True
    if REPEAT_CHAR_PATTERN.search(cleaned):
        return True
    alpha_count = sum(1 for char in cleaned if char.isalpha())
    if alpha_count < 5:
        return True
    return False


def clean_text(text: str) -> str:
    return normalize_whitespace(strip_html(text))


def is_valid_review_text(text: str) -> bool:
    cleaned = clean_text(text)
    return not is_spam(cleaned)
