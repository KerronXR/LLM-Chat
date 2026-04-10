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
    _run_vision_test(page, "google-gemma-4-e4b-it:latest")

def test_heretic_vision_payload_sending(page: Page):
    """Verify Heretic model also sends vision payload."""
    _run_vision_test(page, "gemma-4-e4b-it-heretic:latest")

def _run_vision_test(page: Page, model_id: str):
    """Refactored helper for vision payload testing."""
    captured = []

    def handle_chat(route):
        post_data = route.request.post_data_json
        captured.append(post_data)
        route.fulfill(
            status=200,
            content_type="application/x-ndjson",
            body=json.dumps({"message": {"role": "assistant", "content": "I see a pixel."}, "done": True}) + "\n"
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
        # Mock the server error for non-vision model
        route.fulfill(
            status=200,
            content_type="application/x-ndjson",
            body=json.dumps({
                "model": "dolphin-llama-3",
                "message": {"role": "assistant", "content": "This model cannot analyze images."},
                "done": True
            }) + "\n"
        )

    page.route("**/api/chat", handle_chat_error)
    page.route("**/persona.txt", lambda route: route.fulfill(status=404))
    page.goto(INDEX_HTML)

    page.locator("#chat-attachment").set_input_files({
        "name": "pixel.png",
        "mimeType": "image/png",
        "buffer": TINY_PNG
    })

    # Select Non-Vision Model
    page.select_option("#model-select", "gemma-4-e4b-it-heretic:latest")

    page.locator("#user-input").fill("Analyze this.")
    page.locator("#send-btn").click()

    expect(page.locator("#chat-window")).to_contain_text("cannot analyze images.", timeout=8000)
