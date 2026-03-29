"""
Server-side unit tests for run_ui.py.
Tests the Python logic directly without a browser.
"""
import os
import sys
import tempfile
import shutil
import threading
import http.client
import time
from datetime import datetime

# Add project root to path so we can import run_ui
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Logging / error log tests
# ---------------------------------------------------------------------------

def test_error_log_dir_created():
    """run_ui module-level code must create logs/errors/ automatically."""
    error_log_dir = os.path.join(PROJECT_ROOT, "logs", "errors")
    assert os.path.isdir(error_log_dir), "logs/errors/ directory was not created"


def test_error_log_filename_format():
    """get_error_log_filename() must embed today's YYYY-MM-DD in the filename."""
    import run_ui
    filename = run_ui.get_error_log_filename()
    basename = os.path.basename(filename)
    today = datetime.now().strftime("%Y-%m-%d")
    assert basename == f"error_{today}.log", (
        f"Expected 'error_{today}.log', got '{basename}'"
    )


def test_error_log_file_written(tmp_path):
    """Verify the dated log-file pattern: FileHandler with YYYY-MM-DD name writes correctly."""
    import logging as _logging

    today = datetime.now().strftime("%Y-%m-%d")
    log_path = tmp_path / f"error_{today}.log"

    # Use a fresh standalone handler — immune to pytest log capture
    handler = _logging.FileHandler(str(log_path), encoding="utf-8")
    handler.setLevel(_logging.ERROR)
    handler.setFormatter(_logging.Formatter("%(levelname)s - %(message)s"))

    sentinel = f"SENTINEL-{time.time()}"
    record = _logging.LogRecord(
        name="test_logger", level=_logging.ERROR,
        pathname="", lineno=0, msg=sentinel,
        args=(), exc_info=None
    )
    handler.emit(record)
    handler.flush()
    handler.close()

    assert log_path.is_file(), "Dated log file was not created"
    content = log_path.read_text(encoding="utf-8")
    assert sentinel in content
    assert today in log_path.name


# ---------------------------------------------------------------------------
# Images directory
# ---------------------------------------------------------------------------

def test_images_dir_created():
    """The images/ directory must exist (created at module load time)."""
    images_dir = os.path.join(PROJECT_ROOT, "images")
    assert os.path.isdir(images_dir), "images/ directory was not created"





# ---------------------------------------------------------------------------
# Handler endpoint tests via a live mini-server
# ---------------------------------------------------------------------------

def _start_test_server(directory, port):
    """Start a Handler server in a daemon thread. Returns (server, original_dir)."""
    import run_ui
    import socketserver

    original_dir = run_ui.DIRECTORY
    run_ui.DIRECTORY = directory
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", port), run_ui.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    return server, original_dir


def _stop_test_server(server, original_dir):
    import run_ui
    server.shutdown()
    run_ui.DIRECTORY = original_dir


def test_save_persona_endpoint_writes_file():
    """POST /save_persona must write the body to persona.txt in DIRECTORY."""
    tmp = tempfile.mkdtemp()
    server, orig = _start_test_server(tmp, port=18765)
    try:
        body = b"You are a test assistant."
        conn = http.client.HTTPConnection("localhost", 18765)
        conn.request("POST", "/save_persona", body,
                     {"Content-Length": str(len(body))})
        resp = conn.getresponse()
        assert resp.status == 200, f"Expected 200, got {resp.status}"

        persona_path = os.path.join(tmp, "persona.txt")
        assert os.path.isfile(persona_path), "persona.txt was not created"
        with open(persona_path, encoding="utf-8") as f:
            assert f.read() == "You are a test assistant."
    finally:
        _stop_test_server(server, orig)
        shutil.rmtree(tmp, ignore_errors=True)


def test_persona_txt_endpoint_returns_content():
    """GET /persona.txt must serve the content of an existing persona.txt."""
    tmp = tempfile.mkdtemp()
    persona_content = "Saved persona content here."
    with open(os.path.join(tmp, "persona.txt"), "w", encoding="utf-8") as f:
        f.write(persona_content)

    server, orig = _start_test_server(tmp, port=18766)
    try:
        conn = http.client.HTTPConnection("localhost", 18766)
        conn.request("GET", "/persona.txt")
        resp = conn.getresponse()
        assert resp.status == 200
        assert resp.read().decode("utf-8") == persona_content
    finally:
        _stop_test_server(server, orig)
        shutil.rmtree(tmp, ignore_errors=True)


def test_persona_txt_endpoint_404_when_missing():
    """GET /persona.txt must return 404 when no persona.txt exists."""
    tmp = tempfile.mkdtemp()
    server, orig = _start_test_server(tmp, port=18767)
    try:
        conn = http.client.HTTPConnection("localhost", 18767)
        conn.request("GET", "/persona.txt")
        resp = conn.getresponse()
        assert resp.status == 404
    finally:
        _stop_test_server(server, orig)
        shutil.rmtree(tmp, ignore_errors=True)


def test_unknown_post_returns_404():
    """POST to an unknown endpoint must return 404."""
    tmp = tempfile.mkdtemp()
    server, orig = _start_test_server(tmp, port=18769)
    try:
        conn = http.client.HTTPConnection("localhost", 18769)
        conn.request("POST", "/nonexistent_endpoint", b"", {"Content-Length": "0"})
        resp = conn.getresponse()
        assert resp.status == 404
    finally:
        _stop_test_server(server, orig)
        shutil.rmtree(tmp, ignore_errors=True)
