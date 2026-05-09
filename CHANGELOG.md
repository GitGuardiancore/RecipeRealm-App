# Changelog

## [0.6.0] - 2026-05-09
- feat: Anthropic Claude as the default LLM backend. OpenAI remains as fallback.
- feat: dashboard API — recent observations, category stats, manual cycle trigger.
- feat: /signals/inject endpoint for manual signal injection.
- feat: PostComposer voice validation catches AI self-references and emoji.
- fix: dedup eviction was clearing the entire seen set instead of the oldest half.
- chore: README rewrite for public release.

## [0.5.0] - 2026-05-02
- feat: X/Twitter publisher with OAuth 1.0a and dry-run mode.
- feat: memory window in interpreter — recent observations as context for continuity.
- feat: cognitive categories expanded from 8 to 12 (added temporal-anxiety, hive-synchronization, self-deception, pattern-seeking).
- breaking: observation schema adds `posted` column. Run migration or recreate the DB.

## [0.4.0] - 2026-04-18
- feat: PostComposer with 280-char trimming at sentence boundaries.
- feat: sanitizer strips emoji, hashtags, exclamation marks.
- feat: batch counter for optional post numbering.
- fix: interpreter was not clamping confidence to [0, 1].

## [0.3.0] - 2026-03-28
- feat: SignalInterceptor with RSS feed scanning and deduplication.
- feat: configurable feed list via environment variable.
- feat: manual signal injection for testing.
- fix: XML parser crash on malformed feeds.

## [0.2.0] - 2026-03-01
- feat: MemoryStore with SQLite persistence.
- feat: category queries and unposted observation tracking.
- feat: SignalInterpreter with structured JSON output parsing.
- breaking: interpreter now requires a MemoryStore instance.

## [0.1.0] - 2026-02-01
- feat: alien persona definition with cognitive categories.
- feat: LLM client wrapper (OpenAI only at this stage).
- feat: basic signal-to-interpretation pipeline.

## [0.0.1] - 2026-01-12
- exploration: first sketch of the alien observer concept.
