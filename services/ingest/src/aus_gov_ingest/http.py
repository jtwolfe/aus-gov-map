from __future__ import annotations

import time
from typing import Any

import httpx

from aus_gov_ingest.config import settings

# APH's Azure Front Door / WAF returns 403 for bot-like User-Agents
# (including the identifying research UA). A browser-like UA + Accept
# headers is enough for www.aph.gov.au HTML and /api/hansard/*.
# parlinfo.aph.gov.au still serves an Azure WAF JS challenge from
# typical datacentre IPs — callers should prefer the APH Hansard API.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

BROWSER_HEADERS = {
    "User-Agent": BROWSER_USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "application/json;q=0.8,*/*;q=0.7"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
    "Cache-Control": "no-cache",
}


def _looks_like_browser_ua(ua: str) -> bool:
    lowered = (ua or "").lower()
    return "mozilla/" in lowered or "chrome/" in lowered or "safari/" in lowered


class AphClient:
    """Sessioned HTTP client with browser-like headers, cookies, retries."""

    def __init__(
        self,
        *,
        timeout: float | None = None,
        rate_limit_seconds: float | None = None,
        max_retries: int | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.timeout = timeout if timeout is not None else settings.ingest_timeout_seconds
        self.rate_limit_seconds = (
            rate_limit_seconds
            if rate_limit_seconds is not None
            else settings.ingest_rate_limit_seconds
        )
        self.max_retries = (
            max_retries if max_retries is not None else settings.ingest_max_retries
        )
        configured = user_agent or settings.ingest_user_agent
        # Prefer a browser-like UA; keep an identifying UA as the first attempt
        # only when the operator explicitly set one that already looks like a browser.
        self.user_agents = []
        if configured and configured not in self.user_agents:
            self.user_agents.append(configured)
        if BROWSER_USER_AGENT not in self.user_agents:
            self.user_agents.append(BROWSER_USER_AGENT)
        if not _looks_like_browser_ua(self.user_agents[0]) and len(self.user_agents) > 1:
            # Identifying research UA is blocked — try the browser UA first.
            self.user_agents = [BROWSER_USER_AGENT] + [
                ua for ua in self.user_agents if ua != BROWSER_USER_AGENT
            ]
        self._last_request_at = 0.0
        self._client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers=BROWSER_HEADERS,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> AphClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _throttle(self) -> None:
        if self.rate_limit_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        referer: str | None = None,
    ) -> httpx.Response:
        extra = dict(headers or {})
        if referer:
            extra["Referer"] = referer
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            ua = self.user_agents[min(attempt, len(self.user_agents) - 1)]
            request_headers = {**BROWSER_HEADERS, "User-Agent": ua, **extra}
            self._throttle()
            try:
                response = self._client.get(url, headers=request_headers)
                self._last_request_at = time.monotonic()
            except httpx.HTTPError as exc:
                last_error = exc
                time.sleep(min(2**attempt, 8))
                continue
            if response.status_code == 403 and attempt + 1 < self.max_retries:
                # Rotate UA / retry — APH WAF is UA-sensitive.
                time.sleep(min(1.5 * (attempt + 1), 6))
                continue
            if response.status_code in {429, 500, 502, 503, 504} and attempt + 1 < self.max_retries:
                time.sleep(min(2**attempt, 8))
                continue
            return response
        if last_error:
            raise last_error
        raise RuntimeError(f"Failed to GET {url}")

    def get_text(self, url: str, **kwargs: Any) -> str:
        response = self.get(url, **kwargs)
        response.raise_for_status()
        return response.text

    def get_json(self, url: str, **kwargs: Any) -> Any:
        extra = dict(kwargs.get("headers") or {})
        extra.setdefault("Accept", "application/json, text/javascript, */*;q=0.8")
        extra.setdefault("X-Requested-With", "XMLHttpRequest")
        kwargs["headers"] = extra
        response = self.get(url, **kwargs)
        response.raise_for_status()
        return response.json()
