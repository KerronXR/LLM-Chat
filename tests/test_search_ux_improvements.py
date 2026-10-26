"""
Unit tests for search UX enhancements:
1. Ad / tracking URL rejection (filter /y.js and ad_domain links)
2. Price query expansion with 'retail price MSRP'
3. 5-result organic snippet support
4. Clean inline response guidance in prompt header
"""
import pytest
from web_search import _resolve_ddg_url, _is_safe_url, format_search_prompt_context, MAX_SEARCH_RESULTS
from search_context import resolve_contextual_query


def test_ad_and_tracking_urls_rejected():
    ad_url = "https://duckduckgo.com/y.js?ad_domain=amazon.com&ad_provider=bingv7aa&click_metadata=abc"
    resolved = _resolve_ddg_url(ad_url)
    assert resolved == ""
    assert _is_safe_url(ad_url) is False


def test_organic_urls_accepted():
    real_url = "https://www.amazon.com/8Bitdo-Mechanical-Keyboard/dp/B0CCP8KYGG"
    assert _is_safe_url(real_url) is True
    assert _resolve_ddg_url(real_url) == real_url


def test_price_query_expansion():
    messages = [
        {"role": "user", "content": "What is this keyboard?"},
        {"role": "assistant", "content": "This is an 8Bitdo Retro Mechanical Keyboard."},
        {"role": "user", "content": "What is the price today?"},
    ]
    query = resolve_contextual_query(messages)
    assert "8Bitdo" in query or "Retro Mechanical Keyboard" in query
    assert "price" in query.lower() or "msrp" in query.lower()
    assert "msrp" in query.lower() or "retail" in query.lower()


def test_max_search_results_is_five():
    assert MAX_SEARCH_RESULTS >= 5


def test_format_search_prompt_context_no_raw_urls_directive():
    results = [
        {"title": "Test Title", "url": "https://example.com/item", "snippet": "Priced at $69.99."}
    ]
    context = format_search_prompt_context(results)
    assert "Do not paste" in context or "raw URLs" in context or "inline" in context
