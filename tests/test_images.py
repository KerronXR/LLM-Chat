import pytest
from playwright.sync_api import Page, expect
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html"

def test_image_ui_elements(page: Page):
    page.route("http://localhost:8000/persona.txt", lambda route: route.fulfill(status=404))
    page.goto(INDEX_HTML)
    expect(page.locator("#upload-btn")).to_be_visible()
    expect(page.locator("#auto-image-checkbox")).to_be_visible()
    assert page.locator("#progress-container").count() == 1
    # The old generate-img-btn should NOT exist anymore
    assert page.locator("#generate-img-btn").count() == 0

def test_image_generation_via_checkbox(page: Page):
    """Image generation is now triggered by checking the checkbox."""
    generated_url = "/images/test_gen.png"
    page.route("http://localhost:8000/generate_image", lambda route: route.fulfill(
        status=200, 
        content_type="application/json",
        body='{"url": "'+generated_url+'"}'
    ))
    page.route("http://localhost:8000/persona.txt", lambda route: route.fulfill(status=404))
    
    page.goto(INDEX_HTML)
    
    # Enable auto generation
    page.locator("#auto-image-checkbox").check()
    
    user_input = page.locator("#user-input")
    user_input.fill("A futuristic city")
    
    page.locator("#send-btn").click()
    
    # Check if image message appeared in chat
    chat_window = page.locator("#chat-window")
    expect(chat_window.locator(".image-msg")).to_be_visible(timeout=8000)
    expect(chat_window.locator("img[src='"+generated_url+"']")).to_be_visible()
    expect(chat_window.locator("a[href='"+generated_url+"']")).to_be_visible()
