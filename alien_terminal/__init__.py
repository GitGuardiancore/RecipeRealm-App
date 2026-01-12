"""alien-terminal: an autonomous AI agent that roleplays as an
extraterrestrial intelligence observing humanity.

The agent intercepts human signals (RSS feeds, trending topics, news
headlines) and interprets them through an alien cognitive framework.
Each observation is processed into a cryptic post and broadcast to
X/Twitter on a configurable schedule.

The alien persona is not a chatbot. It does not respond to mentions or
hold conversations. It observes, logs, and broadcasts. The tone is
detached curiosity punctuated by occasional alarm — a xenobiologist's
field notes on a species it finds fascinating and slightly dangerous.

The agent maintains a persistent memory of its observations. Earlier
signals influence how later ones are interpreted. The alien develops
opinions, running theories, and recurring fixations over time.
"""
from alien_terminal._version import __version__
from alien_terminal.agent.persona import ALIEN_PERSONA, Persona
from alien_terminal.agent.interpreter import SignalInterpreter
from alien_terminal.memory.store import MemoryStore, Observation
from alien_terminal.signals.interceptor import SignalInterceptor, Signal
from alien_terminal.composer.writer import PostComposer, Post
from alien_terminal.broadcast.publisher import Publisher

__all__ = [
    "__version__",
    "Persona",
    "ALIEN_PERSONA",
    "SignalInterpreter",
    "MemoryStore",
    "Observation",
    "SignalInterceptor",
    "Signal",
    "PostComposer",
    "Post",
    "Publisher",
]
