"""Wake word detection helpers — fuzzy match for STT mis-hearings."""
from __future__ import annotations

import re

WAKE_ALIASES = frozenset(
    {
        "cassie",
        "casie",
        "cassy",
        "casey",
        "kasey",
        "kasie",
        "kassy",
        "kacie",
        "casi",
        "kasi",
    }
)


def normalize_text(text: str) -> str:
    """Lowercase and strip punctuation/spaces for comparison."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def letters_only(text: str) -> str:
    return re.sub(r"[^a-zA-Z]", "", text).lower()


def is_wake_word(text: str) -> bool:
    """Return True if text contains the wake word (handles spaced letters)."""
    if not text or not text.strip():
        return False

    norm = normalize_text(text)
    if norm in WAKE_ALIASES:
        return True

    # Spaced letters: "K A S IE", "C A S S I E"
    compact = letters_only(text)
    if compact in WAKE_ALIASES:
        return True

    # Substring match in compact form
    for alias in WAKE_ALIASES:
        if alias in compact or compact.startswith(alias[:4]):
            return True

    # Token-based: first word sounds like wake word
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    if tokens:
        first = normalize_text(tokens[0])
        if first in WAKE_ALIASES:
            return True
        if len(tokens) >= 2:
            joined = normalize_text("".join(tokens[:2]))
            if joined in WAKE_ALIASES:
                return True

    return False


def extract_command(text: str) -> str:
    """Remove wake word prefix and return the user's command."""
    if not text:
        return ""

    # Try to strip wake word from start (various forms)
    patterns = [
        r"^(?:c\s*a\s*s\s*s?\s*i?\s*e|c\s*a\s*s\s*i\s*e|k\s*a\s*s?\s*i?\s*e)\s*[,:\-]?\s*",
        r"^(?:cassie|casie|cassy|casey|kasey|kasie|kassy|kacie|casi|kasi)\s*[,:\-]?\s*",
    ]
    remainder = text.strip()
    for pat in patterns:
        remainder = re.sub(pat, "", remainder, flags=re.IGNORECASE)

    if remainder == text.strip() and is_wake_word(text):
        # Wake word only or embedded — try splitting on comma
        parts = re.split(r"[,:\-]\s*", text, maxsplit=1)
        if len(parts) > 1:
            return parts[1].strip()
        # Remove first token if it's the wake word
        tokens = text.split()
        if tokens and is_wake_word(tokens[0]):
            return " ".join(tokens[1:]).strip()

    return remainder.strip()


# Aliases used by older Pi patches
has_wake_word = is_wake_word
strip_wake_word = extract_command
