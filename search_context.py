"""
Multi-turn context-aware search query resolver.
Resolves pronouns ('it', 'this'), continuation follow-ups ('And?', 'Price?'),
and extracts primary subject entities from conversation history.
"""
import re

CONTINUATION_PATTERN = re.compile(
    r"^(and|so|results?|anything|what\s+is\s+it|what\s+about\s+it|did\s+you\s+find\s+(?:it|anything)?)\??$",
    re.IGNORECASE,
)

DEPENDENT_QUERY_PATTERN = re.compile(
    r"\b(it|this|that|these|those|its|price|cost|how\s+much|specs|specifications|features|buy|where\s+to\s+buy|release\s+date|released|who\s+made\s+it)\b",
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

QUERY_STRIP_PREFIXES = [
    r"^(?:can\s+you\s+)?(?:please\s+)?search\s+(?:the\s+)?(?:web|internet|google|ddg)?\s*(?:for\s+)?",
    r"^(?:please\s+)?look\s+up\s+",
    r"^(?:please\s+)?find\s+(?:me\s+)?(?:information\s+about\s+)?",
]


def clean_search_query(text: str) -> str:
    """Clean user prompt to extract focused search keywords (max 100 chars)."""
    clean = text.strip()
    for prefix in QUERY_STRIP_PREFIXES:
        clean = re.sub(prefix, "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"[\r\n\t\x00-\x1f]+", " ", clean).strip()
    return clean[:100].strip()


IGNORE_WORDS = re.compile(
    r"^(?:this|that|what|when|where|which|who|how|is|are|was|were|the|a|an|based|here|there|i|you|we|they|welcome|please)\b",
    re.IGNORECASE,
)


def extract_named_entities(text: str) -> list[str]:
    """Extract consecutive tokens containing uppercase letters or digits."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\.-]+\b", text)
    entities = []
    curr = []
    for t in tokens:
        if any(c.isupper() or c.isdigit() for c in t):
            curr.append(t)
        else:
            if curr:
                entities.append(" ".join(curr))
                curr = []
    if curr:
        entities.append(" ".join(curr))
    return entities


def extract_subject_from_history(messages: list[dict]) -> str:
    """Extract primary named entity or topic from recent conversation turns."""
    for m in reversed(messages[:-1]):
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"
            )
        if not content:
            continue
        search_m = re.search(
            r"(?:search\s+for|checking\s+price\s+for|looking\s+up)\s+[\'\"]?([a-zA-Z0-9\s]+?)(?:price|[\'\"]|\.|\,|$)",
            content,
            re.I,
        )
        if search_m:
            subj = search_m.group(1).strip()
            if len(subj) > 3 and not DATE_MONTH_IGNORE.match(subj):
                return subj
        entities = extract_named_entities(content)
        if entities:
            filtered = [
                e for e in entities
                if not DATE_MONTH_IGNORE.match(e) and not IGNORE_WORDS.match(e) and len(e) > 2
            ]
            if filtered:
                return max(filtered, key=len)
        bolds = re.findall(r"\*\*([^*]+)\*\*", content)
        if bolds:
            clean_bolds = [re.sub(r"[^a-zA-Z0-9\s]", " ", b).strip() for b in bolds]
            clean_bolds = [
                b for b in clean_bolds
                if 3 < len(b) < 50 and not DATE_MONTH_IGNORE.match(b) and not IGNORE_WORDS.match(b)
            ]
            if clean_bolds:
                return clean_bolds[0]
    return ""


def resolve_contextual_query(messages: list[dict]) -> str:
    """Resolve pronouns, follow-ups, and missing subjects across conversation history."""
    if not messages:
        return ""
    last_msg = messages[-1].get("content", "")
    if isinstance(last_msg, list):
        curr_text = " ".join(
            item.get("text", "") for item in last_msg if isinstance(item, dict) and item.get("type") == "text"
        )
    else:
        curr_text = str(last_msg)

    clean_curr = clean_search_query(curr_text)
    clean_curr = AFFIRMATIVE_PREFIXES.sub("", clean_curr).strip()

    if len(messages) <= 1:
        return clean_curr

    if CONTINUATION_PATTERN.match(clean_curr) or clean_curr in ("?", "..."):
        subject = extract_subject_from_history(messages)
        return f"{subject} price".strip() if subject else clean_curr

    has_dependent_word = bool(DEPENDENT_QUERY_PATTERN.search(clean_curr))
    has_own_caps = bool(re.findall(r"\b[A-Z0-9][a-zA-Z0-9]*(?:\s+[A-Z0-9][a-zA-Z0-9]*)+\b", curr_text))
    is_weather = bool(re.search(r"\bweather\b", clean_curr, re.I))

    if has_dependent_word and not has_own_caps and not is_weather:
        subject = extract_subject_from_history(messages)
        if subject:
            clean_without_pronouns = re.sub(
                r"\b(it|this|that|these|those)\b", "", clean_curr, flags=re.IGNORECASE
            )
            clean_without_pronouns = re.sub(r"\s+", " ", clean_without_pronouns).strip()
            suffix = " retail price MSRP" if re.search(r"\b(price|cost|how\s+much)\b", clean_curr, re.I) else ""
            res = f"{subject} {clean_without_pronouns}{suffix}".strip()
            return res[:100]

    if re.search(r"\b(price|cost|how\s+much)\b", clean_curr, re.I) and "msrp" not in clean_curr.lower():
        clean_curr = f"{clean_curr} retail price MSRP"

    return clean_curr[:100]


def should_trigger_search_from_history(messages: list[dict], mode: str = "auto") -> bool:
    """Decide if web search should be triggered taking into account chat history."""
    if not messages:
        return False
    if mode == "off":
        return False
    if mode == "on":
        return True

    last_msg = messages[-1].get("content", "")
    curr_text = last_msg if isinstance(last_msg, str) else " ".join(
        item.get("text", "") for item in last_msg if isinstance(item, dict) and item.get("type") == "text"
    )
    clean = clean_search_query(curr_text)
    clean = AFFIRMATIVE_PREFIXES.sub("", clean).strip()

    from web_search import should_trigger_search
    if should_trigger_search(clean, mode="auto"):
        return True

    if CONTINUATION_PATTERN.match(clean) or clean in ("?", "..."):
        if len(messages) > 1:
            prev_content = str(messages[-2].get("content", ""))
            if re.search(r"\b(search|price|cost|weather|news|specs|finding)\b", prev_content, re.I):
                return True

    if DEPENDENT_QUERY_PATTERN.search(clean) and len(messages) > 1:
        return True

    return False
