import json
from unittest.mock import patch, MagicMock
import run_ui


def test_handle_chat_web_search_trigger():
    # Verify that web_search in request triggers safe_duckduckgo_search and injects context
    mock_results = [
        {"title": "Test Title", "url": "https://example.com", "snippet": "Test search snippet"}
    ]

    handler = run_ui.Handler.__new__(run_ui.Handler)
    handler.wfile = MagicMock()
    handler.rfile = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    request_payload = {
        "model": "gemma-4-e4b-it:latest",
        "web_search": "on",
        "messages": [{"role": "user", "content": "What is the latest news in 2026?"}]
    }

    mock_llm = MagicMock()
    mock_llm.tokenize.return_value = [1, 2, 3]
    mock_llm.create_chat_completion.return_value = [
        {"choices": [{"delta": {"content": "News response based on web"}}]}
    ]

    with patch("run_ui.load_local_model", return_value=mock_llm), \
         patch("run_ui.is_session_continuation", return_value=False), \
         patch("run_ui.record_session_turn"), \
         patch("web_search.safe_duckduckgo_search", return_value=mock_results) as mock_search:
        handler.handle_chat(json.dumps(request_payload))

    assert mock_search.called
    written_data = "".join(call[0][0].decode("utf-8") for call in handler.wfile.write.call_args_list)
    assert "searching" in written_data
    assert "sources" in written_data
    assert "Test Title" in written_data


def test_handle_chat_vision_follow_up_triggers_search():
    mock_results = [
        {"title": "Keychron Q1 Price", "url": "https://example.com/keychron", "snippet": "Keychron Q1 starts at $169."}
    ]

    handler = run_ui.Handler.__new__(run_ui.Handler)
    handler.wfile = MagicMock()
    handler.rfile = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    # Exact conversation sequence from user history:
    # Turn 0: image + question
    # Turn 1: model identified keyboard but no price
    # Turn 2: user says "You need to research"
    request_payload = {
        "model": "gemma-4-e4b-it:latest",
        "web_search": "auto",
        "messages": [
            {"role": "user", "content": "How much that costs?"},
            {
                "role": "assistant",
                "content": "This is a Keychron Q1 Pro keyboard, but the image does not contain the price."
            },
            {"role": "user", "content": "You need to research"}
        ]
    }

    mock_llm = MagicMock()
    mock_llm.tokenize.return_value = [1, 2, 3]
    mock_llm.create_chat_completion.return_value = [
        {"choices": [{"delta": {"content": "The Keychron Q1 costs $169."}}]}
    ]

    with patch("run_ui.load_local_model", return_value=mock_llm), \
         patch("run_ui.is_session_continuation", return_value=False), \
         patch("run_ui.record_session_turn"), \
         patch("web_search.safe_duckduckgo_search", return_value=mock_results) as mock_search:
        handler.handle_chat(json.dumps(request_payload))

    assert mock_search.called
    search_arg = mock_search.call_args[0][0]
    assert "Keychron" in search_arg


def test_handle_chat_stock_query_injects_live_price():
    mock_results = [
        {"title": "Live Stock: AMZN", "url": "https://finance.yahoo.com/quote/AMZN", "snippet": "AMZN is trading at $249.09 USD."}
    ]

    handler = run_ui.Handler.__new__(run_ui.Handler)
    handler.wfile = MagicMock()
    handler.rfile = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    request_payload = {
        "model": "gemma-4-e4b-it:latest",
        "web_search": "auto",
        "messages": [
            {"role": "user", "content": "How much is amzn stock"}
        ]
    }

    mock_llm = MagicMock()
    mock_llm.tokenize.return_value = [1, 2, 3]
    mock_llm.create_chat_completion.return_value = [
        {"choices": [{"delta": {"content": "Amazon stock is currently $249.09."}}]}
    ]

    with patch("run_ui.load_local_model", return_value=mock_llm), \
         patch("run_ui.is_session_continuation", return_value=False), \
         patch("run_ui.record_session_turn"), \
         patch("web_search.safe_duckduckgo_search", return_value=mock_results) as mock_search:
        handler.handle_chat(json.dumps(request_payload))

    assert mock_search.called
    written_data = "".join(call[0][0].decode("utf-8") for call in handler.wfile.write.call_args_list)
    assert "Live Stock: AMZN" in written_data
    assert "searching" in written_data


def test_history_and_session_not_polluted_by_search_context(tmp_path):
    from core import is_session_continuation, _chat_session, reset_chat_session
    reset_chat_session()

    mock_results = [
        {"title": "GTA 6 News", "url": "https://example.com/gta6", "snippet": "GTA 6 launches Fall 2025."}
    ]

    handler = run_ui.Handler.__new__(run_ui.Handler)
    handler.wfile = MagicMock()
    handler.rfile = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    hist_file = tmp_path / "history.json"
    user_q = "Where gta 6 will be released?"
    request_payload = {
        "model": "qwen2.5-vl-7b-instruct:latest",
        "web_search": "auto",
        "messages": [{"role": "user", "content": user_q}]
    }

    mock_llm = MagicMock()
    mock_llm.tokenize.return_value = [1, 2, 3]
    mock_llm.n_tokens = 10
    mock_llm.create_chat_completion.return_value = [
        {"choices": [{"delta": {"content": "GTA 6 will release on PS5 and Xbox."}}]}
    ]

    with patch("run_ui.HISTORY_FILE", str(hist_file)), \
         patch("run_ui.load_local_model", return_value=mock_llm), \
         patch("web_search.safe_duckduckgo_search", return_value=mock_results):
        handler.handle_chat(json.dumps(request_payload))

    saved_history = json.loads(hist_file.read_text(encoding="utf-8"))
    assert saved_history[0]["content"] == user_q
    assert "<web_search_results>" not in saved_history[0]["content"]
    assert "<web_search_results>" not in _chat_session["messages"][0]["content"]

    next_turn_msgs = saved_history + [{"role": "user", "content": "What about PC?"}]
    assert is_session_continuation(next_turn_msgs, "qwen2.5-vl-7b-instruct:latest") is True


def test_web_search_runs_when_mode_on_with_attachments():
    mock_results = [
        {"title": "Doc Reference", "url": "https://example.com/doc", "snippet": "Reference info."}
    ]

    handler = run_ui.Handler.__new__(run_ui.Handler)
    handler.wfile = MagicMock()
    handler.rfile = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    request_payload = {
        "model": "qwen2.5-vl-7b-instruct:latest",
        "web_search": "on",
        "attachments": [{"type": "file", "name": "notes.txt", "content": "Check RTX 5090"}],
        "messages": [{"role": "user", "content": "Verify this against current web specs"}]
    }

    mock_llm = MagicMock()
    mock_llm.tokenize.return_value = [1, 2, 3]
    mock_llm.create_chat_completion.return_value = [
        {"choices": [{"delta": {"content": "Verified."}}]}
    ]

    with patch("run_ui.load_local_model", return_value=mock_llm), \
         patch("run_ui.is_session_continuation", return_value=False), \
         patch("run_ui.record_session_turn"), \
         patch("web_search.safe_duckduckgo_search", return_value=mock_results) as mock_search:
        handler.handle_chat(json.dumps(request_payload))

    assert mock_search.called



