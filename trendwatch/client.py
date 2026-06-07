"""Thin client for the Trends MCP REST API.

Every call goes to a single endpoint (POST https://api.trendsmcp.ai/api) and is
authenticated with your personal API key via a Bearer token. The key is read
from the TRENDS_API_KEY environment variable (a GitHub Secret in CI) — it is
never stored in this repo.

Get a free key (100 requests/month, no credit card): https://trendsmcp.ai
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

API_URL = os.environ.get("TRENDS_API_URL", "https://api.trendsmcp.ai/api")
SIGNUP_URL = "https://trendsmcp.ai"


class TrendsError(RuntimeError):
    """Raised when the Trends MCP API returns an error."""


class RateLimited(TrendsError):
    """Raised on HTTP 429 — the monthly free-tier quota is exhausted."""


class MissingKey(TrendsError):
    """Raised when no API key is configured."""


class TrendsClient:
    """Minimal, dependency-light wrapper around the Trends MCP REST API."""

    def __init__(self, api_key: str | None = None, *, timeout: int = 30, retries: int = 2):
        self.api_key = api_key or os.environ.get("TRENDS_API_KEY", "").strip()
        if not self.api_key:
            raise MissingKey(
                "No Trends MCP API key found.\n"
                "  1. Get a free key at " + SIGNUP_URL + "\n"
                "  2. Add it as a repository secret named TRENDS_API_KEY\n"
                "     (Settings -> Secrets and variables -> Actions -> New repository secret)\n"
                "  3. Re-run the workflow."
            )
        self.timeout = timeout
        self.retries = retries
        self.calls_made = 0  # rough local counter for quota awareness

    # -- low level --------------------------------------------------------
    def _post(self, payload: dict[str, Any]) -> Any:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "TrendWatch/1.0 (+https://github.com/topics/trendwatch)",
        }
        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = requests.post(API_URL, json=payload, headers=headers, timeout=self.timeout)
            except requests.RequestException as exc:  # network blip
                last_exc = exc
                time.sleep(1.5 * (attempt + 1))
                continue

            if resp.status_code == 429:
                raise RateLimited(
                    "Monthly free-tier quota (100 requests) exhausted. "
                    "Trim your config.yml, slow the schedule, or upgrade at " + SIGNUP_URL + "/pricing"
                )
            if resp.status_code == 401:
                raise MissingKey(
                    "API key was rejected (HTTP 401). Double-check the TRENDS_API_KEY secret. "
                    "Get a fresh key at " + SIGNUP_URL
                )
            if resp.status_code >= 500:
                last_exc = TrendsError(f"Server error {resp.status_code}: {resp.text[:200]}")
                time.sleep(1.5 * (attempt + 1))
                continue
            if resp.status_code >= 400:
                try:
                    body = resp.json()
                    msg = body.get("message") or body.get("error") or resp.text
                except ValueError:
                    msg = resp.text
                raise TrendsError(f"HTTP {resp.status_code}: {msg}")

            self.calls_made += 1
            try:
                data = resp.json()
            except ValueError as exc:
                raise TrendsError(f"Non-JSON response: {resp.text[:200]}") from exc
            return self._unwrap(data)

        raise TrendsError(f"Request failed after {self.retries + 1} attempts: {last_exc}")

    @staticmethod
    def _unwrap(data: Any) -> Any:
        """Normalize the API's response.

        Successful data calls come back as a Lambda-style envelope:
            {"statusCode": 200, "body": "<json string>"}
        while some errors arrive as plain JSON. Handle both, and surface an
        error encoded inside the envelope (inner statusCode >= 400).
        """
        if isinstance(data, dict) and "statusCode" in data and "body" in data:
            status = data.get("statusCode")
            body = data.get("body")
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except ValueError:
                    pass  # leave body as-is if it isn't JSON
            if isinstance(status, int) and status >= 400:
                msg = body.get("message") or body.get("error") if isinstance(body, dict) else str(body)
                if status == 429:
                    raise RateLimited(
                        "Monthly free-tier quota (100 requests) exhausted. "
                        "Trim config.yml, slow the schedule, or upgrade at " + SIGNUP_URL + "/pricing"
                    )
                if status == 401:
                    raise MissingKey("API key was rejected. Check the TRENDS_API_KEY secret. " + SIGNUP_URL)
                raise TrendsError(f"API error {status}: {msg}")
            return body
        return data

    # -- public API -------------------------------------------------------
    def get_trends(self, source: str, keyword: str, data_mode: str | None = None) -> list[dict]:
        """Historical normalized (0-100) time series for a keyword."""
        payload: dict[str, Any] = {"source": source, "keyword": keyword}
        if data_mode:
            payload["data_mode"] = data_mode
        return self._post(payload)

    def get_growth(self, source: str, keyword: str, periods: list, data_mode: str | None = None) -> dict:
        """Point-to-point % growth for a keyword across one or more periods."""
        payload: dict[str, Any] = {
            "source": source,
            "keyword": keyword,
            "percent_growth": periods,
        }
        if data_mode:
            payload["data_mode"] = data_mode
        return self._post(payload)

    def get_top_trends(self, feed_type: str | None = None, limit: int = 25, offset: int = 0) -> dict:
        """Live ranked leaderboard for a feed (Google Trends, TikTok, etc.)."""
        payload: dict[str, Any] = {"mode": "top_trends", "limit": limit, "offset": offset}
        if feed_type and feed_type.lower() != "all":
            payload["type"] = feed_type
        return self._post(payload)
