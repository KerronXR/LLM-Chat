import pytest
from playwright.sync_api import Page, expect
import os

# Get the absolute path to the index.html
INDEX_HTML = os.getenv("PLAYWRIGHT_APP_URL", "http://127.0.0.1:8765/index.html")

def login(page: Page):
    page.goto(INDEX_HTML)
    page.locator(".app-wrapper").wait_for(state="visible", timeout=10000)

def test_mobile_menu_button_overlap(page: Page):
    # Set viewport to a common mobile size
    page.set_viewport_size({"width": 375, "height": 667})
    
    login(page)
    
    # Wait for the mobile-toggle to be injected by main.js
    toggle = page.locator("#mobile-toggle")
    toggle.wait_for(state="visible", timeout=10000)
    
    chat_container = page.locator(".chat-container")
    chat_container.wait_for(state="visible", timeout=10000)
    
    # Get bounding boxes
    toggle_box = toggle.bounding_box()
    chat_box = chat_container.bounding_box()
    
    print(f"Toggle Box: {toggle_box}")
    print(f"Chat Box: {chat_box}")
    
    # Verify they don't overlap. Bottom of toggle < Top of chat
    toggle_bottom = toggle_box['y'] + toggle_box['height']
    chat_top = chat_box['y']
    
    assert toggle_bottom < chat_top, \
        f"Mobile toggle overlaps with chat container. Toggle bottom: {toggle_bottom}, Chat top: {chat_top}"
    
    # Expect at least 10px gap
    assert chat_top - toggle_bottom >= 10, \
        f"Gap between toggle and chat is too small: {chat_top - toggle_bottom}px (expected at least 10px)"

def test_sidebar_toggle_visibility(page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    login(page)
    
    # Sidebar should be hidden initially in mobile
    sidebar = page.locator(".sidebar")
    sidebar.wait_for(state="hidden", timeout=5000)
    
    # Click toggle
    toggle = page.locator("#mobile-toggle")
    toggle.wait_for(state="visible")
    toggle.click()
    
    # Sidebar should now be visible
    sidebar.wait_for(state="visible", timeout=5000)
    
    # Click toggle again to close
    toggle.click()
    
    # Sidebar should be hidden again
    sidebar.wait_for(state="hidden", timeout=5000)
