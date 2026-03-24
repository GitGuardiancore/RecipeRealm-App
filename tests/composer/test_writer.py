"""Tests for PostComposer."""
from __future__ import annotations

from alien_terminal.agent.interpreter import InterpretedSignal
from alien_terminal.composer.writer import PostComposer
from alien_terminal.signals.interceptor import Signal


def _make_interpreted(note: str = "The primates continue.") -> InterpretedSignal:
    return InterpretedSignal(
        signal=Signal(source="test", headline="test", summary="test"),
        category="pattern-seeking",
        confidence=0.8,
        field_note=note,
    )


def test_compose_returns_post():
    composer = PostComposer(batch_prefix=False)
    post = composer.compose(_make_interpreted(), "obs_1")
    assert post.text == "The primates continue."
    assert post.observation_id == "obs_1"


def test_compose_trims_long_text():
    long_note = "x" * 300
    composer = PostComposer(batch_prefix=False)
    post = composer.compose(_make_interpreted(long_note), "obs_1")
    assert len(post.text) <= 280


def test_compose_trims_at_sentence_boundary():
    note = "First sentence. " + "x" * 300
    composer = PostComposer(batch_prefix=False)
    post = composer.compose(_make_interpreted(note), "obs_1")
    assert post.text.endswith(".")


def test_sanitize_removes_emoji():
    composer = PostComposer(batch_prefix=False)
    cleaned = composer._sanitize("The primates 🤔 continue.")
    assert "🤔" not in cleaned


def test_sanitize_removes_hashtags():
    composer = PostComposer(batch_prefix=False)
    cleaned = composer._sanitize("The primates #aliens continue.")
    assert "#aliens" not in cleaned


def test_sanitize_removes_exclamation():
    composer = PostComposer(batch_prefix=False)
    cleaned = composer._sanitize("Alarming! The primates continue.")
    assert "!" not in cleaned


def test_validate_clean_text():
    warnings = PostComposer.validate("The primates continue their rituals.")
    assert warnings == []


def test_validate_catches_length():
    warnings = PostComposer.validate("x" * 300)
    assert any("280" in w for w in warnings)


def test_validate_catches_ai_reference():
    warnings = PostComposer.validate("I am an AI observing humans.")
    assert len(warnings) > 0
