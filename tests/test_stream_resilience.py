"""
Unit tests for SSE Keepalive Heartbeat, Phone Screen Wake Lock,
and Background Generation Persistence across socket disconnects.
"""
import json
import os
import time
from unittest.mock import patch, MagicMock
import pytest
import run_ui

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_sse_heartbeat_thread_emits_ping():
    """Verify that heartbeat emits : ping\\n\\n to wfile."""
    handler = run_ui.Handler.__new__(run_ui.Handler)
    handler.wfile = MagicMock()
    handler.rfile = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    request_payload = {
        "model": "gemma-4-e4b-it:latest",
        "web_search": "off",
        "messages": [{"role": "user", "content": "Hello"}]
    }

    mock_llm = MagicMock()
    mock_llm.tokenize.return_value = [1, 2]
    
    # Simulate slow model eval during which heartbeat ticks
    def slow_chat_completion(*args, **kwargs):
        time.sleep(0.15)
        yield {"choices": [{"delta": {"content": "Hi"}}]}

    mock_llm.create_chat_completion = slow_chat_completion

    with patch("run_ui.load_local_model", return_value=mock_llm), \
         patch("run_ui.is_session_continuation", return_value=False), \
         patch("run_ui.record_session_turn"):
        # Temporarily use shorter interval for fast test
        with patch.object(run_ui, "HEARTBEAT_INTERVAL", 0.05):
            handler.handle_chat(json.dumps(request_payload))

    all_writes = b"".join(call[0][0] for call in handler.wfile.write.call_args_list)
    assert b": ping\n\n" in all_writes
    assert b"data: " in all_writes


def test_client_disconnect_preserves_session_and_persists_history(tmp_path):
    """Verify that socket BrokenPipeError doesn't wipe session and saves reply."""
    handler = run_ui.Handler.__new__(run_ui.Handler)
    handler.wfile = MagicMock()
    handler.rfile = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    test_history = str(tmp_path / "test_history.json")

    request_payload = {
        "model": "gemma-4-e4b-it:latest",
        "web_search": "off",
        "messages": [{"role": "user", "content": "Calculate answer"}]
    }

    mock_llm = MagicMock()
    mock_llm.tokenize.return_value = [1, 2]
    mock_llm.n_tokens = 50

    # Simulate BrokenPipeError mid stream
    call_count = 0
    def broken_pipe_write(data):
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            raise BrokenPipeError("Client disconnected / phone locked")

    handler.wfile.write.side_effect = broken_pipe_write

    def stream_tokens(*args, **kwargs):
        yield {"choices": [{"delta": {"content": "Token1"}}]}
        yield {"choices": [{"delta": {"content": "Token2"}}]}

    mock_llm.create_chat_completion = stream_tokens

    with patch("run_ui.load_local_model", return_value=mock_llm), \
         patch("run_ui.is_session_continuation", return_value=False), \
         patch("run_ui.record_session_turn") as mock_record, \
         patch("run_ui.reset_chat_session") as mock_reset, \
         patch.object(run_ui, "HISTORY_FILE", test_history):
        handler.handle_chat(json.dumps(request_payload))

    # Must NOT call reset_chat_session
    assert not mock_reset.called
    # Must record the generated tokens
    assert mock_record.called
    # History file must be updated with the partial/completed reply
    assert os.path.exists(test_history)
    with open(test_history, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert len(saved) >= 2
    assert saved[-1]["role"] == "assistant"
    assert "Token1" in saved[-1]["content"]


def test_wake_lock_present_in_ui_scripts():
    """Verify Screen Wake Lock API calls exist in js/ui.js or js/handlers.js."""
    with open(os.path.join(PROJECT_ROOT, "js", "handlers.js"), "r", encoding="utf-8") as f:
        handlers_code = f.read()
    with open(os.path.join(PROJECT_ROOT, "js", "ui.js"), "r", encoding="utf-8") as f:
        ui_code = f.read()

    combined = handlers_code + ui_code
    assert "wakeLock" in combined
    assert "request" in combined


def test_visibility_change_sync_in_main_js():
    """Verify visibilitychange listener exists in js/main.js to recover on unlock."""
    with open(os.path.join(PROJECT_ROOT, "js", "main.js"), "r", encoding="utf-8") as f:
        main_code = f.read()

    assert "visibilitychange" in main_code
    assert "/api/history" in main_code
