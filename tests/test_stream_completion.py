"""
Test stream completion handling:
1. run_ui.py sets Connection: close header for /api/chat.
2. js/handlers.js breaks out of stream reader loop on json.done.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def test_handlers_js_breaks_on_json_done():
    """Verify handlers.js has break or reader cancellation on json.done."""
    handlers_path = os.path.join(PROJECT_ROOT, "js", "handlers.js")
    with open(handlers_path, "r", encoding="utf-8") as f:
        code = f.read()

    # json.done block must contain break or return
    done_idx = code.find("if (json.done)")
    assert done_idx != -1, "if (json.done) block not found in js/handlers.js"

    # Within the json.done block, there must be a break or return
    done_block = code[done_idx:done_idx + 1500]
    has_break = "break;" in done_block or "return;" in done_block
    assert has_break, "js/handlers.js does not break/return on json.done, causing infinite hang"


def test_run_ui_connection_header_close():
    """Verify run_ui.py handle_chat sends Connection: close."""
    run_ui_path = os.path.join(PROJECT_ROOT, "run_ui.py")
    with open(run_ui_path, "r", encoding="utf-8") as f:
        code = f.read()

    assert "self.send_header('Connection', 'close')" in code or 'self.send_header("Connection", "close")' in code
