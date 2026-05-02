"""
Frontend (Playwright) tests for TPS badge display in AI messages.
Mocks /api/chat to return NDJSON with tps/avg_tps fields.
"""
import json
import time

import pytest


def _build_ndjson_body(tokens, avg_tps=12.5):
    """Build chunked-encoded NDJSON body simulating backend stream."""
    lines = []
    for i, tok in enumerate(tokens, 1):
        live_tps = round(i / 0.1, 2)  # Fake live tps
        lines.append(json.dumps({
            "model": "gemma-4-e4b-it-heretic:latest",
            "message": {"role": "assistant", "content": tok},
            "done": False,
            "tps": live_tps,
        }))
    lines.append(json.dumps({
        "model": "gemma-4-e4b-it-heretic:latest",
        "message": {"role": "assistant", "content": ""},
        "done": True,
        "prompt_eval_count": 5,
        "eval_count": len(tokens),
        "context_length": 8192,
        "avg_tps": avg_tps,
    }))
    return "\n".join(lines)


@pytest.fixture
def chat_page(page):
    """Navigate to app and mock chat endpoint with TPS data."""
    page.goto(page.context.browser.contexts[0].pages[0].url.replace(page.url, "") + "/index.html")
    return page


class TestTpsBadge:
    """TPS badge appears after generation with correct value."""

    def test_tps_badge_appears_after_generation(self, page):
        avg = 8.42
        body = _build_ndjson_body(["Hello", " there"], avg_tps=avg)

        def handle_chat(route):
            route.fulfill(
                status=200,
                headers={"Content-Type": "application/x-ndjson"},
                body=body,
            )

        page.route("**/api/chat", handle_chat)
        app_url = f"http://127.0.0.1:{page.context.browser.contexts[0].pages[0].url.split(':')[2].split('/')[0]}/index.html"
        page.goto(app_url)
        page.wait_for_load_state("domcontentloaded")

        page.fill("#user-input", "hello")
        page.click("#send-btn")
        page.wait_for_selector(".tps-badge", timeout=5000)

        badge = page.query_selector(".tps-badge")
        assert badge is not None, "TPS badge not found after generation"
        assert str(avg) in badge.text_content()

    def test_tps_badge_shows_correct_value(self, page):
        avg = 15.73
        body = _build_ndjson_body(["Test", " output"], avg_tps=avg)

        page.route("**/api/chat", lambda route: route.fulfill(
            status=200,
            headers={"Content-Type": "application/x-ndjson"},
            body=body,
        ))
        app_url = f"http://127.0.0.1:{page.context.browser.contexts[0].pages[0].url.split(':')[2].split('/')[0]}/index.html"
        page.goto(app_url)
        page.wait_for_load_state("domcontentloaded")

        page.fill("#user-input", "test")
        page.click("#send-btn")
        page.wait_for_selector(".tps-badge", timeout=5000)

        badge_text = page.text_content(".tps-badge")
        assert "15.73" in badge_text
        assert "tok/s" in badge_text

    def test_no_tps_badge_on_error(self, page):
        """Error response → no badge."""
        error_body = json.dumps({
            "error": "Model crashed",
            "done": True,
            "prompt_eval_count": 0,
            "eval_count": 0,
            "context_length": 8192,
        })

        page.route("**/api/chat", lambda route: route.fulfill(
            status=200,
            headers={"Content-Type": "application/x-ndjson"},
            body=error_body,
        ))
        app_url = f"http://127.0.0.1:{page.context.browser.contexts[0].pages[0].url.split(':')[2].split('/')[0]}/index.html"
        page.goto(app_url)
        page.wait_for_load_state("domcontentloaded")

        page.fill("#user-input", "break")
        page.click("#send-btn")

        # Wait for error msg to appear, then check no badge
        page.wait_for_selector(".error-msg", timeout=5000)
        badge = page.query_selector(".tps-badge")
        assert badge is None, "TPS badge should not appear on error"
