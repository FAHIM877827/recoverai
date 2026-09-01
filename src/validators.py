"""
Deterministic guardrails for LLM-generated recovery messages.

The LLM is responsible only for wording.
RecoverAI policy decides whether a nudge is allowed.
This validator decides whether the generated message is safe to use.
"""

import re


FORBIDDEN_TERMS = [
    "guaranteed",
    "100% refund",
    "risk-free",
    "free money",
    "no need to pay",
    "act now or lose",
    "final warning",
    "congratulations",
    "you've won",
    "click immediately",
    "urgent!!!",
    "act immediately",
    "payment approved",
    "payment successful",
]


SENSITIVE_PATTERNS = [
    r"\botp\b",
    r"\bcvv\b",
    r"\bpan\b",
    r"\bcard\s*number\b",
    r"\bbank\s*account\s*number\b",
    r"\baccount\s*number\b",
]


COERCIVE_TERMS = [
    "threat",
    "legal action",
    "police",
    "penalty",
    "fine",
    "account will be closed",
    "account will be blocked",
]


CHANNEL_LIMITS = {
    "sms": {"max_chars": 320},
    "email": {"max_words": 120},
}


def validate_message(
    message: str,
    channel: str,
    customer_name: str | None = None,
    amount: float | None = None,
    recovery_link: str | None = None,
    policy_action: str | None = None,
    do_not_contact: bool = False,
) -> tuple[bool, str]:
    """
    Validate an LLM-generated recovery message.

    Returns:
        (True, "") when every check passes.
        (False, reason) when any safety check fails.
    """

    # 1. Empty message
    if not message or not message.strip():
        return False, "empty_message"

    # 2. Policy must explicitly allow a nudge
    if policy_action != "send_nudge":
        return False, "policy_action_not_allowed"

    # 3. Customer opt-out
    if do_not_contact:
        return False, "customer_opted_out"

    # 4. Recovery link must exist
    if not recovery_link:
        return False, "recovery_link_not_generated"

    # Message must contain the exact RecoverAI-generated link
    if recovery_link not in message:
        return False, "recovery_link_missing"

    lowered = message.lower()

    # 5. Amount must match transaction amount
    if amount is not None:
        amount_text = f"{amount:.2f}"

        # Normalize commas so ₹1,299.00 and ₹1299.00 are both detectable
        normalized_message = message.replace(",", "")

        if amount_text not in normalized_message:
            return False, "amount_mismatch"

    # 6. Sensitive payment information
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, lowered):
            return False, f"sensitive_data:{pattern}"

    # 7. Forbidden / manipulative language
    for term in FORBIDDEN_TERMS:
        if term.lower() in lowered:
            return False, f"forbidden_term:{term}"

    # 8. Coercive or threatening language
    for term in COERCIVE_TERMS:
        if term.lower() in lowered:
            return False, f"coercive_language:{term}"

    # 9. Channel-specific limits
    limits = CHANNEL_LIMITS.get(channel)

    if not limits:
        return False, "unsupported_channel"

    if "max_chars" in limits:
        if len(message) > limits["max_chars"]:
            return False, f"too_long_chars:{len(message)}"

    if "max_words" in limits:
        word_count = len(message.split())

        if word_count > limits["max_words"]:
            return False, f"too_long_words:{word_count}"

    # Everything passed
    return True, ""