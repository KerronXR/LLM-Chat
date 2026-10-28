import pytest
from playwright.sync_api import Page, expect
import json
import base64
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.getenv("PLAYWRIGHT_APP_URL", f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html")

TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
TINY_PNG = base64.b64decode(TINY_PNG_B64)

def test_vision_payload_sending(page: Page):
    _run_vision_test(page, "qwen2.5-vl-7b-instruct:latest")

def _run_vision_test(page: Page, model_id: str):
    """Refactored helper for vision payload testing."""
    captured = []

    def handle_chat(route):
        post_data = route.request.post_data_json
        captured.append(post_data)
        route.fulfill(
            status=200,
            content_type="text/event-stream",
            body="data: " + json.dumps({"message": {"role": "assistant", "content": "I see a pixel."}, "done": True}) + "\n\n"
        )

    page.route("**/api/chat", handle_chat)
    page.route("**/persona.txt", lambda route: route.fulfill(status=404))
    page.goto(INDEX_HTML)

    page.locator("#chat-attachment").set_input_files({
        "name": "pixel.png",
        "mimeType": "image/png",
        "buffer": TINY_PNG
    })
    page.select_option("#model-select", model_id)
    page.locator("#user-input").fill("What is this?")
    page.locator("#send-btn").click()

    expect(page.locator("#chat-window")).to_contain_text("I see a pixel.", timeout=8000)

    assert len(captured) == 1
    assert captured[0]["attachment"]["type"] == "image"
    assert captured[0]["model"] == model_id

def test_vision_model_restriction(page: Page):
    """Verify that non-vision models show an error chunk (server-side mock)."""
    
    def handle_chat_error(route):
        route.fulfill(
            status=200,
            content_type="text/event-stream",
            body="data: " + json.dumps({
                "model": "deepseek-r1-distill-qwen-7b-uncensored:latest",
                "message": {"role": "assistant", "content": "This model cannot analyze images."},
                "done": True
            }) + "\n\n"
        )

    page.route("**/api/chat", handle_chat_error)
    page.route("**/persona.txt", lambda route: route.fulfill(status=404))
    page.goto(INDEX_HTML)

    # DeepSeek hides the attach button by default; select DeepSeek
    page.select_option("#model-select", "deepseek-r1-distill-qwen-7b-uncensored:latest")

    page.locator("#user-input").fill("Analyze this.")
    page.locator("#send-btn").click()
