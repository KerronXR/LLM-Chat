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
