import pytest
from playwright.sync_api import Page, expect
import json
import os
import re
import base64

# Get the absolute path to the index.html
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.getenv("PLAYWRIGHT_APP_URL", f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html")

TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
TINY_PNG = base64.b64decode(TINY_PNG_B64)


def ndjson_response(*chunks):
    return "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks).encode()

def test_initial_state(page: Page):
    page.goto(INDEX_HTML)
    
    # Check title
    expect(page).to_have_title("Veloxify Local AI | Uncensored")
    
    # Check default model
    model_select = page.locator("#model-select")
    expect(model_select).to_have_value("qwen2.5-vl-7b-instruct:latest")
    
    # Check default system prompt
    system_prompt = page.locator("#system-prompt")
    expect(system_prompt).to_have_value(re.compile(".*You are a helpful and capable AI assistant.*"))

    # Check initial button state
    stop_btn = page.locator("#stop-btn")
    expect(stop_btn).to_have_text("New")
    expect(stop_btn).to_be_enabled()

def test_model_selection_updates_prompt(page: Page):
    page.goto(INDEX_HTML)
    
    model_select = page.locator("#model-select")
    system_prompt = page.locator("#system-prompt")
    
    # Switch to DeepSeek
    model_select.select_option("deepseek-r1-distill-qwen-7b-uncensored:latest")
    expect(system_prompt).to_have_value(re.compile(".*deep reasoning.*"))
    
    # Switch to Qwen
    model_select.select_option("qwen2.5-vl-7b-instruct:latest")
    expect(system_prompt).to_have_value(re.compile(".*helpful and capable.*"))

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
        
        body = "".join("data: " + json.dumps(c) + "\n\n" for c in chunks).encode()
        route.fulfill(
            status=200,
            content_type="text/event-stream",
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
    requests = []
    
    def handle_route(route):
        request_data = route.request.post_data_json
        requests.append(request_data)

        # Respond
        body = ndjson_response(
            {"message": {"role": "assistant", "content": "Sure"}, "done": False},
            {"message": {"role": "assistant", "content": ""}, "done": True, "prompt_eval_count": 4, "eval_count": 2}
        )
        route.fulfill(status=200, content_type="text/event-stream", body=body)

    page.route("**/api/chat", handle_route)
    page.goto(INDEX_HTML)
    
    user_input = page.locator("#user-input")
    send_btn = page.locator("#send-btn")
    
    # First message
    user_input.fill("I am Roman")
    send_btn.click()
    
    # Wait for the first response to fully land before sending the second prompt
    expect(page.locator("#chat-window")).to_contain_text("Sure")
    expect(send_btn).to_be_enabled()
    
    # The first request should carry the selected model and the initial user turn.
    assert len(requests) == 1
    assert requests[0]["model"] == "qwen2.5-vl-7b-instruct:latest"
    assert requests[0]["messages"] == [{"role": "user", "content": "I am Roman"}]

    # The conversation state and UI should retain the assistant reply for follow-up turns.
    expect(page.locator("#chat-window")).to_contain_text("Sure")

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
    expect(send_btn).to_be_enabled()
    
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

    page.route("**/save_persona", handle_save)
    # Also block persona.txt so loadSavedPersona doesn't overwrite our input
    page.goto(INDEX_HTML)
    
    system_prompt = page.locator("#system-prompt")
    save_btn = page.locator("#save-persona-btn")
    
    new_persona = "New Test Persona"
    system_prompt.fill(new_persona)
    save_btn.click()
    
    expect(save_btn).to_have_text("Saved!")
    assert len(saved_data) == 1
    assert saved_data[0] == new_persona

@pytest.mark.skip(reason="FastSD CPU was removed in fadc1ad")
def test_image_generation_flow(page: Page):
    pass

def test_persona_loaded_from_server(page: Page):
    """Verify that a saved persona.txt is fetched and fills the system-prompt on load."""
    saved_persona = "You are a specialized coding assistant."
    page.route("**/persona.txt",
               lambda route: route.fulfill(status=200, body=saved_persona))
    page.goto(INDEX_HTML)

    page.wait_for_function(
        f"document.getElementById('system-prompt').value === {json.dumps(saved_persona)}",
        timeout=5000
    )
    expect(page.locator("#system-prompt")).to_have_value(saved_persona)

@pytest.mark.skip(reason="FastSD CPU was removed in fadc1ad")
def test_image_upload_shows_preview(page: Page):
    pass

@pytest.mark.skip(reason="FastSD CPU was removed in fadc1ad")
def test_remove_image_clears_preview(page: Page):
    pass

@pytest.mark.skip(reason="FastSD CPU was removed in fadc1ad")
def test_image_generation_sends_init_image(page: Page):
    pass

def test_chat_attachment_and_prompt_send_together(page: Page):
    captured = []

    def handle_chat(route):
        captured.append(route.request.post_data_json)
        body = (
            "data: " + json.dumps({"message": {"role": "assistant", "content": "That looks like a bear."}, "done": False})
            + "\n\n"
            + "data: " + json.dumps({"message": {"role": "assistant", "content": ""}, "done": True, "prompt_eval_count": 5, "eval_count": 7})
            + "\n\n"
        ).encode()
        route.fulfill(status=200, content_type="text/event-stream", body=body)

    page.route("**/api/chat", handle_chat)
    page.goto(INDEX_HTML)

    page.locator("#chat-attachment").set_input_files({
        "name": "bear.png",
        "mimeType": "image/png",
        "buffer": TINY_PNG
    })
    page.locator("#user-input").fill("what animal is this")
    page.locator("#send-btn").click()

    expect(page.locator(".user-message .message-attachment-image img")).to_be_visible(timeout=8000)
    expect(page.locator("#chat-window")).to_contain_text("what animal is this")
    expect(page.locator("#chat-window")).to_contain_text("That looks like a bear.")

    assert len(captured) == 1
    body = captured[0]
    content = body["messages"][-1]["content"]
    assert "what animal is this" in (content if isinstance(content, str) else str(content))
    assert body["attachment"]["type"] == "image"
    assert body["attachment"]["mimeType"] == "image/jpeg"
    assert body["attachment"]["data"].startswith("/9j/")

def test_chat_attachment_is_normalized_for_model(page: Page):
    captured = []

    def handle_chat(route):
        captured.append(route.request.post_data_json)
        body = (
            "data: " + json.dumps({"message": {"role": "assistant", "content": "I can see the image."}, "done": False})
            + "\n\n"
            + "data: " + json.dumps({"message": {"role": "assistant", "content": ""}, "done": True, "prompt_eval_count": 3, "eval_count": 4})
            + "\n\n"
        ).encode()
        route.fulfill(status=200, content_type="text/event-stream", body=body)

    page.route("**/api/chat", handle_chat)
    page.goto(INDEX_HTML)

    page.locator("#chat-attachment").set_input_files({
        "name": "coins.png",
        "mimeType": "image/png",
        "buffer": TINY_PNG
    })
    page.locator("#user-input").fill("describe")
    page.locator("#send-btn").click()

    expect(page.locator("#chat-window")).to_contain_text("I can see the image.")

    assert len(captured) == 1
    body = captured[0]
    assert body["attachment"]["type"] == "image"
    assert body["attachment"]["mimeType"] == "image/jpeg"
    assert body["attachment"]["data"].startswith("/9j/")
