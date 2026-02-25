"""Tests for SignalInterpreter using a stubbed LLM client."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from alien_terminal.agent.interpreter import SignalInterpreter
from alien_terminal.memory.store import MemoryStore
from alien_terminal.signals.interceptor import Signal


@pytest.fixture
def memory():
    with tempfile.TemporaryDirectory() as tmp:
        yield MemoryStore(path=Path(tmp) / "test.db")


@pytest.fixture
def stub_client():
    client = AsyncMock()
    client.chat = AsyncMock(return_value=(
        '{"category": "territorial-display", "confidence": 0.85, '
        '"field_note": "The surface population appears to be engaged in '
        'another territorial boundary dispute."}'
    ))
    return client


@pytest.fixture
def sample_signal():
    return Signal(
        source="https://example.com/rss",
        headline="Country X deploys troops near border",
        summary="Military buildup reported along disputed territory.",
    )


@pytest.mark.asyncio
async def test_interpret_returns_structured_result(stub_client, memory, sample_signal):
    interpreter = SignalInterpreter(client=stub_client, memory=memory)
    result = await interpreter.interpret(sample_signal)
    assert result.category == "territorial-display"
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.field_note) > 0


@pytest.mark.asyncio
async def test_interpret_falls_back_on_bad_json(memory, sample_signal):
    client = AsyncMock()
    client.chat = AsyncMock(return_value="this is not json at all")
    interpreter = SignalInterpreter(client=client, memory=memory)
    result = await interpreter.interpret(sample_signal)
    assert result.category == "pattern-seeking"
    assert result.confidence == 0.5


@pytest.mark.asyncio
async def test_interpret_clamps_confidence(memory, sample_signal):
    client = AsyncMock()
    client.chat = AsyncMock(return_value=(
        '{"category": "fear-response", "confidence": 5.0, '
        '"field_note": "High anxiety detected."}'
    ))
    interpreter = SignalInterpreter(client=client, memory=memory)
    result = await interpreter.interpret(sample_signal)
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_interpret_normalizes_unknown_category(memory, sample_signal):
    client = AsyncMock()
    client.chat = AsyncMock(return_value=(
        '{"category": "unknown-thing", "confidence": 0.5, '
        '"field_note": "Something happened."}'
    ))
    interpreter = SignalInterpreter(client=client, memory=memory)
    result = await interpreter.interpret(sample_signal)
    assert result.category == "pattern-seeking"
