import pytest
from playwright.sync_api import Page, expect
import os

# Get the absolute path to the index.html
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html"

def test_context_size_visibility_on_mobile(page: Page):
    # Set viewport to a common mobile size
    page.set_viewport_size({"width": 375, "height": 667})
    
    # Load the page
    page.goto(INDEX_HTML)
    
    # Wait for the status bar to be visible
    status_bar = page.locator(".status-bar")
    expect(status_bar).to_be_visible()
    
    # Check if the context size elements are visible and have text
    current_context = page.locator("#current-context")
    max_context = page.locator("#max-context")
    
    expect(current_context).to_be_visible()
    expect(max_context).to_be_visible()
    
    # Check dimensions for readability (font-size should be 0.8rem or similar)
    # The original was 0.7rem which was too small
    font_size = current_context.evaluate("el => getComputedStyle(el).fontSize")
    # 0.8rem is about 12.8px to 14.4px depending on base
    assert float(font_size.replace('px', '')) >= 12, f"Font size too small: {font_size}"
    
    # Check that URLs are hidden on mobile
    server_label = page.get_by_text("Server:", exact=False)
    ollama_label = page.get_by_text("Ollama:", exact=False)
    expect(server_label).not_to_be_visible()
    expect(ollama_label).not_to_be_visible()
    
    # Check dimensions to ensure they aren't collapsed
    curr_box = current_context.bounding_box()
    assert curr_box and curr_box['width'] > 0 and curr_box['height'] > 0, "Current context element has 0 dimension"
    
    # Take a screenshot for debugging if it fails (not possible here easily, but good practice)
    
def test_status_bar_layout_on_mobile(page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(INDEX_HTML)
    
    status_bar = page.locator(".status-bar")
    
    # In mobile.css, status-bar should have flex-direction: column
    flex_direction = status_bar.evaluate("el => getComputedStyle(el).flexDirection")
    assert flex_direction == "column", f"Expected flex-direction column on mobile, got {flex_direction}"
    
    # Check if it's pushed off screen
    # The bottom of the status bar should be <= viewport height
    box = status_bar.bounding_box()
    viewport_height = 667
    assert box['y'] + box['height'] <= viewport_height + 5, f"Status bar is pushed off screen: {box['y'] + box['height']} > {viewport_height}"
