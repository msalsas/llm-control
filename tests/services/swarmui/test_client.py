"""Tests for SwarmUI HTTP client."""

import pytest
import respx
from httpx import Response


class TestSwarmUIClient:
    @pytest.mark.asyncio
    async def test_get_session(self):
        """Test POST /API/GetNewSession returns session_id."""
        from llm_control.services.swarmui.client import SwarmUIClient

        with respx.mock as router:
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json={"session_id": "abc123"})
            )

            client = SwarmUIClient(base_url="http://localhost:7801")
            session = await client._get_session()
            assert session == "abc123"

    @pytest.mark.asyncio
    async def test_post_get_resource_info(self):
        """Test POST /API/GetServerResourceInfo with session."""
        from llm_control.services.swarmui.client import SwarmUIClient

        with respx.mock as router:
            # Mock GetNewSession first
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json={"session_id": "abc123"})
            )
            # Mock the actual API call (will include session_id in body)
            router.post("/API/GetServerResourceInfo").mock(
                return_value=Response(200, json={})
            )

            client = SwarmUIClient(base_url="http://localhost:7801")
            result = await client.post("GetServerResourceInfo")
            assert result == {}

    @pytest.mark.asyncio
    async def test_post_select_model(self):
        """Test POST /API/SelectModel."""
        from llm_control.services.swarmui.client import SwarmUIClient

        with respx.mock as router:
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json={"session_id": "abc123"})
            )
            router.post("/API/SelectModel").mock(
                return_value=Response(200, json={"success": True})
            )

            client = SwarmUIClient(base_url="http://localhost:7801")
            result = await client.post("SelectModel", {"model": "test"})
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_post_free_backend_memory(self):
        """Test POST /API/FreeBackendMemory."""
        from llm_control.services.swarmui.client import SwarmUIClient

        with respx.mock as router:
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json={"session_id": "abc123"})
            )
            router.post("/API/FreeBackendMemory").mock(
                return_value=Response(200, json={"success": True})
            )

            client = SwarmUIClient(base_url="http://localhost:7801")
            result = await client.post("FreeBackendMemory")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_session_refresh_on_failure(self):
        """Test session is refreshed after HTTP error."""
        from llm_control.services.swarmui.client import SwarmUIClient

        with respx.mock as router:
            # First GetNewSession succeeds
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json={"session_id": "abc123"})
            )

            client = SwarmUIClient(base_url="http://localhost:7801")
            await client._get_session()  # Get initial session
            assert client._session_id == "abc123"
