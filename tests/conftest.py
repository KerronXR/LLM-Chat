import functools
import http.server
import os
import socket
import socketserver
import threading
from pathlib import Path

import pytest


BASE_DIR = Path(__file__).resolve().parent.parent


def _pick_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


TEST_PORT = _pick_free_port()
os.environ["PLAYWRIGHT_APP_URL"] = f"http://127.0.0.1:{TEST_PORT}/index.html"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format, *args):
        pass


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


@pytest.fixture(scope="session", autouse=True)
def static_server():
    handler = functools.partial(QuietHandler, directory=str(BASE_DIR))
    server = ReusableTCPServer(("127.0.0.1", TEST_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture(autouse=True)
def mock_common_endpoints(request):
    if "page" not in request.fixturenames:
        yield
        return
    
    page = request.getfixturevalue("page")
    def handle_history(route):
        if route.request.method == "POST":
            route.fulfill(status=200, body="")
        else:
            route.fulfill(status=200, content_type="application/json", body="[]")

    page.route("**/api/history", handle_history)
    page.route("**/persona.txt", lambda route: route.fulfill(status=404, body=""))
    page.route("**/api/logout", lambda route: route.fulfill(status=200, body=""))
    yield
