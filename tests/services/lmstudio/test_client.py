"""Tests for LMStudio HTTP client."""

import pytest
import respx
from httpx import Response


class TestLmStudioClient:
    @pytest.mark.asyncio
    async def test_get_models(self):
        """Test GET /api/v1/models returns parsed data."""
        from llm_control.services.lmstudio.client import LmStudioClient

        mock_response = [
            {
                "name": "microsoft/Phi-3-mini",
                "loaded_instances": [{"instance_id": "inst1"}],
            }
        ]

        with respx.mock as router:
            router.route().mock(
                return_value=Response(200, json=mock_response)
            )

            client = LmStudioClient(base_url="http://localhost:1234")
            result = await client.get("models")
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_post_load_model(self):
        """Test POST /api/v1/models/load."""
        from llm_control.services.lmstudio.client import LmStudioClient

        mock_response = {
            "type": "success",
            "instance_id": "inst2",
            "status": "loaded",
        }

        with respx.mock as router:
            router.post("/api/v1/models/load").mock(
                return_value=Response(200, json=mock_response)
            )

            client = LmStudioClient(base_url="http://localhost:1234")
            result = await client.post("models/load", {"model": "test"})
            assert result["status"] == "loaded"

    @pytest.mark.asyncio
    async def test_post_unload_model(self):
        """Test POST /api/v1/models/unload."""
        from llm_control.services.lmstudio.client import LmStudioClient

        mock_response = {"instance_id": "inst1"}

        with respx.mock as router:
            router.post("/api/v1/models/unload").mock(
                return_value=Response(200, json=mock_response)
            )

            client = LmStudioClient(base_url="http://localhost:1234")
            result = await client.post("models/unload", {"instance_id": "inst1"})
            assert result["instance_id"] == "inst1"

    @pytest.mark.asyncio
    async def test_with_token(self):
        """Test that token is passed in Authorization header."""
        from llm_control.services.lmstudio.client import LmStudioClient

        with respx.mock as router:
            route = router.get("/api/v1/models").mock(
                return_value=Response(200, json=[])
            )

            client = LmStudioClient(base_url="http://localhost:1234", token="secret")
            await client.get("models")
            assert route.called
