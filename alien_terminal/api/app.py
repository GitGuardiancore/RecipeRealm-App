"""FastAPI app for the Alien Terminal dashboard.

Endpoints:
  GET  /health                          ping
  GET  /observations/recent?limit=20    recent observations with metadata
  GET  /observations/category/{cat}     observations by cognitive category
  GET  /observations/stats              category distribution and totals
  POST /signals/inject                  manually inject a signal for testing
  POST /cycle/run                       trigger one observe-interpret-post cycle

The dashboard is a monitoring tool, not a user-facing product. It exists
so the operator can see what the alien is observing, how it categorizes
signals, and whether posts are being delivered successfully.

The /cycle/run endpoint triggers a single cycle manually. In production
the cycle runs on a cron schedule (every 2-4 hours). The endpoint exists
for testing and for manual overrides when the operator wants the alien
to say something about a specific event.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from alien_terminal._version import __version__
from alien_terminal.agent.interpreter import SignalInterpreter
from alien_terminal.broadcast.publisher import Publisher
from alien_terminal.clients.llm_client import LLMClient
from alien_terminal.composer.writer import PostComposer
from alien_terminal.memory.store import MemoryStore, Observation
from alien_terminal.signals.interceptor import SignalInterceptor

log = logging.getLogger(__name__)


class InjectRequest(BaseModel):
    headline: str = Field(..., min_length=1, max_length=500)
    summary: str = Field(default="", max_length=1000)
    source: str = Field(default="manual")


class CycleResult(BaseModel):
    signals_found: int
    interpreted: int
    posted: int
    errors: list[str]


def create_app(
    db_path: Path | str = "alien_terminal.db",
    dry_run: bool = True,
    llm_backend: str = "anthropic",
) -> FastAPI:
    """Build the FastAPI app with wired dependencies."""
    app = FastAPI(title="alien-terminal", version=__version__)
    memory = MemoryStore(path=db_path)
    interceptor = SignalInterceptor()
    composer = PostComposer()
    publisher = Publisher(memory=memory, dry_run=dry_run)

    _client: LLMClient | None = None

    def _get_client() -> LLMClient:
        nonlocal _client
        if _client is None:
            _client = LLMClient(backend=llm_backend)
        return _client

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__, "observations": memory.count()}

    @app.get("/observations/recent")
    async def recent(limit: int = 20) -> list[dict]:
        obs = memory.recent(limit=limit)
        return [_obs_to_dict(o) for o in obs]

    @app.get("/observations/category/{category}")
    async def by_category(category: str, limit: int = 20) -> list[dict]:
        obs = memory.by_category(category, limit=limit)
        return [_obs_to_dict(o) for o in obs]

    @app.get("/observations/stats")
    async def stats() -> dict:
        from alien_terminal.agent.persona import COGNITIVE_CATEGORIES
        result = {}
        for cat in COGNITIVE_CATEGORIES:
            result[cat] = len(memory.by_category(cat, limit=1000))
        return {"total": memory.count(), "by_category": result}

    @app.post("/signals/inject")
    async def inject(req: InjectRequest) -> dict:
        signal = interceptor.inject(
            headline=req.headline, summary=req.summary, source=req.source
        )
        interpreter = SignalInterpreter(client=_get_client(), memory=memory)
        interpreted = await interpreter.interpret(signal)
        obs_id = MemoryStore.new_id()
        observation = Observation(
            id=obs_id,
            signal_source=signal.source,
            signal_headline=signal.headline,
            category=interpreted.category,
            confidence=interpreted.confidence,
            field_note=interpreted.field_note,
        )
        memory.store(observation)
        post = composer.compose(interpreted, obs_id)
        result = await publisher.publish(post)
        return {
            "observation_id": obs_id,
            "category": interpreted.category,
            "field_note": interpreted.field_note,
            "published": result.success,
            "tweet_id": result.tweet_id,
        }

    @app.post("/cycle/run", response_model=CycleResult)
    async def run_cycle() -> CycleResult:
        errors: list[str] = []
        signals = await interceptor.scan(max_per_feed=3)
        interpreter = SignalInterpreter(client=_get_client(), memory=memory)

        interpreted_count = 0
        posted_count = 0

        for signal in signals[:5]:
            try:
                interpreted = await interpreter.interpret(signal)
                obs_id = MemoryStore.new_id()
                observation = Observation(
                    id=obs_id,
                    signal_source=signal.source,
                    signal_headline=signal.headline,
                    category=interpreted.category,
                    confidence=interpreted.confidence,
                    field_note=interpreted.field_note,
                )
                memory.store(observation)
                interpreted_count += 1

                post = composer.compose(interpreted, obs_id)
                result = await publisher.publish(post)
                if result.success:
                    posted_count += 1
                elif result.error:
                    errors.append(result.error)
            except Exception as exc:  # noqa: BLE001
                log.exception("cycle error for signal=%s", signal.headline[:50])
                errors.append(str(exc))

        return CycleResult(
            signals_found=len(signals),
            interpreted=interpreted_count,
            posted=posted_count,
            errors=errors,
        )

    return app


def _obs_to_dict(obs: Observation) -> dict:
    return {
        "id": obs.id,
        "signal_source": obs.signal_source,
        "signal_headline": obs.signal_headline,
        "category": obs.category,
        "confidence": obs.confidence,
        "field_note": obs.field_note,
        "posted": obs.posted,
        "created_at": obs.created_at.isoformat(),
    }
