import re
import config

# Matches patterns like: "pg:100", "pg 100", "page 100", "p. 100", "p:100", "பக்கம் 100"
PAGE_REGEX = re.compile(
    r"(?:\b(?:pg|page|p|பக்கம்)\s*[:.\-]?\s*(\d+)\b)",
    re.IGNORECASE,
)

# Noise words to strip when isolating the clean topic or page query
STOP_WORDS = re.compile(
    r"\b(explain|what\s+is|define|about|tell\s+me|in|on|from|the|of|विवरण|விளக்கு|விளக்குக)\b",
    re.IGNORECASE,
)


def parse_query(raw_query: str) -> dict:
    """
    Parse a student query into:
      - page: int or None
      - subject: canonical subject string ('science', 'maths', ...) or None
      - topic: cleaned topic string
    """
    text = (raw_query or "").strip()

    # 1. Detect page number via regex
    page_num = None
    page_match = PAGE_REGEX.search(text)
    if page_match:
        page_num = int(page_match.group(1))
        # Remove the matched page expression from the working text
        text = text[: page_match.start()] + " " + text[page_match.end() :]

    # 2. Detect subject keyword (English or Tamil alias)
    detected_subject = None
    for canonical, aliases in config.SUBJECT_ALIASES.items():
        # Sort aliases longest-first so multi-word phrases match before short tokens
        for alias in sorted(aliases, key=len, reverse=True):
            pattern = re.compile(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", re.IGNORECASE)
            if pattern.search(text):
                detected_subject = canonical
                text = pattern.sub(" ", text, count=1)
                break
        if detected_subject:
            break

    # 3. Clean remaining topic words
    topic = STOP_WORDS.sub(" ", text)
    topic = re.sub(r"[,:;?!.]+", " ", topic)
    topic = re.sub(r"\s+", " ", topic).strip()

    return {
        "page": page_num,
        "subject": detected_subject,
        "topic": topic,
    }


if __name__ == "__main__":
    # Quick sanity check
    for sample in ["explain pg:100", "page 100", "science pg:45", "reflex action", "science Ohm's law"]:
        print(f"{sample!r:22} -> {parse_query(sample)}")
