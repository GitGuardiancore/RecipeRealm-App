"""Tests for MemoryStore."""
from __future__ import annotations

import tempfile
from pathlib import Path

from alien_terminal.memory.store import MemoryStore, Observation


def _make_obs(category: str = "pattern-seeking", note: str = "test") -> Observation:
    return Observation(
        id=MemoryStore.new_id(),
        signal_source="test",
        signal_headline="test headline",
        category=category,
        confidence=0.8,
        field_note=note,
    )


def test_store_and_retrieve():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(path=Path(tmp) / "test.db")
        obs = _make_obs()
        store.store(obs)
        recent = store.recent(limit=1)
        assert len(recent) == 1
        assert recent[0].id == obs.id


def test_count():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(path=Path(tmp) / "test.db")
        assert store.count() == 0
        store.store(_make_obs())
        store.store(_make_obs())
        assert store.count() == 2


def test_mark_posted():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(path=Path(tmp) / "test.db")
        obs = _make_obs()
        store.store(obs)
        assert store.recent()[0].posted is False
        store.mark_posted(obs.id)
        assert store.recent()[0].posted is True


def test_unposted():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(path=Path(tmp) / "test.db")
        obs1 = _make_obs(note="first")
        obs2 = _make_obs(note="second")
        store.store(obs1)
        store.store(obs2)
        store.mark_posted(obs1.id)
        unposted = store.unposted()
        assert len(unposted) == 1
        assert unposted[0].id == obs2.id


def test_by_category():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(path=Path(tmp) / "test.db")
        store.store(_make_obs(category="fear-response"))
        store.store(_make_obs(category="fear-response"))
        store.store(_make_obs(category="tool-worship"))
        fear = store.by_category("fear-response")
        assert len(fear) == 2
        tool = store.by_category("tool-worship")
        assert len(tool) == 1


def test_recent_ordering():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(path=Path(tmp) / "test.db")
        for i in range(5):
            store.store(_make_obs(note=f"obs_{i}"))
        recent = store.recent(limit=3)
        assert len(recent) == 3
        assert recent[0].field_note == "obs_4"
