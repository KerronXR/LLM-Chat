import pytest
from playwright.sync_api import Page, expect
import os
import json

# Get the absolute path to the index.html
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html"

def test_save_persona_button_exists(page: Page):
    page.goto(INDEX_HTML)
    save_btn = page.locator("#save-persona-btn")
    expect(save_btn).to_be_visible()
    expect(save_btn).to_have_text("Save Persona")

def test_save_persona_api_call(page: Page):
    # Mock the save endpoint
    saved_data = []
    def handle_save(route):
        saved_data.append(route.request.post_data)
        route.fulfill(status=200, body="Persona saved successfully")

    page.route("**/save_persona", handle_save)
    page.goto(INDEX_HTML)
    
    system_prompt = page.locator("#system-prompt")
    save_btn = page.locator("#save-persona-btn")
    
    new_persona = "New Test Persona"
    system_prompt.fill(new_persona)
    save_btn.click()
    
    # Check if button text changes to "Saved!" (briefly)
    expect(save_btn).to_have_text("Saved!")
    
    # Check if data was sent
    assert len(saved_data) == 1
    assert saved_data[0] == new_persona

def test_load_persona_api_call(page: Page):
    # Mock the load endpoint
    persona_content = "Loaded from server file"
    # Match both relative and absolute paths
    page.route("**/persona.txt", lambda route: route.fulfill(status=200, body=persona_content))
    
    page.goto(INDEX_HTML)
    
    # Wait for the JS to update the value
    page.wait_for_function(f"document.getElementById('system-prompt').value === '{persona_content}'", timeout=5000)
    
    system_prompt = page.locator("#system-prompt")
    expect(system_prompt).to_have_value(persona_content)
