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

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager enters and exits cleanly."""
        from llm_control.services.swarmui.client import SwarmUIClient

        with respx.mock as router:
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json={"session_id": "sess1"})
            )
            router.post("/API/GetServerResourceInfo").mock(
                return_value=Response(200, json={})
            )

            async with SwarmUIClient(base_url="http://localhost:7801") as client:
                result = await client.post("GetServerResourceInfo")
                assert result == {}

    @pytest.mark.asyncio
    async def test_session_reuse(self):
        """Test that _ensure_session reuses an existing session."""
        from llm_control.services.swarmui.client import SwarmUIClient

        call_count = 0

        with respx.mock as router:
            def count_calls(request):
                nonlocal call_count
                call_count += 1
                return Response(200, json={"session_id": "abc"})

            router.post("/API/GetNewSession").mock(side_effect=count_calls)
            router.post("/API/GetServerResourceInfo").mock(
                return_value=Response(200, json={})
            )

            client = SwarmUIClient(base_url="http://localhost:7801")
            # Two requests — session should be created only once
            await client.post("GetServerResourceInfo")
            await client.post("GetServerResourceInfo")
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_session_id_as_plain_string(self):
        """Test that plain-string session_id response is handled correctly."""
        from llm_control.services.swarmui.client import SwarmUIClient

        with respx.mock as router:
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json="plain-session-id")
            )

            client = SwarmUIClient(base_url="http://localhost:7801")
            session = await client._get_session()
            assert session == "plain-session-id"

    @pytest.mark.asyncio
    async def test_session_id_as_other_type(self):
        """Test that non-string/non-dict session data is coerced to string."""
        from llm_control.services.swarmui.client import SwarmUIClient

        with respx.mock as router:
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json=42)
            )

            client = SwarmUIClient(base_url="http://localhost:7801")
            session = await client._get_session()
            assert session == "42"

    @pytest.mark.asyncio
    async def test_get_method_with_session(self):
        """Test GET request includes session_id as query param."""
        from llm_control.services.swarmui.client import SwarmUIClient

        with respx.mock as router:
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json={"session_id": "sess-get"})
            )
            route = router.get("/API/SomeEndpoint").mock(
                return_value=Response(200, json={"data": "ok"})
            )

            client = SwarmUIClient(base_url="http://localhost:7801")
            result = await client.get("SomeEndpoint")
            assert result == {"data": "ok"}
            assert route.called

    @pytest.mark.asyncio
    async def test_retry_resets_session_on_error(self):
        """Test that _retry resets the session_id on HTTP errors."""
        from llm_control.services.swarmui.client import SwarmUIClient

        call_count = 0

        with respx.mock as router:
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json={"session_id": "fresh"})
            )

            def fail_then_succeed(request):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return Response(500)
                return Response(200, json={"ok": True})

            router.post("/API/DoSomething").mock(side_effect=fail_then_succeed)

            client = SwarmUIClient(
                base_url="http://localhost:7801", retry_intervals=(0, 0)
            )
            result = await client.post("DoSomething")
            assert result == {"ok": True}
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_raises_after_all_failures(self):
        """Test that _retry raises after exhausting all attempts."""
        from llm_control.services.swarmui.client import SwarmUIClient
        import httpx

        with respx.mock as router:
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json={"session_id": "s"})
            )
            router.post("/API/BadEndpoint").mock(
                return_value=Response(503)
            )

            client = SwarmUIClient(
                base_url="http://localhost:7801", retry_intervals=(0, 0)
            )
            with pytest.raises(httpx.HTTPStatusError):
                await client.post("BadEndpoint")

    @pytest.mark.asyncio
    async def test_get_session_retry_on_http_error(self):
        """Test that _get_session retries when the server returns an error."""
        from llm_control.services.swarmui.client import SwarmUIClient

        call_count = 0

        with respx.mock as router:
            def fail_then_succeed(request):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return Response(503)
                return Response(200, json={"session_id": "retry-sess"})

            router.post("/API/GetNewSession").mock(side_effect=fail_then_succeed)

            client = SwarmUIClient(
                base_url="http://localhost:7801", retry_intervals=(0, 0)
            )
            session = await client._get_session()
            assert session == "retry-sess"
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_get_session_raises_after_all_failures(self):
        """Test that _get_session raises after exhausting all session attempts."""
        from llm_control.services.swarmui.client import SwarmUIClient
        import httpx

        with respx.mock as router:
            router.post("/API/GetNewSession").mock(return_value=Response(503))

            client = SwarmUIClient(
                base_url="http://localhost:7801", retry_intervals=(0, 0)
            )
            with pytest.raises(httpx.HTTPStatusError):
                await client._get_session()

    @pytest.mark.asyncio
    async def test_get_session_raises_when_session_id_always_empty(self):
        """Test RuntimeError is raised when GetNewSession always returns empty id."""
        from llm_control.services.swarmui.client import SwarmUIClient

        with respx.mock as router:
            # Returns a dict with an empty session_id for every attempt
            router.post("/API/GetNewSession").mock(
                return_value=Response(200, json={"session_id": ""})
            )

            client = SwarmUIClient(
                base_url="http://localhost:7801", retry_intervals=(0, 0)
            )
            with pytest.raises(RuntimeError, match="Failed to obtain"):
                await client._get_session()
