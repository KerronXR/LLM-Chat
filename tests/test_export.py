import pytest
from playwright.sync_api import Page, expect
import os
import json

# Use the local server for tests to avoid ESM over file:// issues
INDEX_HTML = os.getenv("PLAYWRIGHT_APP_URL", "http://127.0.0.1:8765/index.html")

def test_export_conversation_triggers_download(page: Page):
    # Log console messages
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    page.on("pageerror", lambda err: print(f"PAGE ERROR: {err.message}"))

    # Mock all potential fetch calls to prevent file:/// errors
    page.route("**/api/chat", lambda route: route.fulfill(
        status=200, 
        content_type="application/x-ndjson", 
        body=json.dumps({"message": {"role": "assistant", "content": "I am fine"}, "done": True}).encode()
    ))
    page.route("**/api/history", lambda route: route.fulfill(status=200, body="[]"))
    page.route("**/api/logout", lambda route: route.fulfill(status=200, body="{}"))
    page.route("**/persona.txt", lambda route: route.fulfill(status=404))
    page.route("**/save_persona", lambda route: route.fulfill(status=200, body="OK"))

    page.goto(INDEX_HTML)
    
    # Wait for the page to be conceptually loaded
    # Even if chat-cleared is already there from an previous run of handleClearChat?
    # No, it's a fresh page.
    
    user_input = page.locator("#user-input")
    send_btn = page.locator("#send-btn")
    
    # Wait for JS to load - check for the 'New' button which is in HTML, but we want to ensure JS is ready.
    # We can check a global variable if we had one, but let's just wait a bit.
    page.wait_for_timeout(2000)
    
    user_input.fill("Hello")
    send_btn.click()
    
    # Wait for user message to appear
    chat_window = page.locator("#chat-window")
    expect(chat_window).to_contain_text("Hello", timeout=5000)
    
    # Click export button and wait for download
    export_btn = page.locator("#export-btn")
    
    with page.expect_download() as download_info:
        export_btn.click()
    
    download = download_info.value
    assert download.suggested_filename.startswith("veloxify_conversation_")
    assert download.suggested_filename.endswith(".txt")
    
    # Verify content
    download_path = download.path()
    with open(download_path, 'r') as f:
        content = f.read()
        assert "Veloxify AI Conversation Export" in content
        assert "User: Hello" in content
        assert "AI: I am fine" in content
