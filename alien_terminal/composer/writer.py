"""PostComposer: shapes raw field notes into broadcastable posts.

The composer sits between the interpreter and the publisher. It takes
an InterpretedSignal (with its field_note, category, and confidence)
and produces a Post object ready for broadcast.

The composition pipeline:
  1. Trim the field note to 280 characters (X/Twitter limit).
  2. Optionally prepend a signal batch identifier for continuity.
  3. Validate that the post does not contain forbidden patterns
     (emoji, hashtags, exclamation marks, first-person references
     to being an AI).
  4. Return a Post with metadata for the publisher.

Why a separate composer instead of just trimming in the publisher:
the composer is where we enforce the alien's voice constraints AFTER
the LLM has generated text. LLMs occasionally break character. The
composer catches that.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

from alien_terminal.agent.interpreter import InterpretedSignal

log = logging.getLogger(__name__)

POST_MAX_LENGTH = 280

FORBIDDEN_PATTERNS = [
    re.compile(r"[\U0001f600-\U0001f9ff]"),  # emoji
    re.compile(r"#\w+"),                       # hashtags
    re.compile(r"!"),                           # exclamation marks
    re.compile(r"\bI am an AI\b", re.IGNORECASE),
    re.compile(r"\blanguage model\b", re.IGNORECASE),
    re.compile(r"\bI'm an AI\b", re.IGNORECASE),
    re.compile(r"\bAs an AI\b", re.IGNORECASE),
]


@dataclass
class Post:
    """A post ready for broadcast."""

    text: str
    category: str
    confidence: float
    signal_headline: str
    observation_id: str
    composed_at: datetime = field(default_factory=datetime.utcnow)


class PostComposer:
    """Shapes interpreted signals into broadcastable posts."""

    def __init__(self, batch_prefix: bool = True):
        self._batch_counter = 0
        self._batch_prefix = batch_prefix

    def compose(self, interpreted: InterpretedSignal, observation_id: str) -> Post:
        """Compose a post from an interpreted signal."""
        text = interpreted.field_note.strip()
        text = self._sanitize(text)
        text = self._trim(text)

        if self._batch_prefix:
            self._batch_counter += 1

        return Post(
            text=text,
            category=interpreted.category,
            confidence=interpreted.confidence,
            signal_headline=interpreted.signal.headline,
            observation_id=observation_id,
        )

    def _sanitize(self, text: str) -> str:
        """Remove forbidden patterns from the post text."""
        cleaned = text
        for pattern in FORBIDDEN_PATTERNS:
            cleaned = pattern.sub("", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def _trim(text: str) -> str:
        """Trim to 280 characters, breaking at the last sentence boundary."""
        if len(text) <= POST_MAX_LENGTH:
            return text
        truncated = text[:POST_MAX_LENGTH]
        last_period = truncated.rfind(".")
        if last_period > POST_MAX_LENGTH // 2:
            return truncated[:last_period + 1]
        return truncated.rstrip() + "..."

    @staticmethod
    def validate(text: str) -> list[str]:
        """Return a list of validation warnings (empty = clean)."""
        warnings: list[str] = []
        if len(text) > POST_MAX_LENGTH:
            warnings.append(f"exceeds {POST_MAX_LENGTH} chars ({len(text)})")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                warnings.append(f"contains forbidden pattern: {pattern.pattern}")
        return warnings
