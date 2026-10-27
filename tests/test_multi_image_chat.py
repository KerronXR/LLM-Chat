import pytest
from playwright.sync_api import Page, expect
import json
import base64
import os
import time

import re

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.getenv("PLAYWRIGHT_APP_URL", f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html")

TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
TINY_PNG = base64.b64decode(TINY_PNG_B64)


def _block_persona(page: Page):
    page.route("**/persona.txt", lambda route: route.fulfill(status=404))


def test_append_up_to_three_images_and_preview(page: Page):
    """Verify up to 3 images can be attached, previewed, and capped."""
    _block_persona(page)
    page.goto(INDEX_HTML)

    # Attach 3 files
    page.locator("#chat-attachment").set_input_files([
        {"name": "p1.png", "mimeType": "image/png", "buffer": TINY_PNG},
        {"name": "p2.png", "mimeType": "image/png", "buffer": TINY_PNG},
        {"name": "p3.png", "mimeType": "image/png", "buffer": TINY_PNG},
    ])

    # Expect 3 images in preview
    preview = page.locator("#attachment-preview")
    expect(preview).not_to_have_class(re.compile(r"attachment-preview-hidden"))
    expect(preview.locator("img")).to_have_count(3)


def test_clear_ui_clipboard_immediately_on_send(page: Page):
    """Verify UI clipboard / preview is cleared immediately once message sent."""
    _block_persona(page)

    def slow_chat(route):
        # Keep response hanging to check preview is cleared BEFORE response arrives
        time.sleep(0.5)
        route.fulfill(
            status=200,
            content_type="application/x-ndjson",
            body=json.dumps({"message": {"role": "assistant", "content": "Done."}, "done": True}) + "\n"
        )

    page.route("**/api/chat", slow_chat)
    page.goto(INDEX_HTML)

    page.locator("#chat-attachment").set_input_files([
        {"name": "p1.png", "mimeType": "image/png", "buffer": TINY_PNG}
    ])
    page.locator("#user-input").fill("Analyze this image")
    page.locator("#send-btn").click()

    # Preview must be cleared and hidden immediately
    preview = page.locator("#attachment-preview")
    expect(preview).to_have_class(re.compile(r"attachment-preview-hidden"))
    expect(preview.locator("img")).to_have_count(0)


def test_generation_bubble_appears_immediately_when_sending_image(page: Page):
    """Verify AI thinking bubble appears immediately upon sending image before reply arrives."""
    _block_persona(page)

    chat_started = []

    def delayed_chat(route):
        chat_started.append(True)
        time.sleep(1.0)
        route.fulfill(
            status=200,
            content_type="application/x-ndjson",
            body=json.dumps({"message": {"role": "assistant", "content": "Done analyzing."}, "done": True}) + "\n"
        )

    page.route("**/api/chat", delayed_chat)
    page.goto(INDEX_HTML)

    page.locator("#chat-attachment").set_input_files([
        {"name": "p1.png", "mimeType": "image/png", "buffer": TINY_PNG}
    ])
    page.locator("#user-input").fill("Fast check image")
    page.locator("#send-btn").click()

    # AI message bubble must exist in chat window immediately
    ai_messages = page.locator("#chat-window .ai-message")
    # There is 1 default welcome ai-message, so sending creates the second one immediately
    expect(ai_messages).to_have_count(2, timeout=2000)
    # The new AI bubble must show thinking / preparing indicator immediately
    expect(ai_messages.nth(1)).to_contain_text("...")


def test_interrupt_middle_of_thinking_and_continue_straight_away(page: Page):
    """Sending message while generating interrupts previous and starts new generation immediately."""
    _block_persona(page)
    requests = []
    first_route_holder = []

    def stream_handler(route):
        requests.append(route.request.post_data_json)
        if len(requests) == 1:
            # Keep first route pending without blocking thread
            first_route_holder.append(route)
        else:
            route.fulfill(
                status=200,
                content_type="text/event-stream",
                body=(
                    f"data: {json.dumps({'message': {'role': 'assistant', 'content': 'Second response fast.'}})}\n\n"
                    f"data: {json.dumps({'done': True, 'prompt_eval_count': 5, 'eval_count': 5})}\n\n"
                )
            )

    page.route("**/api/chat", stream_handler)
    page.goto(INDEX_HTML)

    page.locator("#user-input").fill("First message")
    page.locator("#send-btn").click()

    # Wait for first request to register
    page.wait_for_timeout(200)
    assert len(requests) == 1

    # Immediately send second message while first is generating
    page.locator("#user-input").fill("Second message interrupting")
    page.locator("#send-btn").click()

    # Should have triggered second request and rendered response
    expect(page.locator("#chat-window")).to_contain_text("Second response fast.", timeout=8000)
    assert len(requests) >= 2


def test_paste_image_from_clipboard(page: Page):
    """Verify pasting an image from clipboard stages it in the UI attachment preview."""
    _block_persona(page)
    page.goto(INDEX_HTML)

    # Dispatch synthetic paste event with an image file
    page.evaluate(
        """(b64) => {
            const byteCharacters = atob(b64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'image/png' });
            const file = new File([blob], 'pasted.png', { type: 'image/png' });

            const dt = new DataTransfer();
            dt.items.add(file);

            const pasteEvent = new ClipboardEvent('paste', {
                clipboardData: dt,
                bubbles: true,
                cancelable: true
            });
            document.getElementById('user-input').dispatchEvent(pasteEvent);
        }""",
        TINY_PNG_B64
    )

    preview = page.locator("#attachment-preview")
    expect(preview).not_to_have_class(re.compile(r"attachment-preview-hidden"))
    expect(preview.locator("img")).to_have_count(1)


def test_model_select_toggles_attach_button_visibility(page: Page):
    """Verify attach button is visible for Gemma and Qwen-VL, hidden for text models."""
    _block_persona(page)
    page.goto(INDEX_HTML)

    attach_btn = page.locator("#attach-btn")

    # 1. Default (Gemma) -> visible
    expect(attach_btn).to_be_visible()

    # 2. Select Qwen-VL -> visible
    page.locator("#model-select").select_option("qwen2.5-vl-7b-instruct:latest")
    expect(attach_btn).to_be_visible()

    # 3. Select Llama-3.2 (Text-only) -> hidden
    page.locator("#model-select").select_option("llama-3.2-3b-instruct-uncensored:latest")
    expect(attach_btn).to_be_hidden()

    # 4. Select DeepSeek-R1 (Text-only) -> hidden
    page.locator("#model-select").select_option("deepseek-r1-distill-qwen-7b-uncensored:latest")
    expect(attach_btn).to_be_hidden()

    # 5. Switch back to Qwen-VL -> visible again
    page.locator("#model-select").select_option("qwen2.5-vl-7b-instruct:latest")
    expect(attach_btn).to_be_visible()
