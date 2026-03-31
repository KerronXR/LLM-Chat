import pytest
from playwright.sync_api import Page, expect
import json
import os
import re

# Get the absolute path to the index.html
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html"

def test_initial_state(page: Page):
    page.goto(INDEX_HTML)
    
    # Check title
    expect(page).to_have_title("Veloxify Local AI | Uncensored")
    
    # Check default model
    model_select = page.locator("#model-select")
    expect(model_select).to_have_value("gemma-3-12b-it:latest")
    
    # Check default system prompt
    system_prompt = page.locator("#system-prompt")
    expect(system_prompt).to_have_value(re.compile(".*You are Gemma.*"))

    # Check initial button state
    stop_btn = page.locator("#stop-btn")
    expect(stop_btn).to_have_text("New")
    expect(stop_btn).to_be_enabled()

def test_model_selection_updates_prompt(page: Page):
    page.goto(INDEX_HTML)
    
    model_select = page.locator("#model-select")
    system_prompt = page.locator("#system-prompt")
    
    # Switch to Qwen
    model_select.select_option("qwen3.5:latest")
    expect(system_prompt).to_have_value(re.compile(".*helpful and capable AI assistant.*"))
    
    # Switch back to Dolphin
    model_select.select_option("dolphin-llama3:latest")
    expect(system_prompt).to_have_value(re.compile(".*You are Dolphin.*"))

def test_clear_chat(page: Page):
    page.goto(INDEX_HTML)
    
    chat_window = page.locator("#chat-window")
    clear_btn = page.locator("#clear-btn")
    
    # Trigger clear
    clear_btn.click()
    
    # Check if cleared
    expect(chat_window).to_contain_text("Chat cleared")

def test_message_flow_mocked(page: Page):
    # Mock Ollama API for /api/chat
    def handle_route(route):
        chunks = [
            {"message": {"role": "assistant", "content": "Hello"}, "done": False},
            {"message": {"role": "assistant", "content": " there"}, "done": False},
            {"message": {"role": "assistant", "content": "!"}, "done": True, "prompt_eval_count": 10, "eval_count": 5}
        ]
        
        body = "".join(json.dumps(c) + "\n" for c in chunks).encode()
        route.fulfill(
            status=200,
            content_type="application/x-ndjson",
            body=body
        )

    page.route("**/api/chat", handle_route)
    page.goto(INDEX_HTML)
    
    user_input = page.locator("#user-input")
    send_btn = page.locator("#send-btn")
    chat_window = page.locator("#chat-window")
    
    user_input.fill("Hello AI")
    send_btn.click()
    
    # Check user message
    expect(chat_window).to_contain_text("Hello AI")
    
    # Check AI response
    expect(chat_window).to_contain_text("Hello there!")
    
    # Check context size update
    expect(page.locator("#current-context")).to_have_text("15")
    expect(page.locator("#max-context")).to_have_text("8192")

def test_context_persistence(page: Page):
    history = []
    
    def handle_route(route):
        request_data = route.request.post_data_json
        history.append(request_data)
        
        # Respond
        body = json.dumps({"message": {"role": "assistant", "content": "Sure"}, "done": True}).encode()
        route.fulfill(status=200, body=body)

    page.route("**/api/chat", handle_route)
    page.goto(INDEX_HTML)
    
    user_input = page.locator("#user-input")
    send_btn = page.locator("#send-btn")
    
    # First message
    user_input.fill("I am Roman")
    send_btn.click()
    
    # Wait for UI to be ready again
    expect(send_btn).to_be_enabled()
    
    # Second message
    user_input.fill("What is my name?")
    send_btn.click()
    
    expect(send_btn).to_be_enabled()
    
    # Check history
    assert len(history) == 2
    # Second request should have 4 messages: system, user1, assistant1, user2
    messages = history[1]["messages"]
    assert len(messages) == 4
    assert messages[0]["role"] == "system"
    assert messages[1]["content"] == "I am Roman"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["content"] == "What is my name?"

def test_stop_button_logic(page: Page):
    page.goto(INDEX_HTML)
    stop_btn = page.locator("#stop-btn")
    send_btn = page.locator("#send-btn")
    
    # Mock a slow response
    def handle_route(route):
        # Never fulfill to simulate ongoing stream
        pass

    page.route("**/api/chat", handle_route)
    
    page.locator("#user-input").fill("Tell me a long story")
    send_btn.click()
    
    # Stop button should be enabled and say 'Stop'
    expect(stop_btn).to_be_enabled()
    expect(stop_btn).to_be_visible()
    expect(stop_btn).to_have_text("Stop")
    expect(send_btn).to_be_disabled()
    
    # Stop it
    stop_btn.click()
    
    # UI should reset: button should say 'New' and be enabled
    expect(send_btn).to_be_enabled()
    expect(stop_btn).to_have_text("New")
    expect(stop_btn).to_be_enabled()
    expect(page.locator("#chat-window")).to_contain_text("[Generation Stopped]")

def test_new_button_clears_chat(page: Page):
    page.goto(INDEX_HTML)
    stop_btn = page.locator("#stop-btn")
    chat_window = page.locator("#chat-window")
    
    # Initial state should say 'New'
    expect(stop_btn).to_have_text("New")
    
    # Trigger 'New' (Clear)
    stop_btn.click()
    
    # Check if cleared
    expect(chat_window).to_contain_text("Chat cleared")


def test_context_size_display(page: Page):
    page.goto(INDEX_HTML)
    current_context = page.locator("#current-context")
    max_context = page.locator("#max-context")
    expect(current_context).to_be_visible()
    expect(max_context).to_be_visible()
    expect(current_context).to_have_text("0")
    expect(max_context).to_have_text("8192")

def test_save_persona_api_call(page: Page):
    # Mock the save endpoint — app.js now uses absolute localhost:8000 URLs
    saved_data = []
    def handle_save(route):
        saved_data.append(route.request.post_data)
        route.fulfill(status=200, body="Persona saved successfully")

    page.route("http://localhost:8000/save_persona", handle_save)
    # Also block persona.txt so loadSavedPersona doesn't overwrite our input
    page.route("http://localhost:8000/persona.txt", lambda route: route.fulfill(status=404))
    page.goto(INDEX_HTML)
    
    system_prompt = page.locator("#system-prompt")
    save_btn = page.locator("#save-persona-btn")
    
    new_persona = "New Test Persona"
    system_prompt.fill(new_persona)
    save_btn.click()
    
    expect(save_btn).to_have_text("Saved!")
    assert len(saved_data) == 1
    assert saved_data[0] == new_persona

def test_image_generation_flow(page: Page):
    # Mock the generate_image endpoint — app.js sends to localhost:8000 explicitly
    generated_url = "/images/test_gen.png"
    page.route("http://localhost:8000/generate_image", lambda route: route.fulfill(
        status=200, 
        content_type="application/json",
        body='{"url": "' + generated_url + '"}'
    ))
    page.route("http://localhost:8000/persona.txt", lambda route: route.fulfill(status=404))
    page.goto(INDEX_HTML)
    
    page.locator("#auto-image-checkbox").check()
    user_input = page.locator("#user-input")
    user_input.fill("A futuristic city")
    
    send_btn = page.locator("#send-btn")
    send_btn.click()
    
    # Check if image message appeared in chat
    chat_window = page.locator("#chat-window")
    expect(chat_window.locator(".image-msg")).to_be_visible(timeout=8000)
    expect(chat_window.locator(f"img[src='{generated_url}']")).to_be_visible()

def test_persona_loaded_from_server(page: Page):
    """Verify that a saved persona.txt is fetched and fills the system-prompt on load."""
    saved_persona = "You are a specialized coding assistant."
    page.route("http://localhost:8000/persona.txt",
               lambda route: route.fulfill(status=200, body=saved_persona))
    page.goto(INDEX_HTML)

    page.wait_for_function(
        f"document.getElementById('system-prompt').value === {json.dumps(saved_persona)}",
        timeout=5000
    )
    expect(page.locator("#system-prompt")).to_have_value(saved_persona)

def test_image_upload_shows_preview(page: Page):
    """Uploading an image file reveals the preview container and image."""
    page.route("http://localhost:8000/persona.txt", lambda route: route.fulfill(status=404))
    page.goto(INDEX_HTML)

    preview_container = page.locator("#image-preview-container")
    expect(preview_container).to_be_hidden()

    # Create a minimal 1×1 PNG in memory and inject it as a file upload
    import base64
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    tiny_png = base64.b64decode(tiny_png_b64)

    page.locator("#image-upload").set_input_files({
        "name": "test.png",
        "mimeType": "image/png",
        "buffer": tiny_png
    })

    expect(preview_container).to_be_visible()
    expect(page.locator("#image-preview")).to_have_attribute("src", re.compile(r"data:image/png"))

def test_remove_image_clears_preview(page: Page):
    """Clicking the × button hides the preview and clears the attached image."""
    page.route("http://localhost:8000/persona.txt", lambda route: route.fulfill(status=404))
    page.goto(INDEX_HTML)

    import base64
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    tiny_png = base64.b64decode(tiny_png_b64)

    page.locator("#image-upload").set_input_files({
        "name": "test.png",
        "mimeType": "image/png",
        "buffer": tiny_png
    })

    preview_container = page.locator("#image-preview-container")
    expect(preview_container).to_be_visible()

    page.locator("#remove-image-btn").click()
    expect(preview_container).to_be_hidden()
    expect(page.locator("#image-preview")).to_have_attribute("src", "")

def test_image_generation_sends_init_image(page: Page):
    """When an image is uploaded and 'Generate Image Use My Image ...' is sent, init_image is included."""
    captured = []

    def handle_generate(route):
        captured.append(route.request.post_data_json)
        route.fulfill(status=200, content_type="application/json",
                      body='{"url": "/images/gen.png"}')

    page.route("http://localhost:8000/generate_image", handle_generate)
    page.route("http://localhost:8000/persona.txt", lambda route: route.fulfill(status=404))
    page.goto(INDEX_HTML)

    import base64
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    tiny_png = base64.b64decode(tiny_png_b64)

    page.locator("#image-upload").set_input_files({
        "name": "test.png",
        "mimeType": "image/png",
        "buffer": tiny_png
    })

    page.locator("#auto-image-checkbox").check()
    page.locator("#user-input").fill("astronaut on mars")
    page.locator("#send-btn").click()

    expect(page.locator(".image-msg")).to_be_visible(timeout=8000)

    assert len(captured) == 1
    body = captured[0]
    assert body["prompt"] == "astronaut on mars"
    assert "init_image" in body
    # Frontend sends full data-URL; server strips prefix before forwarding to FastSD
    assert body["init_image"].startswith("data:image/png;base64,")
    assert "iVBORw0" in body["init_image"]  # base64 PNG magic bytes
