"""Publisher: broadcasts posts to X/Twitter.

The publisher is the agent's mouth. It takes a composed Post and delivers
it to the X API. On success, it marks the observation as posted in the
memory store.

Authentication uses OAuth 1.0a (User Context) with four tokens:
API key, API secret, access token, access token secret. These are read
from environment variables. The publisher refuses to initialize without
them — silent failure on missing credentials is worse than a loud crash.

Rate limiting is handled at the application level, not here. The
scheduler (cron or the daemon loop) controls how often the publisher
fires. The publisher itself is stateless: give it a Post, it posts it.

Dry-run mode exists for testing. When enabled, the publisher logs the
post text but does not call the X API. The flag is controlled via the
ALIEN_DRY_RUN environment variable or the constructor.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from base64 import b64encode
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from alien_terminal.composer.writer import Post
from alien_terminal.memory.store import MemoryStore

log = logging.getLogger(__name__)

TWEET_ENDPOINT = "https://api.x.com/2/tweets"


@dataclass
class PublishResult:
    """Outcome of a publish attempt."""

    success: bool
    tweet_id: str | None = None
    error: str | None = None


class Publisher:
    """Broadcasts posts to X/Twitter."""

    def __init__(
        self,
        memory: MemoryStore,
        api_key: str | None = None,
        api_secret: str | None = None,
        access_token: str | None = None,
        access_secret: str | None = None,
        dry_run: bool | None = None,
    ):
        self.memory = memory
        self._api_key = api_key or os.environ.get("X_API_KEY", "")
        self._api_secret = api_secret or os.environ.get("X_API_SECRET", "")
        self._access_token = access_token or os.environ.get("X_ACCESS_TOKEN", "")
        self._access_secret = access_secret or os.environ.get("X_ACCESS_SECRET", "")

        if dry_run is not None:
            self.dry_run = dry_run
        else:
            self.dry_run = os.environ.get("ALIEN_DRY_RUN", "").lower() in ("1", "true", "yes")

    async def publish(self, post: Post) -> PublishResult:
        """Publish a post to X. Returns the result."""
        if self.dry_run:
            log.info("[DRY RUN] would post: %s", post.text)
            self.memory.mark_posted(post.observation_id)
            return PublishResult(success=True, tweet_id="dry_run")

        if not all([self._api_key, self._api_secret, self._access_token, self._access_secret]):
            return PublishResult(success=False, error="X API credentials not configured")

        try:
            headers = self._build_oauth_header("POST", TWEET_ENDPOINT)
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.post(
                    TWEET_ENDPOINT,
                    json={"text": post.text},
                    headers={**headers, "Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                tweet_id = data.get("data", {}).get("id")

            self.memory.mark_posted(post.observation_id)
            log.info("published tweet_id=%s observation=%s", tweet_id, post.observation_id)
            return PublishResult(success=True, tweet_id=tweet_id)

        except Exception as exc:  # noqa: BLE001
            log.error("publish failed: %s", exc)
            return PublishResult(success=False, error=str(exc))

    def _build_oauth_header(self, method: str, url: str) -> dict[str, str]:
        """Build an OAuth 1.0a Authorization header."""
        timestamp = str(int(time.time()))
        nonce = hashlib.sha256(f"{timestamp}{os.urandom(8).hex()}".encode()).hexdigest()[:32]

        params = {
            "oauth_consumer_key": self._api_key,
            "oauth_nonce": nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": timestamp,
            "oauth_token": self._access_token,
            "oauth_version": "1.0",
        }

        param_string = "&".join(f"{quote(k)}={quote(v)}" for k, v in sorted(params.items()))
        base_string = f"{method}&{quote(url, safe='')}&{quote(param_string, safe='')}"
        signing_key = f"{quote(self._api_secret, safe='')}&{quote(self._access_secret, safe='')}"
        signature = b64encode(
            hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        ).decode()

        params["oauth_signature"] = signature
        auth_header = "OAuth " + ", ".join(
            f'{quote(k)}="{quote(v)}"' for k, v in sorted(params.items())
        )
        return {"Authorization": auth_header}
