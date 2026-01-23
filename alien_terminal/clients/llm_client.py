"""LLMClient: async wrapper over the Anthropic or OpenAI HTTP API.

The agent needs one capability from the LLM: chat completions with a
system prompt and a message history. No streaming, no tool use, no
vision. The client is deliberately thin — it wraps the HTTP call, handles
retries on transient errors, and returns the text content.

The default backend is Anthropic (Claude). An OpenAI fallback exists for
testing and for users who only have an OpenAI key. The interpreter and
composer do not care which backend is in use; the prompts are tuned for
both.

Models in use:
  - Anthropic: claude-sonnet-4-20250514 (default, good balance of cost and quality)
  - OpenAI: gpt-4o-mini (fallback, cheaper but slightly less consistent
    at maintaining the alien voice over long memory contexts)
"""
from __future__ import annotations

import asyncio
import logging
import os

import httpx

log = logging.getLogger(__name__)


class LLMClient:
    """Async client for LLM chat completions."""

    def __init__(
        self,
        backend: str = "anthropic",
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        self.backend = backend.lower()
        if self.backend == "anthropic":
            self._key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            self._base_url = "https://api.anthropic.com/v1"
            self.model = model or "claude-sonnet-4-20250514"
        elif self.backend == "openai":
            self._key = api_key or os.environ.get("OPENAI_API_KEY")
            self._base_url = "https://api.openai.com/v1"
            self.model = model or "gpt-4o-mini"
        else:
            raise ValueError(f"unknown backend: {backend}")

        if not self._key:
            env_var = "ANTHROPIC_API_KEY" if self.backend == "anthropic" else "OPENAI_API_KEY"
            raise RuntimeError(f"{env_var} not set")

        self.timeout = timeout
        self.max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        if self.backend == "anthropic":
            return {
                "x-api-key": self._key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
        return {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[dict],
        max_tokens: int = 400,
    ) -> str:
        """Send a chat completion and return the assistant text."""
        if self.backend == "anthropic":
            return await self._chat_anthropic(messages, max_tokens)
        return await self._chat_openai(messages, max_tokens)

    async def _chat_anthropic(self, messages: list[dict], max_tokens: int) -> str:
        system = ""
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                api_messages.append(msg)

        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": api_messages,
        }
        if system:
            body["system"] = system

        return await self._post(
            f"{self._base_url}/messages",
            body,
            extract=lambda data: data["content"][0]["text"].strip(),
        )

    async def _chat_openai(self, messages: list[dict], max_tokens: int) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        return await self._post(
            f"{self._base_url}/chat/completions",
            body,
            extract=lambda data: data["choices"][0]["message"]["content"].strip(),
        )

    async def _post(self, url: str, body: dict, extract) -> str:
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as http:
                    resp = await http.post(url, json=body, headers=self._headers())
                    resp.raise_for_status()
                    return extract(resp.json())
            except httpx.HTTPStatusError as exc:
                last_err = exc
                if exc.response.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_err = exc
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"LLM call failed after {self.max_retries} retries") from last_err
