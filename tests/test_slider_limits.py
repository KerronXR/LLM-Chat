import pytest
pytestmark = pytest.mark.skip(reason="FastSD CPU was removed in fadc1ad")
from playwright.sync_api import Page, expect
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html"

def test_batch_size_slider_max_value(page: Page):
    """Verifies that the batch size slider maximum is 50."""
    page.goto(INDEX_HTML)
    
    slider = page.locator("#batch-size-slider")
    expect(slider).to_be_visible()
    
    # Check max attribute
    max_val = slider.get_attribute("max")
    assert max_val == "50", f"Expected max batch size to be 50, but got {max_val}"
