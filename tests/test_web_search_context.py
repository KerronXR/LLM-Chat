"""
Tests for Multi-Turn Context-Aware Web Search Query Resolution.
Verifies pronouns, follow-ups ('And?', 'Price?'), and entity retention across chat turns.
"""
import pytest
from web_search import (
    resolve_contextual_query,
    should_trigger_search_from_history,
)


def test_resolve_contextual_query_with_prior_subject():
    messages = [
        {"role": "user", "content": "What is this keyboard?"},
        {
            "role": "assistant",
            "content": "This is an 8Bitdo Retro Mechanical Keyboard with dual programmable buttons.",
        },
        {"role": "user", "content": "Yes, what is the price?"},
    ]
    resolved = resolve_contextual_query(messages)
    assert "8Bitdo" in resolved or "Retro Mechanical Keyboard" in resolved
    assert "price" in resolved.lower()
    assert "yes" not in resolved.lower()


def test_resolve_contextual_query_continuation_prompt():
    messages = [
        {"role": "user", "content": "What is the price of 8Bitdo Retro Mechanical Keyboard?"},
        {
            "role": "assistant",
            "content": "Executing a search for 8Bitdo Retro Mechanical Keyboard price, please wait.",
        },
        {"role": "user", "content": "And?"},
    ]
    should_trigger = should_trigger_search_from_history(messages, mode="auto")
    assert should_trigger is True

    resolved = resolve_contextual_query(messages)
    assert "8Bitdo" in resolved or "Mechanical Keyboard" in resolved
    assert "price" in resolved.lower()


def test_standalone_query_not_polluted():
    messages = [
        {"role": "user", "content": "Tell me about Python asyncio event loops."},
        {"role": "assistant", "content": "Asyncio is a library to write concurrent code."},
        {"role": "user", "content": "What is the weather in Lynnwood today?"},
    ]
    resolved = resolve_contextual_query(messages)
    assert "asyncio" not in resolved.lower()
    assert "weather" in resolved.lower()
    assert "lynnwood" in resolved.lower()


def test_pronoun_it_replacement():
    messages = [
        {"role": "user", "content": "When was iPhone 16 released?"},
        {"role": "assistant", "content": "iPhone 16 was announced in September 2024."},
        {"role": "user", "content": "How much does it cost?"},
    ]
    resolved = resolve_contextual_query(messages)
    assert "iPhone 16" in resolved or "iphone" in resolved.lower()
    assert "cost" in resolved.lower() or "price" in resolved.lower()
