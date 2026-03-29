import pytest
from playwright.sync_api import Page, expect
import os
import re

# Get the absolute path to the index.html
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html"

def test_mobile_toggle_button_exists(page: Page):
    """Verify that a mobile toggle button is present in the DOM."""
    page.goto(INDEX_HTML)
    # This will fail initially as the button doesn't exist yet
    toggle = page.locator("#mobile-toggle")
    expect(toggle).to_be_attached()

def test_sidebar_hidden_on_mobile_initially(page: Page):
    """Verify that the sidebar is hidden (off-screen) on mobile by default."""
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(INDEX_HTML)
    
    sidebar = page.locator(".sidebar")
    # We'll use a class or transform to hide it
    expect(sidebar).not_to_be_visible()

def test_mobile_toggle_opens_sidebar(page: Page):
    """Verify that clicking the toggle button shows the sidebar on mobile."""
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(INDEX_HTML)
    
    toggle = page.locator("#mobile-toggle")
    sidebar = page.locator(".sidebar")
    
    toggle.click()
    expect(sidebar).to_be_visible()
    
    # Click again to hide
    toggle.click()
    expect(sidebar).not_to_be_visible()

def test_desktop_layout_remains_unchanged(page: Page):
    """Verify that on desktop, the sidebar is visible and the toggle is hidden."""
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(INDEX_HTML)
    
    sidebar = page.locator(".sidebar")
    toggle = page.locator("#mobile-toggle")
    
    expect(sidebar).to_be_visible()
    # Toggle should be hidden on desktop
    expect(toggle).not_to_be_visible()
