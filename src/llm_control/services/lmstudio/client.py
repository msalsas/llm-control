"""LMStudio HTTP client — communicates with LMStudio v1 REST API."""

import asyncio
import logging
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)


class LmStudioClient:
    """Low-level HTTP client for the LMStudio v1 REST API.

    Handles optional Bearer token authentication and retry/backoff logic.
    Supports async context manager usage for proper resource cleanup.
    """

    DEFAULT_RETRY_INTERVALS = (1, 2, 5)

    def __init__(self, base_url: str, token: str | None = None,
                 retry_intervals: tuple[int, ...] | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._retry_intervals = retry_intervals or self.DEFAULT_RETRY_INTERVALS
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=30.0),
            headers={"Authorization": f"Bearer {token}"} if token else {},
        )

    async def __aenter__(self) -> "LmStudioClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager — closes HTTP client."""
        await self.close()

    async def _retry(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute an async function with configurable retry/backoff.

        Shared helper used by get() and post() to eliminate duplicate retry loops.
        """
        for attempt, delay in enumerate(self._retry_intervals):
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPError as exc:
                logger.warning("Attempt %d failed: %s", attempt + 1, exc)
                if attempt < len(self._retry_intervals) - 1:
                    await asyncio.sleep(delay)
                else:
                    raise

    async def get(self, path: str, **kwargs: Any) -> dict:
        """Send a GET request and return the JSON response."""
        url = f"/api/v1/{path.lstrip('/')}"

        async def _do_get():
            resp = await self._client.get(url, **kwargs)
            resp.raise_for_status()
            logger.info("GET %s succeeded", url)
            return resp.json()

        return await self._retry(_do_get)

    async def post(self, path: str, payload: dict | None = None) -> dict:
        """Send a POST request and return the JSON response."""
        url = f"/api/v1/{path.lstrip('/')}"

        async def _do_post():
            resp = await self._client.post(url, json=payload or {})
            resp.raise_for_status()
            logger.info("POST %s succeeded", url)
            return resp.json()

        return await self._retry(_do_post)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
