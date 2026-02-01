"""SignalInterpreter: processes intercepted signals through the alien
cognitive framework.

The interpreter takes a raw Signal (a headline, a trending topic, a news
snippet) and produces an alien interpretation: a classified observation
with a cognitive category, a confidence level, and a raw text response
that the PostComposer will later trim into a broadcast.

The interpretation pipeline:
  1. Build the message list: system prompt, memory context (recent
     observations as "previous field notes"), and the new signal.
  2. Call the LLM for a structured response: category, confidence,
     and the field note text.
  3. Parse the response into an InterpretedSignal.

Memory context is critical. Without it, the alien has no continuity
between observations. The memory window is configurable but defaults
to the 10 most recent observations — enough to maintain running
theories without blowing the context budget.

The interpreter does NOT post. It produces structured data that the
composer and publisher handle downstream. This separation exists so
the same interpreter can feed a dashboard, a log file, or a social
media account without changes.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

from alien_terminal.agent.persona import ALIEN_PERSONA, COGNITIVE_CATEGORIES, Persona
from alien_terminal.clients.llm_client import LLMClient
from alien_terminal.memory.store import MemoryStore, Observation
from alien_terminal.signals.interceptor import Signal

log = logging.getLogger(__name__)

MEMORY_WINDOW = 10


@dataclass
class InterpretedSignal:
    """The alien's interpretation of a single intercepted signal."""

    signal: Signal
    category: str
    confidence: float
    field_note: str
    interpreted_at: datetime = field(default_factory=datetime.utcnow)


class SignalInterpreter:
    """Processes signals through the alien cognitive framework."""

    def __init__(
        self,
        client: LLMClient,
        memory: MemoryStore,
        persona: Persona = ALIEN_PERSONA,
        memory_window: int = MEMORY_WINDOW,
    ):
        self.client = client
        self.memory = memory
        self.persona = persona
        self.memory_window = memory_window

    async def interpret(self, signal: Signal) -> InterpretedSignal:
        """Interpret a signal and return the structured observation."""
        messages = self._build_messages(signal)
        raw = await self.client.chat(messages, max_tokens=600)
        parsed = self._parse_response(raw, signal)
        log.info(
            "interpreted signal=%r category=%s confidence=%.2f",
            signal.headline[:50],
            parsed.category,
            parsed.confidence,
        )
        return parsed

    def _build_messages(self, signal: Signal) -> list[dict]:
        recent = self.memory.recent(limit=self.memory_window)
        messages: list[dict] = [
            {"role": "system", "content": self.persona.system_prompt},
        ]

        if recent:
            notes = "\n".join(
                f"[{obs.category}] {obs.field_note}" for obs in recent
            )
            messages.append({
                "role": "user",
                "content": (
                    f"Your recent field notes for context. Do not repeat "
                    f"these — they are here so you can reference patterns "
                    f"or contradictions:\n\n{notes}"
                ),
            })

        categories_str = ", ".join(COGNITIVE_CATEGORIES)
        messages.append({
            "role": "user",
            "content": (
                f"New intercepted signal from the surface population:\n\n"
                f'Source: {signal.source}\n'
                f'Headline: "{signal.headline}"\n'
                f'Summary: "{signal.summary}"\n\n'
                f"{self.persona.interpretation_hint}\n\n"
                f"Respond with a JSON object containing:\n"
                f'- "category": one of [{categories_str}]\n'
                f'- "confidence": float 0.0-1.0, how confident you are '
                f"in the categorization\n"
                f'- "field_note": your observation, 1-3 sentences, '
                f"following the post style rules\n\n"
                f"Respond ONLY with the JSON object. No preamble. No "
                f"markdown fences."
            ),
        })

        return messages

    def _parse_response(self, raw: str, signal: Signal) -> InterpretedSignal:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            log.warning("failed to parse interpreter response, using fallback")
            return InterpretedSignal(
                signal=signal,
                category="pattern-seeking",
                confidence=0.5,
                field_note=cleaned[:280],
            )

        category = data.get("category", "pattern-seeking")
        if category not in COGNITIVE_CATEGORIES:
            category = "pattern-seeking"

        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        return InterpretedSignal(
            signal=signal,
            category=category,
            confidence=confidence,
            field_note=str(data.get("field_note", ""))[:280],
        )
