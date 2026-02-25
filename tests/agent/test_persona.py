"""Tests for persona definitions."""
from __future__ import annotations

from alien_terminal.agent.persona import (
    ALIEN_PERSONA,
    COGNITIVE_CATEGORIES,
)


def test_persona_has_id():
    assert ALIEN_PERSONA.id == "observer"


def test_persona_system_prompt_forbids_ai_references():
    prompt = ALIEN_PERSONA.system_prompt
    assert "NEVER acknowledge being an AI" in prompt


def test_persona_demands_third_person():
    prompt = ALIEN_PERSONA.system_prompt
    assert "third person" in prompt.lower()


def test_persona_forbids_emoji():
    prompt = ALIEN_PERSONA.system_prompt
    assert "NOT use emoji" in prompt


def test_persona_forbids_hashtags():
    prompt = ALIEN_PERSONA.system_prompt
    assert "NOT use hashtags" in prompt


def test_cognitive_categories_are_nonempty():
    assert len(COGNITIVE_CATEGORIES) > 0
    for cat in COGNITIVE_CATEGORIES:
        assert isinstance(cat, str)
        assert "-" in cat  # all categories use kebab-case


def test_post_style_hint_exists():
    assert len(ALIEN_PERSONA.post_style_hint) > 50
