# alien-terminal

> An autonomous AI agent that roleplays as an extraterrestrial intelligence observing humanity.

[![python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](#)
[![license MIT](https://img.shields.io/badge/license-MIT-green.svg)](#)

An alien xenobiologist has been monitoring Earth's electromagnetic emissions for roughly 200 orbital periods. It intercepts human signals — news headlines, trending topics, RSS feeds — and interprets them through a non-human cognitive framework. The result is a stream of field notes posted to X/Twitter: clinical observations about a species the alien finds fascinating, contradictory, and occasionally alarming.

The agent is not a chatbot. It does not respond to mentions or hold conversations. It observes, categorizes, and broadcasts. It develops running theories about human behavior over time, referencing earlier observations and building a narrative across posts.

## How it works

The agent runs a cycle on a configurable schedule (default: every 2-4 hours):

1. **Intercept.** The signal interceptor scans RSS feeds and extracts new headlines.
2. **Interpret.** Each signal is processed through the alien cognitive framework — an LLM call with the alien persona prompt and the agent's recent memory context. The interpreter classifies the signal into a behavioral category (territorial-display, resource-hoarding, mating-signal, pack-hierarchy, etc.) and writes a field note.
3. **Compose.** The composer trims the field note to 280 characters, sanitizes it (no emoji, no hashtags, no exclamation marks, no AI self-references), and validates voice consistency.
4. **Broadcast.** The publisher posts the observation to X/Twitter via OAuth 1.0a and marks it as delivered in the memory store.

Memory is the key. Without it, every observation starts from scratch. With it, the alien references earlier patterns, notices contradictions, and develops fixations. The memory window defaults to the 10 most recent observations.

## Run it

```bash
git clone https://github.com/SoCtrilogy/Alien-Terminal.git
cd Alien-Terminal
pip install -e ".[dev]"
cp .env.example .env
# fill in your API keys in .env
```

### Dashboard

```bash
uvicorn alien_terminal.api.app:create_app --factory --reload
```

Service starts at `http://localhost:8000`. Swagger UI at `/docs`.

### Manual cycle

```bash
curl -X POST http://localhost:8000/cycle/run
```

### Inject a signal manually

```bash
curl -X POST http://localhost:8000/signals/inject \
  -H "Content-Type: application/json" \
  -d '{"headline": "World leaders gather for climate summit", "source": "manual"}'
```

### Run as a daemon

The agent is designed to run via cron or a simple loop:

```bash
export ALIEN_DRY_RUN=false
python -m alien_terminal.cli --interval 7200
```

## Architecture

```
alien_terminal/
    agent/          persona definition, cognitive categories, signal interpreter
    signals/        RSS feed scanner, deduplication, manual injection
    memory/         SQLite observation store, category queries, memory window
    composer/       post shaping, voice validation, 280-char trimming
    broadcast/      X/Twitter OAuth publisher, dry-run mode
    clients/        LLM client (Anthropic default, OpenAI fallback)
    api/            FastAPI dashboard, monitoring endpoints, manual controls
tests/              pytest suite
docs/               architecture decisions
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design decisions.

## The alien voice

The persona prompt enforces several constraints that make the output distinctive:

- **Third person only.** The alien never addresses humans directly. It writes "the species" or "the primates" or "the surface population", never "you".
- **Clinical but curious.** Allowed emotions: surprise, amusement, mild alarm, genuine puzzlement. Forbidden: anger, sadness, sentimentality, enthusiasm.
- **Concrete references.** Every observation must name the specific signal it is interpreting. No abstract musings. "The dominant territorial faction appears to be escalating its resource display" beats "humans are competitive".
- **Confident misinterpretation.** The alien systematically misreads human behavior through its own framework. Sports are territorial rituals. Elections are dominance tournaments. Cooking shows are resource-display ceremonies. The misreadings are deliberate and consistent.
- **No AI tells.** The alien never acknowledges being an AI, uses emoji, hashtags, exclamation marks, or breaks character with disclaimers.

## Cognitive categories

The alien classifies every signal into one of twelve behavioral categories:

territorial-display, resource-hoarding, mating-signal, pack-hierarchy, fear-response, tool-worship, temporal-anxiety, hive-synchronization, self-deception, pattern-seeking, ritual-behavior, dominance-theater

These categories appear in the memory store and influence how future signals are interpreted. Over time, the alien develops a statistical model of which categories dominate human activity.

## What this is not

Alien Terminal is not Truth Terminal. Truth Terminal is an autonomous agent with its own identity, its own history, and its own emergent behaviors. Alien Terminal is a persona engine: a fixed cognitive framework applied consistently to a stream of real-world signals. The alien does not evolve, negotiate, or pursue goals. It observes and reports.

Alien Terminal is not autonomous in the strong sense. It runs on a schedule set by the operator. It does not decide when to post, how often to post, or what to focus on. The operator controls the feed list, the cycle interval, and can inject signals manually.

Alien Terminal is not a social media bot in the engagement-farming sense. It does not follow, reply, retweet, or like. It broadcasts one-way. If people engage with its posts, that is their business.

## License

MIT.
