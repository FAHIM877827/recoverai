# src/validators.py
"""
Guardrails for LLM-generated recovery messages.

Every message the LLM produces is checked here BEFORE it's allowed to reach
a customer. If any check fails, the caller should fall back to the safe
template — never send an unvalidated LLM message.

This is the deterministic boundary around a generative step: the LLM decides
*wording*, this module decides *whether that wording is allowed out the door*.
"""

# Words/phrases that should never appear in a payment recovery message —
# false promises, compliance risk, or manipulative urgency.
FORBIDDEN_TERMS = [
    "guaranteed", "100% refund", "risk-free", "free money",
    "no need to pay", "act now or lose", "final warning",
    "congratulations", "you've won", "click immediately",
    "urgent!!!", "act immediately",
]

CHANNEL_LIMITS = {
    "sms": {"max_chars": 160},      # standard SMS segment limit, a little headroom over the 150 we prompt for
    "email": {"max_words": 120},    # some headroom over the 80-word prompt target
}


def validate_message(message: str, channel: str) -> tuple[bool, str]:
    """
    Validate an LLM-generated recovery message before it's allowed to send.

    Returns (is_valid, reason). reason is "" when valid, otherwise a short
    machine-readable code explaining what failed (useful for logging/audit).
    """
    if not message or not message.strip():
        return False, "empty_message"

    # Must contain the retry link placeholder — a message with no clear
    # action for the customer to take defeats the purpose.
    if "[LINK]" not in message:
        return False, "missing_link_placeholder"

    # Forbidden terms check (case-insensitive)
    lowered = message.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in lowered:
            return False, f"forbidden_term:{term}"

    # Channel-specific length bounds
    limits = CHANNEL_LIMITS.get(channel, {})
    if "max_chars" in limits and len(message) > limits["max_chars"]:
        return False, f"too_long_chars:{len(message)}"
    if "max_words" in limits:
        word_count = len(message.split())
        if word_count > limits["max_words"]:
            return False, f"too_long_words:{word_count}"

    return True, ""