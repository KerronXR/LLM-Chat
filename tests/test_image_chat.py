"""
Tests for chat-driven image generation.
Verifies that checking 'Auto Generate Images' triggers FastSD instead of LLM,
and 'Use My Image' includes the uploaded reference image.
"""
import pytest
from playwright.sync_api import Page, expect
import json
import os
import re
import base64

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html"

TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
TINY_PNG = base64.b64decode(TINY_PNG_B64)


def _block_persona(page: Page):
    """Block persona.txt so loadSavedPersona doesn't interfere."""
    page.route("http://localhost:8000/persona.txt",
               lambda route: route.fulfill(status=404))


# -------------------------------------------------------------------
# 1. "Auto Generate Images" checkbox routes to FastSD, not LLM
# -------------------------------------------------------------------

def test_auto_generate_checkbox_routes_to_fastsd(page: Page):
    """Checking 'Auto Generate Images' should call /generate_image, NOT /api/chat."""
    llm_called = []
    fastsd_called = []

    def handle_llm(route):
        llm_called.append(True)
        route.fulfill(status=200, body=json.dumps(
            {"message": {"role": "assistant", "content": "Hi"}, "done": True}
        ))

    def handle_fastsd(route):
        fastsd_called.append(route.request.post_data_json)
        route.fulfill(status=200, content_type="application/json",
                      body='{"url": "/images/gen_test.png"}')

    page.route("**/api/chat", handle_llm)
    page.route("http://localhost:8000/generate_image", handle_fastsd)
    _block_persona(page)
    page.goto(INDEX_HTML)

    # Enable auto generation
    page.locator("#auto-image-checkbox").check()

    page.locator("#user-input").fill("a cartoon dog with big eyes")
    page.locator("#send-btn").click()

    # Wait for the image message to appear
    expect(page.locator(".image-msg")).to_be_visible(timeout=8000)

    # LLM should NOT have been called
    assert len(llm_called) == 0, "LLM was called but should not have been"
    # FastSD SHOULD have been called
    assert len(fastsd_called) == 1
    assert "cartoon dog" in fastsd_called[0]["prompt"].lower()


def test_progress_bar_visible_during_gen(page: Page):
    """The progress bar should be visible during generation."""
    page.route("http://localhost:8000/generate_image", lambda route: (
        # Delay the response to see the progress bar
        page.wait_for_timeout(1000),
        route.fulfill(status=200, content_type="application/json",
                      body='{"url": "/images/gen.png"}')
    ))
    _block_persona(page)
    page.goto(INDEX_HTML)

    page.locator("#auto-image-checkbox").check()
    page.locator("#user-input").fill("a cute cat")
    page.locator("#send-btn").click()

    # Progress bar should be visible while loading
    expect(page.locator("#progress-container")).not_to_have_class(re.compile(r"progress-hidden"))
    
    expect(page.locator(".image-msg")).to_be_visible(timeout=8000)
    
    # After done, it should be hidden
    expect(page.locator("#progress-container")).to_have_class(re.compile(r"progress-hidden"))


# -------------------------------------------------------------------
# 2. Normal messages still go to LLM when checkbox is OFF
# -------------------------------------------------------------------

def test_normal_message_goes_to_llm_when_checkbox_off(page: Page):
    """Messages go to Ollama as usual when checkbox is unchecked."""
    llm_called = []
    fastsd_called = []

    def handle_llm(route):
        llm_called.append(True)
        route.fulfill(status=200, body=json.dumps(
            {"message": {"role": "assistant", "content": "Hello!"}, "done": True}
        ))

    page.route("**/api/chat", handle_llm)
    page.route("http://localhost:8000/generate_image",
               lambda route: (fastsd_called.append(True),
                               route.fulfill(status=200, body='{}')))
    _block_persona(page)
    page.goto(INDEX_HTML)

    # Checkbox is OFF by default
    page.locator("#user-input").fill("Tell me a joke")
    page.locator("#send-btn").click()

    expect(page.locator("#chat-window")).to_contain_text("Hello!", timeout=8000)
    assert len(llm_called) == 1
    assert len(fastsd_called) == 0


# -------------------------------------------------------------------
# 3. Reference image usage
# -------------------------------------------------------------------

def test_image_sent_with_checkbox_on(page: Page):
    """If checkbox is on and image uploaded, it should be used."""
    captured = []

    def handle_generate(route):
        captured.append(route.request.post_data_json)
        route.fulfill(status=200, content_type="application/json",
                      body='{"url": "/images/gen.png"}')

    page.route("http://localhost:8000/generate_image", handle_generate)
    _block_persona(page)
    page.goto(INDEX_HTML)

    # Upload an image first
    page.locator("#image-upload").set_input_files({
        "name": "ref.png",
        "mimeType": "image/png",
        "buffer": TINY_PNG
    })
    expect(page.locator("#image-preview-container")).to_be_visible()

    # Enable auto generation
    page.locator("#auto-image-checkbox").check()

    page.locator("#user-input").fill("cyberpunk style")
    page.locator("#send-btn").click()

    expect(page.locator(".image-msg")).to_be_visible(timeout=8000)

    assert len(captured) == 1
    body = captured[0]
    assert "cyberpunk style" in body["prompt"].lower()
    # init_image should be present
    assert "init_image" in body
    assert body["init_image"].startswith("data:image/png;base64,")


# -------------------------------------------------------------------
# 4. Error handling
# -------------------------------------------------------------------

def test_generate_image_error_shown_in_chat(page: Page):
    """If image generation fails, an error message should appear in chat."""
    page.route("http://localhost:8000/generate_image",
               lambda route: route.fulfill(status=500, body="FastSD down"))
    _block_persona(page)
    page.goto(INDEX_HTML)

    page.locator("#auto-image-checkbox").check()
    page.locator("#user-input").fill("a broken image")
    page.locator("#send-btn").click()

    # Error should be shown in chat, not via an alert
    error_msg = page.locator(".error-message")
    expect(error_msg).to_be_visible(timeout=8000)
    expect(error_msg).to_contain_text("Image generation failed")


# -------------------------------------------------------------------
# 5. Image Upscaling
# -------------------------------------------------------------------

def test_image_upscale_flow(page: Page):
    """Clicking the upscale button on a generated image calls /upscale_image."""
    upscale_called = []

    def handle_generate(route):
        route.fulfill(status=200, content_type="application/json",
                      body='{"url": "http://localhost:8000/images/gen_test.png"}')

    def handle_upscale(route):
        upscale_called.append(route.request.post_data_json)
        route.fulfill(status=200, content_type="application/json",
                      body='{"url": "/images/upscaled_test.png"}')

    page.route("http://localhost:8000/generate_image", handle_generate)
    page.route("http://localhost:8000/upscale_image", handle_upscale)
    _block_persona(page)
    
    # Mock fetching the original image so it can be blobbed
    page.route("**/images/gen_test.png", lambda route: route.fulfill(
        status=200, content_type="image/png", body=TINY_PNG
    ))
    
    page.goto(INDEX_HTML)

    page.locator("#auto-image-checkbox").check()
    page.locator("#user-input").fill("a tiny image to upscale")
    page.locator("#send-btn").click()

    expect(page.locator(".image-msg")).to_be_visible(timeout=8000)
    
    upscale_btn = page.locator(".upscale-btn").first
    expect(upscale_btn).to_be_visible()
    upscale_btn.click()

    # The button should change state
    expect(upscale_btn).to_have_text(re.compile(r"Upscaled!"), timeout=8000)

    # A new image message should appear
    expect(page.locator(".image-msg")).to_have_count(2)
    assert len(upscale_called) == 1
    assert upscale_called[0]["mode"] == "aura_sr"

def test_image_upscale_error(page: Page):
    """If upscaling fails, show an error message."""
    page.route("http://localhost:8000/generate_image", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{"url": "http://localhost:8000/images/gen_test.png"}'
    ))
    page.route("**/images/gen_test.png", lambda route: route.fulfill(
        status=200, content_type="image/png", body=TINY_PNG
    ))
    page.route("http://localhost:8000/upscale_image", lambda route: route.fulfill(
        status=500, body='{"error": "Upscale failed"}'
    ))
    _block_persona(page)
    page.goto(INDEX_HTML)

    page.locator("#auto-image-checkbox").check()
    page.locator("#user-input").fill("a tiny image to upscale")
    page.locator("#send-btn").click()

    expect(page.locator(".image-msg")).to_be_visible(timeout=8000)
    upscale_btn = page.locator(".upscale-btn").first
    upscale_btn.click()

    error_msg = page.locator(".error-message")
    expect(error_msg).to_be_visible(timeout=8000)
    expect(error_msg).to_contain_text("Upscale failed")


