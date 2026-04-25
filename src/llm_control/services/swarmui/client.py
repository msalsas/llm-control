"""SwarmUI HTTP client — session flow + API routes."""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SwarmUIClient:
    """Low-level HTTP client for the SwarmUI API.

    Reuses sessions until invalidity; auto-refreshes on error.
    Handles retry/backoff logic with configurable intervals.
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
        self._session_id: str | None = None

    async def __aenter__(self) -> "SwarmUIClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager — closes HTTP client."""
        await self.close()

    async def _get_session(self) -> str:
        """Get a fresh session ID from GetNewSession."""
        for attempt, delay in enumerate(self._retry_intervals):
            try:
                resp = await self._client.post("/API/GetNewSession")
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, str):
                    # Some versions return session_id as a plain string
                    session_id = data
                elif isinstance(data, dict):
                    session_id = data.get("session_id", "")
                else:
                    session_id = str(data)

                if session_id:
                    self._session_id = session_id
                    logger.info("Obtained new SwarmUI session")
                    return session_id
            except (httpx.HTTPError, httpx.RequestError) as exc:
                logger.warning("Attempt %d to get session failed: %s", attempt + 1, exc)
                if attempt < len(self._retry_intervals) - 1:
                    await asyncio.sleep(delay)
                else:
                    raise

        raise RuntimeError("Failed to obtain a SwarmUI session")

    async def _ensure_session(self) -> str:
        """Ensure we have a valid session; refresh only when needed.

        Reuses existing session until an error indicates invalidity.
        This avoids creating unnecessary new sessions on every request.
        """
        if self._session_id is None:
            return await self._get_session()
        # Session already exists — reuse it until server rejects it
        return self._session_id

    async def get(self, path: str, **kwargs: Any) -> dict:
        """Send a GET request with session."""
        session_id = await self._ensure_session()
        url = f"/API/{path.lstrip('/')}"
        params = {"session_id": session_id}
        for attempt, delay in enumerate(self._retry_intervals):
            try:
                resp = await self._client.get(url, params=params, **kwargs)
                resp.raise_for_status()
                logger.info("GET %s succeeded (attempt %d)", url, attempt + 1)
                return resp.json()
            except (httpx.HTTPError, httpx.RequestError) as exc:
                logger.warning("Attempt %d failed for GET %s: %s", attempt + 1, url, exc)
                self._session_id = None  # Force session refresh on error
                if attempt < len(self._retry_intervals) - 1:
                    await asyncio.sleep(delay)
                else:
                    raise

    async def post(self, path: str, payload: dict | None = None) -> dict:
        """Send a POST request with session."""
        session_id = await self._ensure_session()
        url = f"/API/{path.lstrip('/')}"
        body = payload or {}
        body["session_id"] = session_id

        for attempt, delay in enumerate(self._retry_intervals):
            try:
                resp = await self._client.post(url, json=body)
                resp.raise_for_status()
                logger.info("POST %s succeeded (attempt %d)", url, attempt + 1)
                return resp.json()
            except (httpx.HTTPError, httpx.RequestError) as exc:
                logger.warning("Attempt %d failed for POST %s: %s", attempt + 1, url, exc)
                self._session_id = None  # Force session refresh on error
                if attempt < len(self._retry_intervals) - 1:
                    await asyncio.sleep(delay)
                else:
                    raise

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
