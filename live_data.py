"""
Live real-time metrics providers (Weather via wttr.in, Stocks via Yahoo Finance chart API).
Zero external dependencies, fast timeout fallback.
"""
import json
import logging
import re
import urllib.parse
import urllib.request

logger = logging.getLogger("live_data")

STOCK_MAP = {
    "amazon": "AMZN",
    "apple": "AAPL",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "microsoft": "MSFT",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "amd": "AMD",
    "intel": "INTC",
}

NON_TICKERS = {
    "HOW", "MUCH", "IS", "THE", "AND", "FOR", "WHAT", "WHO",
    "USD", "STOCK", "SHARE", "PRICE", "TODAY", "THIS", "THAT",
    "TELL", "ME", "ABOUT"
}


def extract_stock_ticker(query: str) -> str | None:
    """Extract stock ticker symbol from conversational query."""
    q = query.strip()
    for name, sym in STOCK_MAP.items():
        if re.search(rf"\b{name}\b", q, re.I):
            return sym
    lower_m = re.findall(r"\b([a-z]{1,5})\s+(?:stock|share|quote)\b", q, re.I)
    if lower_m:
        cand = lower_m[0].upper()
        if cand not in NON_TICKERS:
            return cand
    caps = re.findall(r"\b[A-Z]{1,5}\b", q)
    for c in caps:
        if c not in NON_TICKERS:
            return c
    return None


def fetch_live_stock(ticker: str, timeout: float = 2.5) -> dict | None:
    """Fetch real-time stock price and day range from Yahoo Finance chart API."""
    if not ticker or len(ticker) > 6:
        return None
    sym = ticker.upper()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            if price is None:
                return None
            curr = meta.get("currency", "USD")
            high = meta.get("regularMarketDayHigh", price)
            low = meta.get("regularMarketDayLow", price)
            return {
                "title": f"Live Stock: {sym}",
                "url": f"https://finance.yahoo.com/quote/{sym}",
                "snippet": f"{sym} is currently trading at {curr} ${price:.2f}. Today's Range: ${low:.2f} - ${high:.2f}.",
            }
    except Exception as e:
        logger.debug("Live stock fetch skipped/failed for %s: %s", sym, e)
        return None


def fetch_live_weather(location: str, timeout: float = 2.5) -> dict | None:
    """Fetch real-time weather metrics for exact temperature & conditions."""
    if not location or len(location) > 40:
        return None
    loc_clean = re.sub(r"[^a-zA-Z\s]", "", location).strip()
    if not loc_clean:
        return None
    url = f"https://wttr.in/{urllib.parse.quote(loc_clean)}?format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            cc = data.get("current_condition", [{}])[0]
            temp_f = cc.get("temp_F", "")
            temp_c = cc.get("temp_C", "")
            desc = cc.get("weatherDesc", [{}])[0].get("value", "")
            humidity = cc.get("humidity", "")
            wind = cc.get("windspeedMiles", "")
            return {
                "title": f"Live Weather: {loc_clean.title()}",
                "url": f"https://wttr.in/{urllib.parse.quote(loc_clean)}",
                "snippet": f"Currently {desc}, {temp_f}°F ({temp_c}°C). Humidity: {humidity}%, Wind: {wind} mph.",
            }
    except Exception as e:
        logger.debug("Live weather fetch skipped/failed: %s", e)
        return None
