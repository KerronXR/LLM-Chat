"""
Multi-turn context-aware search query resolver.
Resolves pronouns ('it', 'this'), continuation follow-ups ('And?', 'Price?', 'You need to research'),
and extracts primary subject entities from conversation history.
"""
import re

CONTINUATION_PATTERN = re.compile(
    r"^(and|so|results?|anything|what\s+is\s+it|what\s+about\s+it|did\s+you\s+find\s+(?:it|anything)?|"
    r"(?:you\s+need\s+to\s+)?research(?:\s+(?:it|this|that|online))?|"
    r"(?:can\s+you\s+)?search(?:\s+(?:for\s+it|it|online|web|internet))?|"
    r"(?:please\s+)?look(?:\s+it)?\s+up(?:\s+(?:online|internet))?|"
    r"(?:please\s+)?check(?:\s+it)?\s+(?:online|internet|the\s+web)|"
    r"(?:can\s+you\s+)?find(?:\s+it|\s+out)?|try\s+again|search\s+again)\??$",
    re.IGNORECASE,
)

DIRECTIVE_PATTERN = re.compile(
    r"^(?:(?:you\s+need\s+to|can\s+you|please|go|just)\s+)?(?:research|search|look\s+up|check|find\s+out|google)(?:\s+(?:it|this|that|online|internet|on\s+internet|the\s+internet|the\s+web|web|for|again))?[\s\.\?!]*$",
    re.IGNORECASE,
)

RETRY_DIRECTIVE_PATTERN = re.compile(
    r"^(?:.*(?:bad\s+search|wrong\s+search|didn\'?t\s+find).*?)?(?:please\s+)?(?:try\s+again|search\s+again|retry|redo|look\s+again|check\s+again|one\s+more\s+time)[\s\.\?!]*$",
    re.IGNORECASE,
)


def is_search_directive(text: str) -> bool:
    t = text.strip()
    return bool(
        DIRECTIVE_PATTERN.match(t)
        or CONTINUATION_PATTERN.match(t)
        or RETRY_DIRECTIVE_PATTERN.match(t)
        or t.lower() in ("?", "...", "internet")
    )


def get_last_substantive_user_query(messages: list[dict]) -> str:
    """Find the most recent user question that had genuine standalone search/topic content."""
    for m in reversed(messages[:-1]):
        if m.get("role") != "user":
            continue
        c = m.get("content", "")
        if isinstance(c, list):
            c = " ".join(item.get("text", "") for item in c if isinstance(item, dict) and item.get("type") == "text")
        c = clean_search_query(c)
        c = AFFIRMATIVE_PREFIXES.sub("", c).strip()
        if is_search_directive(c):
            continue
        without_filler = re.sub(
            r"\b(what|where|when|who|which|how|why|is|are|was|were|do|does|did|will|would|can|could|be|been|"
            r"have|has|had|the|a|an|for|to|of|in|on|at|about|much|some|any|all|here|there|please|just|tell|me|you|"
            r"i|we|they|give|this|that|these|those|it|its|them|one|ones|price|prices|pricing|cost|costs|how\s+much|"
            r"pay|charge|worth|sell|buy|get)\b",
            "",
            c,
            flags=re.IGNORECASE,
        ).strip()
        if len(re.sub(r"[^a-zA-Z0-9]+", "", without_filler)) >= 3:
            return c
    return ""

DEPENDENT_QUERY_PATTERN = re.compile(
    r"\b(it|this|that|these|those|its|price|cost|how\s+much|specs|specifications|features|buy|where\s+to\s+buy|"
    r"release\s+date|released|who\s+made\s+it|research|search|look\s+up|google|check\s+online|find\s+out)\b",
    re.IGNORECASE,
)

AFFIRMATIVE_PREFIXES = re.compile(
    r"^(?:yes|yeah|yep|well|ok|okay|sure)[\s,\.\!\?]+|^(?:so|and|then)\s+(?=\S)",
    re.IGNORECASE,
)

DATE_MONTH_IGNORE = re.compile(
    r"^(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Today|Yesterday|Tomorrow|\d{4}|\s)+$",
    re.IGNORECASE,
)

REFUSAL_BOILERPLATE = re.compile(
    r"\b(not\s+contain|does\s+not|doesn't|cannot|can't|real-time|web\s+search|"
    r"store\s+inventory|product\s+listing|screenshot|actual\s+website|image\s+originated|"
    r"sorry|apologize|online\s+store|visit\s+the|find\s+out\s+how\s+much)\b",
    re.IGNORECASE,
)

PRODUCT_IDENTIFY_PATTERN = re.compile(
    r"(?:this\s+is\s+(?:an?|the)?|looks?\s+like\s+(?:an?|the)?|appears\s+to\s+be\s+(?:an?|the)?|"
    r"product\s+listing\s+for)\s*([A-Za-z0-9\s\-_]+?)(?:,|\.|\s+but|\s+and|\s+with|\s+or|\n|$)",
    re.IGNORECASE,
)

QUERY_STRIP_PREFIXES = [
    r"^(?:can\s+you\s+)?(?:please\s+)?search\s+(?:the\s+)?(?:web|internet|google|ddg)?\s*(?:for\s+)?",
    r"^(?:please\s+)?look\s+up\s+",
    r"^(?:please\s+)?find\s+(?:me\s+)?(?:information\s+about\s+)?",
    r"^(?:you\s+need\s+to\s+)?(?:please\s+)?research\s*(?:for\s+)?",
]


def clean_search_query(text: str) -> str:
    """Clean user prompt to extract focused search keywords (max 100 chars)."""
    clean = text.strip()
    for prefix in QUERY_STRIP_PREFIXES:
        clean = re.sub(prefix, "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"[\r\n\t\x00-\x1f]+", " ", clean).strip()
    return clean[:100].strip()


IGNORE_WORDS = re.compile(
    r"^(?:this|that|what|when|where|which|who|how|is|are|was|were|the|a|an|based|here|there|i|you|we|they|welcome|please|"
    r"therefore|however|because|since|although|instead|moreover|furthermore|as|if|when|to|in)\b|"
    r"^(?:price|cost|prices|buy|search|check|look|find|item|product|screenshot|image|photo|store|retailer|amazon|target|ebay|walmart|google|country)$",
    re.IGNORECASE,
)


def extract_named_entities(text: str) -> list[str]:
    """Extract consecutive tokens containing uppercase letters or digits, respecting boundaries."""
    chunks = re.split(r"(?<!\d)\.(?!\d)|[\?!;\n,]+", text)
    entities = []
    for chunk in chunks:
        tokens = re.findall(r"\b[a-zA-Z0-9_\.-]+\b", chunk)
        curr = []
        for t in tokens:
            if any(c.isupper() or c.isdigit() for c in t):
                if re.match(r"^(?:19|20)\d{2}$", t) and not curr:
                    continue
                curr.append(t)
            else:
                if curr:
                    while curr and curr[0].lower() in ("the", "a", "an"):
                        curr.pop(0)
                    while curr and curr[-1].lower() in ("the", "a", "an", "and", "or", "to", "in", "of"):
                        curr.pop()
                    if curr:
                        entities.append(" ".join(curr))
                    curr = []
        if curr:
            while curr and curr[0].lower() in ("the", "a", "an"):
                curr.pop(0)
            while curr and curr[-1].lower() in ("the", "a", "an", "and", "or", "to", "in", "of"):
                curr.pop()
            if curr:
                entities.append(" ".join(curr))
    return entities


STRUCTURAL_BOLD_IGNORE = re.compile(
    r"(?:understanding\s+your\s+intent|addressing\s+the\s+limitation|providing\s+the\s+best\s+next\s+step|"
    r"in\s+short|next\s+steps?|best\s+next\s+step|key\s+takeaways?|for\s+example|note\s+that|"
    r"typical\s+listings?|general\s+search|current\s+retailer|various\s+retailers|online\s+stores?|"
    r"current\s+price|selling\s+price|exact\s+price|where\s+you\s+buy\s+it|whether\s+it\s+is\s+new\s+or\s+used|"
    r"any\s+ongoing\s+sales|local\s+bookstore|major\s+online\s+retailers?)"
    r"|:\s*$",
    re.IGNORECASE,
)


def is_valid_product_candidate(text: str) -> bool:
    """Validate whether candidate string represents a real product, title, or named entity."""
    t = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", text).strip()
    if len(t) < 4 or len(t) > 60:
        return False
    if DATE_MONTH_IGNORE.match(t) or IGNORE_WORDS.match(t) or REFUSAL_BOILERPLATE.search(t) or STRUCTURAL_BOLD_IGNORE.search(t):
        return False
    if " " not in t and (t.islower() or t.lower() in ("think", "search", "browse", "price", "prices", "cost")):
        return False
    return True


def _extract_content_text(message: dict) -> str:
    content = message.get("content", "")
    if isinstance(content, list):
        return " ".join(item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text")
    return str(content or "")


def extract_subject_from_history(messages: list[dict]) -> str:
    """Extract primary named entity or topic from recent conversation turns, filtering boilerplate."""
    history_contents = [_extract_content_text(m) for m in reversed(messages[:-1])]
    history_contents = [c for c in history_contents if c]

    # Pass 1: High confidence (search targets, product patterns, quoted titles)
    for content in history_contents:
        search_m = re.search(r"(?:search\s+for|checking\s+price\s+for|looking\s+up)\s+[\'\"]?([a-zA-Z0-9\s]+?)(?:price|[\'\"]|\.|\,|$)", content, re.I)
        if search_m:
            subj = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", search_m.group(1)).strip()
            if is_valid_product_candidate(subj):
                return subj

        prod_m = PRODUCT_IDENTIFY_PATTERN.search(content)
        if prod_m:
            prod_candidate = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", prod_m.group(1)).strip()
            if is_valid_product_candidate(prod_candidate):
                return prod_candidate

        for q in re.findall(r'["\']([^"\']{4,60})["\']', content):
            clean_q = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", q).strip()
            if is_valid_product_candidate(clean_q):
                return clean_q

    # Pass 2: Fallback to validated bolds and named entities
    for content in history_contents:
        bolds = [re.sub(r"[^a-zA-Z0-9\s]", " ", b).strip() for b in re.findall(r"\*\*([^*]+)\*\*", content)]
        valid_bolds = [b for b in bolds if is_valid_product_candidate(b)]
        if valid_bolds:
            return valid_bolds[0]

        entities = [e for e in extract_named_entities(content) if is_valid_product_candidate(e)]
        if entities:
            return max(entities, key=len)

    return ""


def resolve_contextual_query(messages: list[dict]) -> str:
    """Resolve pronouns, follow-ups, and missing subjects across conversation history."""
    if not messages:
        return ""
    curr_text = _extract_content_text(messages[-1])
    clean_curr = AFFIRMATIVE_PREFIXES.sub("", clean_search_query(curr_text)).strip()
    if len(messages) <= 1:
        return clean_curr

    history_text = " ".join(_extract_content_text(m) for m in messages[:-1])
    price_context = bool(re.search(r"\b(price|cost|how\s+much)\b", history_text + " " + curr_text, re.I))

    is_directive = not clean_curr or is_search_directive(clean_curr) or is_search_directive(curr_text)
    if is_directive:
        last_user_q = get_last_substantive_user_query(messages)
        if last_user_q:
            return last_user_q[:100]
        subject = extract_subject_from_history(messages)
        if subject:
            return f"{subject} retail price MSRP" if price_context else f"{subject} price"
        return clean_curr or curr_text[:100]

    has_dependent_word = bool(DEPENDENT_QUERY_PATTERN.search(clean_curr))
    non_store = [w for w in re.findall(r"\b[A-Za-z0-9]+\b", clean_curr) if not re.match(r"^(?:ebay|amazon|google|target|walmart|bestbuy|search|check|look|find|browse|listings?|sold|prices?|cost|how|what|where|or|and|for|on|in|current|online|web|the|a|an)$", w, re.I)]
    has_standalone_subject = len(non_store) >= 2 and any(w[0].isupper() or any(c.isdigit() for c in w) for w in non_store)
    is_weather = bool(re.search(r"\bweather\b", clean_curr, re.I))

    if (has_dependent_word or not has_standalone_subject) and not is_weather:
        subject = extract_subject_from_history(messages)
        if subject:
            clean_without_pronouns = re.sub(r"\b(it|this|that|these|those)\b", "", clean_curr, flags=re.IGNORECASE)
            clean_without_pronouns = re.sub(r"\s+", " ", clean_without_pronouns).strip()
            is_marketplace = bool(re.search(r"\b(ebay|amazon|target|walmart|bestbuy|listings?|retail|msrp)\b", clean_without_pronouns, re.I))
            suffix = " retail price MSRP" if price_context and not is_marketplace else ""
            res = f"{subject} {clean_without_pronouns}{suffix}".strip()
            return res[:100]

    is_marketplace = bool(re.search(r"\b(ebay|amazon|target|walmart|bestbuy|listings?|retail|msrp)\b", clean_curr, re.I))
    if price_context and not is_marketplace:
        clean_curr = f"{clean_curr} retail price MSRP"

    return clean_curr[:100]


def should_trigger_search_from_history(messages: list[dict], mode: str = "auto") -> bool:
    """Decide if web search should be triggered taking into account chat history."""
    if not messages or mode == "off":
        return False
    if mode == "on":
        return True

    curr_text = _extract_content_text(messages[-1])
    clean = AFFIRMATIVE_PREFIXES.sub("", clean_search_query(curr_text)).strip()

    from web_search import should_trigger_search
    if should_trigger_search(curr_text, mode="auto") or should_trigger_search(clean, mode="auto"):
        return True

    if len(messages) > 1 and (is_search_directive(clean) or is_search_directive(curr_text) or DEPENDENT_QUERY_PATTERN.search(clean)):
        return True

    return False

