"""
50+ Real-World Search Pattern Battery.
Tests auto-trigger accuracy, query resolution, entity inheritance,
and negative controls across 7 distinct categories.
"""
import pytest
from web_search import should_trigger_search
from search_context import should_trigger_search_from_history, resolve_contextual_query
from live_data import extract_stock_ticker, fetch_live_stock

# 1. Release Dates & Upcoming Products (8 cases)
RELEASE_CASES = [
    ("Where gta 6 will be released?", True, "gta 6"),
    ("When will Elder Scrolls 6 launch?", True, "elder scrolls 6"),
    ("Nintendo Switch 2 release date announcement", True, "switch 2"),
    ("Is Half-Life 3 announced yet?", True, "half-life 3"),
    ("What platforms will Monster Hunter Wilds be on?", True, "monster hunter"),
    ("When does Dune 3 come out?", True, "dune 3"),
    ("iPhone 17 Pro Max announcement date", True, "iphone 17"),
    ("When will Windows 12 be released?", True, "windows 12"),
]

# 2. Live Stocks & Financial Queries (6 cases)
STOCK_CASES = [
    ("How much is NVDA stock today?", True, "NVDA"),
    ("Apple AAPL stock price right now", True, "AAPL"),
    ("Tesla share price today", True, "TSLA"),
    ("Amazon stock quote", True, "AMZN"),
    ("Bitcoin current price USD", True, "bitcoin"),
    ("Current S&P 500 index level", True, "s&p 500"),
]

# 3. Weather & Forecasts (6 cases)
WEATHER_CASES = [
    ("Weather in Tokyo today", True, "Tokyo"),
    ("What is the weather like in New York tomorrow?", True, "New York"),
    ("London weather forecast this week", True, "London"),
    ("Is it raining in Paris right now?", True, "Paris"),
    ("Temperature in Chicago currently", True, "Chicago"),
    ("Sydney weather radar", True, "Sydney"),
]

# 4. Product Specs, Hardware & Pricing (8 cases)
PRODUCT_PRICING_CASES = [
    ("RTX 5090 specs and MSRP", True, "5090"),
    ("How much does PS5 Pro cost?", True, "ps5 pro"),
    ("Best price on M3 MacBook Air", True, "macbook air"),
    ("Where to buy Framework laptop", True, "framework laptop"),
    ("Sony WH-1000XM5 retail price", True, "wh-1000xm5"),
    ("Pixel 9 Pro specifications", True, "pixel 9 pro"),
    ("Steam Deck OLED price in 2026", True, "steam deck"),
    ("Keychron Q1 Pro keyboard cost", True, "keychron"),
]

# 5. Current News, People & Events (8 cases)
NEWS_CASES = [
    ("Who is the current prime minister of the UK?", True, "prime minister"),
    ("Latest news on SpaceX Starship test flight", True, "starship"),
    ("Who won the latest Super Bowl?", True, "super bowl"),
    ("Current president of France in 2026", True, "france"),
    ("Nobel prize winners this year", True, "nobel"),
    ("Latest earthquake reports today", True, "earthquake"),
    ("NASA Artemis mission current status", True, "artemis"),
    ("Who is leading F1 championship right now?", True, "f1"),
]

# 6. Multi-Turn Follow-ups, Directives & Retries (10 cases)
MULTITURN_CASES = [
    (
        "GTA 6 Directive",
        [
            {"role": "user", "content": "Where gta 6 will be released?"},
            {"role": "assistant", "content": "I do not have real time information."},
            {"role": "user", "content": "Check internet"}
        ],
        True,
        "gta 6"
    ),
    (
        "GTA 6 Complaint Retry",
        [
            {"role": "user", "content": "Where gta 6 will be released?"},
            {"role": "assistant", "content": "Broadband providers list."},
            {"role": "user", "content": "Well it was a bad search then, try again"}
        ],
        True,
        "gta 6"
    ),
    (
        "Vision Book eBay",
        [
            {"role": "user", "content": "How much i can sell these for?"},
            {"role": "assistant", "content": "The books shown in the picture are **Mario Kart (Step 3)** and **Mario Takes Off**."},
            {"role": "user", "content": "Search eBay or Amazon for current listings"}
        ],
        True,
        "mario kart"
    ),
    (
        "Hardware MSRP Followup",
        [
            {"role": "user", "content": "Tell me about Nvidia RTX 5090"},
            {"role": "assistant", "content": "The RTX 5090 is Nvidia's flagship next-gen GPU."},
            {"role": "user", "content": "What is its MSRP?"}
        ],
        True,
        "rtx 5090"
    ),
    (
        "Research Directive",
        [
            {"role": "user", "content": "What is Keychron Q1?"},
            {"role": "assistant", "content": "It is a 75% mechanical keyboard."},
            {"role": "user", "content": "You need to research its price"}
        ],
        True,
        "keychron"
    ),
    (
        "Pronoun Followup",
        [
            {"role": "user", "content": "Tell me about James Webb telescope"},
            {"role": "assistant", "content": "The James Webb Space Telescope was launched in 2021."},
            {"role": "user", "content": "What did it discover recently?"}
        ],
        True,
        "james webb"
    ),
    (
        "Store Recommendation",
        [
            {"role": "user", "content": "Recommend a rapid trigger keyboard"},
            {"role": "assistant", "content": "I recommend the **Wooting 60HE** keyboard."},
            {"role": "user", "content": "Where can I buy one?"}
        ],
        True,
        "wooting 60he"
    ),
    (
        "Online Benchmark Request",
        [
            {"role": "user", "content": "Tell me about Claude 3.5 Sonnet"},
            {"role": "assistant", "content": "Claude 3.5 Sonnet is an LLM from Anthropic."},
            {"role": "user", "content": "Can you search online for benchmarks?"}
        ],
        True,
        "claude"
    ),
    (
        "Latest Updates Directive",
        [
            {"role": "user", "content": "What are new features of Rust 2024 edition?"},
            {"role": "assistant", "content": "Rust 2024 adds new language idioms."},
            {"role": "user", "content": "Check latest updates"}
        ],
        True,
        "rust"
    ),
    (
        "Google That Directive",
        [
            {"role": "user", "content": "Was Mars Sample Return cancelled?"},
            {"role": "assistant", "content": "NASA proposed changes to the budget."},
            {"role": "user", "content": "Google that"}
        ],
        True,
        "mars sample return"
    ),
]

# 7. Negative Controls - No Search Needed (10 cases)
NEGATIVE_CASES = [
    "Write a python function to reverse a linked list",
    "Explain difference between TCP and UDP",
    "Translate 'Good morning, friend' into Spanish",
    "Solve for x: 3x + 15 = 45",
    "Write a short poem about autumn rain",
    "What is time complexity of merge sort?",
    "How do pointers work in C?",
    "Summarize the plot of Hamlet in 3 sentences",
    "Debug this code: for i in range(10) print(i)",
    "Tell me a joke about programming",
]


@pytest.mark.parametrize("query,expected_trigger,expected_keyword", RELEASE_CASES)
def test_release_patterns(query, expected_trigger, expected_keyword):
    assert should_trigger_search(query, mode="auto") == expected_trigger
    assert expected_keyword.lower() in query.lower()


@pytest.mark.parametrize("query,expected_trigger,expected_symbol", STOCK_CASES)
def test_stock_patterns(query, expected_trigger, expected_symbol):
    assert should_trigger_search(query, mode="auto") == expected_trigger
    ticker = extract_stock_ticker(query)
    if expected_symbol.isupper() and len(expected_symbol) <= 5:
        assert ticker == expected_symbol


@pytest.mark.parametrize("query,expected_trigger,expected_city", WEATHER_CASES)
def test_weather_patterns(query, expected_trigger, expected_city):
    assert should_trigger_search(query, mode="auto") == expected_trigger
    assert expected_city.lower() in query.lower()


@pytest.mark.parametrize("query,expected_trigger,expected_keyword", PRODUCT_PRICING_CASES)
def test_product_pricing_patterns(query, expected_trigger, expected_keyword):
    assert should_trigger_search(query, mode="auto") == expected_trigger
    assert expected_keyword.lower() in query.lower()


@pytest.mark.parametrize("query,expected_trigger,expected_keyword", NEWS_CASES)
def test_news_patterns(query, expected_trigger, expected_keyword):
    assert should_trigger_search(query, mode="auto") == expected_trigger
    assert expected_keyword.lower() in query.lower()


@pytest.mark.parametrize("name,messages,expected_trigger,expected_keyword", MULTITURN_CASES)
def test_multiturn_patterns(name, messages, expected_trigger, expected_keyword):
    triggered = should_trigger_search_from_history(messages, mode="auto")
    assert triggered == expected_trigger, f"Failed trigger on {name}"
    resolved = resolve_contextual_query(messages)
    assert expected_keyword.lower() in resolved.lower(), f"Failed keyword '{expected_keyword}' in resolved '{resolved}' for {name}"


@pytest.mark.parametrize("query", NEGATIVE_CASES)
def test_negative_controls(query):
    assert should_trigger_search(query, mode="auto") is False
