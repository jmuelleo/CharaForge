"""Minimal Danbooru client: pagination, rate limiting, retry with backoff.

Danbooru sits behind a Cloudflare check that blocks plain `requests` (and
Playwright's own lightweight `context.request` client) with a 403 "Just a
moment..." challenge page -- confirmed by direct response inspection
(`Cf-Mitigated: challenge`). The check also rejects headless Chromium.
Only a real, non-headless Chromium page navigation (`page.goto`) gets a
clean 200, for both the `posts.json` API and the `cdn.donmai.us` image CDN.
So instead of a `requests.Session`, this client drives one persistent,
visible Chromium page for every request -- there is no cookie to extract
and replay, the browser must stay open for the whole session.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Iterator, Optional

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

BASE_URL = "https://danbooru.donmai.us"


@dataclass
class DanbooruPost:
    id: int
    md5: Optional[str]
    file_url: Optional[str]
    file_ext: Optional[str]
    image_width: int
    image_height: int
    rating: str
    tag_string: str
    tag_string_character: str
    # Danbooru also exposes the same tags pre-split by category -- tag_string
    # alone can't tell an artist name apart from a general descriptive tag.
    tag_string_artist: str = ""
    tag_string_general: str = ""
    tag_string_copyright: str = ""
    tag_string_meta: str = ""

    @classmethod
    def from_json(cls, data: dict) -> "DanbooruPost":
        return cls(
            id=data["id"],
            md5=data.get("md5"),
            file_url=data.get("file_url"),
            file_ext=data.get("file_ext"),
            image_width=data.get("image_width", 0),
            image_height=data.get("image_height", 0),
            rating=data.get("rating", ""),
            tag_string=data.get("tag_string", ""),
            tag_string_character=data.get("tag_string_character", ""),
            tag_string_artist=data.get("tag_string_artist", ""),
            tag_string_general=data.get("tag_string_general", ""),
            tag_string_copyright=data.get("tag_string_copyright", ""),
            tag_string_meta=data.get("tag_string_meta", ""),
        )

    @property
    def character_count(self) -> int:
        return len([t for t in self.tag_string_character.split(" ") if t])

    @property
    def tags(self) -> set[str]:
        return set(self.tag_string.split(" "))


class RateLimiter:
    """Simple fixed-interval rate limiter (sleeps before allowing the next call)."""

    def __init__(self, requests_per_second: float = 2.0):
        self._min_interval = 1.0 / requests_per_second
        self._last_call = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        remaining = self._min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_call = time.monotonic()


class DanbooruClient:
    def __init__(
        self,
        base_url: str = BASE_URL,
        api_key: Optional[str] = None,
        login: Optional[str] = None,
        requests_per_second: float = 1.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.login = login
        self._rate_limiter = RateLimiter(requests_per_second)
        self._max_retries = max_retries

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=False)

    def close(self) -> None:
        self._browser.close()
        self._playwright.stop()

    def __enter__(self) -> "DanbooruClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def _fetch(self, url: str) -> bytes:
        """Navigates a fresh, short-lived browser context to `url` and
        returns the raw response body.

        Some responses report a clean 200 from `page.goto()` but then throw
        `Response.body: ... evicted from inspector cache` when read -- this
        reproduces deterministically for at least one specific ~20MB PNG
        post, even as the very first request of a brand-new browser session,
        so it's a per-resource Chromium/CDP body-buffer limit, not a
        Cloudflare rate-limit or session-state issue. There's no fix from
        here (tried raising the CDP buffer size via a manual session, and
        forcing a native download via an anchor `download` attribute -- the
        latter is a browser no-op for cross-origin links without server-side
        Content-Disposition support). Retry a couple of times in case it's
        transient; if not, the caller is expected to skip that post rather
        than abort the whole collection run.
        """
        backoff = 1.0
        last_error = None
        for attempt in range(self._max_retries):
            self._rate_limiter.wait()
            context = self._browser.new_context()
            try:
                page = context.new_page()
                resp = page.goto(url, wait_until="domcontentloaded")
                if resp is not None and resp.status == 200:
                    return resp.body()
                last_error = f"status {resp.status if resp is not None else 'no response'}"
            except PlaywrightError as e:
                last_error = str(e)
            finally:
                context.close()
            if attempt < self._max_retries - 1:
                time.sleep(backoff)
                backoff *= 2
        raise RuntimeError(f"GET {url} failed after {self._max_retries} attempts (last error: {last_error})")

    def _get_json(self, path: str, params: dict) -> list[dict]:
        if self.login and self.api_key:
            params = {**params, "login": self.login, "api_key": self.api_key}
        query = "&".join(f"{k}={v}" for k, v in params.items())
        body = self._fetch(f"{self.base_url}{path}?{query}")
        return json.loads(body)

    def download_bytes(self, url: str) -> bytes:
        """Fetches a binary resource (e.g. an image on cdn.donmai.us) through
        the same real-browser navigation, since that CDN is behind the same
        Cloudflare check."""
        return self._fetch(url)

    def search_posts(self, tags: str, limit: int = 200, page: int = 1) -> list[DanbooruPost]:
        data = self._get_json("/posts.json", {"tags": tags, "limit": limit, "page": page})
        return [DanbooruPost.from_json(p) for p in data]

    def get_post(self, post_id: int) -> Optional[DanbooruPost]:
        """Looks up a single post by id (e.g. to re-fetch fuller metadata for
        an already-collected post). Returns None if the post no longer
        exists (e.g. deleted since collection)."""
        data = self._get_json("/posts.json", {"tags": f"id:{post_id}", "limit": 1})
        return DanbooruPost.from_json(data[0]) if data else None

    def iter_all_posts(
        self, tags: str, limit: int = 200, max_pages: Optional[int] = None
    ) -> Iterator[DanbooruPost]:
        """Yields posts across pages until an empty page is returned or max_pages is hit.

        Danbooru's page-based pagination is only reliable up to ~1000 pages for
        anonymous users; that's far more than needed for a single character tag
        with a few thousand posts.
        """
        page = 1
        while max_pages is None or page <= max_pages:
            posts = self.search_posts(tags=tags, limit=limit, page=page)
            if not posts:
                return
            yield from posts
            page += 1
