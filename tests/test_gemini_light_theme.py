import pytest
from playwright.sync_api import Page, expect
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.getenv("PLAYWRIGHT_APP_URL", f"file:///{BASE_PATH.replace(os.sep, '/')}/index.html")
LOGIN_HTML = f"file:///{BASE_PATH.replace(os.sep, '/')}/login.html"

def test_gemini_light_css_variables(page: Page):
    page.goto(INDEX_HTML)
    canvas = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg-canvas').trim()")
    surface = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg-surface').trim()")
    text_main = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--text-main').trim()")
    accent_primary = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent-primary').trim()")
    
    assert canvas.lower() in ["#ffffff", "#f8fafd"]
    assert surface.lower() in ["#f0f4f9", "#e9eef6"]
    assert text_main.lower() in ["#1f1f1f", "#111827", "#1e1f20"]
    assert accent_primary.lower() in ["#0b57d0", "#1a73e8"]

def test_gemini_light_body_style(page: Page):
    page.goto(INDEX_HTML)
    body_bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
    body_color = page.evaluate("getComputedStyle(document.body).color")
    
    # Check light background (e.g. rgb(248, 250, 253) or rgb(255, 255, 255))
    assert body_bg in ["rgb(248, 250, 253)", "rgb(255, 255, 255)", "rgb(240, 244, 249)"]
    # Check dark readable text (e.g. rgb(31, 31, 31))
    assert body_color in ["rgb(31, 31, 31)", "rgb(17, 24, 39)", "rgb(30, 31, 32)"]

def test_gemini_light_user_and_ai_message(page: Page):
    page.goto(INDEX_HTML)
    
    # Inject user and AI messages to test styles
    page.evaluate("""() => {
        const win = document.getElementById('chat-window');
        const userMsg = document.createElement('div');
        userMsg.className = 'message user-message';
        userMsg.innerText = 'Test prompt';
        win.appendChild(userMsg);
        
        const aiMsg = document.createElement('div');
        aiMsg.className = 'message ai-message';
        aiMsg.innerText = 'Test response';
        win.appendChild(aiMsg);
    }""")
    
    user_bubble = page.locator(".user-message").last
    ai_bubble = page.locator(".ai-message").last
    
    user_bg = user_bubble.evaluate("el => getComputedStyle(el).backgroundColor")
    user_color = user_bubble.evaluate("el => getComputedStyle(el).color")
    ai_color = ai_bubble.evaluate("el => getComputedStyle(el).color")
    
    # User message in Gemini light is soft blue-gray bubble (#f0f4f9 or #e9eef6) with dark text
    assert user_bg in ["rgb(240, 244, 249)", "rgb(233, 238, 246)", "rgb(232, 238, 247)"]
    assert user_color in ["rgb(31, 31, 31)", "rgb(17, 24, 39)", "rgb(30, 31, 32)"]
    assert ai_color in ["rgb(31, 31, 31)", "rgb(17, 24, 39)", "rgb(30, 31, 32)"]

def test_gemini_light_input_pill(page: Page):
    page.goto(INDEX_HTML)
    input_box = page.locator("#user-input")
    radius = input_box.evaluate("el => getComputedStyle(el).borderRadius")
    bg = input_box.evaluate("el => getComputedStyle(el).backgroundColor")
    
    # Should have rounded pill styling >= 20px
    radius_val = int(radius.replace("px", "").split()[0])
    assert radius_val >= 20
    assert bg in ["rgb(240, 244, 249)", "rgb(233, 238, 246)", "rgb(255, 255, 255)"]

def test_gemini_light_login_page(page: Page):
    page.goto(LOGIN_HTML)
    card = page.locator(".login-card")
    card_bg = card.evaluate("el => getComputedStyle(el).backgroundColor")
    btn = page.locator("#login-btn")
    btn_bg = btn.evaluate("el => getComputedStyle(el).backgroundColor")
    
    assert card_bg in ["rgb(255, 255, 255)", "rgb(248, 250, 253)"]
    # Login button should have Google blue or Gemini gradient
    assert btn_bg in ["rgb(11, 87, 208)", "rgb(26, 115, 232)"] or "linear-gradient" in btn.evaluate("el => getComputedStyle(el).backgroundImage")

def test_gemini_light_mobile_theme(page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(INDEX_HTML)
    
    toggle = page.locator("#mobile-toggle")
    toggle.wait_for(state="visible", timeout=8000)
    
    toggle_color = toggle.evaluate("el => getComputedStyle(el).color")
    toggle_bg = toggle.evaluate("el => getComputedStyle(el).backgroundColor")
    
    # Toggle button in Gemini Light has Google blue accent and white background
    assert toggle_color in ["rgb(11, 87, 208)", "rgb(26, 115, 232)"]
    assert toggle_bg in ["rgb(255, 255, 255)", "rgb(248, 250, 253)"]
    
    # Open sidebar drawer on mobile
    toggle.click()
    sidebar = page.locator(".sidebar")
    sidebar.wait_for(state="visible", timeout=5000)
    sidebar_bg = sidebar.evaluate("el => getComputedStyle(el).backgroundColor")
    
    # Sidebar drawer must be light surface (#f0f4f9), not dark neon
    assert sidebar_bg in ["rgb(240, 244, 249)", "rgb(233, 238, 246)"]
    
    # Check status bar in mobile
    status_bar = page.locator(".status-bar")
    status_bg = status_bar.evaluate("el => getComputedStyle(el).backgroundColor")
    assert status_bg in ["rgb(240, 244, 249)", "rgb(233, 238, 246)"]

