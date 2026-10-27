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


def test_follow_up_research_directive_triggers_search():
    messages = [
        {"role": "user", "content": "How much that costs?"},
        {
            "role": "assistant",
            "content": "This is an Akko 3084 Mechanical Keyboard, but the image **does not contain the price**.",
        },
        {"role": "user", "content": "You need to research"},
    ]
    assert should_trigger_search_from_history(messages, mode="auto") is True

    messages_check = [
        {"role": "user", "content": "What is this item?"},
        {"role": "assistant", "content": "It looks like a Keychron K2 keyboard."},
        {"role": "user", "content": "Check online"},
    ]
    assert should_trigger_search_from_history(messages_check, mode="auto") is True


def test_extract_subject_from_history_filters_refusal_boilerplate():
    from search_context import extract_subject_from_history
    messages = [
        {"role": "user", "content": "How much that costs?"},
        {
            "role": "assistant",
            "content": (
                "I am sorry, but the image you provided is a product listing for **Keychron Q1 Pro** "
                "or a screenshot of a product page, and it **does not contain the price**.\n\n"
                "I cannot perform real-time web searches or access specific store inventory."
            ),
        },
        {"role": "user", "content": "You need to research"},
    ]
    subject = extract_subject_from_history(messages)
    assert "Keychron Q1 Pro" in subject or "Keychron" in subject
    assert "does not contain" not in subject.lower()
    assert "real-time" not in subject.lower()


def test_resolve_contextual_query_for_research_directive():
    messages = [
        {"role": "user", "content": "How much that costs?"},
        {
            "role": "assistant",
            "content": "This is a Keychron Q1 Pro keyboard, but does not contain the price.",
        },
        {"role": "user", "content": "You need to research"},
    ]
    resolved = resolve_contextual_query(messages)
    assert "Keychron" in resolved
    assert "research" not in resolved.lower()
    assert "price" in resolved.lower() or "msrp" in resolved.lower()

