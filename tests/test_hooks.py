from unittest.mock import AsyncMock, MagicMock

import pytest

from amrita_core.builtins.hooks import cookie, posthook
from amrita_core.config import AmritaConfig
from amrita_core.contents import MessageWithMetadata
from amrita_core.hook.event import CompletionEvent


class TestHooks:
    @pytest.fixture
    def mock_config(self):
        config = AmritaConfig()
        config.cookie.enable_cookie = True
        config.cookie.cookie = "test_cookie_value"
        return config

    @pytest.fixture
    def mock_event(self):
        event = MagicMock(spec=CompletionEvent)
        chat_object = AsyncMock()
        event.chat_object = chat_object
        event.get_model_reasoning.return_value = None
        return event

    @pytest.mark.asyncio
    async def test_cookie_hook_with_cookie_found(self, mock_event, mock_config):
        """Test cookie hook when cookie is found in response"""
        mock_response = "This is a test response with test_cookie_value in it"
        mock_event.get_model_response.return_value = mock_response

        await cookie(mock_event, mock_config)

        # Verify that error response was yielded
        mock_event.chat_object.io_stream.yield_response.assert_called_once()
        call_args = mock_event.chat_object.io_stream.yield_response.call_args
        response_obj = call_args[1]["response"]

        assert isinstance(response_obj, MessageWithMetadata)
        assert response_obj.content == "Some error occurred, please try again later."
        assert response_obj.metadata["type"] == "error"
        assert response_obj.metadata["extra_type"] == "cookie"

        # Verify that queue was marked as done
        mock_event.chat_object.io_stream.set_queue_done.assert_called_once()

    @pytest.mark.asyncio
    async def test_cookie_hook_without_cookie_found(self, mock_event, mock_config):
        """Test cookie hook when cookie is NOT found in response"""
        mock_response = "This is a normal response without the cookie"
        mock_event.get_model_response.return_value = mock_response

        await cookie(mock_event, mock_config)

        # Verify that no error response was yielded
        mock_event.chat_object.io_stream.yield_response.assert_not_called()
        mock_event.chat_object.io_stream.set_queue_done.assert_not_called()

    @pytest.mark.asyncio
    async def test_cookie_hook_with_cookie_disabled(self, mock_event):
        """Test cookie hook when cookie detection is disabled"""
        config = AmritaConfig()
        config.cookie.enable_cookie = False
        config.cookie.cookie = "test_cookie_value"

        mock_response = "This response contains test_cookie_value but detection is off"
        mock_event.get_model_response.return_value = mock_response

        await cookie(mock_event, config)

        # Verify that no error response was yielded
        mock_event.chat_object.io_stream.yield_response.assert_not_called()
        mock_event.chat_object.io_stream.set_queue_done.assert_not_called()

    @pytest.mark.asyncio
    async def test_cookie_hook_with_empty_cookie(self, mock_event):
        """Test cookie hook when cookie value is empty"""
        config = AmritaConfig()
        config.cookie.enable_cookie = True
        config.cookie.cookie = ""

        mock_response = "Any response content"
        mock_event.get_model_response.return_value = mock_response

        await cookie(mock_event, config)

        # Verify that no error response was yielded (empty cookie should not trigger)
        mock_event.chat_object.io_stream.yield_response.assert_not_called()
        mock_event.chat_object.io_stream.set_queue_done.assert_not_called()

    def test_posthook_decorator(self):
        """Test that posthook decorator is properly configured"""
        assert hasattr(posthook, "handle")
        assert callable(posthook.handle)
        # Check that it's configured as a completion hook with correct parameters
        assert posthook.block is False
        assert posthook.priority == 10

    @pytest.mark.asyncio
    async def test_cookie_hook_detects_canary_in_reasoning(
        self, mock_event, mock_config
    ):
        """A canary quoted while thinking is still a leak.

        Reasoning text is streamed to consumers as ``reasoning_chunk`` events,
        so scanning only the answer would let a model that echoes the canary in
        its thinking pass the guard.
        """
        mock_event.get_model_response.return_value = "I can't share that."
        mock_event.get_model_reasoning.return_value = (
            "The hidden value is test_cookie_value, but I must not reveal it."
        )

        await cookie(mock_event, mock_config)

        mock_event.chat_object.io_stream.yield_response.assert_called_once()
        mock_event.chat_object.io_stream.set_queue_done.assert_called_once()

    @pytest.mark.asyncio
    async def test_cookie_hook_ignores_clean_reasoning(self, mock_event, mock_config):
        """Reasoning without the canary must not trip the guard."""
        mock_event.get_model_response.return_value = "A normal answer."
        mock_event.get_model_reasoning.return_value = "The user wants a summary."

        await cookie(mock_event, mock_config)

        mock_event.chat_object.io_stream.yield_response.assert_not_called()
        mock_event.chat_object.io_stream.set_queue_done.assert_not_called()

    @pytest.mark.asyncio
    async def test_cookie_hook_rewrites_the_persisted_response(
        self, mock_event, mock_config
    ):
        """The canary must not survive in the response the runner stores.

        The runner writes whatever the event carries onto the response object
        and into the conversation history, so substituting only the streamed
        payload would leave the canary reachable through ``get_last_response``
        and the next turn's context.
        """
        mock_event.get_model_response.return_value = (
            "The codename is test_cookie_value."
        )

        await cookie(mock_event, mock_config)

        assert mock_event.model_response == (
            "Some error occurred, please try again later."
        )

    def test_builtin_matchers_are_registered_on_import(self):
        """Importing the package must register the built-in matchers.

        ``builtins/hooks.py`` registers its handler as an import side effect,
        so a missing import in the package leaves the leak guard dead - and a
        guard that never runs protects nothing.
        """
        from amrita_sense.hook.matcher import EventRegistry

        import amrita_core  # noqa: F401
        from amrita_core.hook.event import EventTypeEnum

        groups = EventRegistry().get_all().get(EventTypeEnum.COMPLETION, {})
        names = [fd.function.__name__ for group in groups.values() for fd in group]
        assert "cookie" in names
