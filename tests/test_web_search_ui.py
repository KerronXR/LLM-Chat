"""
Unit tests for Web Search UI components and state logic.
"""
import os
import json
import subprocess
from pathlib import Path
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_index_html_has_web_search_button():
    index_path = os.path.join(PROJECT_ROOT, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert 'id="web-search-btn"' in html
    assert 'id="web-search-badge"' in html


def test_components_css_has_web_search_styles():
    css_path = os.path.join(PROJECT_ROOT, "css", "components.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()
    assert ".web-search-btn" in css
    assert ".search-sources-container" in css
    assert ".search-source-chip" in css


def test_state_js_includes_web_search():
    state_path = os.path.join(PROJECT_ROOT, "js", "state.js")
    with open(state_path, "r", encoding="utf-8") as f:
        js = f.read()
    assert "webSearchMode" in js
    assert "webSearchBtn" in js


def test_web_search_button_toggle_interaction(page):
    INDEX_HTML = os.getenv("PLAYWRIGHT_APP_URL", f"file:///{PROJECT_ROOT.replace(os.sep, '/')}/index.html")
    page.goto(INDEX_HTML)

    search_btn = page.locator("#web-search-btn")
    badge = page.locator("#web-search-badge")

    # Initial state is AUTO
    assert search_btn.is_visible()
    assert badge.inner_text() == "AUTO"
    assert "web-search-auto" in search_btn.get_attribute("class")

    # Click 1: AUTO -> ON
    search_btn.click()
    assert badge.inner_text() == "ON"
    assert "web-search-on" in search_btn.get_attribute("class")

    # Click 2: ON -> OFF
    search_btn.click()
    assert badge.inner_text() == "OFF"
    assert "web-search-off" in search_btn.get_attribute("class")

    # Click 3: OFF -> AUTO
    search_btn.click()
    assert badge.inner_text() == "AUTO"
    assert "web-search-auto" in search_btn.get_attribute("class")


def test_search_sources_badge_renders_count_without_chips():
    search_js_path = os.path.join(PROJECT_ROOT, "js", "search.js")
    with open(search_js_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Must contain search results count text
    assert "search results" in code
    # Must NOT build individual source chips or chip link elements
    assert "search-source-chip" not in code
    assert "search-sources-list" not in code


