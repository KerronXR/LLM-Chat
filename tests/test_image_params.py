import pytest
from playwright.sync_api import Page, expect
import json
import os
import re
import base64

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.getenv("PLAYWRIGHT_APP_URL", f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html")

def _block_persona(page: Page):
    """Block persona.txt so loadSavedPersona doesn't interfere."""
    page.route("**/persona.txt",
               lambda route: route.fulfill(status=404))

def ndjson_response(*chunks):
    return "".join(json.dumps(chunk) + "\n" for chunk in chunks).encode()

def test_image_parameters_sent_to_backend(page: Page):
    """Verifies that width, height, and batch size are sent to the backend."""
    captured_requests = []

    def handle_generate(route):
        captured_requests.append(route.request.post_data_json)
        route.fulfill(
            status=200,
            content_type="application/x-ndjson",
            body=ndjson_response(
                {"url": "/images/gen1.png"},
                {"url": "/images/gen2.png"},
                {"done": True, "urls": ["/images/gen1.png", "/images/gen2.png"]}
            )
        )

    page.route("**/generate_image", handle_generate)
    _block_persona(page)
    page.goto(INDEX_HTML)

    # Enable auto generation
    page.locator("#auto-image-checkbox").check()

    # Set image parameters
    # Note: We need to add these IDs to index.html
    page.select_option("#image-size-select", "768x512")
    page.fill("#batch-size-slider", "2")

    page.locator("#user-input").fill("a sunset over mountains")
    page.locator("#send-btn").click()

    # Wait for the images to appear
    expect(page.locator(".image-msg")).to_be_visible(timeout=8000)
    
    # Check that multiple images are rendered
    expect(page.locator(".image-msg img")).to_have_count(2)

    assert len(captured_requests) == 1
    body = captured_requests[0]
    assert body["width"] == 768
    assert body["height"] == 512
    assert body["batch_size"] == 2
    assert body["prompt"] == "a sunset over mountains"
