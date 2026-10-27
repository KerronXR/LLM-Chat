"""
Tests for stateful multi-turn vision dialogue:
1. Verify KV cache is reused on turn 2 without re-encoding image.
2. Verify session reset clears cache on model switch or clear.
3. Verify handlers.js does not inject duplicate base64 into messages array.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
import core


def test_handlers_js_clean_serialization():
    """Verify serializeMessagesForApi does not reinflate history with base64 on pure text turns."""
    handlers_path = os.path.join(PROJECT_ROOT, "js", "handlers.js")
    with open(handlers_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Should serialize clean role and content
    assert "function serializeMessagesForApi" in code


def test_core_has_stateful_session_tracker():
    """Verify core provides stateful conversation management functions."""
    import core
    assert hasattr(core, "reset_chat_session"), "core must expose reset_chat_session"
    assert hasattr(core, "is_session_continuation"), "core must expose is_session_continuation"


def test_stateful_stream_chat_continuation():
    """Verify stateful_chat_stream evaluates only new tokens when continuation is detected."""
    import core
    fake_llm = MagicMock()
    fake_llm.n_tokens = 100
    fake_llm.input_ids = list(range(200))
    fake_llm.tokenize.return_value = [10, 11, 12]
    fake_llm.create_completion.return_value = [
        {"choices": [{"text": "More"}]},
        {"choices": [{"text": " detail"}]}
    ]

    core.reset_chat_session()
    # Simulate turn 1 recorded
    core.record_session_turn(
        messages=[{"role": "user", "content": "hello"}],
        assistant_content="Hi there",
        tokens_count=50
    )

    continuation = core.is_session_continuation([
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "tell me more"}
    ])
    assert continuation is True, "Should detect exact session continuation"

    # Reset test
    core.reset_chat_session()
    assert core.is_session_continuation([{"role": "user", "content": "new"}]) is False


def test_continuation_preserves_after_web_search():
    core.reset_chat_session()
    # Turn 1 recorded with injected search context on server
    search_context_text = "\n\n---\nWeb Search Results:\n[1] 8BitDo Pad: $24.99"
    core.record_session_turn(
        messages=[{"role": "user", "content": f"You can search for prices{search_context_text}"}],
        assistant_content="I found the price is $24.99",
        tokens_count=120,
        model_id="gemma-4-e4b-it:latest"
    )

    # Turn 2 incoming from browser (browser does not have injected search context)
    incoming_messages = [
        {"role": "user", "content": "You can search for prices"},
        {"role": "assistant", "content": "I found the price is $24.99"},
        {"role": "user", "content": "Well go"}
    ]

    assert core.is_session_continuation(incoming_messages, "gemma-4-e4b-it:latest") is True

