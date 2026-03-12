"""Tests for SignalInterceptor."""
from __future__ import annotations

from alien_terminal.signals.interceptor import Signal, SignalInterceptor


def test_signal_fingerprint_is_deterministic():
    s = Signal(source="test", headline="hello world", summary="test")
    assert s.fingerprint == s.fingerprint
    assert len(s.fingerprint) == 16


def test_signal_different_headlines_different_fingerprints():
    a = Signal(source="test", headline="hello", summary="test")
    b = Signal(source="test", headline="world", summary="test")
    assert a.fingerprint != b.fingerprint


def test_inject_returns_signal():
    interceptor = SignalInterceptor(feeds=[])
    signal = interceptor.inject("test headline", "test summary")
    assert signal.headline == "test headline"
    assert signal.source == "manual"


def test_inject_marks_as_seen():
    interceptor = SignalInterceptor(feeds=[])
    signal = interceptor.inject("test headline")
    assert signal.fingerprint in interceptor._seen


def test_parse_rss_extracts_items():
    xml = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>First headline</title>
          <description>First description</description>
          <link>https://example.com/1</link>
        </item>
        <item>
          <title>Second headline</title>
          <description>Second description</description>
          <link>https://example.com/2</link>
        </item>
      </channel>
    </rss>"""
    signals = SignalInterceptor._parse_rss(xml, "https://example.com/rss", max_items=10)
    assert len(signals) == 2
    assert signals[0].headline == "First headline"
    assert signals[1].url == "https://example.com/2"


def test_parse_rss_respects_max_items():
    xml = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item><title>A</title></item>
        <item><title>B</title></item>
        <item><title>C</title></item>
      </channel>
    </rss>"""
    signals = SignalInterceptor._parse_rss(xml, "test", max_items=2)
    assert len(signals) == 2


def test_parse_rss_handles_malformed_xml():
    signals = SignalInterceptor._parse_rss("not xml", "test", max_items=5)
    assert signals == []


def test_dedup_evicts_oldest_when_full():
    interceptor = SignalInterceptor(feeds=[])
    for i in range(2500):
        interceptor._mark_seen(f"hash_{i}")
    assert len(interceptor._seen) <= 2000
