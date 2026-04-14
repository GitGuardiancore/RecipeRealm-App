"""Tests for Publisher."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from alien_terminal.broadcast.publisher import Publisher
from alien_terminal.composer.writer import Post
from alien_terminal.memory.store import MemoryStore, Observation


def _make_post(obs_id: str = "obs_1") -> Post:
    return Post(
        text="The primates continue.",
        category="pattern-seeking",
        confidence=0.8,
        signal_headline="test",
        observation_id=obs_id,
    )


@pytest.mark.asyncio
async def test_dry_run_marks_posted():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(path=Path(tmp) / "test.db")
        obs = Observation(
            id="obs_1",
            signal_source="test",
            signal_headline="test",
            category="pattern-seeking",
            confidence=0.8,
            field_note="test",
        )
        store.store(obs)
        publisher = Publisher(memory=store, dry_run=True)
        result = await publisher.publish(_make_post("obs_1"))
        assert result.success is True
        assert result.tweet_id == "dry_run"
        assert store.recent()[0].posted is True


@pytest.mark.asyncio
async def test_missing_credentials_returns_error():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(path=Path(tmp) / "test.db")
        obs = Observation(
            id="obs_2",
            signal_source="test",
            signal_headline="test",
            category="pattern-seeking",
            confidence=0.8,
            field_note="test",
        )
        store.store(obs)
        publisher = Publisher(
            memory=store,
            dry_run=False,
            api_key="",
            api_secret="",
            access_token="",
            access_secret="",
        )
        result = await publisher.publish(_make_post("obs_2"))
        assert result.success is False
        assert "credentials" in result.error.lower()
